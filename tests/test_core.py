from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from freshroute.agent import QAgent, encode
from freshroute.environment import Config, LEADER, ReplicaEnv
from freshroute.experiments import evaluate, rollout, train


class SimulatorTests(unittest.TestCase):
    def test_seeded_rollout_is_reproducible(self):
        left, right = ReplicaEnv(), ReplicaEnv()
        self.assertEqual(left.reset(seed=83), right.reset(seed=83))
        for step in range(160):
            self.assertEqual(left.step(step % 3), right.step(step % 3))

    def test_routing_changes_future_queue_not_exogenous_randomness(self):
        left, right = ReplicaEnv(), ReplicaEnv()
        left.reset(seed=13)
        right.reset(seed=13)
        for _ in range(12):
            a = left.step(0)[0]
            b = right.step(2)[0]
            self.assertEqual(a["client_region"], b["client_region"])
            self.assertEqual(a["request_class"], b["request_class"])
            self.assertEqual(left.commits, right.commits)
            self.assertEqual(left.online, right.online)
        self.assertNotEqual(left.queues, right.queues)
        self.assertGreater(left.queues[0], right.queues[0])

    def test_caught_up_replica_is_fresh_even_with_old_write(self):
        env = ReplicaEnv()
        env.reset()
        env.clock_ms = 10_000
        self.assertTrue(all(replica["staleness_ms"] == 0 for replica in env.observe()["replicas"]))

    def test_leader_is_fresh_when_online_and_versions_never_regress(self):
        env = ReplicaEnv(scenario="write-burst")
        observation, _ = env.reset(seed=9)
        previous = [0, 0, 0]
        for step in range(160):
            observation, _, _, _, _ = env.step(step % 3)
            for replica in observation["replicas"]:
                self.assertGreaterEqual(replica["applied_version"], previous[replica["id"]])
                self.assertLessEqual(replica["applied_version"], observation["leader_version"])
                previous[replica["id"]] = replica["applied_version"]
            if observation["replicas"][LEADER]["online"]:
                self.assertEqual(observation["replicas"][LEADER]["version_lag"], 0)

    def test_reward_terms_and_failure_accounting(self):
        env = ReplicaEnv()
        env.reset(seed=42)
        env.online[0] = False
        _, reward, _, _, info = env.step(0)
        self.assertEqual(reward, sum(info["reward_terms"].values()))
        self.assertEqual(reward, -5.0)
        self.assertTrue(info["unavailable"])
        self.assertFalse(info["sla_met"])
        self.assertIsNone(info["staleness_ms"])
        self.assertEqual(info["reward_terms"]["freshness"], 0)

    def test_stale_response_is_not_freshness_success(self):
        env = ReplicaEnv()
        env.reset(seed=42)
        env.commits = [0, 200]
        env.applied = [0, 1, 0]
        env.client, env.request_class = 0, 0
        _, reward, _, _, info = env.step(0)
        self.assertTrue(info["transport_ok"])
        self.assertTrue(info["freshness_violation"])
        self.assertFalse(info["sla_met"])
        self.assertEqual(info["reward_terms"]["freshness"], -4.0)
        self.assertEqual(reward, sum(info["reward_terms"].values()))

    def test_timeout_consumes_work_but_returns_no_read(self):
        env = ReplicaEnv()
        observation, _ = env.reset(seed=0)
        env.queues[0] = 500
        _, _, _, _, info = env.step(0)
        self.assertTrue(info["timeout"])
        self.assertEqual(info["response_ms"], observation["deadline_ms"])
        self.assertIsNone(info["staleness_ms"])
        self.assertGreater(env.queues[0], 500)

    def test_limit_is_truncation_and_requires_reset(self):
        env = ReplicaEnv(Config(episode_steps=1))
        with self.assertRaises(RuntimeError):
            env.step(0)
        env.reset()
        _, _, terminated, truncated, _ = env.step(LEADER)
        self.assertFalse(terminated)
        self.assertTrue(truncated)
        with self.assertRaises(RuntimeError):
            env.step(0)
        env.reset()
        for bad in (-1, 3, 0.5, True):
            with self.assertRaises(ValueError):
                env.step(bad)


class LearningTests(unittest.TestCase):
    def test_temporal_difference_target_and_terminal_mask(self):
        env = ReplicaEnv()
        observation, _ = env.reset()
        following = deepcopy(observation)
        following["client_region"] = (following["client_region"] + 1) % 3
        agent = QAgent(alpha=0.5, gamma=0.9)
        agent.table[encode(following)] = [1, 2, 3]
        agent.update(observation, 0, -1, following)
        self.assertAlmostEqual(agent.values(observation)[0], 0.5 * (-1 + 0.9 * 3))
        agent.update(observation, 1, -1, following, terminated=True)
        self.assertEqual(agent.values(observation)[1], -0.5)

    def test_training_save_reload_and_frozen_evaluation(self):
        agent, curve = train(episodes=8, steps=20, seed=7)
        repeated, repeated_curve = train(episodes=8, steps=20, seed=7)
        self.assertEqual(agent.table, repeated.table)
        self.assertEqual(curve, repeated_curve)
        self.assertEqual(sum(sum(counts) for counts in agent.visits.values()), 160)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "q.json"
            agent.save(path)
            loaded = QAgent.load(path)
            snapshot = deepcopy(loaded.table)
            first = rollout(agent)
            second = rollout(loaded)
            self.assertEqual(first, second)
            evaluate(loaded, episodes=1)
            self.assertEqual(loaded.table, snapshot)
            payload = json.loads(path.read_text())
            payload["encoder_version"] = 100
            path.write_text(json.dumps(payload))
            with self.assertRaises(ValueError):
                QAgent.load(path)

    def test_unseen_state_is_visible_and_has_no_heuristic_fallback(self):
        env = ReplicaEnv()
        observation, _ = env.reset()
        agent = QAgent()
        self.assertEqual(agent.values(observation), [0, 0, 0])
        self.assertEqual(agent.act(observation), 0)
        self.assertEqual(agent.table, {})

    def test_validation_does_not_overlap_reserved_training_or_test_ranges(self):
        with self.assertRaises(ValueError):
            train(episodes=2, seed=99_999)
        agent, _ = train(episodes=1, steps=2)
        with self.assertRaises(ValueError):
            evaluate(agent, seed=7)
        with self.assertRaises(ValueError):
            evaluate(agent, seed=199_999, episodes=2)

    def test_corrupt_action_values_are_rejected(self):
        agent, _ = train(episodes=1, steps=2)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "q.json"
            agent.save(path)
            payload = json.loads(path.read_text())
            key = next(iter(payload["q_table"]))
            payload["q_table"][key] = [0, float("nan"), 0]
            path.write_text(json.dumps(payload))
            with self.assertRaisesRegex(ValueError, "finite numbers"):
                QAgent.load(path)


if __name__ == "__main__":
    unittest.main()
