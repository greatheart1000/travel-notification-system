import { LucideIcon } from 'lucide-react'

interface MetricTileProps {
  title: string
  value: string
  detail?: string
  trend?: string
  trendTone?: 'good' | 'warn' | 'bad' | 'neutral'
  icon: LucideIcon
}

const trendToneClass = {
  good: 'text-emerald-700 bg-emerald-50',
  warn: 'text-amber-700 bg-amber-50',
  bad: 'text-red-700 bg-red-50',
  neutral: 'text-slate-600 bg-slate-100',
}

export function MetricTile({
  title,
  value,
  detail,
  trend,
  trendTone = 'neutral',
  icon: Icon,
}: MetricTileProps) {
  return (
    <div className="rounded-xl border border-blue-100 bg-white p-6 shadow-[0_14px_40px_rgba(15,23,42,0.07)]">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-slate-600">{title}</p>
          <p className="mt-2 text-4xl font-black tracking-tight text-slate-900">{value}</p>
          {detail ? <p className="mt-2 text-sm text-slate-500">{detail}</p> : null}
        </div>
        <div className="rounded-xl bg-blue-50 p-3 text-blue-700 ring-1 ring-blue-100">
          <Icon className="h-6 w-6" />
        </div>
      </div>
      {trend ? (
        <span className={`mt-5 inline-flex rounded-full px-2.5 py-1 text-xs font-bold ${trendToneClass[trendTone]}`}>
          {trend}
        </span>
      ) : null}
    </div>
  )
}
