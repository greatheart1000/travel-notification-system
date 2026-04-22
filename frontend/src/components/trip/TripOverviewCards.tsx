import { CalendarDays, Map, Phone, Users } from 'lucide-react'
import { type TripDetailViewModel } from '../../features/trip-management/tripDetailMapper'

interface TripOverviewCardsProps {
  detail: TripDetailViewModel
}

export function TripOverviewCards({ detail }: TripOverviewCardsProps) {
  const routeText = detail.routeOverview

  const items = [
    {
      label: '团名称',
      value: detail.destination || '未设置',
      helper: '旅行团名称',
      icon: Map,
    },
    {
      label: '团号',
      value: detail.teamId || '未设置',
      helper: '旅行团编号',
      icon: Map,
    },
    {
      label: '状态',
      value: detail.statusLabel || '状态未知',
      helper: detail.statusCode || 'unknown',
      icon: Map,
    },
    {
      label: '日期',
      value: `${detail.startDate || '待定'} 至 ${detail.endDate || '待定'}`,
      helper: '出发 / 结束',
      icon: CalendarDays,
    },
    {
      label: '游客人数',
      value: `${detail.travelerCount} 人`,
      helper: '按客人名单优先统计',
      icon: Users,
    },
    {
      label: '领队联系',
      value: detail.leaderName || '未配置',
      helper: detail.contactPhone || '暂无联系方式',
      icon: Phone,
    },
  ]

  return (
    <div className="space-y-5">
      <div className="rounded-[2rem] border border-blue-100 bg-white/90 p-6 shadow-[0_20px_60px_rgba(15,23,42,0.08)]">
        <p className="mb-3 text-xs font-black uppercase tracking-[0.28em] text-blue-700">
          Route Overview
        </p>
        <h2 className="text-2xl font-black tracking-tight text-slate-950">{detail.destination}</h2>
        <p className="mt-3 text-base font-semibold text-slate-700">{routeText}</p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
        {items.map((item) => {
          const Icon = item.icon
          return (
            <div key={item.label} className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
              <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-2xl bg-blue-50 text-blue-700">
                <Icon className="h-5 w-5" />
              </div>
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-slate-400">{item.label}</p>
              <p className="mt-2 text-lg font-black text-slate-950">{item.value}</p>
              <p className="mt-1 text-sm text-slate-500">{item.helper}</p>
            </div>
          )
        })}
      </div>
    </div>
  )
}
