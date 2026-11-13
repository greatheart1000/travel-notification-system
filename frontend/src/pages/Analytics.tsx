import { useEffect, useState } from 'react'
import { Star } from 'lucide-react'
import { PageShell } from '../components/PageShell'
import { PageState } from '../components/PageState'
import { analyticsApi } from '../services/api'
import type { AnalyticsData, AnalyticsChannelPerformance, AnalyticsTopTrip } from '../types/api'

function MetricCard({
  label,
  value,
  primary = false,
}: {
  label: string
  value: string
  primary?: boolean
}) {
  return (
    <div
      className={`rounded-card border p-5 ${
        primary ? 'border-accent-200 bg-accent-50/45 md:col-span-12 lg:col-span-6' : 'border-paper-200 bg-white md:col-span-4 lg:col-span-2'
      }`}
    >
      <p className="text-sm font-medium text-paper-600">{label}</p>
      <p
        className={`mt-2 font-semibold tabular-nums text-paper-900 ${
          primary ? 'text-3xl' : 'text-2xl'
        }`}
      >
        {value}
      </p>
    </div>
  )
}

function ChannelBar({ item }: { item: AnalyticsChannelPerformance }) {
  const total = item.sent || 1
  const successPct = (item.successful / total) * 100
  const failPct = (item.failed / total) * 100
  return (
    <div>
      <div className="mb-2 flex items-center justify-between text-sm">
        <span className="text-paper-700">{item.channelLabel}</span>
        <span className="tabular-nums text-paper-900">
          {item.sent} 条 · {item.rate}
        </span>
      </div>
      <div className="flex h-1.5 w-full overflow-hidden rounded-sm bg-paper-100">
        <div className="bg-accent-600" style={{ width: `${successPct}%` }} />
        <div className="bg-danger-300" style={{ width: `${failPct}%` }} />
      </div>
    </div>
  )
}

export function Analytics() {
  const [data, setData] = useState<AnalyticsData | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    const load = async () => {
      try {
        const result = await analyticsApi.metrics()
        if (active) setData(result)
      } catch (error) {
        if (active) setLoadError(error instanceof Error ? error.message : '数据分析加载失败')
      }
    }
    void load()
    return () => {
      active = false
    }
  }, [])

  if (loadError) {
    return (
      <PageShell title="数据分析" description="查看通知发送统计与渠道表现">
        <PageState kind="error" title="数据分析加载失败" description={loadError} />
      </PageShell>
    )
  }

  if (!data) {
    return (
      <PageShell title="数据分析" description="查看通知发送统计与渠道表现">
        <PageState kind="loading" title="正在加载数据分析" />
      </PageShell>
    )
  }

  const { metrics, channelPerformance, topTrips } = data

  return (
    <PageShell title="数据分析" description="查看通知发送统计与渠道表现">
      <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-12">
        <MetricCard label="通知成功率" value={metrics.notificationSuccessRate} primary />
        <MetricCard label="平均响应时间" value={metrics.avgResponseTime} />
        <MetricCard label="环比增长" value={metrics.wowGrowth} />
        <MetricCard label="用户满意度" value={metrics.userSatisfaction} />
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <section className="rounded-card border border-paper-200 bg-white shadow-card">
          <div className="border-b border-paper-200 px-5 py-4">
            <h2 className="text-base font-semibold text-paper-900">渠道表现</h2>
          </div>
          <div className="space-y-5 p-5">
            {channelPerformance.length === 0 ? (
              <p className="py-8 text-center text-sm text-paper-500">暂无数据</p>
            ) : (
              channelPerformance.map((item) => <ChannelBar key={item.channel} item={item} />)
            )}
          </div>
        </section>

        <section className="rounded-card border border-paper-200 bg-white shadow-card">
          <div className="border-b border-paper-200 px-5 py-4">
            <h2 className="text-base font-semibold text-paper-900">热门行程通知</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-paper-200 text-xs font-medium text-paper-500">
                  <th className="px-5 py-3 text-left">行程名</th>
                  <th className="px-5 py-3 text-right">通知数</th>
                  <th className="px-5 py-3 text-right">满意度</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-paper-100">
                {topTrips.length === 0 ? (
                  <tr>
                    <td colSpan={3} className="px-5 py-8 text-center text-sm text-paper-500">
                      暂无数据
                    </td>
                  </tr>
                ) : (
                  topTrips.map((trip: AnalyticsTopTrip) => (
                    <tr key={trip.name} className="transition-colors hover:bg-paper-50">
                      <td className="px-5 py-3">
                        {trip.tripId ? (
                          <a
                            href={`/trips/${encodeURIComponent(trip.tripId)}`}
                            onClick={(event) => {
                              event.preventDefault()
                              window.history.pushState(
                                {},
                                '',
                                `/trips/${encodeURIComponent(trip.tripId)}`,
                              )
                              window.dispatchEvent(new PopStateEvent('popstate'))
                            }}
                            className="text-accent-700 hover:text-accent-800 hover:underline"
                          >
                            {trip.name}
                          </a>
                        ) : (
                          <span className="text-paper-900">{trip.name}</span>
                        )}
                      </td>
                      <td className="px-5 py-3 text-right tabular-nums text-paper-700">{trip.notifications}</td>
                      <td className="px-5 py-3 text-right">
                        <span className="inline-flex items-center justify-end gap-1 tabular-nums text-paper-700">
                          {trip.satisfaction}
                          <Star className="h-3.5 w-3.5 text-paper-400" aria-hidden="true" />
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </PageShell>
  )
}
