import importlib.util
from pathlib import Path
import tempfile
import unittest


@unittest.skipUnless(importlib.util.find_spec('stable_baselines3'), 'install the rl extra')
class DQNTests(unittest.TestCase):
    def test_real_training_checkpoint_reload_and_integrity(self):
        from freshroute.dqn import DQNAgent, train_dqn
        from freshroute.environment import ReplicaEnv
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'model'
            agent = train_dqn(output=path, timesteps=200, seed=19, steps=20, eval_frequency=200, net_width=16)
            loaded = DQNAgent.load(path)
            observation, _ = ReplicaEnv().reset(seed=100_000)
            self.assertEqual(agent.values(observation), loaded.values(observation))
            self.assertEqual(agent.act(observation), loaded.act(observation))
            self.assertEqual(agent.metadata['training_steps'], 200)
            self.assertEqual(len(agent.values(observation)), 3)
            weights = path / 'model.zip'
            weights.write_bytes(weights.read_bytes() + b'corrupt')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                DQNAgent.load(path)
