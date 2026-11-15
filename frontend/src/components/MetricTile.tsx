interface MetricTileProps {
  title: string
  value: string
  detail?: string
  trend?: string
  trendTone?: 'good' | 'warn' | 'bad' | 'neutral'
}

const trendToneClass = {
  good: 'text-success-700',
  warn: 'text-warning-700',
  bad: 'text-danger-700',
  neutral: 'text-paper-500',
}

export function MetricTile({ title, value, detail, trend, trendTone = 'neutral' }: MetricTileProps) {
  return (
    <div className="rounded-card border border-paper-200 bg-white p-5 shadow-card">
      <p className="text-sm text-paper-500">{title}</p>
      <p className="mt-2 text-2xl font-semibold tabular-nums text-paper-900">{value}</p>
      {detail ? <p className="mt-2 text-sm text-paper-500">{detail}</p> : null}
      {trend ? <p className={`mt-3 text-xs font-medium ${trendToneClass[trendTone]}`}>{trend}</p> : null}
    </div>
  )
}
