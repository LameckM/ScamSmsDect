import StatusBadge from './StatusBadge.jsx'
import RiskMeter from './RiskMeter.jsx'

export default function NumberTable({ numbers, onSelect, selectedNumber }) {
  if (numbers.length === 0) {
    return (
      <p className="empty-state">
        No numbers in this view yet. Reports will appear here as they come in.
      </p>
    )
  }

  return (
    <table className="number-table">
      <thead>
        <tr>
          <th>Number</th>
          <th>Reports</th>
          <th>Risk score</th>
          <th>Status</th>
          <th>Last updated</th>
        </tr>
      </thead>
      <tbody>
        {numbers.map((n) => (
          <tr
            key={n.number}
            className={n.number === selectedNumber ? 'is-selected' : ''}
            onClick={() => onSelect(n.number)}
          >
            <td className="mono">{n.number}</td>
            <td className="mono">{n.report_count}</td>
            <td>
              <RiskMeter score={n.aggregate_score} />
            </td>
            <td>
              <StatusBadge status={n.status} />
            </td>
            <td className="text-secondary">{new Date(n.updated_at).toLocaleString()}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
