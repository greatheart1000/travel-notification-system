import { Header } from '../components/Header'
import { Card } from '../components/Card'
import { Badge } from '../components/Badge'
import { TrendingUp, Users, Send, AlertCircle } from 'lucide-react'

export function Dashboard() {
  const stats = [
    {
      title: '今日发送通知',
      value: '1,234',
      icon: Send,
      color: 'bg-blue-50 text-blue-600',
      trend: '+12%',
    },
    {
      title: '活跃行程',
      value: '45',
      icon: TrendingUp,
      color: 'bg-green-50 text-green-600',
      trend: '+8%',
    },
    {
      title: '用户总数',
      value: '2,856',
      icon: Users,
      color: 'bg-purple-50 text-purple-600',
      trend: '+23%',
    },
    {
      title: '投诉待处理',
      value: '12',
      icon: AlertCircle,
      color: 'bg-red-50 text-red-600',
      trend: '-5%',
    },
  ]

  const recentNotifications = [
    {
      id: 1,
      customer: '张三',
      trip: '乌鲁木齐 - 喀什',
      status: '已发送',
      time: '2分钟前',
      channel: '短信',
    },
    {
      id: 2,
      customer: '李四',
      trip: '伊犁 - 塔城',
      status: '待发送',
      time: '5分钟前',
      channel: '企业微信',
    },
    {
      id: 3,
      customer: '王五',
      trip: '阿克苏 - 库尔勒',
      status: '已发送',
      time: '10分钟前',
      channel: '短信',
    },
  ]

  return (
    <>
      <Header />
      <div className="p-8">
        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {stats.map((stat) => {
            const Icon = stat.icon
            return (
              <Card key={stat.title}>
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-sm text-gray-600 mb-1">{stat.title}</p>
                    <p className="text-3xl font-bold text-gray-900">{stat.value}</p>
                    <p className="text-xs text-green-600 mt-2">{stat.trend} vs 昨天</p>
                  </div>
                  <div className={`p-3 rounded-lg ${stat.color}`}>
                    <Icon className="w-6 h-6" />
                  </div>
                </div>
              </Card>
            )
          })}
        </div>

        {/* Recent Notifications */}
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
                    <td className="py-3 px-4 font-medium text-gray-900">{notif.customer}</td>
                    <td className="py-3 px-4 text-gray-600">{notif.trip}</td>
                    <td className="py-3 px-4">{notif.channel}</td>
                    <td className="py-3 px-4">
                      <Badge variant={notif.status === '已发送' ? 'success' : 'warning'}>
                        {notif.status}
                      </Badge>
                    </td>
                    <td className="py-3 px-4 text-gray-500">{notif.time}</td>
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
