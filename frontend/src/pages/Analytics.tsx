import { useEffect, useState } from 'react'
import { Header } from '../components/Header'
import { Card } from '../components/Card'
import { Badge } from '../components/Badge'
import { PageState } from '../components/PageState'
import { BarChart3, TrendingUp, Clock, CheckCircle } from 'lucide-react'
import { analyticsApi, getErrorMessage } from '../services/api'
import { type AnalyticsData } from '../types/api'

type LoadState = 'loading' | 'ready' | 'error' | 'empty'

export function Analytics() {
  const [loadState, setLoadState] = useState<LoadState>('loading')
  const [errorMessage, setErrorMessage] = useState('')
  const [analyticsData, setAnalyticsData] = useState<AnalyticsData | null>(null)

  const loadData = async () => {
    setLoadState('loading')
    setErrorMessage('')

    try {
      const data = await analyticsApi.metrics()
      setAnalyticsData(data)

      if (data.channelPerformance.length === 0 && data.topTrips.length === 0) {
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
          <PageState kind="loading" title="正在加载数据分析" />
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
            title="数据分析加载失败"
            description={errorMessage}
            onRetry={() => {
              void loadData()
            }}
          />
        </div>
      </>
    )
  }

  if (loadState === 'empty' || !analyticsData) {
    return (
      <>
        <Header />
        <div className="p-8">
          <PageState
            kind="empty"
            title="暂无分析数据"
            description="当前没有可展示的渠道和行程指标"
            onRetry={() => {
              void loadData()
            }}
          />
        </div>
      </>
    )
  }

  const metrics = [
    {
      title: '通知成功率',
      value: analyticsData.metrics.notificationSuccessRate,
      icon: CheckCircle,
      color: 'bg-green-50 text-green-600',
      change: '实时',
    },
    {
      title: '平均响应时间',
      value: analyticsData.metrics.avgResponseTime,
      icon: Clock,
      color: 'bg-blue-50 text-blue-600',
      change: '实时',
    },
    {
      title: '周环比增长',
      value: analyticsData.metrics.wowGrowth,
      icon: TrendingUp,
      color: 'bg-purple-50 text-purple-600',
      change: '实时',
    },
    {
      title: '用户满意度',
      value: analyticsData.metrics.userSatisfaction,
      icon: BarChart3,
      color: 'bg-orange-50 text-orange-600',
      change: '实时',
    },
  ]

  return (
    <>
      <Header />
      <div className="p-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">数据分析</h1>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {metrics.map((metric) => {
            const Icon = metric.icon
            return (
              <Card key={metric.title}>
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-sm text-gray-600 mb-1">{metric.title}</p>
                    <p className="text-3xl font-bold text-gray-900">{metric.value}</p>
                    <p className="text-xs text-green-600 mt-2">{metric.change}</p>
                  </div>
                  <div className={`p-3 rounded-lg ${metric.color}`}>
                    <Icon className="w-6 h-6" />
                  </div>
                </div>
              </Card>
            )
          })}
        </div>

        <Card title="渠道性能" className="mb-6">
          {analyticsData.channelPerformance.length === 0 ? (
            <PageState
              kind="empty"
              title="暂无渠道性能数据"
              onRetry={() => {
                void loadData()
              }}
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 px-4 font-semibold text-gray-700">渠道</th>
                    <th className="text-left py-3 px-4 font-semibold text-gray-700">总发送</th>
                    <th className="text-left py-3 px-4 font-semibold text-gray-700">成功</th>
                    <th className="text-left py-3 px-4 font-semibold text-gray-700">失败</th>
                    <th className="text-left py-3 px-4 font-semibold text-gray-700">成功率</th>
                  </tr>
                </thead>
                <tbody>
                  {analyticsData.channelPerformance.map((channel) => (
                    <tr key={channel.channel} className="border-b border-gray-100 hover:bg-gray-50 transition">
                      <td className="py-3 px-4 font-medium text-gray-900">{channel.channelLabel}</td>
                      <td className="py-3 px-4 text-gray-600">{channel.sent}</td>
                      <td className="py-3 px-4">
                        <Badge variant="success">{channel.successful}</Badge>
                      </td>
                      <td className="py-3 px-4">
                        <Badge variant="danger">{channel.failed}</Badge>
                      </td>
                      <td className="py-3 px-4 font-semibold text-green-600">{channel.rate}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <Card title="热门行程排行">
          {analyticsData.topTrips.length === 0 ? (
            <PageState
              kind="empty"
              title="暂无热门行程"
              onRetry={() => {
                void loadData()
              }}
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 px-4 font-semibold text-gray-700">行程</th>
                    <th className="text-left py-3 px-4 font-semibold text-gray-700">通知数</th>
                    <th className="text-left py-3 px-4 font-semibold text-gray-700">用户满意度</th>
                    <th className="text-left py-3 px-4 font-semibold text-gray-700">评级</th>
                  </tr>
                </thead>
                <tbody>
                  {analyticsData.topTrips.map((trip) => (
                    <tr key={trip.name} className="border-b border-gray-100 hover:bg-gray-50 transition">
                      <td className="py-3 px-4 font-medium text-gray-900">{trip.name}</td>
                      <td className="py-3 px-4 text-gray-600">{trip.notifications}</td>
                      <td className="py-3 px-4">{trip.satisfaction}/5.0</td>
                      <td className="py-3 px-4">
                        <Badge variant={trip.satisfaction >= 4.5 ? 'success' : 'warning'}>
                          {'⭐'.repeat(Math.max(1, Math.round(trip.satisfaction)))}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </>
  )
}
