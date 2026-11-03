import { useCallback, useEffect, useState } from 'react'
import NumberTable from './components/NumberTable.jsx'
import NumberDetail from './components/NumberDetail.jsx'
import { listNumbers, getNumber, moderateNumber, API_BASE_URL, ApiError } from './api.js'

const FILTERS = [
  { value: 'flagged', label: 'Flagged' },
  { value: 'escalated', label: 'Escalated' },
  { value: 'monitoring', label: 'Monitoring' },
  { value: 'cleared', label: 'Cleared' },
  { value: 'all', label: 'All' },
]

const POLL_INTERVAL_MS = 8000

export default function App() {
  const [numbers, setNumbers] = useState([])
  const [filter, setFilter] = useState('flagged')
  const [selectedNumber, setSelectedNumber] = useState(null)
  const [detail, setDetail] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState(null)
  const [listError, setListError] = useState(null)
  const [moderatorKey, setModeratorKey] = useState(
    () => localStorage.getItem('scamshield_moderator_key') || ''
  )

  const refreshList = useCallback(async () => {
    try {
      const data = await listNumbers(filter)
      setNumbers(data)
      setListError(null)
    } catch (err) {
      setListError(err instanceof ApiError ? err.message : 'Could not reach the ScamShield API.')
    }
  }, [filter])

  useEffect(() => {
    refreshList()
    const id = setInterval(refreshList, POLL_INTERVAL_MS)
    return () => clearInterval(id)
  }, [refreshList])

  useEffect(() => {
    localStorage.setItem('scamshield_moderator_key', moderatorKey)
  }, [moderatorKey])

  const openDetail = useCallback(async (number) => {
    setSelectedNumber(number)
    setDetailLoading(true)
    setDetailError(null)
    try {
      const data = await getNumber(number)
      setDetail(data)
    } catch (err) {
      setDetailError(err instanceof ApiError ? err.message : 'Could not load this number.')
      setDetail(null)
    } finally {
      setDetailLoading(false)
    }
  }, [])

  const handleModerate = useCallback(
    async (number, action) => {
      setDetailError(null)
      try {
        await moderateNumber(number, action, moderatorKey)
        await openDetail(number)
        await refreshList()
      } catch (err) {
        setDetailError(err instanceof ApiError ? err.message : 'Moderation action failed.')
      }
    },
    [moderatorKey, openDetail, refreshList]
  )

  const closeDetail = () => {
    setSelectedNumber(null)
    setDetail(null)
    setDetailError(null)
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <p className="eyebrow">ScamShield</p>
          <h1>Moderation console</h1>
        </div>
        <div className="header-controls">
          <span className="api-indicator mono">{API_BASE_URL}</span>
          <input
            type="password"
            className="moderator-key-input"
            placeholder="Moderator key"
            value={moderatorKey}
            onChange={(e) => setModeratorKey(e.target.value)}
          />
        </div>
      </header>

      <nav className="filter-tabs">
        {FILTERS.map((f) => (
          <button
            key={f.value}
            className={`filter-tab ${filter === f.value ? 'is-active' : ''}`}
            onClick={() => setFilter(f.value)}
          >
            {f.label}
          </button>
        ))}
      </nav>

      {listError && <p className="error-banner">{listError}</p>}

      <main className={`main-layout ${selectedNumber ? 'has-detail' : ''}`}>
        <NumberTable numbers={numbers} onSelect={openDetail} selectedNumber={selectedNumber} />
        {selectedNumber && (
          <NumberDetail
            detail={detail}
            isLoading={detailLoading}
            error={detailError}
            moderatorKey={moderatorKey}
            onModerate={handleModerate}
            onClose={closeDetail}
          />
        )}
      </main>
    </div>
  )
}
