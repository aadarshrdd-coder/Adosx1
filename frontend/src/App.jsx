import { useEffect, useState } from 'react'
import './App.css'

const API = `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/disagreements/`
const reasons = [
  '',
  'MISSING_IN_B',
  'ORPHAN_IN_B',
  'DUPLICATE_IN_B',
  'VALUE_MISMATCH',
  'LOCATION_MISMATCH',
  'DATE_MISMATCH',
]

function App() {
  const [org, setOrg] = useState('ORG-A')
  const [reason, setReason] = useState('')
  const [sort, setSort] = useState('value')
  const [result, setResult] = useState(null)
  const params = new URLSearchParams({ org, sort })
  if (reason) params.set('reason', reason)
  const query = params.toString()
  const isCurrentResult = result?.query === query
  const rows = isCurrentResult && !result.error ? result.rows : []
  const error = isCurrentResult ? result.error : ''
  const loading = !isCurrentResult

  useEffect(() => {
    const controller = new AbortController()
    fetch(`${API}?${query}`, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error(`API returned ${response.status}`)
        return response.json()
      })
      .then((data) => {
        if (!Array.isArray(data)) throw new Error('API returned an invalid response')
        if (!controller.signal.aborted) setResult({ query, rows: data })
      })
      .catch((cause) => {
        if (cause.name !== 'AbortError' && !controller.signal.aborted) {
          setResult({ query, rows: [], error: cause.message })
        }
      })

    return () => controller.abort()
  }, [query])

  function toggleValueSort() {
    setSort((current) => current === 'value' ? '-value' : 'value')
  }

  return (
    <main>
      <h1>DealerOS Reconciliation</h1>
      <div className="filters">
        <label>
          Org
          <select value={org} onChange={(event) => setOrg(event.target.value)}>
            <option value="ORG-A">ORG-A</option>
            <option value="ORG-B">ORG-B</option>
          </select>
        </label>
        <label>
          Reason
          <select value={reason} onChange={(event) => setReason(event.target.value)}>
            {reasons.map((value) => (
              <option key={value} value={value}>{value || 'All reasons'}</option>
            ))}
          </select>
        </label>
      </div>

      {error && <p role="alert">{error}</p>}
      <table>
        <thead>
          <tr>
            <th>Reason</th>
            <th>Record ID</th>
            <th>Location</th>
            <th>System A value</th>
            <th>
              <button type="button" className="sort-button" onClick={toggleValueSort}>
                System B value {sort.startsWith('-') ? '↓' : '↑'}
              </button>
            </th>
            <th>Difference</th>
          </tr>
        </thead>
        <tbody>
          {!loading && rows.map((row) => (
            <tr key={`${row.reason}-${row.record_id}`}>
              <td>{row.reason}</td>
              <td>{row.record_id}</td>
              <td>{row.location || ''}</td>
              <td>{row.a_value ?? ''}</td>
              <td>{row.b_value ?? ''}</td>
              <td>{row.difference ?? ''}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {loading && <p role="status">Loading disagreements...</p>}
      {!loading && !error && rows.length === 0 && <p>No disagreements found.</p>}
    </main>
  )
}

export default App
