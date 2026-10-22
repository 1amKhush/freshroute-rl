import hashlib
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ReleaseTests(unittest.TestCase):
    def test_frozen_model_and_trace_integrity(self):
        root = ROOT / 'artifacts/releases'
        frozen = json.loads((root/'frozen.json').read_text())
        manifest = json.loads((root/'decisions.manifest.json').read_text())
        for model in frozen['models']:
            self.assertEqual(hashlib.sha256((ROOT/model['path']/'model.zip').read_bytes()).hexdigest(), model['weights_sha256'])
        self.assertEqual(hashlib.sha256((root/'dqn/model.zip').read_bytes()).hexdigest(), manifest['model_sha256'])
        self.assertEqual(hashlib.sha256((root/'decisions.jsonl').read_bytes()).hexdigest(), manifest['trace_sha256'])

    @unittest.skipUnless(importlib.util.find_spec('stable_baselines3'), 'install the rl extra')
    def test_current_simulator_reproduces_frozen_dqn_replay(self):
        from freshroute.dqn import DQNAgent
        from freshroute.experiments import rollout
        root = ROOT / 'artifacts/releases'
        expected = [json.loads(line) for line in (root/'decisions.jsonl').read_text().splitlines()]
        self.assertEqual(rollout(DQNAgent.load(root/'dqn'), seed=110000, scenario='regional-outage'), expected)
