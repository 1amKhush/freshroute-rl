import { useEffect, useState } from 'react'
import { loadDemo } from './data'
import type { Decision } from './types'
import { Inspector, Mark, OutcomeCards, Topology } from './components'

export function App() {
  const [decisions, setDecisions] = useState<Decision[]>([])
  const [error, setError] = useState('')
  useEffect(() => {
    let active = true
    loadDemo().then(data => { if (active) setDecisions(data.decisions) })
      .catch(error => { if (active) setError(String(error)) })
    return () => { active = false }
  }, [])
  return <div className="app-shell"><a className="skip-link" href="#main">Skip to decisions</a><aside className="sidebar"><a className="brand" href="/"><Mark /><span>FreshRoute<small>REINFORCEMENT LEARNING LAB</small></span></a><div className="sidebar-section"><p className="eyebrow">WORKSPACE</p><span className="nav-item current">◈ Decision explorer</span></div><div className="learning-loop"><p className="eyebrow">THE LEARNING LOOP</p>{['Receive a read request', 'Observe replica conditions', 'Choose where to read', 'Learn from the outcome'].map((label, i) => <div key={label}><span>{i + 1}</span>{label}</div>)}</div><div className="sidebar-foot"><span className="tag blue">RL, made visible</span><p>Every route has a tradeoff.<br />Explore how an agent learns it.</p></div></aside><main id="main"><header className="page-header"><div><p className="eyebrow">FRESHROUTE / DECISION LABORATORY</p><h1>Every read is a <em>decision.</em></h1><p>Follow the route. Understand the tradeoff.</p></div><span className="tag"><span className="dot green-dot" /> Captured replay</span></header>{error ? <p className="error" role="alert">{error}</p> : decisions.length ? <><OutcomeCards row={decisions[0]} /><div className="lab-grid"><Topology row={decisions[0]} snapshot={false} /><Inspector row={decisions[0]} /></div></> : <p role="status">Loading captured decisions…</p>}</main></div>
}
