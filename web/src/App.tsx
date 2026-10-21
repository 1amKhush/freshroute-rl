import { useEffect, useMemo, useState } from 'react'
import { loadDemo, parseTrace } from './data'
import type { Decision, Evaluation } from './types'
import { Comparison, Inspector, LatencyChart, Mark, OutcomeCards, Topology } from './components'
import { LiveLab } from './LiveLab'

export function App() {
  const [decisions, setDecisions] = useState<Decision[]>([])
  const [error, setError] = useState('')
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null)
  const [training, setTraining] = useState<{episode: number; return: number}[]>([])
  const [tab, setTab] = useState('decisions')
  const [cursor, setCursor] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(800)
  const [filter, setFilter] = useState('all')
  const [snapshot, setSnapshot] = useState(false)
  const visible = useMemo(() => decisions.filter(row => filter === 'all' || (filter === 'stale' ? row.outcome.freshness_violation : !row.outcome.transport_ok)), [decisions, filter])
  const row = visible[Math.min(cursor, Math.max(0, visible.length - 1))]
  useEffect(() => {
    let active = true
    loadDemo().then(data => { if (active) { setDecisions(data.decisions); setEvaluation(data.evaluation); setTraining(data.training.episodes) } })
      .catch(error => { if (active) setError(String(error)) })
    return () => { active = false }
  }, [])
  useEffect(() => {
    if (!playing) return
    if (cursor >= visible.length - 1) { setPlaying(false); return }
    const timer = window.setTimeout(() => setCursor(index => index + 1), speed)
    return () => window.clearTimeout(timer)
  }, [playing, cursor, visible.length, speed])

  async function openTrace(file: File | undefined) {
    if (!file) return
    try {
      if (file.size > 20_000_000) throw new Error('Choose a trace smaller than 20 MB.')
      const rows = parseTrace(await file.text())
      setDecisions(rows); setCursor(0); setPlaying(false); setFilter('all'); setError('')
    } catch (error) { setError(`Could not open trace: ${String(error)}`) }
  }

  return <div className="app-shell"><a className="skip-link" href="#main">Skip to decisions</a>
    <aside className="sidebar"><a className="brand" href="/"><Mark /><span>FreshRoute<small>REINFORCEMENT LEARNING LAB</small></span></a><nav className="sidebar-section" aria-label="Workspace"><p className="eyebrow">WORKSPACE</p><button className={`nav-item ${tab === 'decisions' ? 'current' : ''}`} aria-current={tab === 'decisions' ? 'page' : undefined} onClick={() => { setTab('decisions'); setPlaying(false) }}>◈ Decision explorer</button><button className={`nav-item ${tab === 'evaluation' ? 'current' : ''}`} aria-current={tab === 'evaluation' ? 'page' : undefined} onClick={() => { setTab('evaluation'); setPlaying(false) }}>↗ Training & evaluation</button><button className={`nav-item ${tab === 'live' ? 'current' : ''}`} aria-current={tab === 'live' ? 'page' : undefined} onClick={() => { setTab('live'); setPlaying(false) }}>⌁ Live laboratory</button></nav><div className="learning-loop"><p className="eyebrow">THE LEARNING LOOP</p>{['Receive a read request', 'Observe replica conditions', 'Choose where to read', 'Learn from the outcome'].map((label, i) => <div key={label}><span>{i + 1}</span>{label}</div>)}</div><div className="sidebar-foot"><span className="tag blue">RL, made visible</span><p>Every route has a tradeoff.<br />Explore how an agent learns it.</p></div></aside>
    <main id="main"><header className="page-header"><div><p className="eyebrow">FRESHROUTE / DECISION LABORATORY</p><h1>Every read is a <em>decision.</em></h1><p>Follow the route. Understand the tradeoff.</p></div><span className="tag"><span className="dot green-dot" /> {tab === 'live' ? 'Live laboratory' : 'Captured replay'}</span></header>
      {error ? <p className="error" role="alert">{error}</p> : null}
      {tab === 'live' ? <LiveLab /> : tab === 'decisions' ? <>
        <div className="toolbar"><div className="run-identity"><span className="run-icon">◈</span><div><strong>{row?.scenario.replaceAll('-', ' ') ?? 'Captured episode'}</strong><small>{row?.policy ?? 'RL agent'} · seed {row?.seed ?? '—'} · immutable replay</small></div></div><div className="toolbar-actions"><label className="file-button">Open trace<input type="file" aria-label="Open decision trace" accept=".jsonl" onChange={event => { void openTrace(event.target.files?.[0]); event.target.value = '' }} /></label><label className="filter-label"><span className="sr-only">Event filter</span><select aria-label="Event filter" value={filter} onChange={event => { setFilter(event.target.value); setCursor(0); setPlaying(false) }}><option value="all">All decisions</option><option value="stale">Freshness violations</option><option value="failed">Failed requests</option></select></label></div></div>
        {row ? <><div className="playback panel"><div className="playback-buttons"><button className="primary" onClick={() => setPlaying(value => !value)} disabled={cursor >= visible.length - 1}>{playing ? 'Ⅱ Pause' : '▶ Play'}</button><button aria-label="Previous decision" disabled={cursor === 0} onClick={() => { setPlaying(false); setCursor(value => value - 1) }}>←</button><button aria-label="Next decision" disabled={cursor >= visible.length - 1} onClick={() => { setPlaying(false); setCursor(value => value + 1) }}>→</button><button onClick={() => { setPlaying(false); setCursor(0) }}>Reset</button></div><label className="seek-label"><span>Request <strong>{row.step + 1}</strong> / {decisions.length}</span><input aria-label="Replay position" type="range" min="0" max={visible.length - 1} value={cursor} onChange={event => { setPlaying(false); setCursor(Number(event.target.value)) }} /></label><select aria-label="Playback speed" value={speed} onChange={event => setSpeed(Number(event.target.value))}><option value="1600">0.5×</option><option value="800">1×</option><option value="200">4×</option></select><label className="snapshot-label"><input type="checkbox" checked={snapshot} onChange={event => setSnapshot(event.target.checked)} /> Show next state</label></div><OutcomeCards row={row} /><div className="lab-grid"><Topology row={row} snapshot={snapshot} /><Inspector row={row} /></div><LatencyChart decisions={decisions} current={row.step} /><p className="page-footnote">Snapshot at dispatch · latest freshness does not imply linearizability · simulation time {(row.observation.clock_ms / 1000).toFixed(2)} s</p></> : <p role="status">{decisions.length ? 'No requests match this filter.' : 'Loading captured decisions…'}</p>}
      </> : <>{training.length ? <section className="panel training-panel"><div className="panel-heading"><div><p className="eyebrow">ACTUAL ENVIRONMENT INTERACTION</p><h2>Learning from experience</h2></div><span className="tag">{training.length} recorded episodes</span></div><TrainingCurve episodes={training} /><p className="helper">Raw episode returns. Exploration and changing scenarios create variability; the curve is not smoothed or a promise of convergence.</p></section> : null}{evaluation ? <Comparison results={evaluation.results} split={evaluation.split} episodes={evaluation.episodes_per_scenario} /> : null}</>}
    </main></div>
}

function TrainingCurve({ episodes }: { episodes: {episode: number; return: number}[] }) {
  const low = Math.min(...episodes.map(row => row.return)); const high = Math.max(...episodes.map(row => row.return))
  const points = episodes.map((row, index) => `${index / Math.max(1, episodes.length - 1) * 1000},${140 - (row.return - low) / (high - low || 1) * 120}`).join(' ')
  return <svg className="latency-chart" viewBox="0 0 1000 160" role="img" aria-label={`Raw training returns over ${episodes.length} episodes`}><polyline fill="none" className="response-line" points={points} /></svg>
}
