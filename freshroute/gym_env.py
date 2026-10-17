"""Gymnasium adapter with fixed bounded observations and explicit time limits."""

import gymnasium as gym
import numpy as np

from .environment import Config, REQUESTS, SCENARIOS, ReplicaEnv


OBSERVATION_VERSION = 1
ABLATIONS = ("full", "no-freshness", "no-queue")


def vectorize(observation, ablation="full"):
    if ablation not in ABLATIONS:
        raise ValueError(f"unknown observation ablation: {ablation}")
    values = [float(observation['client_region'] == i) for i in range(3)]
    values += [float(observation['request_class'] == request[0]) for request in REQUESTS]
    values += [observation['freshness_tolerance_ms'] / 500, observation['deadline_ms'] / 240]
    for replica in observation['replicas']:
        queue, stale = replica['queue_ms'], replica['staleness_ms']
        versions, delay = replica['version_lag'], replica['replication_delay_ms']
        values += [
            float(replica['online']), replica['rtt_ms'] / 250,
            queue / (queue + 100) if ablation != 'no-queue' else 0,
            stale / (stale + 200) if ablation != 'no-freshness' else 0,
            versions / (versions + 10) if ablation != 'no-freshness' else 0,
            delay / (delay + 200) if ablation == 'full' else 0,
        ]
    return np.asarray(values, dtype=np.float32)


class RoutingEnv(gym.Env):
    metadata = {'render_modes': []}

    def __init__(self, config=None, scenario='balanced', ablation='full'):
        if ablation not in ABLATIONS:
            raise ValueError(f"unknown ablation: {ablation}")
        self.config = config or Config()
        self.scenario, self.ablation = scenario, ablation
        self.observation_space = gym.spaces.Box(0, 1, shape=(26,), dtype=np.float32)
        self.action_space = gym.spaces.Discrete(3)
        self.env = None

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        # All mixed-scenario selection and derived episode seeds use Gym's RNG.
        scenario = SCENARIOS[int(self.np_random.integers(len(SCENARIOS)))] if self.scenario == 'mixed' else self.scenario
        episode_seed = int(seed) if seed is not None else int(self.np_random.integers(0, 100_000))
        self.env = ReplicaEnv(self.config, scenario)
        observation, info = self.env.reset(seed=episode_seed)
        return vectorize(observation, self.ablation), info

    def step(self, action):
        if self.env is None:
            raise RuntimeError('reset before step')
        observation, reward, terminated, truncated, info = self.env.step(int(action))
        return vectorize(observation, self.ablation), reward, terminated, truncated, info
