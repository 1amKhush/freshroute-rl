import unittest

from freshroute.environment import ReplicaEnv
from freshroute.scenarios import BUILTINS, Phase, Scenario


class ScenarioTests(unittest.TestCase):
    def test_roundtrip_and_phase_schedule(self):
        for name, scenario in BUILTINS.items():
            restored = Scenario.from_dict(scenario.to_dict())
            self.assertEqual(restored, scenario)
            a, b = ReplicaEnv(scenario=name), ReplicaEnv(scenario=restored)
            self.assertEqual(a.reset(seed=22), b.reset(seed=22))
            for step in range(160):
                self.assertEqual(a.step(step % 3), b.step(step % 3))
        self.assertEqual(BUILTINS['write-burst'].at(.4).write_probability, .85)
        self.assertEqual(BUILTINS['regional-outage'].at(.4).offline_replica, 0)

    def test_invalid_schedules_fail(self):
        for kwargs in ({'write_probability': 2}, {'background_ms': float('nan')}, {'offline_replica': 9}):
            with self.assertRaises(ValueError):
                Phase(0, **kwargs)
        with self.assertRaises(ValueError):
            Scenario('bad', phases=(Phase(.1, .6), Phase(.5, .8)))
        with self.assertRaises(ValueError):
            Scenario('bad', follower_delay_ms=(80, 5, 160))
