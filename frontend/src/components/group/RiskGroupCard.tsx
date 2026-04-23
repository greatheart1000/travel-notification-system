import type { RiskGroup } from '../../modules/groups/types'
import { StatusPill } from '../common/StatusPill'

interface RiskGroupCardProps {
  group: RiskGroup
  onOpen: (groupId: string) => void
}

function riskTone(level: RiskGroup['riskLevel']): 'danger' | 'warning' | 'info' {
  if (level === 'critical') return 'danger'
  if (level === 'high') return 'warning'
  return 'info'
}

export function RiskGroupCard({ group, onOpen }: RiskGroupCardProps) {
  return (
    <button
      onClick={() => onOpen(group.id)}
      className="w-full rounded-xl border border-rose-100 bg-white p-4 text-left shadow-sm transition hover:-translate-y-0.5 hover:shadow"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-base font-semibold text-slate-900">{group.groupName}</p>
          <p className="mt-1 text-sm text-slate-500">{group.routeName}</p>
        </div>
        <StatusPill tone={riskTone(group.riskLevel)} label={`风险 ${group.riskLevel.toUpperCase()}`} />
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
        <p className="text-slate-600">出发：{new Date(group.departureDate).toLocaleString()}</p>
        <p className="text-slate-600">风险分：{group.riskScore}</p>
        <p className="text-slate-600">待处理任务：{group.pendingTaskCount}</p>
        <p className="text-slate-600">负责人：{group.owner}</p>
      </div>
      <p className="mt-3 text-sm text-slate-700">{group.summary}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {group.riskTags.map((tag) => (
          <span key={tag} className="rounded-md bg-rose-50 px-2 py-1 text-xs text-rose-600">
            {tag}
          </span>
        ))}
      </div>
    </button>
  )
}
