import { useEffect, useState } from 'react'
import { Card } from '../components/Card'
import { MetricTile } from '../components/MetricTile'
import { PageShell } from '../components/PageShell'
import { PageState } from '../components/PageState'
import { AlertTriangle, BarChart3, CheckCircle, Clock, Mail, Plus, TrendingUp } from 'lucide-react'
import { api, getErrorMessage } from '../services/api'
import { CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

const COLORS = ['#2563eb', '#0ea5e9', '#10b981', '#f59e0b', '#ef4444']

const itineraryRows = [
  {
    date: 'Apr 18',
    transport: 'Transport',
    route: 'Suram Hotel to Climate Parian',
    hotel: 'TEAM-DEMO-ON',
    morning: '08:00 AM: Weather & Schedule Reminder',
    noon: '12:30 PM: Lunch & Meeting Info',
    evening: '06:00 PM: Dinner & Evening Plan',
  },
  {
    date: 'Apr 19',
    transport: 'Transport',
    route: 'Suram Hotel to Climate Parian',
    hotel: 'TEAM-DEMO-ON',
    morning: '08:00 AM: Weather & Schedule Reminder',
    noon: '12:30 PM: Lunch & Meeting Info',
    evening: '06:00 PM: Dinner & Evening Plan',
  },
  {
    date: 'Apr 20',
    transport: 'Transport',
    route: 'Hemu Village scenic transfer',
    hotel: 'TEAM-DEMO-ON',
    morning: '08:00 AM: Mountain Road Notice',
    noon: '12:30 PM: Lunch & Free Time',
    evening: '06:00 PM: Campfire Reminder',
  },
]

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

  if (loading) {
    return (
      <PageShell title="Itinerary SMS Management and Emergency Alerts">
        <PageState kind="loading" title="正在加载高级报表" />
      </PageShell>
    )
  }

  if (error) {
    return (
      <PageShell title="Itinerary SMS Management and Emergency Alerts">
        <PageState kind="error" title="加载失败" description={error} onRetry={loadData} />
      </PageShell>
    )
  }

  const summary = data.summary ?? {}
  const metrics = data.metrics ?? {}
  const chartTrend = data.charts?.notification_trend ?? []
  const channelDistribution = data.charts?.channel_distribution ?? []

  return (
    <PageShell
      eyebrow="Analytics"
      title="Itinerary SMS Management and Emergency Alerts"
      description="集中查看通知表现、紧急预警和每日短信编排。"
      actions={
        <button className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-bold text-white transition hover:bg-slate-900">
          <Plus className="mr-2 inline h-4 w-4" />
          New Day
        </button>
      }
    >
      <div className="mb-5 flex items-center justify-between rounded-xl bg-gradient-to-r from-red-700 to-red-500 px-5 py-4 text-white shadow-lg shadow-red-900/20">
        <div className="flex items-center gap-3">
          <AlertTriangle className="h-6 w-6" />
          <span className="font-black">Emergency Weather Alert:</span>
          <span className="text-red-50">Send Mass Notification to All Groups</span>
        </div>
        <button className="rounded-lg bg-white px-4 py-2 text-sm font-bold text-red-700 transition hover:bg-red-50">
          Send Alert
        </button>
      </div>

      <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-4">
        <MetricTile title="Total Notifications Sent" value={String(metrics.total_notifications ?? summary.total_notifications ?? 0)} detail="+12.5% last week" trend="增长" trendTone="good" icon={Mail} />
        <MetricTile title="Avg. Delivery Rate" value={String(metrics.notification_success_rate ?? summary.success_rate ?? '0%')} detail="+1.1% vs target" trend="稳定" trendTone="good" icon={CheckCircle} />
        <MetricTile title="Avg. Response Time" value={String(metrics.avg_response_time ?? `${summary.avg_latency_ms ?? 0}ms`)} detail="-15% improved" trend="改善" trendTone="good" icon={Clock} />
        <MetricTile title="Channel Growth" value={`${summary.wow_growth ?? metrics.wow_growth ?? 0}%`} detail="+0.8% vs month" trend="增长" trendTone="good" icon={TrendingUp} />
      </div>

      <Card title="Daily Itinerary and SMS Management" className="mt-6 border-blue-100 shadow-[0_14px_40px_rgba(15,23,42,0.06)]">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[980px] text-sm">
            <thead>
              <tr className="bg-blue-50 text-left text-slate-700">
                <th className="px-3 py-4 font-black">Date</th>
                <th className="px-3 py-4 font-black">Transport</th>
                <th className="px-3 py-4 font-black">Route Details</th>
                <th className="px-3 py-4 font-black">Hotel</th>
                <th className="px-3 py-4 font-black">Morning SMS</th>
                <th className="px-3 py-4 font-black">Noon SMS</th>
                <th className="px-3 py-4 font-black">Evening SMS</th>
              </tr>
            </thead>
            <tbody>
              {itineraryRows.map((row) => (
                <tr key={row.date} className="border-b border-slate-100 align-top hover:bg-blue-50/40">
                  <td className="px-3 py-4 font-bold text-slate-900">{row.date}</td>
                  <td className="px-3 py-4 text-slate-600">{row.transport}</td>
                  <td className="px-3 py-4 text-slate-700">{row.route}</td>
                  <td className="px-3 py-4 font-mono text-slate-500">{row.hotel}</td>
                  {[row.morning, row.noon, row.evening].map((message) => (
                    <td key={message} className="px-3 py-4">
                      <p className="mb-2 max-w-[190px] text-slate-700">{message}</p>
                      <div className="flex gap-2">
                        <button className="rounded bg-blue-600 px-2 py-1 font-bold text-white">+</button>
                        <button className="rounded bg-slate-100 px-2 py-1 text-slate-600">✎</button>
                        <button className="rounded bg-slate-100 px-2 py-1 text-slate-600">🗑</button>
                      </div>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <div className="mt-8 grid grid-cols-1 gap-8 lg:grid-cols-2">
        <Card title="发送量趋势 (近7日)" className="border-blue-100">
          <div className="mt-4 h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartTrend}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 12 }} dy={10} />
                <YAxis axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 12 }} />
                <Tooltip />
                <Line type="monotone" dataKey="count" name="总发送" stroke="#2563eb" strokeWidth={3} dot={{ r: 4, fill: '#2563eb' }} activeDot={{ r: 6 }} />
                <Line type="monotone" dataKey="success" name="成功数" stroke="#10b981" strokeWidth={3} dot={{ r: 4, fill: '#10b981' }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card title="发送渠道分布" className="border-blue-100">
          <div className="mt-4 h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={channelDistribution} cx="50%" cy="50%" innerRadius={60} outerRadius={100} paddingAngle={5} dataKey="value">
                  {channelDistribution.map((_: any, index: number) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend verticalAlign="bottom" height={36} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>
    </PageShell>
  )
}
