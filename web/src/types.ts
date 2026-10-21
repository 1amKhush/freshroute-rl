export const regions = ['Mumbai', 'Frankfurt', 'Virginia'] as const
export type Replica = {
  id: number; region: string; is_leader: boolean; online: boolean; rtt_ms: number;
  queue_ms: number; staleness_ms: number; version_lag: number;
  applied_version: number; replication_delay_ms: number
}
export type Observation = {
  step: number; clock_ms: number; scenario: string; client_region: number;
  request_class: string; freshness_tolerance_ms: number; deadline_ms: number;
  leader_version: number; replicas: Replica[]
}
export type Outcome = {
  action: number; replica: string; response_ms: number; transport_ok: boolean;
  unavailable: boolean; timeout: boolean; staleness_ms: number | null;
  version_lag: number | null; freshness_violation: boolean; sla_met: boolean;
  reward_terms: { latency: number; freshness: number; failure: number }
}
export type Decision = {
  schema_version: number; policy: string; seed: number; scenario: string; step: number;
  observation: Observation; next_observation: Observation; action: number; reward: number;
  outcome: Outcome; q_values: number[] | null; state_seen_in_training: boolean | null;
  action_training_visits: number[] | null; terminated: boolean; truncated: boolean
}
export type Metrics = {
  scenario: string; policy: string; mean_reward: number; sla_rate: number;
  availability_rate: number; mean_response_ms_including_failures: number;
  freshness_violation_rate_among_responses: number | null;
  p95_success_response_ms: number | null; requests: number
}
export type Evaluation = { split: string; episodes_per_scenario: number; results: Metrics[] }
export type Model = { id: string; label: string; algorithm: string }
export type Session = { id: string; model_id: string; seed: number; scenario: string; observation: Observation }
export type Counterfactual = {
  snapshot_sha256: string; step: number; horizon: number; rollout_policy: string;
  branches: { action: number; immediate_reward: number; discounted_return: number; first_outcome: Outcome }[]
}
