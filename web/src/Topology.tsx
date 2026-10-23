import { useState } from 'react'
import type { Decision } from './types'
import { regions } from './types'
import { useReadMotion, useReducedMotion } from './read-motion'
import './topology.css'

const ms = (value: number | null) => value === null ? '—' : `${value.toFixed(0)} ms`
const stages = ['Observe', 'Choose', 'Read', 'Outcome']

function DatabaseIcon() {
  return <svg className="database-icon" viewBox="0 0 32 32" aria-hidden="true"><ellipse cx="16" cy="7" rx="11" ry="4" /><path d="M5 7v17c0 5.3 22 5.3 22 0V7M5 15c0 5.3 22 5.3 22 0M5 23c0 5.3 22 5.3 22 0" /></svg>
}

export function Topology({ row, snapshot, playback = false, durationMs = 3200, animateOnChange = false, onPausePlayback }: {
  row: Decision; snapshot: boolean; playback?: boolean; durationMs?: number; animateOnChange?: boolean; onPausePlayback?: () => void;
}) {
  const [motion, setMotion] = useState(true)
  const reduced = useReducedMotion()
  const enabled = motion && !reduced
  const { root, phase, status, toggle } = useReadMotion({ row, snapshot, playback, durationMs, animateOnChange, enabled })
  const obs = snapshot ? row.next_observation : row.observation
  const outcome = row.outcome
  const chosen = row.observation.replicas[row.action]
  const tone = !outcome.transport_ok ? 'failure' : outcome.freshness_violation ? 'stale' : 'fresh'
  const result = outcome.unavailable ? 'Replica unavailable' : outcome.timeout ? 'Deadline exceeded' : outcome.freshness_violation ? 'Stale data returned' : 'Fresh data returned'
  const stage = phase === 0 ? 0 : phase === 1 ? 1 : phase < 5 ? 2 : 3
  const narration = [
    [`A read arrives from ${regions[row.observation.client_region]}.`, `${row.observation.request_class} request · ${ms(row.observation.freshness_tolerance_ms)} freshness budget · ${ms(row.observation.deadline_ms)} deadline`],
    [`The policy chooses ${chosen.region}.`, row.q_values ? `Recorded Q-value ${row.q_values[row.action].toFixed(3)} · estimated future return` : 'Executed action recorded in this decision trace'],
    [`Request → ${chosen.region}`, `At dispatch: ${ms(chosen.rtt_ms)} RTT · ${ms(chosen.queue_ms)} queued work`],
    [chosen.online ? `${chosen.region} processes the read.` : `${chosen.region} is offline.`, chosen.online ? `At dispatch: v${chosen.applied_version} applied / v${row.observation.leader_version} committed` : 'The request cannot obtain data from this replica.'],
    [outcome.transport_ok ? `${chosen.region} → client` : outcome.unavailable ? 'No response from this replica.' : 'The client waits until its deadline.', outcome.transport_ok ? `${ms(outcome.staleness_ms)} returned data lag · ${ms(outcome.response_ms)} measured response` : 'No successful data response · no return packet'],
    [result, `${ms(outcome.response_ms)} response · reward ${row.reward.toFixed(3)} · SLA ${outcome.sla_met ? 'met' : 'missed'}`],
  ][phase]
  const activeStage = !snapshot && enabled && status !== 'finished'

  return <section ref={root} className={`panel topology-panel read-${tone}`} aria-labelledby="topology-title" data-phase={phase} data-motion={enabled && !snapshot ? status : 'off'} data-request={row.step + 1}>
    <div className="panel-heading"><div><p className="eyebrow">GLOBAL REPLICA NETWORK</p><h2 id="topology-title">Follow a read, end to end.</h2></div><span className="tag">{snapshot ? 'Next request state' : 'At decision time'}</span></div>
    <div className="read-controls"><ol className="read-stages" aria-label="Read lifecycle">{stages.map((label, index) => <li key={label} className={activeStage && index === stage ? 'current-stage' : ''} aria-current={activeStage && index === stage ? 'step' : undefined}><span>{index + 1}</span>{label}</li>)}</ol><div className="motion-actions"><button className="animate-read" onClick={() => { if (playback) onPausePlayback?.(); toggle() }} disabled={!enabled || snapshot} aria-label={status === 'running' ? 'Pause read animation' : status === 'paused' ? 'Resume read animation' : 'Animate this read'}>{status === 'running' && enabled && !snapshot ? 'Ⅱ Pause motion' : status === 'paused' && enabled && !snapshot ? '▶ Resume' : '↻ Animate read'}</button><label><input type="checkbox" aria-label="Enable routing motion" checked={motion && !reduced} disabled={reduced} onChange={event => setMotion(event.target.checked)} />Motion</label></div></div>
    <div className="read-progress" aria-hidden="true"><span /></div>
    <div className="topology-canvas">
      <div className="client-node"><span className="client-symbol" aria-hidden="true">↗</span><span>Read request<small>{regions[obs.client_region]} · {obs.request_class}</small></span><span className="tag blue">{ms(obs.freshness_tolerance_ms)} freshness budget</span></div>
      <div className="router-stem" aria-hidden="true" /><div className={`policy-hub ${activeStage && phase === 1 ? 'thinking' : ''}`}><span aria-hidden="true">◈</span><strong>{row.policy === 'dqn' ? 'DQN' : row.policy} router</strong><small>3 actions · 1 choice</small></div>
      <svg className="network-lines" viewBox="0 0 600 140" preserveAspectRatio="none" aria-label={`Selected route to ${chosen.region}. ${result}.`} role="img">
        {[100, 300, 500].map((x, id) => <path key={id} d={`M300 0 V20 C300 64 ${x} 45 ${x} 108 V140`} className={id === row.action ? 'route selected' : 'route'} vectorEffect="non-scaling-stroke" />)}
        <g transform={`translate(${100 + row.action * 200} 132)`} aria-hidden="true"><circle className="service-ring" r="14" /><circle className={`route-terminal ${phase === 5 ? 'result-terminal' : ''}`} r="5" /><text className="failure-cross" textAnchor="middle" y="4">×</text></g>
        <g className="request-packet" aria-hidden="true"><circle className="packet-halo" r="12" /><circle className="packet-core" r="5" /></g>
        <g className="response-packet" aria-hidden="true" data-returned={outcome.transport_ok}><circle className="packet-halo" r="12" /><circle className="packet-core" r="5" /><path d="m-2.5 0 1.8 2 3.5-4" /></g>
      </svg>
      <div className="replica-grid">{obs.replicas.map(replica => {
        const stale = replica.staleness_ms > obs.freshness_tolerance_ms
        return <article key={replica.id} className={`replica ${row.action === replica.id ? 'chosen' : ''} ${!replica.online ? 'offline' : ''}`}>
          <div className="replica-title"><DatabaseIcon /><span className={`dot ${replica.online ? 'green-dot' : 'red-dot'}`} /><span className="replica-state">{replica.online ? 'Online' : 'Offline'}</span></div><h3>{replica.region}</h3><p className="replica-role">{replica.is_leader ? 'PRIMARY / LEADER' : 'READ REPLICA'}</p>
          <dl><div><dt>Network RTT</dt><dd>{ms(replica.rtt_ms)}</dd></div><div><dt>Queued work</dt><dd>{ms(replica.queue_ms)}</dd></div><div><dt>Data lag</dt><dd className={stale ? 'amber-text' : 'green-text'}>{ms(replica.staleness_ms)}</dd></div><div><dt>Applied version</dt><dd>v{replica.applied_version}<small> / v{obs.leader_version}</small></dd></div></dl>
          <div className={`lag-gauge ${stale ? 'lag-exceeded' : ''}`}><div aria-hidden="true"><span style={{ transform: `scaleX(${Math.min(1, replica.staleness_ms / Math.max(1, obs.freshness_tolerance_ms))})` }} /></div><small>{!replica.online ? 'Replica unavailable' : stale ? 'Beyond freshness budget' : 'Within freshness budget'}</small></div>
          <div className={`route-label ${replica.id === row.action ? 'active' : ''}`}>{replica.id === row.action ? '↳ Selected by policy' : `${replica.version_lag} versions behind`}</div>
        </article>
      })}</div>
      <div className="packet-legend"><span><i className="request-key" />Request</span><span><i className="response-key" />{outcome.transport_ok ? 'Data response' : 'No data response'}</span><span className={`outcome-key ${tone}`}>{outcome.transport_ok ? outcome.freshness_violation ? '△ Stale' : '✓ Fresh' : '× Failed'}</span></div>
    </div>
    <div className="read-narration" aria-label="Read walkthrough"><span className="narration-icon" aria-hidden="true">{snapshot ? '↗' : phase === 5 ? outcome.transport_ok ? '↳' : '!' : String(stage + 1).padStart(2, '0')}</span><div><strong>{snapshot ? 'Telemetry for the next request.' : narration[0]}</strong><p>{snapshot ? 'Client and replica values are the next observation. The highlighted route belongs to the preceding read.' : narration[1]}</p></div><span className="walkthrough-state">{snapshot ? 'Snapshot' : reduced ? 'Reduced motion' : !motion ? 'Motion off' : status === 'running' ? 'Walking through' : status === 'paused' ? 'Paused' : 'Recorded outcome'}</span></div>
    <p className="motion-footnote">{snapshot ? 'Next observation · preceding route' : 'Dispatch snapshot · recorded outcome'} · Visual timing is illustrative, not network time.</p>
  </section>
}
