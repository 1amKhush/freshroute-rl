import json
from pathlib import Path
import unittest

from freshroute.environment import ReplicaEnv


class FaultTests(unittest.TestCase):
    def test_outage_duration_and_restore(self):
        env = ReplicaEnv(); env.reset(seed=23)
        env.inject_fault(kind='outage', replica=0, duration_steps=2)
        self.assertFalse(env.observe()['replicas'][0]['online'])
        self.assertTrue(env.step(0)[4]['unavailable'])
        self.assertFalse(env.observe()['replicas'][0]['online'])
        env.step(1)
        self.assertTrue(env.observe()['replicas'][0]['online'])
        env.inject_fault(kind='outage', replica=0)
        env.inject_fault(kind='restore', replica=0)
        self.assertTrue(env.observe()['replicas'][0]['online'])

    def test_load_and_lag_change_actual_transitions_without_consuming_rng(self):
        healthy, faulted = ReplicaEnv(), ReplicaEnv()
        healthy.reset(seed=11); faulted.reset(seed=11)
        faulted.inject_fault(kind='load', replica=0, value=100)
        faulted.inject_fault(kind='lag', replica=0, value=300)
        for _ in range(15):
            healthy.step(1); faulted.step(1)
        self.assertEqual(healthy.rng.getstate(), faulted.rng.getstate())
        self.assertGreater(faulted.queues[0], healthy.queues[0])
        self.assertGreater(faulted.observe()['replicas'][0]['version_lag'], healthy.observe()['replicas'][0]['version_lag'])
        with self.assertRaises(ValueError):
            faulted.inject_fault(kind='lag', replica=1)

    def test_no_faults_preserve_original_q_replay(self):
        from freshroute.agent import QAgent
        from freshroute.experiments import rollout
        root = Path(__file__).resolve().parents[1] / 'artifacts/demo'
        original = [json.loads(line) for line in (root/'decisions.jsonl').read_text().splitlines()]
        self.assertEqual(rollout(QAgent.load(root/'q-agent.json'), seed=110000, scenario='regional-outage'), original)
