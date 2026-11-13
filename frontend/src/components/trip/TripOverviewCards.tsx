import { CalendarDays, Map, Phone, Users } from 'lucide-react'
import { type TripDetailViewModel } from '../../features/trip-management/tripDetailMapper'

interface TripOverviewCardsProps {
  detail: TripDetailViewModel
}

export function TripOverviewCards({ detail }: TripOverviewCardsProps) {
  const routeText = detail.routeOverview

  const items = [
    { label: '团名称', value: detail.destination || '未设置', helper: '旅行团名称', icon: Map },
    { label: '团号', value: detail.teamId || '未设置', helper: '旅行团编号', icon: Map },
    { label: '状态', value: detail.statusLabel || '状态未知', helper: detail.statusCode || 'unknown', icon: Map },
    {
      label: '日期',
      value: `${detail.startDate || '待定'} 至 ${detail.endDate || '待定'}`,
      helper: '出发 / 结束',
      icon: CalendarDays,
    },
    { label: '游客人数', value: `${detail.travelerCount} 人`, helper: '按客人名单优先统计', icon: Users },
    { label: '领队联系', value: detail.leaderName || '未配置', helper: detail.contactPhone || '暂无联系方式', icon: Phone },
  ]

  return (
    <div className="space-y-5">
      <div className="rounded-card border border-paper-200 bg-white p-5 shadow-card">
        <h2 className="text-lg font-semibold text-paper-900">{detail.destination}</h2>
        <p className="mt-2 text-sm text-paper-600">{routeText}</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {items.map((item) => (
          <div key={item.label} className="rounded-card border border-paper-200 bg-white p-4 shadow-card">
            <p className="text-xs text-paper-500">{item.label}</p>
            <p className="mt-2 text-base font-medium text-paper-900">{item.value}</p>
            <p className="mt-1 text-xs text-paper-500">{item.helper}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
