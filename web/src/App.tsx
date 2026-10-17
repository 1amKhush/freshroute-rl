import { useEffect, useState } from 'react'
import { loadDemo } from './data'
import type { Decision } from './types'

export function App() {
  const [decisions, setDecisions] = useState<Decision[]>([])
  const [error, setError] = useState('')
  useEffect(() => {
    let active = true
    loadDemo().then(data => { if (active) setDecisions(data.decisions) })
      .catch(error => { if (active) setError(String(error)) })
    return () => { active = false }
  }, [])
  return <main><h1>FreshRoute RL</h1><p>Learning where fresh reads should go.</p>
    {error ? <p role="alert">{error}</p> : <p>{decisions.length ? `${decisions.length} captured routing decisions loaded.` : 'Loading captured decisions…'}</p>}
  </main>
}
