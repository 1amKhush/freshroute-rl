import importlib.util
import unittest


@unittest.skipUnless(importlib.util.find_spec('fastapi'), 'install the server extra')
class APITests(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from freshroute.api import ROOT, create_app
        self.client = TestClient(create_app(models={'q-learning': ROOT / 'artifacts/demo/q-agent.json'}))

    def create(self, **kwargs):
        response = self.client.post('/api/sessions', json={'seed': 110000, **kwargs})
        self.assertEqual(response.status_code, 201)
        return response.json()['id']

    def test_seeded_api_and_cli_records_match_and_sessions_are_isolated(self):
        from freshroute.api import ROOT
        from freshroute.agent import QAgent
        from freshroute.experiments import rollout
        agent = QAgent.load(ROOT / 'artifacts/demo/q-agent.json')
        expected = rollout(agent, seed=110000)
        first, second = self.create(), self.create()
        for index in range(5):
            self.assertEqual(self.client.post(f'/api/sessions/{first}/step').json(), expected[index])
        self.assertEqual(self.client.post(f'/api/sessions/{second}/step').json(), expected[0])
        exported = self.client.get(f'/api/sessions/{first}/trace').text
        self.assertEqual(len(exported.splitlines()), 5)
        import hashlib
        manifest = self.client.get(f'/api/sessions/{first}/manifest').json()
        self.assertEqual(manifest['trace_sha256'], hashlib.sha256(exported.encode()).hexdigest())
        self.assertEqual(self.client.delete(f'/api/sessions/{first}').status_code, 204)
        self.assertEqual(self.client.post(f'/api/sessions/{first}/step').status_code, 404)

    def test_bad_requests_and_episode_end(self):
        self.assertEqual(self.client.post('/api/sessions', json={'model_id': '../secret'}).status_code, 404)
        self.assertEqual(self.client.post('/api/sessions', json={'seed': 7}).status_code, 422)
        self.assertEqual(self.client.post('/api/sessions', json={'scenario': 'other'}).status_code, 422)
        session = self.create()
        for _ in range(160):
            self.assertEqual(self.client.post(f'/api/sessions/{session}/step').status_code, 200)
        self.assertEqual(self.client.post(f'/api/sessions/{session}/step').status_code, 409)

    def test_faults_and_selected_decision_counterfactuals(self):
        session = self.create()
        base = f'/api/sessions/{session}'
        fault = self.client.post(base + '/faults', json={'kind': 'outage', 'replica': 0, 'duration_steps': 20})
        self.assertEqual(fault.status_code, 200)
        self.assertFalse(fault.json()['observation']['replicas'][0]['online'])
        self.assertEqual(self.client.post(base + '/faults', json={'kind': 'lag', 'replica': 1}).status_code, 400)
        row = self.client.post(base + '/step').json()
        branches = self.client.post(base + '/counterfactuals', json={'horizon': 8}).json()
        self.assertEqual(branches['step'], row['step'])
        self.assertEqual(branches['branches'][row['action']]['first_outcome'], row['outcome'])
        self.assertEqual(len(self.client.get(base + '/trace').text.splitlines()), 1)
