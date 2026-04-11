import { useEffect, useState } from 'react'
import { Header } from '../components/Header'
import { Card } from '../components/Card'
import { Badge } from '../components/Badge'
import { TrendingUp, Users, Send, AlertCircle } from 'lucide-react'
import { dashboardApi } from '../services/api'

export function Dashboard() {
  const [stats, setStats] = useState({
    today_notifications: 0,
    active_trips: 0,
    total_users: 0,
    pending_complaints: 0,
    notification_success_rate: 0,
  })
  const [recentNotifications, setRecentNotifications] = useState<any[]>([])

  useEffect(() => {
    dashboardApi.getStats().then((res) => setStats(res.data))
    dashboardApi.getRecentNotifications(10).then((res) => setRecentNotifications(res.data.items))
  }, [])

  const cards = [
    {
      title: '今日发送通知',
      value: String(stats.today_notifications),
      icon: Send,
      color: 'bg-blue-50 text-blue-600',
      trend: `${stats.notification_success_rate}% 成功率`,
    },
    {
      title: '活跃行程',
      value: String(stats.active_trips),
      icon: TrendingUp,
      color: 'bg-green-50 text-green-600',
      trend: '实时',
    },
    {
      title: '用户总数',
      value: String(stats.total_users),
      icon: Users,
      color: 'bg-purple-50 text-purple-600',
      trend: '实时',
    },
    {
      title: '投诉待处理',
      value: String(stats.pending_complaints),
      icon: AlertCircle,
      color: 'bg-red-50 text-red-600',
      trend: '实时',
    },
  ]

  return (
    <>
      <Header />
      <div className="p-8">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {cards.map((stat) => {
            const Icon = stat.icon
            return (
              <Card key={stat.title}>
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-sm text-gray-600 mb-1">{stat.title}</p>
                    <p className="text-3xl font-bold text-gray-900">{stat.value}</p>
                    <p className="text-xs text-green-600 mt-2">{stat.trend}</p>
                  </div>
                  <div className={`p-3 rounded-lg ${stat.color}`}>
                    <Icon className="w-6 h-6" />
                  </div>
                </div>
              </Card>
            )
          })}
        </div>

        <Card title="最近的通知">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-4 font-semibold text-gray-700">客户</th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-700">行程</th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-700">渠道</th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-700">状态</th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-700">时间</th>
                </tr>
              </thead>
              <tbody>
                {recentNotifications.map((notif) => (
                  <tr key={notif.id} className="border-b border-gray-100 hover:bg-gray-50 transition">
                    <td className="py-3 px-4 font-medium text-gray-900">{notif.customer_name}</td>
                    <td className="py-3 px-4 text-gray-600">{notif.trip}</td>
                    <td className="py-3 px-4">{notif.channel}</td>
                    <td className="py-3 px-4">
                      <Badge variant={notif.status === 'sent' ? 'success' : 'warning'}>
                        {notif.status}
                      </Badge>
                    </td>
                    <td className="py-3 px-4 text-gray-500">{new Date(notif.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </>
  )
}
