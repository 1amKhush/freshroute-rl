"""Seeded, single-shard simulator. Reads take snapshots at dispatch time."""

from bisect import bisect_right
from dataclasses import asdict, dataclass
import math
import random

from .scenarios import BUILTINS, load_scenario


REGIONS = ("Mumbai", "Frankfurt", "Virginia")
LEADER = 1
RTT_MS = ((12, 120, 215), (120, 12, 95), (215, 95, 12))
SERVICE_MS = (14, 22, 14)
REQUESTS = (
    ("latest", 0, 240),
    ("bounded", 100, 180),
    ("relaxed", 500, 140),
)
SCENARIOS = tuple(BUILTINS)


@dataclass(frozen=True)
class Config:
    episode_steps: int = 160
    arrival_interval_ms: int = 12
    latency_weight: float = 1.0
    freshness_weight: float = 2.0
    failure_weight: float = 4.0

    def __post_init__(self):
        if any(type(value) is not int or value < 1 for value in (
            self.episode_steps, self.arrival_interval_ms
        )):
            raise ValueError("episode_steps and arrival_interval_ms must be positive integers")
        if any(not 0 <= value < float("inf") for value in (
            self.latency_weight, self.freshness_weight, self.failure_weight
        )):
            raise ValueError("reward weights must be finite and nonnegative")


class ReplicaEnv:
    """Three direct-read actions; no retries, quorum reads, or leader election.

    Uses reset/step tuple conventions but is not yet a gymnasium.Env.
    Episode limits truncate a continuing routing process.
    """

    def __init__(self, config: Config | None = None, scenario: str = "balanced"):
        self.config = config or Config()
        self.scenario_spec = load_scenario(scenario)
        self.scenario = self.scenario_spec.name
        self._ready = False

    def reset(self, *, seed: int = 0):
        self.rng = random.Random(seed)
        self.seed = seed
        self.step_index = 0
        self.clock_ms = 0
        self.commits = [0]
        self.applied = [0, 0, 0]
        self.queues = [0.0, 0.0, 0.0]
        self.online = [True, True, True]
        self._natural_online = [True, True, True]
        self.link_lag = list(self.scenario_spec.follower_delay_ms)
        self._base_link_lag = list(self.link_lag)
        self.fault_events = []
        self.client = self.rng.randrange(3)
        self.request_class = self.rng.randrange(3)
        self._ready = True
        return self.observe(), {"seed": seed, "scenario": self.scenario}

    def active_faults(self, replica):
        return [event for event in self.fault_events if event['replica'] == replica
                and event['start_step'] <= self.step_index < event['end_step']]

    def inject_fault(self, *, kind, replica, duration_steps=20, value=100):
        if not self._ready or self.step_index >= self.config.episode_steps:
            raise ValueError('faults require an active episode')
        if kind not in ('outage', 'lag', 'load', 'restore') or type(replica) is not int or replica not in range(3):
            raise ValueError('unknown fault kind or replica')
        if type(duration_steps) is not int or not 1 <= duration_steps <= 160 or not math.isfinite(value) or not 0 <= value <= 1000:
            raise ValueError('fault duration must be 1..160 steps and value must be 0..1000 ms')
        if kind == 'lag' and replica == LEADER:
            raise ValueError('the write leader has no follower replay lag')
        if len(self.fault_events) >= 100:
            raise ValueError('at most 100 fault events per episode')
        if kind == 'restore':
            for event in self.active_faults(replica):
                event['end_step'] = self.step_index
        event = {'schema_version': 1, 'kind': kind, 'replica': replica,
                 'start_step': self.step_index, 'end_step': self.step_index + duration_steps, 'value': value}
        self.fault_events.append(event)
        if kind == 'load':
            self.queues[replica] += value
        active = self.active_faults(replica)
        self.online[replica] = self._natural_online[replica] and not any(item['kind'] == 'outage' for item in active)
        self.link_lag[replica] = self._base_link_lag[replica] + sum(item['value'] for item in active if item['kind'] == 'lag')
        return event

    def observe(self):
        if not self._ready:
            raise RuntimeError("call reset before using the environment")
        name, tolerance, deadline = REQUESTS[self.request_class]
        latest = len(self.commits) - 1
        return {
            "step": self.step_index,
            "clock_ms": self.clock_ms,
            "scenario": self.scenario,
            "client_region": self.client,
            "request_class": name,
            "freshness_tolerance_ms": tolerance,
            "deadline_ms": deadline,
            "leader_version": latest,
            "replicas": [
                {
                    "id": i, "region": REGIONS[i], "is_leader": i == LEADER,
                    "online": self.online[i],
                    "rtt_ms": RTT_MS[self.client][i],
                    "queue_ms": self.queues[i],
                    "replication_delay_ms": self.link_lag[i],
                    "applied_version": self.applied[i],
                    "version_lag": latest - self.applied[i],
                    "staleness_ms": self.commits[-1] - self.commits[self.applied[i]],
                }
                for i in range(3)
            ],
        }

    def step(self, action: int):
        if not self._ready:
            raise RuntimeError("call reset before using the environment")
        if self.step_index >= self.config.episode_steps:
            raise RuntimeError("episode truncated; call reset")
        if type(action) is not int or action not in range(3):
            raise ValueError("action must be an integer replica ID in [0, 2]")
        before = self.observe()
        replica = before["replicas"][action]
        deadline = before["deadline_ms"]
        # A snapshot is taken at admission. Network/service completion is analytical.
        raw_latency = replica["rtt_ms"] + replica["queue_ms"] + SERVICE_MS[action]
        unavailable = not replica["online"]
        timeout = not unavailable and raw_latency > deadline
        transport_ok = not (unavailable or timeout)
        response_ms = float(deadline if unavailable else min(raw_latency, deadline))
        excess = max(0, replica["staleness_ms"] - before["freshness_tolerance_ms"])
        stale = transport_ok and excess > 0
        terms = {
            "latency": -self.config.latency_weight * response_ms / deadline,
            "freshness": -self.config.freshness_weight * min(
                excess / max(before["freshness_tolerance_ms"], 50), 2
            ) if transport_ok else 0.0,
            "failure": -self.config.failure_weight if not transport_ok else 0.0,
        }
        if not unavailable:
            # Timed-out work still consumes service; it cannot silently disappear.
            self.queues[action] += SERVICE_MS[action]
        info = {
            "action": action, "replica": REGIONS[action],
            "response_ms": response_ms, "transport_ok": transport_ok,
            "unavailable": unavailable, "timeout": timeout,
            "staleness_ms": replica["staleness_ms"] if transport_ok else None,
            "version_lag": replica["version_lag"] if transport_ok else None,
            "freshness_violation": stale, "sla_met": transport_ok and not stale,
            "reward_terms": terms,
        }
        self.step_index += 1
        self._advance()
        return self.observe(), sum(terms.values()), False, (
            self.step_index >= self.config.episode_steps
        ), info

    def _advance(self):
        self.clock_ms += self.config.arrival_interval_ms
        progress = self.step_index / self.config.episode_steps
        phase = self.scenario_spec.at(progress)
        # Draw an identical exogenous frame regardless of the policy's action.
        write_draw = self.rng.random()
        client_draw = self.rng.random()
        next_client = self.rng.randrange(3)
        next_class = self.rng.randrange(3)
        frames = [(self.rng.random(), self.rng.random(), self.rng.random()) for _ in range(3)]
        for i, (availability_draw, background_draw, lag_draw) in enumerate(frames):
            faults = self.active_faults(i)
            if self.scenario == "regional-outage" and i == 0:
                self._natural_online[i] = phase.offline_replica != i
            elif phase.offline_replica == i:
                self._natural_online[i] = False
            elif self._natural_online[i]:
                self._natural_online[i] = availability_draw >= 0.002
            else:
                self._natural_online[i] = availability_draw < 0.15
            self.online[i] = self._natural_online[i] and not any(event['kind'] == 'outage' for event in faults)
            if self.online[i]:
                background_work = background_draw * phase.background_ms + sum(event['value'] for event in faults if event['kind'] == 'load')
                self.queues[i] = max(
                    0.0, self.queues[i] - self.config.arrival_interval_ms
                ) + background_work
            self._base_link_lag[i] = 0.0 if i == LEADER else (
                self.scenario_spec.follower_delay_ms[i] * phase.lag_multiplier
                + lag_draw * 30 + self.queues[i] * 0.25
            )
            self.link_lag[i] = self._base_link_lag[i] + sum(event['value'] for event in faults if event['kind'] == 'lag')
        if self.online[LEADER] and write_draw < phase.write_probability:
            self.commits.append(self.clock_ms)
        for i in range(3):
            if self.online[i]:
                cutoff = self.clock_ms - self.link_lag[i]
                visible = max(0, bisect_right(self.commits, cutoff) - 1)
                # Replication may stall but applied versions never move backwards.
                self.applied[i] = max(self.applied[i], visible)
        if client_draw < 0.06:
            self.client = next_client
        if phase.client_region is not None:
            self.client = phase.client_region
        self.request_class = next_class

    def config_dict(self):
        return asdict(self.config)
