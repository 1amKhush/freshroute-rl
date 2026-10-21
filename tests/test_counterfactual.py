import unittest

from freshroute.agent import QAgent
from freshroute.counterfactual import branch_actions, snapshot_hash
from freshroute.environment import Config, ReplicaEnv


class BranchTests(unittest.TestCase):
    def test_branches_replay_exactly_and_preserve_parent(self):
        env = ReplicaEnv(); env.reset(seed=42)
        env.inject_fault(kind='lag', replica=0, value=300)
        before = snapshot_hash(env)
        agent = QAgent()
        first = branch_actions(env, agent)
        self.assertEqual(first, branch_actions(env, agent))
        self.assertEqual(snapshot_hash(env), before)
        action = agent.act(env.observe())
        _, reward, _, _, info = env.step(action)
        self.assertEqual(first['branches'][action]['first_outcome'], info)
        self.assertEqual(first['branches'][action]['immediate_reward'], reward)
        self.assertEqual(agent.table, {})

    def test_horizon_stops_at_truncation(self):
        env = ReplicaEnv(Config(episode_steps=1)); env.reset()
        result = branch_actions(env, QAgent(), horizon=30)
        self.assertEqual(result['horizon'], 1)
        self.assertTrue(all(len(branch['steps']) == 1 for branch in result['branches']))
