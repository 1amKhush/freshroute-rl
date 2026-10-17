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
        || Number(observation.client_region) > 2) throw new Error(`Invalid observation at line ${index + 1}.`)
      observation.replicas.forEach((replica: unknown, id: number) => {
        if (!object(replica) || replica.id !== id || typeof replica.online !== 'boolean'
          || !['rtt_ms', 'queue_ms', 'staleness_ms', 'version_lag', 'applied_version'].every(key => finite(replica[key]))) {
          throw new Error(`Invalid replica measurements at line ${index + 1}.`)
        }
      })
    }
    if (row.q_values !== null && (!Array.isArray(row.q_values) || row.q_values.length !== 3 || !row.q_values.every(finite))) {
      throw new Error(`Invalid action values at line ${index + 1}.`)
    }
    if (!finite(row.outcome.response_ms) || !object(row.outcome.reward_terms)
      || !['latency', 'freshness', 'failure'].every(key => finite((row.outcome as Record<string, unknown>).reward_terms && (row.outcome as {reward_terms: Record<string, unknown>}).reward_terms[key]))) {
      throw new Error(`Invalid reward or response at line ${index + 1}.`)
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
  const [traceResponse, evaluation] = await Promise.all([
    fetch('/demo/decisions.jsonl'), jsonRequest<Evaluation>('/demo/evaluation.json'),
  ])
  if (!traceResponse.ok) throw new Error('The bundled replay could not be loaded.')
  return { decisions: parseTrace(await traceResponse.text()), evaluation }
}
