"""Training, frozen evaluation, and structured decision replay artifacts."""

from collections import Counter
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import platform
import random
import statistics

from .agent import QAgent, encode
from .environment import Config, LEADER, REGIONS, SCENARIOS, ReplicaEnv


def source_fingerprint() -> str:
    digest = hashlib.sha256()
    for path in sorted(Path(__file__).parent.glob("*.py")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def train(*, episodes=1200, steps=160, seed=7, scenario="mixed"):
    if episodes < 1 or seed < 0 or seed + episodes > 100_000:
        raise ValueError("use positive episodes and training seeds entirely in [0, 100000)")
    if scenario not in (*SCENARIOS, "mixed"):
        raise ValueError(f"unknown training scenario: {scenario}")
    agent = QAgent(seed=seed)
    curve = []
    config = Config(episode_steps=steps)
    for episode in range(episodes):
        selected = SCENARIOS[episode % len(SCENARIOS)] if scenario == "mixed" else scenario
        env = ReplicaEnv(config, selected)
        observation, _ = env.reset(seed=seed + episode)
        epsilon = max(0.05, 1 - 0.95 * episode / max(1, episodes * 0.8))
        total, met = 0.0, 0
        while True:
            action = agent.act(observation, epsilon=epsilon)
            following, reward, terminated, truncated, info = env.step(action)
            # An external time limit is not an absorbing terminal state.
            agent.update(observation, action, reward, following, terminated=terminated)
            total += reward
            met += int(info["sla_met"])
            observation = following
            if terminated or truncated:
                break
        curve.append({
            "episode": episode + 1, "seed": seed + episode, "scenario": selected,
            "epsilon": epsilon, "return": total, "sla_rate": met / steps,
        })
    agent.metadata = {
        "purpose": "initial simulator demonstration; not release-qualified",
        "training_seed_start": seed, "training_seed_end_exclusive": seed + episodes,
        "agent_seed": seed, "episodes": episodes, "training_steps": episodes * steps,
        "scenario": scenario, "config": asdict(config), "python": platform.python_version(),
        "source_sha256": source_fingerprint(),
        "observation_note": "coarse state aggregation; not a complete Markov state",
    }
    return agent, curve


def policy_action(policy, observation, rng, agent):
    if policy in ("q-learning", "dqn"):
        return agent.act(observation)
    if policy == "leader":
        return LEADER
    if policy == "nearest":
        return min(range(3), key=lambda i: observation["replicas"][i]["rtt_ms"])
    if policy == "random":
        return rng.randrange(3)
    raise ValueError(f"unknown policy: {policy}")


def rollout(agent, *, policy=None, seed=100_000, scenario="balanced", config=None):
    policy = policy or agent.algorithm
    config = config or Config(**agent.metadata["config"])
    env = ReplicaEnv(config, scenario)
    observation, _ = env.reset(seed=seed)
    rng = random.Random(seed + 10_000_000)
    records = []
    while True:
        action = policy_action(policy, observation, rng, agent)
        following, reward, terminated, truncated, info = env.step(action)
        key = encode(observation)
        records.append({
            "schema_version": 1, "policy": policy, "seed": seed, "scenario": scenario,
            "step": len(records), "observation": observation, "state_key": key,
            "q_values": agent.values(observation) if policy in ('q-learning', 'dqn') else None,
            "state_seen_in_training": key in agent.table if policy == "q-learning" else None,
            "action_training_visits": list(agent.visits.get(key, [0, 0, 0]))
            if policy == "q-learning" else None,
            "action": action, "reward": reward, "outcome": info,
            "next_observation": following, "terminated": terminated, "truncated": truncated,
        })
        observation = following
        if terminated or truncated:
            return records


def percentile(values, probability):
    ordered = sorted(values)
    return ordered[max(0, (probability * len(ordered) + 99) // 100 - 1)] if ordered else None


def summarize(records, *, breakdowns=True):
    count = len(records)
    outcomes = [row["outcome"] for row in records]
    successes = [row for row in outcomes if row["transport_ok"]]
    success_latencies = sorted(row["response_ms"] for row in successes)
    requests = Counter(REGIONS[row["action"]] for row in records)
    q_records = [row for row in records if row["policy"] == "q-learning"]
    summary = {
        "requests": count,
        "successful_responses": len(successes),
        "mean_reward": statistics.fmean(row["reward"] for row in records),
        "mean_response_ms_including_failures": statistics.fmean(row["response_ms"] for row in outcomes),
        "p95_success_response_ms": success_latencies[max(0, (95 * len(success_latencies) + 99) // 100 - 1)]
        if successes else None,
        "availability_rate": len(successes) / count,
        "sla_rate": sum(row["sla_met"] for row in outcomes) / count,
        "freshness_violation_rate_among_responses": sum(row["freshness_violation"] for row in successes)
        / len(successes) if successes else None,
        "mean_staleness_ms_among_responses": statistics.fmean(row["staleness_ms"] for row in successes)
        if successes else None,
        "timeout_rate": sum(row["timeout"] for row in outcomes) / count,
        "unavailable_rate": sum(row["unavailable"] for row in outcomes) / count,
        "unseen_state_rate": sum(not row["state_seen_in_training"] for row in q_records)
        / len(q_records) if q_records else None,
        "routes": {region: requests[region] for region in REGIONS},
    }
    for label, values in (
        ('success_response_ms', success_latencies),
        ('response_ms_including_failures', [row['response_ms'] for row in outcomes]),
        ('staleness_ms_among_responses', [row['staleness_ms'] for row in successes]),
        ('version_lag_among_responses', [row['version_lag'] for row in successes]),
    ):
        for probability in (50, 95, 99):
            summary[f'p{probability}_{label}'] = percentile(values, probability)
    summary['mean_reward_terms'] = {
        term: statistics.fmean(row['reward_terms'][term] for row in outcomes)
        for term in ('latency', 'freshness', 'failure')
    }
    if breakdowns:
        for field in ('client_region', 'request_class'):
            summary[f'by_{field}'] = {
                str(value): summarize(subset, breakdowns=False)
                for value in sorted({row['observation'][field] for row in records})
                if (subset := [row for row in records if row['observation'][field] == value])
            }
    return summary


def evaluate(agent, *, episodes=8, seed=100_000, split='validation', scenarios=None):
    bands = {'validation': (100_000, 200_000), 'test': (200_000, 300_000)}
    if split not in bands:
        raise ValueError('evaluation split must be validation or test')
    lower, upper = bands[split]
    if episodes < 1 or seed < lower or seed + episodes > upper:
        raise ValueError(f'{split} seeds must stay in [{lower},{upper})')
    results = []
    for scenario in scenarios or SCENARIOS:
        for policy in (agent.algorithm, "nearest", "leader", "random"):
            rows = []
            per_episode = []
            for index in range(episodes):
                records = rollout(agent, policy=policy, seed=seed + index, scenario=scenario)
                rows.extend(records)
                per_episode.append({"seed": seed + index, **summarize(records)})
            results.append({"scenario": scenario, "policy": policy, **summarize(rows), "episodes": per_episode})
    return {
        "schema_version": 1, "split": split, "seed_start": seed,
        "episodes_per_scenario": episodes,
        "comparison_note": "common exogenous seeds; each policy evolves its own queues",
        "model_metadata": agent.metadata, "evaluation_source_sha256": source_fingerprint(),
        "results": results,
    }


def bootstrap_interval(values, *, seed=42, samples=2000):
    if len(values) < 2:
        return None
    rng = random.Random(seed)
    means = sorted(statistics.fmean(rng.choices(values, k=len(values))) for _ in range(samples))
    return [means[int(samples * .025)], means[int(samples * .975) - 1]]


def evaluate_matrix(models, *, episodes=30, seed=100_100, split='validation'):
    """Aggregate independent trained agents, not dependent requests, for uncertainty."""
    from .policies import load_agent

    reports, groups = [], {}
    common_config = None
    for path in models:
        agent = load_agent(path)
        config = agent.metadata['config']
        if common_config is not None and config != common_config:
            raise ValueError('paired matrix requires identical environment and reward configuration')
        common_config = config
        report = evaluate(agent, episodes=episodes, seed=seed, split=split)
        report['model_path'] = str(path)
        reports.append(report)
        condition = agent.metadata.get('ablation', 'tabular')
        if agent.metadata.get('gamma') == 0:
            condition = 'gamma-zero'
        for result in report['results']:
            if result['policy'] != agent.algorithm:
                continue
            group = groups.setdefault((condition, result['scenario']), [])
            if any(row['training_seed'] == agent.metadata['agent_seed'] for row in group):
                raise ValueError('duplicate training seed within an experiment condition')
            group.append({'training_seed': agent.metadata['agent_seed'], 'metrics': result})
    summaries = []
    for (condition, scenario), rows in groups.items():
        metrics = {}
        for metric in ('mean_reward', 'sla_rate', 'availability_rate', 'freshness_violation_rate_among_responses'):
            values = [row['metrics'][metric] for row in rows if row['metrics'][metric] is not None]
            metrics[metric] = {'mean': statistics.fmean(values) if values else None,
                               'bootstrap_95_interval_across_training_seeds': bootstrap_interval(values)}
        summaries.append({'condition': condition, 'scenario': scenario,
                          'training_seeds': [row['training_seed'] for row in rows], 'metrics': metrics})
    return {'schema_version': 1, 'split': split, 'seed_start': seed,
            'episodes_per_scenario': episodes, 'summaries': summaries, 'runs': reports,
            'uncertainty_unit': 'independent training seed; percentile bootstrap, descriptive for small N',
            'source_sha256': source_fingerprint()}
