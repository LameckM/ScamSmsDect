import { useState } from 'react'
import StatusBadge from './StatusBadge.jsx'
import RiskMeter from './RiskMeter.jsx'

export default function NumberDetail({ detail, moderatorKey, onModerate, onClose, isLoading, error }) {
  const [actionPending, setActionPending] = useState(null)

  if (isLoading) {
    return (
      <aside className="detail-panel">
        <p className="text-secondary">Loading…</p>
      </aside>
    )
  }

  if (!detail) return null

  const canModerate = Boolean(moderatorKey)

  const handleAction = async (action) => {
    setActionPending(action)
    await onModerate(detail.number, action)
    setActionPending(null)
  }

  return (
    <aside className="detail-panel">
      <div className="detail-header">
        <div>
          <p className="eyebrow">Reported number</p>
          <h2 className="mono">{detail.number}</h2>
        </div>
        <button className="btn-ghost" onClick={onClose} aria-label="Close detail panel">
          ✕
        </button>
      </div>

      <div className="detail-summary">
        <StatusBadge status={detail.status} />
        <RiskMeter score={detail.aggregate_score} />
        <span className="text-secondary">
          {detail.report_count} report{detail.report_count === 1 ? '' : 's'}
        </span>
      </div>

      {error && <p className="error-banner">{error}</p>}

      {!canModerate && (
        <p className="hint-banner">Enter a moderator key above to confirm or dismiss this number.</p>
      )}

      <div className="detail-actions">
        <button
          className="btn-danger"
          disabled={!canModerate || actionPending !== null}
          onClick={() => handleAction('escalate')}
        >
          {actionPending === 'escalate' ? 'Confirming…' : 'Confirm & escalate'}
        </button>
        <button
          className="btn-secondary"
          disabled={!canModerate || actionPending !== null}
          onClick={() => handleAction('clear')}
        >
          {actionPending === 'clear' ? 'Dismissing…' : 'Dismiss as false positive'}
        </button>
        {detail.status !== 'monitoring' && (
          <button
            className="btn-ghost"
            disabled={!canModerate || actionPending !== null}
            onClick={() => handleAction('reset')}
          >
            {actionPending === 'reset' ? 'Resetting…' : 'Reset to automatic'}
          </button>
        )}
      </div>

      <h3 className="section-label">Reported messages</h3>
      <ul className="message-list">
        {detail.reports.map((r) => (
          <li key={r.id} className="message-item">
            <p className="message-content">{r.message_content}</p>
            <div className="message-meta">
              <span className="mono">{r.message_score}/100</span>
              <span className="text-secondary">{new Date(r.created_at).toLocaleString()}</span>
            </div>
            {r.flags.length > 0 && (
              <div className="flag-list">
                {r.flags.map((flag) => (
                  <span key={flag} className="flag-chip">
                    {flag}
                  </span>
                ))}
              </div>
            )}
          </li>
        ))}
      </ul>
    </aside>
  )
}
