import { useEffect, useState } from 'react'
import { Header } from '../components/Header'
import { Card } from '../components/Card'
import { PageState } from '../components/PageState'
import { TrendingUp, Clock, CheckCircle, Mail } from 'lucide-react'
import { api, getErrorMessage } from '../services/api'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts'

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

export function Analytics() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [data, setData] = useState<any>(null)

  const loadData = async () => {
    setLoading(true)
    try {
      const res = await api.get('/analytics/metrics')
      setData(res)
      setError('')
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadData()
  }, [])

  if (loading) return <><Header /><div className="p-8"><PageState kind="loading" title="正在加载高级报表" /></div></>
  if (error) return <><Header /><div className="p-8"><PageState kind="error" title="加载失败" description={error} onRetry={loadData} /></div></>

  const summary = [
    { title: '总通知发送量', value: data.summary.total_notifications, icon: Mail, color: 'bg-blue-50 text-blue-600' },
    { title: '平均成功率', value: `${data.summary.success_rate}%`, icon: CheckCircle, color: 'bg-green-50 text-green-600' },
    { title: '平均延迟', value: `${data.summary.avg_latency_ms}ms`, icon: Clock, color: 'bg-yellow-50 text-yellow-600' },
    { title: '周环比增长', value: `${data.summary.wow_growth}%`, icon: TrendingUp, color: 'bg-purple-50 text-purple-600' },
  ]

  return (
    <>
      <Header />
      <div className="p-8 max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">高级统计分析报表</h1>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {summary.map((s) => (
            <Card key={s.title}>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">{s.title}</p>
                  <p className="text-2xl font-bold text-gray-900 mt-1">{s.value}</p>
                </div>
                <div className={`p-3 rounded-xl ${s.color}`}><s.icon size={24} /></div>
              </div>
            </Card>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <Card title="发送量趋势 (近7日)">
            <div className="h-[300px] mt-4">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data.charts.notification_trend}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                  <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{fill: '#9ca3af', fontSize: 12}} dy={10} />
                  <YAxis axisLine={false} tickLine={false} tick={{fill: '#9ca3af', fontSize: 12}} />
                  <Tooltip />
                  <Line type="monotone" dataKey="count" name="总发送" stroke="#3b82f6" strokeWidth={3} dot={{r: 4, fill: '#3b82f6'}} activeDot={{r: 6}} />
                  <Line type="monotone" dataKey="success" name="成功数" stroke="#10b981" strokeWidth={3} dot={{r: 4, fill: '#10b981'}} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>

          <Card title="发送渠道分布">
            <div className="h-[300px] mt-4">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={data.charts.channel_distribution}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {data.charts.channel_distribution.map((_: any, index: number) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend verticalAlign="bottom" height={36}/>
                </PieChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </div>
      </div>
    </>
  )
}
