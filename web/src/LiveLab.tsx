import { useCallback, useEffect, useState } from 'react'
import { BranchResults, Inspector, LatencyChart, OutcomeCards, Topology } from './components'
import { jsonRequest } from './data'
import type { Counterfactual, Decision, Model, Session } from './types'
import { regions } from './types'

const post = (body: unknown): RequestInit => ({ method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })

export function LiveLab() {
  const [models, setModels] = useState<Model[]>([])
  const [model, setModel] = useState('q-learning')
  const [scenario, setScenario] = useState('balanced')
  const [seed, setSeed] = useState(110000)
  const [session, setSession] = useState<Session | null>(null)
  const [records, setRecords] = useState<Decision[]>([])
  const [busy, setBusy] = useState(false)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [kind, setKind] = useState('outage')
  const [replica, setReplica] = useState(0)
  const [duration, setDuration] = useState(20)
  const [value, setValue] = useState(100)
  const [branches, setBranches] = useState<Counterfactual | null>(null)
  const row = records.at(-1)
  const complete = !!row && (row.truncated || row.terminated)

  useEffect(() => {
    let active = true
    jsonRequest<Model[]>('/api/models').then(result => { if (active) { setModels(result); if (result.some(model => model.id === 'dqn')) setModel('dqn') } })
      .catch(() => { if (active) setError('The live laboratory is unavailable. Start the local server using the README instructions, then reopen this view.') })
    return () => { active = false }
  }, [])

  useEffect(() => {
    if (!session) return
    return () => { void fetch(`/api/sessions/${session.id}`, { method: 'DELETE' }).catch(() => {}) }
  }, [session])

  const step = useCallback(async (id: string) => {
    setBusy(true); setError(''); setBranches(null)
    try {
      const result = await jsonRequest<Decision>(`/api/sessions/${id}/step`, post({}))
      setRecords(rows => [...rows, result]); setNotice('')
      if (result.truncated || result.terminated) { setRunning(false); setNotice('Episode complete. Reset to begin the same seeded episode again.') }
    } catch (error) { setError(String(error)); setRunning(false) }
    finally { setBusy(false) }
  }, [])

  useEffect(() => {
    if (!running || busy || !session || complete) return
    const timer = window.setTimeout(() => { void step(session.id) }, 600)
    return () => window.clearTimeout(timer)
  }, [running, busy, session, complete, records.length, step])

  async function begin() {
    setBusy(true); setRunning(false); setError(''); setBranches(null)
    try {
      const result = await jsonRequest<Session>('/api/sessions', post({ model_id: model, scenario, seed }))
      setSession(result); setRecords([]); await step(result.id)
    } catch (error) { setError(String(error)) }
    finally { setBusy(false) }
  }

  async function inject() {
    if (!session) return
    setBusy(true); setRunning(false); setError(''); setBranches(null)
    try {
      await jsonRequest(`/api/sessions/${session.id}/faults`, post({ kind, replica, duration_steps: duration, value }))
      setNotice(`${kind === 'restore' ? 'Restoration' : kind} applied to ${regions[replica]}. Step to observe the next routing decision.`)
    } catch (error) { setError(String(error)) }
    finally { setBusy(false) }
  }

  async function explain() {
    if (!session) return
    setBusy(true); setRunning(false); setError('')
    try { setBranches(await jsonRequest<Counterfactual>(`/api/sessions/${session.id}/counterfactuals`, post({ horizon: 8 }))) }
    catch (error) { setError(String(error)) }
    finally { setBusy(false) }
  }

  return <>
    <form className="panel live-controls" onSubmit={event => { event.preventDefault(); void begin() }}>
      <div className="panel-heading"><div><p className="eyebrow">FROZEN POLICY · LIVE SIMULATOR</p><h2>Change conditions. Watch the policy respond.</h2></div><span className="tag">Isolated session</span></div>
      <div className="live-form"><label>Model<select aria-label="Live model" value={model} disabled={!!session || busy} onChange={event => setModel(event.target.value)}>{models.map(model => <option value={model.id} key={model.id}>{model.label}</option>)}</select></label><label>Workload<select aria-label="Live workload" disabled={!!session || busy} value={scenario} onChange={event => setScenario(event.target.value)}>{['balanced', 'write-burst', 'regional-outage', 'traffic-shift'].map(value => <option key={value} value={value}>{value.replaceAll('-', ' ')}</option>)}</select></label><label>Workload seed<input aria-label="Live seed" type="number" min="100000" max="199999" required disabled={!!session || busy} value={seed} onChange={event => setSeed(Number(event.target.value))} /></label><button className="primary" disabled={busy || !models.length}>{session ? 'Reset session' : 'Start session'}</button>{session ? <button type="button" disabled={busy} onClick={() => { setRunning(false); setSession(null); setRecords([]); setBranches(null); setNotice('') }}>End session</button> : null}</div>
    </form>
    {error ? <p className="error" role="alert">{error}</p> : null}{notice ? <p className="notice" role="status">{notice}</p> : null}
    {session ? <><div className="live-actions"><button className="primary" disabled={busy || complete} onClick={() => { void step(session.id) }}>Step live request</button><button disabled={complete} onClick={() => setRunning(value => !value)}>{running ? 'Pause live' : 'Run live'}</button><span className="tag mono">seed {session.seed} · {records.length} / 160 requests</span><a href={`/api/sessions/${session.id}/trace`} download="decisions.jsonl">Export trace</a><a href={`/api/sessions/${session.id}/manifest`} download="manifest.json">Manifest</a></div>
      <form className="panel fault-controls" onSubmit={event => { event.preventDefault(); void inject() }}><div><p className="eyebrow">FAULT INJECTION</p><p>Changes affect the next read; previous records stay unchanged.</p></div><label>Fault<select aria-label="Fault kind" value={kind} onChange={event => { setKind(event.target.value); if (event.target.value === 'lag' && replica === 1) setReplica(0) }}><option value="outage">Replica outage</option><option value="lag">Replication lag</option><option value="load">Background load</option><option value="restore">Restore replica</option></select></label><label>Replica<select aria-label="Fault replica" value={replica} onChange={event => setReplica(Number(event.target.value))}>{regions.map((name, id) => kind === 'lag' && id === 1 ? null : <option key={name} value={id}>{name}</option>)}</select></label><label>Duration (reads)<input aria-label="Fault duration" type="number" min="1" max="160" value={duration} onChange={event => setDuration(Number(event.target.value))} required /></label>{['lag', 'load'].includes(kind) ? <label>Extra delay / work (ms)<input aria-label="Fault magnitude" type="number" min="0" max="1000" value={value} onChange={event => setValue(Number(event.target.value))} required /></label> : null}<button disabled={busy || complete}>Apply fault</button></form>
      {row ? <><OutcomeCards row={row} /><div className="lab-grid"><Topology row={row} snapshot={false} /><Inspector row={row} /></div><div className="explain-control"><button disabled={busy} onClick={() => { void explain() }}>Compare all choices from this snapshot</button><span>Same simulator and random state · 8-step policy rollout</span></div>{branches ? <BranchResults result={branches} /> : null}<LatencyChart decisions={records} current={row.step} /></> : <p role="status">Preparing the first live read…</p>}
    </> : !error ? <p className="empty-live">Choose a trained model, workload, and seed. Start a session to route a real simulated request.</p> : null}
  </>
}
