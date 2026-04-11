import { useEffect, useState } from 'react'
import { Header } from '../components/Header'
import { Card } from '../components/Card'
import { Badge } from '../components/Badge'
import { BarChart3, TrendingUp, Clock, CheckCircle } from 'lucide-react'
import { analyticsApi } from '../services/api'

export function Analytics() {
  const [metricsData, setMetricsData] = useState<any>(null)

  useEffect(() => {
    analyticsApi.metrics().then((res) => setMetricsData(res.data))
  }, [])

  const metrics = [
    { title: '通知成功率', value: metricsData?.metrics?.notification_success_rate ?? '-', icon: CheckCircle, color: 'bg-green-50 text-green-600', change: '实时' },
    { title: '平均响应时间', value: metricsData?.metrics?.avg_response_time ?? '-', icon: Clock, color: 'bg-blue-50 text-blue-600', change: '实时' },
    { title: '周环比增长', value: metricsData?.metrics?.wow_growth ?? '-', icon: TrendingUp, color: 'bg-purple-50 text-purple-600', change: '实时' },
    { title: '用户满意度', value: metricsData?.metrics?.user_satisfaction ?? '-', icon: BarChart3, color: 'bg-orange-50 text-orange-600', change: '实时' },
  ]

  const channelPerformance = metricsData?.channel_performance ?? []
  const topTrips = metricsData?.top_trips ?? []

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
                  <div className={`p-3 rounded-lg ${metric.color}`}><Icon className="w-6 h-6" /></div>
                </div>
              </Card>
            )
          })}
        </div>

        <Card title="渠道性能" className="mb-6">
          <div className="overflow-x-auto">
            <table className="w-full text-sm"><thead><tr className="border-b border-gray-200"><th className="text-left py-3 px-4 font-semibold text-gray-700">渠道</th><th className="text-left py-3 px-4 font-semibold text-gray-700">总发送</th><th className="text-left py-3 px-4 font-semibold text-gray-700">成功</th><th className="text-left py-3 px-4 font-semibold text-gray-700">失败</th><th className="text-left py-3 px-4 font-semibold text-gray-700">成功率</th></tr></thead>
              <tbody>
                {channelPerformance.map((channel: any) => (
                  <tr key={channel.name} className="border-b border-gray-100 hover:bg-gray-50 transition"><td className="py-3 px-4 font-medium text-gray-900">{channel.name}</td><td className="py-3 px-4 text-gray-600">{channel.sent}</td><td className="py-3 px-4"><Badge variant="success">{channel.successful}</Badge></td><td className="py-3 px-4"><Badge variant="danger">{channel.failed}</Badge></td><td className="py-3 px-4 font-semibold text-green-600">{channel.rate}</td></tr>
                ))}
              </tbody></table>
          </div>
        </Card>

        <Card title="热门行程排行">
          <div className="overflow-x-auto">
            <table className="w-full text-sm"><thead><tr className="border-b border-gray-200"><th className="text-left py-3 px-4 font-semibold text-gray-700">行程</th><th className="text-left py-3 px-4 font-semibold text-gray-700">通知数</th><th className="text-left py-3 px-4 font-semibold text-gray-700">用户满意度</th><th className="text-left py-3 px-4 font-semibold text-gray-700">评级</th></tr></thead>
              <tbody>
                {topTrips.map((trip: any) => (
                  <tr key={trip.name} className="border-b border-gray-100 hover:bg-gray-50 transition"><td className="py-3 px-4 font-medium text-gray-900">{trip.name}</td><td className="py-3 px-4 text-gray-600">{trip.notifications}</td><td className="py-3 px-4">{trip.satisfaction}/5.0</td><td className="py-3 px-4"><Badge variant={trip.satisfaction >= 4.5 ? 'success' : 'warning'}>{'⭐'.repeat(Math.round(trip.satisfaction))}</Badge></td></tr>
                ))}
              </tbody></table>
          </div>
        </Card>
      </div>
    </>
  )
}
