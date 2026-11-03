const STATUS_LABELS = {
  monitoring: 'Monitoring',
  flagged: 'Flagged',
  escalated: 'Escalated',
  cleared: 'Cleared',
}

export default function StatusBadge({ status }) {
  const label = STATUS_LABELS[status] || status
  return (
    <span className="status-badge" data-status={status}>
      {label}
    </span>
  )
}
