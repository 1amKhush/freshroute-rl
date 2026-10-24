import type { Decision, Evaluation } from './types'

const finite = (x: unknown): x is number => typeof x === 'number' && Number.isFinite(x)
const object = (x: unknown): x is Record<string, unknown> => !!x && typeof x === 'object' && !Array.isArray(x)

export function parseTrace(text: string): Decision[] {
  const lines = text.trim().split('\n')
  if (lines.length > 20000) throw new Error('This explorer supports at most 20,000 decisions per replay.')
  return lines.map((line, index) => {
    const row: unknown = JSON.parse(line)
    if (!object(row) || row.schema_version !== 1 || row.step !== index || !finite(row.reward)
      || !Number.isInteger(row.action) || Number(row.action) < 0 || Number(row.action) > 2
      || !object(row.outcome) || !object(row.observation) || !object(row.next_observation)) {
      throw new Error(`Invalid decision schema at line ${index + 1}.`)
    }
    for (const observation of [row.observation, row.next_observation]) {
      if (!Array.isArray(observation.replicas) || observation.replicas.length !== 3
        || !finite(observation.deadline_ms) || !finite(observation.freshness_tolerance_ms)
        || !Number.isInteger(observation.client_region) || Number(observation.client_region) < 0
        || Number(observation.client_region) > 2 || typeof observation.request_class !== 'string'
        || !finite(observation.clock_ms) || !finite(observation.leader_version)) throw new Error(`Invalid observation at line ${index + 1}.`)
      observation.replicas.forEach((replica: unknown, id: number) => {
        if (!object(replica) || replica.id !== id || typeof replica.online !== 'boolean'
          || typeof replica.region !== 'string' || typeof replica.is_leader !== 'boolean'
          || !['rtt_ms', 'queue_ms', 'staleness_ms', 'version_lag', 'applied_version', 'replication_delay_ms'].every(key => finite(replica[key]) && Number(replica[key]) >= 0)) {
          throw new Error(`Invalid replica measurements at line ${index + 1}.`)
        }
      })
    }
    if (row.q_values !== null && (!Array.isArray(row.q_values) || row.q_values.length !== 3 || !row.q_values.every(finite))) {
      throw new Error(`Invalid action values at line ${index + 1}.`)
    }
    const outcome = row.outcome
    const terms = outcome.reward_terms
    if (!finite(outcome.response_ms) || !object(terms)
      || !finite(terms.latency) || !finite(terms.freshness) || !finite(terms.failure)) {
      throw new Error(`Invalid reward or response at line ${index + 1}.`)
    }
    if (typeof row.policy !== 'string' || typeof row.scenario !== 'string' || !Number.isInteger(row.seed)
      || !['transport_ok', 'unavailable', 'timeout', 'freshness_violation', 'sla_met'].every(key => typeof outcome[key] === 'boolean')
      || ![outcome.staleness_ms, outcome.version_lag].every(value => value === null || finite(value))
      || ![row.terminated, row.truncated].every(value => typeof value === 'boolean')
      || (row.state_seen_in_training !== null && typeof row.state_seen_in_training !== 'boolean')
      || (row.action_training_visits !== null && (!Array.isArray(row.action_training_visits)
          || row.action_training_visits.length !== 3 || !row.action_training_visits.every(value => Number.isInteger(value) && value >= 0)))) {
      throw new Error(`Invalid decision outcome or training coverage at line ${index + 1}.`)
    }
    if (Math.abs(terms.latency + terms.freshness + terms.failure - row.reward) > 1e-6) {
      throw new Error(`Reward terms do not sum to the recorded reward at line ${index + 1}.`)
    }
    return row as unknown as Decision
  })
}

export async function jsonRequest<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, options)
  if (!response.ok) {
    const message = await response.text()
    throw new Error(`Request failed (${response.status}): ${message.slice(0, 180)}`)
  }
  return response.json() as Promise<T>
}

export async function loadDemo() {
  const [traceResponse, evaluation, training, manifest] = await Promise.all([
    fetch('/demo/decisions.jsonl'), jsonRequest<Evaluation>('/demo/evaluation.json'),
    jsonRequest<{ episodes: { episode: number; return: number }[] }>('/demo/training.json'),
    jsonRequest<{ trace_sha256: string }>('/demo/decisions.manifest.json'),
  ])
  if (!traceResponse.ok) throw new Error('The bundled replay could not be loaded.')
  const text = await traceResponse.text()
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text))
  const hash = Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('')
  if (hash !== manifest.trace_sha256) throw new Error('The bundled trace does not match its recorded manifest hash.')
  return { decisions: parseTrace(text), evaluation, training }
}
