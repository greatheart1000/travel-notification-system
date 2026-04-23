import { useEffect, useState } from 'react'
import { Card } from '../components/Card'
import { MetricTile } from '../components/MetricTile'
import { PageShell } from '../components/PageShell'
import { PageState } from '../components/PageState'
import { AlertTriangle, BarChart3, CheckCircle, Clock, Mail, Plus, TrendingUp } from 'lucide-react'
import { api, getErrorMessage, tripsApi } from '../services/api'
import { CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { type Trip, type TripSchedule } from '../types/api'

const COLORS = ['#2563eb', '#0ea5e9', '#10b981', '#f59e0b', '#ef4444']

export function Analytics() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [data, setData] = useState<any>(null)
  const [selectedTrip, setSelectedTrip] = useState<Trip | null>(null)
  const [schedule, setSchedule] = useState<TripSchedule | null>(null)

  const resolvePreferredTrip = (trips: Trip[]): Trip | null => {
    if (trips.length === 0) return null
    return (
      trips.find((trip) => trip.status === 'in_progress')
      || trips.find((trip) => trip.status === 'planned')
      || trips[0]
    )
  }

  const loadData = async () => {
    setLoading(true)
    try {
      const [res, trips] = await Promise.all([
        api.get('/analytics/metrics'),
        tripsApi.list(),
      ])
      const preferredTrip = resolvePreferredTrip(trips)
      setSelectedTrip(preferredTrip)
      if (preferredTrip) {
        const tripSchedule = await tripsApi.getSchedule(preferredTrip.id)
        setSchedule(tripSchedule)
      } else {
        setSchedule(null)
      }
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
      <PageShell title="行程通知数据分析">
        <PageState kind="loading" title="正在加载高级报表" />
      </PageShell>
    )
  }

  if (error) {
    return (
      <PageShell title="行程通知数据分析">
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
      eyebrow="数据分析"
      title="行程通知与紧急预警分析看板"
      description="集中查看通知表现、紧急预警以及来自数据库的行程编排数据。"
      actions={
        <button className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-bold text-white transition hover:bg-slate-900">
          <Plus className="mr-2 inline h-4 w-4" />
          新增行程日
        </button>
      }
    >
      <div className="mb-5 flex items-center justify-between rounded-xl bg-gradient-to-r from-red-700 to-red-500 px-5 py-4 text-white shadow-lg shadow-red-900/20">
        <div className="flex items-center gap-3">
          <AlertTriangle className="h-6 w-6" />
          <span className="font-black">紧急天气预警：</span>
          <span className="text-red-50">建议立即向所有在途团发送风险提示</span>
        </div>
        <button className="rounded-lg bg-white px-4 py-2 text-sm font-bold text-red-700 transition hover:bg-red-50">
          发送预警
        </button>
      </div>

      <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-4">
        <MetricTile title="通知发送总量" value={String(metrics.total_notifications ?? summary.total_notifications ?? 0)} detail="近7日发送规模" trend="增长" trendTone="good" icon={Mail} />
        <MetricTile title="平均送达率" value={String(metrics.notification_success_rate ?? summary.success_rate ?? '0%')} detail="对比目标值稳定" trend="稳定" trendTone="good" icon={CheckCircle} />
        <MetricTile title="平均响应耗时" value={String(metrics.avg_response_time ?? `${summary.avg_latency_ms ?? 0}ms`)} detail="自动派发耗时" trend="改善" trendTone="good" icon={Clock} />
        <MetricTile title="渠道增长率" value={`${summary.wow_growth ?? metrics.wow_growth ?? 0}%`} detail="环比增长表现" trend="增长" trendTone="good" icon={TrendingUp} />
      </div>

      <Card
        title={`行程短信编排明细${selectedTrip ? `（${selectedTrip.destination}）` : ''}`}
        className="mt-6 border-blue-100 shadow-[0_14px_40px_rgba(15,23,42,0.06)]"
      >
        <div className="overflow-x-auto">
          <table className="w-full min-w-[980px] text-sm">
            <thead>
              <tr className="bg-blue-50 text-left text-slate-700">
                <th className="px-3 py-4 font-black">日期</th>
                <th className="px-3 py-4 font-black">交通方式</th>
                <th className="px-3 py-4 font-black">路线详情</th>
                <th className="px-3 py-4 font-black">酒店</th>
                <th className="px-3 py-4 font-black">晨间提醒</th>
                <th className="px-3 py-4 font-black">午间提醒</th>
                <th className="px-3 py-4 font-black">晚间提醒</th>
              </tr>
            </thead>
            <tbody>
              {(schedule?.days ?? []).map((day) => (
                <tr key={`${day.day}-${day.date}`} className="border-b border-slate-100 align-top hover:bg-blue-50/40">
                  <td className="px-3 py-4 font-bold text-slate-900">{day.date || `第 ${day.day} 天`}</td>
                  <td className="px-3 py-4 text-slate-600">{day.transport || '待补充'}</td>
                  <td className="px-3 py-4 text-slate-700">{day.route || '待补充行程路线'}</td>
                  <td className="px-3 py-4 font-mono text-slate-500">{day.hotel || '待补充酒店'}</td>
                  {[
                    `08:00 早安提醒｜${day.route || '今日路线待配置'}`,
                    `12:30 午间提醒｜${day.transport || '交通待配置'}`,
                    `18:00 晚间提醒｜${day.hotel || '住宿待配置'}`,
                  ].map((message) => (
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
              {(schedule?.days ?? []).length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-3 py-10 text-center text-slate-500">
                    暂无数据库行程日数据，请先在行程管理中新增每日安排。
                  </td>
                </tr>
              ) : null}
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
