"""Tabular temporal-difference Q-learning; no routing rules in the learned policy."""

import json
import math
from pathlib import Path
import random


ENCODER_VERSION = 1


def encode(observation: dict) -> str:
    """Coarse state aggregation: region, SLA, and per-replica telemetry buckets."""
    parts = [str(observation["client_region"]), observation["request_class"]]
    for replica in observation["replicas"]:
        parts.extend([
            str(int(replica["online"])),
            str(int(replica["queue_ms"] >= 30)),
            str(int(replica["staleness_ms"] > observation["freshness_tolerance_ms"])),
        ])
    return "|".join(parts)


class QAgent:
    algorithm = 'q-learning'

    def __init__(self, *, alpha: float = 0.12, gamma: float = 0.95, seed: int = 0):
        if not 0 < alpha <= 1 or not 0 <= gamma < 1:
            raise ValueError("alpha must be in (0, 1]; gamma must be in [0, 1)")
        self.alpha, self.gamma = alpha, gamma
        self.rng = random.Random(seed)
        self.table: dict[str, list[float]] = {}
        self.visits: dict[str, list[int]] = {}
        self.metadata: dict = {}

    def values(self, observation: dict) -> list[float]:
        return list(self.table.get(encode(observation), [0.0, 0.0, 0.0]))

    def act(self, observation: dict, *, epsilon: float = 0.0) -> int:
        if not 0 <= epsilon <= 1:
            raise ValueError("epsilon must be in [0, 1]")
        if epsilon and self.rng.random() < epsilon:
            return self.rng.randrange(3)
        values = self.values(observation)
        best = [i for i, value in enumerate(values) if value == max(values)]
        # Evaluation is deterministic; training breaks ties using its own RNG.
        return self.rng.choice(best) if epsilon else best[0]

    def update(self, observation, action, reward, next_observation, *, terminated=False):
        key = encode(observation)
        row = self.table.setdefault(key, [0.0, 0.0, 0.0])
        target = reward if terminated else reward + self.gamma * max(self.values(next_observation))
        row[action] += self.alpha * (target - row[action])
        counts = self.visits.setdefault(key, [0, 0, 0])
        counts[action] += 1

    def save(self, path: str | Path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1, "algorithm": "tabular-q-learning",
            "encoder_version": ENCODER_VERSION, "alpha": self.alpha, "gamma": self.gamma,
            "metadata": self.metadata, "q_table": self.table, "visits": self.visits,
        }
        path.write_text(json.dumps(payload, sort_keys=True, indent=2, allow_nan=False) + "\n")

    @classmethod
    def load(cls, path: str | Path):
        payload = json.loads(Path(path).read_text())
        if (payload.get("schema_version"), payload.get("encoder_version"), payload.get("algorithm")) != (
            1, ENCODER_VERSION, "tabular-q-learning"
        ):
            raise ValueError("unsupported checkpoint schema, encoder, or algorithm")
        agent = cls(alpha=payload["alpha"], gamma=payload["gamma"])
        table, visits = payload["q_table"], payload["visits"]
        if not isinstance(table, dict) or not isinstance(visits, dict) or table.keys() != visits.keys():
            raise ValueError("checkpoint table and visitation states must match")
        for key, values in table.items():
            counts = visits[key]
            if not isinstance(values, list) or len(values) != 3 or any(
                type(value) not in (int, float) or not math.isfinite(value) for value in values
            ):
                raise ValueError("checkpoint action values must contain three finite numbers")
            if not isinstance(counts, list) or len(counts) != 3 or any(
                type(count) is not int or count < 0 for count in counts
            ):
                raise ValueError("checkpoint visitation counts must contain three nonnegative integers")
        agent.table = payload["q_table"]
        agent.visits = payload["visits"]
        agent.metadata = payload["metadata"]
        return agent
