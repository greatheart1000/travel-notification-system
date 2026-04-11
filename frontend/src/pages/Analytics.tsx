import { Header } from '../components/Header'
import { Card } from '../components/Card'
import { Badge } from '../components/Badge'
import { BarChart3, TrendingUp, Clock, CheckCircle } from 'lucide-react'

export function Analytics() {
  const metrics = [
    {
      title: '通知成功率',
      value: '98.5%',
      icon: CheckCircle,
      color: 'bg-green-50 text-green-600',
      change: '+2.3%',
    },
    {
      title: '平均响应时间',
      value: '1.2s',
      icon: Clock,
      color: 'bg-blue-50 text-blue-600',
      change: '-0.5s',
    },
    {
      title: '周环比增长',
      value: '+15.3%',
      icon: TrendingUp,
      color: 'bg-purple-50 text-purple-600',
      change: '+3.2%',
    },
    {
      title: '用户满意度',
      value: '4.5/5',
      icon: BarChart3,
      color: 'bg-orange-50 text-orange-600',
      change: '+0.3',
    },
  ]

  const channelPerformance = [
    { name: '短信', sent: 5234, successful: 5156, failed: 78, rate: '98.5%' },
    { name: '企业微信', sent: 3421, successful: 3398, failed: 23, rate: '99.3%' },
    { name: '邮件', sent: 1256, successful: 1198, failed: 58, rate: '95.4%' },
  ]

  const topTrips = [
    { name: '乌鲁木齐 - 喀什', notifications: 1234, satisfaction: 4.6 },
    { name: '伊犁 - 塔城', notifications: 856, satisfaction: 4.3 },
    { name: '阿克苏 - 库尔勒', notifications: 645, satisfaction: 4.7 },
  ]

  return (
    <>
      <Header />
      <div className="p-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">数据分析</h1>

        {/* Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {metrics.map((metric) => {
            const Icon = metric.icon
            return (
              <Card key={metric.title}>
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-sm text-gray-600 mb-1">{metric.title}</p>
                    <p className="text-3xl font-bold text-gray-900">{metric.value}</p>
                    <p className="text-xs text-green-600 mt-2">{metric.change} vs 上周</p>
                  </div>
                  <div className={`p-3 rounded-lg ${metric.color}`}>
                    <Icon className="w-6 h-6" />
                  </div>
                </div>
              </Card>
            )
          })}
        </div>

        {/* Channel Performance */}
        <Card title="渠道性能" className="mb-6">
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
                {channelPerformance.map((channel) => (
                  <tr key={channel.name} className="border-b border-gray-100 hover:bg-gray-50 transition">
                    <td className="py-3 px-4 font-medium text-gray-900">{channel.name}</td>
                    <td className="py-3 px-4 text-gray-600">{channel.sent.toLocaleString()}</td>
                    <td className="py-3 px-4">
                      <Badge variant="success">{channel.successful.toLocaleString()}</Badge>
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
        </Card>

        {/* Top Trips */}
        <Card title="热门行程排行">
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
                {topTrips.map((trip) => (
                  <tr key={trip.name} className="border-b border-gray-100 hover:bg-gray-50 transition">
                    <td className="py-3 px-4 font-medium text-gray-900">{trip.name}</td>
                    <td className="py-3 px-4 text-gray-600">{trip.notifications}</td>
                    <td className="py-3 px-4">{trip.satisfaction}/5.0</td>
                    <td className="py-3 px-4">
                      <Badge variant={trip.satisfaction >= 4.5 ? 'success' : 'warning'}>
                        {'⭐'.repeat(Math.round(trip.satisfaction))}
                      </Badge>
                    </td>
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
