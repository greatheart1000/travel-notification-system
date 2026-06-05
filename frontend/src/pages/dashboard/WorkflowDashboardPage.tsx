import { useEffect, useState } from 'react'
import { FigmaTripService } from '../../services/figmaTripService'
import { notificationsApi } from '../../services/api'

interface WorkflowDashboardPageProps {
  onNavigate: (path: string) => void
}

export function WorkflowDashboardPage({ onNavigate }: WorkflowDashboardPageProps) {
  const [ongoingCount, setOngoingCount] = useState<number | null>(null)
  const [pendingCount, setPendingCount] = useState<number | null>(null)

  useEffect(() => {
    const load = async () => {
      try {
        const trips = await FigmaTripService.getAllTrips()
        setOngoingCount(trips.filter((t) => t.status === '进行中' || t.status === '即将出发').length)
      } catch { setOngoingCount(0) }

      try {
        const recent: any = await notificationsApi.listRules()
        setPendingCount(Array.isArray(recent) ? recent.length : 0)
      } catch { setPendingCount(0) }
    }
    void load()
  }, [])

  const cards = [
    { label: '进行中的团', value: ongoingCount ?? '...', color: 'text-cyan-600', path: '/dashboard/ongoing-trips' },
    { label: '待发通知', value: pendingCount ?? '...', color: 'text-orange-600', path: '/dashboard/pending-notifications' },
  ]

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">仪表盘</h1>
      <div className="grid grid-cols-1 gap-6 max-w-3xl md:grid-cols-2">
        {cards.map((card) => (
          <button
            key={card.label}
            onClick={() => onNavigate(card.path)}
            className="bg-white p-8 rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow cursor-pointer text-left"
          >
            <div className="text-gray-600 mb-2">{card.label}</div>
            <div className={`text-5xl font-bold ${card.color}`}>{card.value}</div>
          </button>
        ))}
      </div>
    </div>
  )
}
