import importlib.util
import unittest


@unittest.skipUnless(importlib.util.find_spec('gymnasium'), 'install the rl extra')
class GymTests(unittest.TestCase):
    def test_checker_and_bounds(self):
        from gymnasium.utils.env_checker import check_env
        from freshroute.gym_env import RoutingEnv
        for scenario in ('balanced', 'write-burst', 'regional-outage', 'traffic-shift', 'mixed'):
            env = RoutingEnv(scenario=scenario)
            check_env(env, skip_render_check=True)
            observation, _ = env.reset(seed=43)
            self.assertTrue(env.observation_space.contains(observation))
            for index in range(160):
                observation, _, terminated, truncated, _ = env.step(index % 3)
                self.assertTrue(env.observation_space.contains(observation))
                self.assertFalse(terminated)
            self.assertTrue(truncated)

    def test_adapter_matches_core_and_ablation_channels(self):
        from freshroute.environment import ReplicaEnv
        from freshroute.gym_env import RoutingEnv, vectorize
        core, wrapped = ReplicaEnv(), RoutingEnv()
        observation, _ = core.reset(seed=12)
        actual, _ = wrapped.reset(seed=12)
        self.assertEqual(vectorize(observation).tolist(), actual.tolist())
        for action in (0, 1, 2, 0):
            following, reward, terminated, truncated, info = core.step(action)
            result = wrapped.step(action)
            self.assertEqual(result[0].tolist(), vectorize(following).tolist())
            self.assertEqual(result[1:], (reward, terminated, truncated, info))
        for start in (8, 14, 20):
            self.assertTrue(all(vectorize(following, 'no-freshness')[start + i] == 0 for i in (3, 4, 5)))
            self.assertEqual(vectorize(following, 'no-queue')[start + 2], 0)
