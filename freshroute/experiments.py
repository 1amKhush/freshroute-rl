"""Training, frozen evaluation, and structured decision replay artifacts."""

from collections import Counter
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import platform
import random
import statistics

from .agent import QAgent, encode
from .environment import Config, LEADER, REGIONS, SCENARIOS, ReplicaEnv


def source_fingerprint() -> str:
    digest = hashlib.sha256()
    for path in sorted(Path(__file__).parent.glob("*.py")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def train(*, episodes=1200, steps=160, seed=7, scenario="mixed"):
    if episodes < 1 or seed < 0 or seed + episodes > 100_000:
        raise ValueError("use positive episodes and training seeds entirely in [0, 100000)")
    if scenario not in (*SCENARIOS, "mixed"):
        raise ValueError(f"unknown training scenario: {scenario}")
    agent = QAgent(seed=seed)
    curve = []
    config = Config(episode_steps=steps)
    for episode in range(episodes):
        selected = SCENARIOS[episode % len(SCENARIOS)] if scenario == "mixed" else scenario
        env = ReplicaEnv(config, selected)
        observation, _ = env.reset(seed=seed + episode)
        epsilon = max(0.05, 1 - 0.95 * episode / max(1, episodes * 0.8))
        total, met = 0.0, 0
        while True:
            action = agent.act(observation, epsilon=epsilon)
            following, reward, terminated, truncated, info = env.step(action)
            # An external time limit is not an absorbing terminal state.
            agent.update(observation, action, reward, following, terminated=terminated)
            total += reward
            met += int(info["sla_met"])
            observation = following
            if terminated or truncated:
                break
        curve.append({
            "episode": episode + 1, "seed": seed + episode, "scenario": selected,
            "epsilon": epsilon, "return": total, "sla_rate": met / steps,
        })
    agent.metadata = {
        "purpose": "initial simulator demonstration; not release-qualified",
        "training_seed_start": seed, "training_seed_end_exclusive": seed + episodes,
        "agent_seed": seed, "episodes": episodes, "training_steps": episodes * steps,
        "scenario": scenario, "config": asdict(config), "python": platform.python_version(),
        "source_sha256": source_fingerprint(),
        "observation_note": "coarse state aggregation; not a complete Markov state",
    }
    return agent, curve


def policy_action(policy, observation, rng, agent):
    if policy in ("q-learning", "dqn"):
        return agent.act(observation)
    if policy == "leader":
        return LEADER
    if policy == "nearest":
        return min(range(3), key=lambda i: observation["replicas"][i]["rtt_ms"])
    if policy == "random":
        return rng.randrange(3)
    raise ValueError(f"unknown policy: {policy}")


def rollout(agent, *, policy=None, seed=100_000, scenario="balanced", config=None):
    policy = policy or agent.algorithm
    config = config or Config(**agent.metadata["config"])
    env = ReplicaEnv(config, scenario)
    observation, _ = env.reset(seed=seed)
    rng = random.Random(seed + 10_000_000)
    records = []
    while True:
        action = policy_action(policy, observation, rng, agent)
        following, reward, terminated, truncated, info = env.step(action)
        key = encode(observation)
        records.append({
            "schema_version": 1, "policy": policy, "seed": seed, "scenario": scenario,
            "step": len(records), "observation": observation, "state_key": key,
            "q_values": agent.values(observation) if policy in ("q-learning", "dqn") else None,
            "state_seen_in_training": key in agent.table if policy == "q-learning" else None,
            "action_training_visits": list(agent.visits.get(key, [0, 0, 0]))
            if policy == "q-learning" else None,
            "action": action, "reward": reward, "outcome": info,
            "next_observation": following, "terminated": terminated, "truncated": truncated,
        })
        observation = following
        if terminated or truncated:
            return records


def summarize(records):
    count = len(records)
    outcomes = [row["outcome"] for row in records]
    successes = [row for row in outcomes if row["transport_ok"]]
    success_latencies = sorted(row["response_ms"] for row in successes)
    requests = Counter(REGIONS[row["action"]] for row in records)
    q_records = [row for row in records if row["policy"] == "q-learning"]
    return {
        "requests": count,
        "mean_reward": statistics.fmean(row["reward"] for row in records),
        "mean_response_ms_including_failures": statistics.fmean(row["response_ms"] for row in outcomes),
        "p95_success_response_ms": success_latencies[max(0, (95 * len(success_latencies) + 99) // 100 - 1)]
        if successes else None,
        "availability_rate": len(successes) / count,
        "sla_rate": sum(row["sla_met"] for row in outcomes) / count,
        "freshness_violation_rate_among_responses": sum(row["freshness_violation"] for row in successes)
        / len(successes) if successes else None,
        "mean_staleness_ms_among_responses": statistics.fmean(row["staleness_ms"] for row in successes)
        if successes else None,
        "timeout_rate": sum(row["timeout"] for row in outcomes) / count,
        "unavailable_rate": sum(row["unavailable"] for row in outcomes) / count,
        "unseen_state_rate": sum(not row["state_seen_in_training"] for row in q_records)
        / len(q_records) if q_records else None,
        "routes": {region: requests[region] for region in REGIONS},
    }


def evaluate(agent, *, episodes=8, seed=100_000):
    if episodes < 1 or seed < 100_000 or seed + episodes > 200_000:
        raise ValueError("validation seeds must stay in [100000, 200000)")
    results = []
    for scenario in SCENARIOS:
        for policy in (agent.algorithm, "nearest", "leader", "random"):
            rows = []
            per_episode = []
            for index in range(episodes):
                records = rollout(agent, policy=policy, seed=seed + index, scenario=scenario)
                rows.extend(records)
                per_episode.append({"seed": seed + index, **summarize(records)})
            results.append({"scenario": scenario, "policy": policy, **summarize(rows), "episodes": per_episode})
    return {
        "schema_version": 1, "split": "validation", "seed_start": seed,
        "episodes_per_scenario": episodes,
        "comparison_note": "common exogenous seeds; each policy evolves its own queues",
        "model_metadata": agent.metadata, "evaluation_source_sha256": source_fingerprint(),
        "results": results,
    }
