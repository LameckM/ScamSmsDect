import { useCallback, useEffect, useState } from 'react'
import { listReviewMessages, labelReviewMessage, trainCandidate, activateCandidate, ApiError } from '../api.js'

export default function MessageReview({ moderatorKey }) {
  const [status, setStatus] = useState('pending')
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [busyId, setBusyId] = useState(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [training, setTraining] = useState(false)
  const [metrics, setMetrics] = useState(null)

  const refresh = useCallback(async () => {
    if (!moderatorKey) { setMessages([]); return }
    setLoading(true); setError('')
    try { setMessages(await listReviewMessages(moderatorKey, status)) }
    catch (err) { setError(err instanceof ApiError ? err.message : 'Could not load message reviews.') }
    finally { setLoading(false) }
  }, [moderatorKey, status])

  useEffect(() => { refresh() }, [refresh])

  async function label(reportId, value) {
    setBusyId(reportId); setError(''); setNotice('')
    try {
      await labelReviewMessage(reportId, value, moderatorKey)
      setNotice(`Message #${reportId} labelled ${value}.`)
      await refresh()
    } catch (err) { setError(err instanceof ApiError ? err.message : 'Could not save message label.') }
    finally { setBusyId(null) }
  }

  async function train() {
    setTraining(true); setError(''); setNotice(''); setMetrics(null)
    try {
      const result = await trainCandidate(moderatorKey)
      setMetrics(result.metrics)
      setNotice('Candidate model trained. Review its holdout metrics before activation.')
    } catch (err) { setError(err instanceof ApiError ? err.message : 'Training failed.') }
    finally { setTraining(false) }
  }

  async function activate() {
    setTraining(true); setError(''); setNotice('')
    try {
      const result = await activateCandidate(moderatorKey)
      setNotice(`Model activated at ${result.model_path}. Monitor false positives carefully.`)
    } catch (err) { setError(err instanceof ApiError ? err.message : 'Activation failed.') }
    finally { setTraining(false) }
  }

  return (
    <section className="review-panel">
      <div className="review-heading">
        <div><p className="eyebrow">Machine learning</p><h2>Message review & training</h2></div>
        <button className="filter-tab" onClick={refresh} disabled={loading}>Refresh</button>
      </div>
      {!moderatorKey && <p className="error-banner">Enter the moderator key above to review messages.</p>}
      <div className="review-toolbar">
        <label htmlFor="review-status">Queue</label>
        <select id="review-status" value={status} onChange={e => setStatus(e.target.value)}>
          <option value="pending">Pending</option><option value="reviewed">Reviewed</option><option value="all">All</option>
        </select>
        <span className="mono">{messages.length} messages</span>
      </div>
      {error && <p className="error-banner">{error}</p>}
      {notice && <p className="success-banner">{notice}</p>}
      {loading ? <p>Loading messages…</p> : messages.length === 0 ? <p className="empty-state">No messages in this queue.</p> : (
        <div className="review-list">
          {messages.map(item => (
            <article className="review-card" key={item.report_id}>
              <div className="review-card-meta"><strong>Report #{item.report_id}</strong><span>{new Date(item.submitted_at).toLocaleString()}</span><span>Rule score: {item.message_score}/100</span></div>
              <p className="review-message">{item.message_content}</p>
              {!!item.flags?.length && <div className="review-flags">{item.flags.map(flag => <span key={flag}>{flag}</span>)}</div>}
              <div className="review-actions">
                {item.label ? <span className="review-label">Confirmed: {item.label}</span> : <span className="review-label muted">Awaiting decision</span>}
                <button disabled={busyId === item.report_id} onClick={() => label(item.report_id, 'scam')}>Confirm scam</button>
                <button disabled={busyId === item.report_id} onClick={() => label(item.report_id, 'legitimate')}>Mark legitimate</button>
              </div>
            </article>
          ))}
        </div>
      )}
      <div className="training-card">
        <div><h3>Model management</h3><p>Train a candidate from confirmed message labels. Activation is a separate manual action.</p></div>
        <div className="training-actions">
          <button disabled={!moderatorKey || training} onClick={train}>{training ? 'Working…' : 'Train candidate'}</button>
          <button disabled={!moderatorKey || training || !metrics} onClick={activate}>Activate candidate</button>
        </div>
        {metrics && <div className="metrics-grid">
          <span>Unique examples <strong>{metrics.examples_unique}</strong></span>
          <span>Accuracy <strong>{(metrics.accuracy * 100).toFixed(1)}%</strong></span>
          <span>Scam precision <strong>{(metrics.scam_precision * 100).toFixed(1)}%</strong></span>
          <span>Scam recall <strong>{(metrics.scam_recall * 100).toFixed(1)}%</strong></span>
          <span>Scam F1 <strong>{(metrics.scam_f1 * 100).toFixed(1)}%</strong></span>
        </div>}
        <p className="muted">Metrics are based on a small holdout split and do not guarantee real-world performance. Check false positives before activation.</p>
      </div>
    </section>
  )
}
