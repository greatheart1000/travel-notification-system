interface WorkflowDashboardPageProps {
  onNavigate: (path: string) => void
}

const dashboardCards = [
  { label: '进行中的团', value: 3, color: 'text-cyan-600', path: '/dashboard/ongoing-trips' },
  { label: '待发通知', value: 8, color: 'text-orange-600', path: '/dashboard/pending-notifications' },
]

export function WorkflowDashboardPage({ onNavigate }: WorkflowDashboardPageProps) {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">仪表盘</h1>
      <div className="grid grid-cols-1 gap-6 max-w-3xl md:grid-cols-2">
        {dashboardCards.map((card) => (
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
