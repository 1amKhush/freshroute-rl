import unittest

from freshroute.experiments import bootstrap_interval, evaluate, percentile, rollout, summarize, train


class EvaluationTests(unittest.TestCase):
    def test_control_records_do_not_inherit_learned_policy_metadata(self):
        agent, _ = train(episodes=2, steps=20)
        for policy in (agent.algorithm, 'nearest', 'leader', 'random'):
            with self.subTest(policy=policy):
                rows = rollout(agent, policy=policy)
                for row in rows:
                    self.assertEqual(row['policy'], policy)
                    if policy == agent.algorithm:
                        self.assertEqual(row['q_values'], agent.values(row['observation']))
                        self.assertIsInstance(row['state_seen_in_training'], bool)
                        self.assertEqual(len(row['action_training_visits']), 3)
                    else:
                        for field in ('q_values', 'state_seen_in_training', 'action_training_visits'):
                            self.assertIsNone(row[field])

    def test_percentiles_and_denominators(self):
        agent, _ = train(episodes=2, steps=20)
        rows = rollout(agent)
        metrics = summarize(rows)
        self.assertEqual(metrics['requests'], 20)
        self.assertEqual(metrics['successful_responses'], sum(row['outcome']['transport_ok'] for row in rows))
        self.assertEqual(sum(row['requests'] for row in metrics['by_request_class'].values()), 20)
        self.assertAlmostEqual(sum(metrics['mean_reward_terms'].values()), metrics['mean_reward'])
        self.assertEqual(percentile(range(1, 101), 95), 95)
        self.assertIsNone(percentile([], 95))

    def test_intervals_are_seeded_and_split_ranges_are_strict(self):
        self.assertEqual(bootstrap_interval([1, 2, 3]), bootstrap_interval([1, 2, 3]))
        self.assertIsNone(bootstrap_interval([1]))
        agent, _ = train(episodes=1, steps=2)
        for split, seed in [('test', 100_000), ('validation', 200_000), ('training', 0)]:
            with self.assertRaises(ValueError):
                evaluate(agent, split=split, seed=seed)
