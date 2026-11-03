const FLAG_THRESHOLD = Number(import.meta.env.VITE_SCORE_THRESHOLD) || 55

export default function RiskMeter({ score, threshold = FLAG_THRESHOLD }) {
  const clamped = Math.max(0, Math.min(100, score))
  const level =
    clamped >= threshold ? 'danger' : clamped >= threshold * 0.6 ? 'warning' : 'accent'

  return (
    <div
      className="risk-meter"
      title={`Risk score ${clamped}/100 — numbers are flagged at ${threshold}+`}
    >
      <div className="risk-meter-track">
        <div
          className="risk-meter-fill"
          data-level={level}
          style={{ width: `${clamped}%` }}
        />
        <div className="risk-meter-threshold" style={{ left: `${threshold}%` }} />
      </div>
      <span className="risk-meter-value mono">{clamped}</span>
    </div>
  )
}
