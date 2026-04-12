import { useEffect, useState } from 'react'
import { Header } from '../components/Header'
import { Card } from '../components/Card'
import { Badge } from '../components/Badge'
import { PageState } from '../components/PageState'
import { TrendingUp, Users, Send, AlertCircle } from 'lucide-react'
import { dashboardApi, getErrorMessage } from '../services/api'
import { type DashboardStats, type RecentNotification } from '../types/api'

type LoadState = 'loading' | 'ready' | 'error' | 'empty'

const DEFAULT_STATS: DashboardStats = {
  todayNotifications: 0,
  activeTrips: 0,
  totalUsers: 0,
  pendingComplaints: 0,
  notificationSuccessRate: 0,
}

function isStatsEmpty(stats: DashboardStats): boolean {
  return (
    stats.todayNotifications === 0 &&
    stats.activeTrips === 0 &&
    stats.totalUsers === 0 &&
    stats.pendingComplaints === 0 &&
    stats.notificationSuccessRate === 0
  )
}

export function Dashboard() {
  const [loadState, setLoadState] = useState<LoadState>('loading')
  const [stats, setStats] = useState<DashboardStats>(DEFAULT_STATS)
  const [recentNotifications, setRecentNotifications] = useState<RecentNotification[]>([])
  const [errorMessage, setErrorMessage] = useState('')

  const loadData = async () => {
    setLoadState('loading')
    setErrorMessage('')

    try {
      const [statsData, recentData] = await Promise.all([
        dashboardApi.getStats(),
        dashboardApi.getRecentNotifications(10),
      ])

      setStats(statsData)
      setRecentNotifications(recentData)

      if (isStatsEmpty(statsData) && recentData.length === 0) {
        setLoadState('empty')
      } else {
        setLoadState('ready')
      }
    } catch (error) {
      setLoadState('error')
      setErrorMessage(getErrorMessage(error))
    }
  }

  useEffect(() => {
    void loadData()
  }, [])

  if (loadState === 'loading') {
    return (
      <>
        <Header />
        <div className="p-8">
          <PageState kind="loading" title="正在加载仪表盘" />
        </div>
      </>
    )
  }

  if (loadState === 'error') {
    return (
      <>
        <Header />
        <div className="p-8">
          <PageState
            kind="error"
            title="仪表盘加载失败"
            description={errorMessage}
            onRetry={() => {
              void loadData()
            }}
          />
        </div>
      </>
    )
  }

  if (loadState === 'empty') {
    return (
      <>
        <Header />
        <div className="p-8">
          <PageState
            kind="empty"
            title="仪表盘暂无数据"
            description="暂时没有统计与通知记录"
            onRetry={() => {
              void loadData()
            }}
          />
        </div>
      </>
    )
  }

  const cards = [
    {
      title: '今日发送通知',
      value: String(stats.todayNotifications),
      icon: Send,
      color: 'bg-blue-50 text-blue-600',
      trend: `${stats.notificationSuccessRate}% 成功率`,
    },
    {
      title: '活跃行程',
      value: String(stats.activeTrips),
      icon: TrendingUp,
      color: 'bg-green-50 text-green-600',
      trend: '实时',
    },
    {
      title: '用户总数',
      value: String(stats.totalUsers),
      icon: Users,
      color: 'bg-purple-50 text-purple-600',
      trend: '实时',
    },
    {
      title: '投诉待处理',
      value: String(stats.pendingComplaints),
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

        {recentNotifications.length === 0 ? (
          <PageState
            kind="empty"
            title="暂无最近通知"
            description="可稍后重试刷新"
            onRetry={() => {
              void loadData()
            }}
          />
        ) : (
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
                      <td className="py-3 px-4 font-medium text-gray-900">{notif.customerName}</td>
                      <td className="py-3 px-4 text-gray-600">{notif.trip}</td>
                      <td className="py-3 px-4">{notif.channelLabel}</td>
                      <td className="py-3 px-4">
                        <Badge variant={notif.status === 'sent' ? 'success' : 'warning'}>
                          {notif.statusLabel}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 text-gray-500">{new Date(notif.createdAt).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}
      </div>
    </>
  )
}
