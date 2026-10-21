"""Exact simulator-state branches, including RNG state, under a frozen policy."""

from copy import deepcopy
import hashlib
import json


def snapshot_hash(env):
    state = {
        'config': env.config_dict(), 'scenario': env.scenario_spec.to_dict(),
        'seed': env.seed, 'step': env.step_index, 'clock': env.clock_ms,
        'commits': env.commits, 'applied': env.applied, 'queues': env.queues,
        'online': env.online, 'natural_online': env._natural_online,
        'link_lag': env.link_lag, 'base_link_lag': env._base_link_lag,
        'client': env.client, 'request_class': env.request_class,
        'faults': env.fault_events, 'random_state': env.rng.getstate(),
    }
    return hashlib.sha256(json.dumps(state, sort_keys=True, allow_nan=False).encode()).hexdigest()


def branch_actions(env, agent, *, horizon=8):
    if type(horizon) is not int or not 1 <= horizon <= 30:
        raise ValueError('counterfactual horizon must be an integer in [1,30]')
    horizon = min(horizon, env.config.episode_steps - env.step_index)
    if horizon < 1:
        raise ValueError('no decision remains in this episode')
    original_hash = snapshot_hash(env)
    gamma = agent.metadata.get('gamma', getattr(agent, 'gamma', .95))
    branches = []
    for first_action in range(3):
        clone = deepcopy(env)
        total, first_outcome, rewards = 0, None, []
        for step in range(horizon):
            action = first_action if step == 0 else agent.act(clone.observe())
            _, reward, terminated, truncated, info = clone.step(action)
            total += gamma ** step * reward
            rewards.append({'action': action, 'reward': reward})
            if first_outcome is None:
                first_outcome = info
            if terminated or truncated:
                break
        branches.append({'action': first_action, 'immediate_reward': rewards[0]['reward'],
                         'discounted_return': total, 'first_outcome': first_outcome, 'steps': rewards})
    if snapshot_hash(env) != original_hash:
        raise RuntimeError('counterfactual branching changed the source session')
    return {'schema_version': 1, 'snapshot_sha256': original_hash, 'step': env.step_index,
            'horizon': horizon, 'rollout_policy': agent.algorithm, 'gamma': gamma, 'branches': branches}
