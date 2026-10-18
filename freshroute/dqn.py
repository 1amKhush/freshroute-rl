"""CPU DQN training with fixed validation workloads and self-describing checkpoints."""

from dataclasses import asdict
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import time

import torch
from stable_baselines3 import DQN
from stable_baselines3.common.callbacks import BaseCallback

from .environment import Config, SCENARIOS, ReplicaEnv
from .experiments import source_fingerprint, write_json
from .gym_env import ABLATIONS, OBSERVATION_VERSION, RoutingEnv, vectorize


class DQNAgent:
    algorithm = 'dqn'

    def __init__(self, model, metadata):
        self.model, self.metadata = model, metadata

    def values(self, observation):
        vector = vectorize(observation, self.metadata['ablation'])
        with torch.no_grad():
            tensor = torch.as_tensor(vector, device=self.model.device).unsqueeze(0)
            return self.model.q_net(tensor).squeeze(0).cpu().tolist()

    def act(self, observation, *, epsilon=0):
        if epsilon:
            raise ValueError('checkpoint inference is frozen and deterministic')
        values = self.values(observation)
        return max(range(3), key=values.__getitem__)

    @classmethod
    def load(cls, directory):
        directory = Path(directory)
        metadata = json.loads((directory / 'metadata.json').read_text())
        if metadata.get('algorithm') != 'dqn' or metadata.get('observation_version') != OBSERVATION_VERSION:
            raise ValueError('unsupported DQN checkpoint or observation schema')
        if metadata.get('ablation') not in ABLATIONS:
            raise ValueError('unsupported DQN observation ablation')
        weights = directory / 'model.zip'
        if hashlib.sha256(weights.read_bytes()).hexdigest() != metadata['weights_sha256']:
            raise ValueError('DQN weights checksum does not match metadata')
        torch.set_num_threads(1)
        return cls(DQN.load(weights, device='cpu'), metadata)


def validation_score(model, config, ablation, episodes=2):
    agent = DQNAgent(model, {'ablation': ablation})
    returns = []
    for scenario in SCENARIOS:
        for index in range(episodes):
            env = ReplicaEnv(config, scenario)
            observation, _ = env.reset(seed=100_000 + index)
            total = 0
            for _ in range(config.episode_steps):
                observation, reward, _, _, _ = env.step(agent.act(observation))
                total += reward
            returns.append(total / config.episode_steps)
    return sum(returns) / len(returns)


class TrainingLog(BaseCallback):
    def __init__(self, output, config, ablation, eval_frequency):
        super().__init__()
        self.output, self.config, self.ablation = output, config, ablation
        self.eval_frequency = eval_frequency
        self.episodes, self.validations = [], []
        self.best_score = float('-inf')
        self.best_step = 0

    def evaluate_checkpoint(self):
        score = validation_score(self.model, self.config, self.ablation)
        self.validations.append({'timesteps': self.num_timesteps, 'mean_reward': score})
        if score > self.best_score:
            self.best_score, self.best_step = score, self.num_timesteps
            self.model.save(self.output / 'model.zip')
        print(f'DQN step {self.num_timesteps}: validation reward {score:.3f}; best {self.best_score:.3f}', flush=True)

    def _on_step(self):
        for info in self.locals['infos']:
            if 'episode' in info:
                self.episodes.append({
                    'episode': len(self.episodes) + 1, 'timesteps': self.num_timesteps,
                    'return': info['episode']['r'], 'length': info['episode']['l'],
                    'epsilon': self.model.exploration_rate,
                })
        if self.num_timesteps % self.eval_frequency == 0:
            self.evaluate_checkpoint()
        return True


def train_dqn(*, output, timesteps=250_000, seed=7, ablation='full', gamma=.95,
              steps=160, eval_frequency=10_000, net_width=128):
    if not 0 <= seed < 100_000 or timesteps < 1 or eval_frequency < 1:
        raise ValueError('positive timesteps/eval frequency and a training seed in [0,100000) required')
    if not 0 <= gamma < 1 or ablation not in ABLATIONS:
        raise ValueError('invalid gamma or ablation')
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError('use an empty output directory to preserve earlier experiment evidence')
    output.mkdir(parents=True, exist_ok=True)
    config = Config(episode_steps=steps)
    torch.set_num_threads(1)
    env = RoutingEnv(config, scenario='mixed', ablation=ablation)
    model = DQN(
        'MlpPolicy', env, seed=seed, device='cpu', learning_rate=1e-4,
        buffer_size=100_000, learning_starts=min(5000, max(100, timesteps // 10)),
        batch_size=64, gamma=gamma, train_freq=4, gradient_steps=1,
        target_update_interval=1000, exploration_fraction=.7,
        exploration_initial_eps=1, exploration_final_eps=.05,
        policy_kwargs={'net_arch': [net_width, net_width]}, verbose=0,
    )
    callback = TrainingLog(output, config, ablation, eval_frequency)
    started = time.monotonic()
    model.learn(total_timesteps=timesteps, callback=callback)
    if not callback.validations or callback.validations[-1]['timesteps'] != model.num_timesteps:
        callback.evaluate_checkpoint()
    metadata = {
        'schema_version': 1, 'algorithm': 'dqn', 'observation_version': OBSERVATION_VERSION,
        'ablation': ablation, 'gamma': gamma, 'agent_seed': seed,
        'training_seed_range': [0, 100_000], 'selection_split': 'validation',
        'selection_seeds': [100_000, 100_001], 'scenario': 'mixed', 'config': asdict(config),
        'training_steps': model.num_timesteps, 'checkpoint_steps': callback.best_step,
        'best_validation_mean_reward': callback.best_score,
        'training_seconds': time.monotonic() - started,
        'source_sha256': source_fingerprint(), 'python': platform.python_version(),
        'packages': {name: importlib.metadata.version(name) for name in ('torch', 'stable-baselines3', 'gymnasium', 'numpy')},
        'weights_sha256': hashlib.sha256((output / 'model.zip').read_bytes()).hexdigest(),
        'hyperparameters': {'learning_rate': 1e-4, 'buffer_size': 100_000, 'batch_size': 64,
                            'target_update_interval': 1000, 'net_arch': [net_width, net_width]},
        'limitations': 'synthetic simulator; aggregated telemetry; validation-selected checkpoint',
    }
    write_json(output / 'metadata.json', metadata)
    write_json(output / 'training.json', {'episodes': callback.episodes, 'validation': callback.validations})
    env.close()
    return DQNAgent.load(output)
