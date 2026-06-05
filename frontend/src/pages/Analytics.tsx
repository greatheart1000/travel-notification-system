import { useEffect, useState } from 'react'
import { analyticsApi } from '../services/api'
import type { AnalyticsData, AnalyticsChannelPerformance, AnalyticsTopTrip } from '../types/api'

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
      <div className="text-gray-600 text-sm mb-2">{label}</div>
      <div className="text-3xl font-bold text-gray-900">{value}</div>
    </div>
  )
}

function ChannelBar({ item }: { item: AnalyticsChannelPerformance }) {
  const total = item.sent || 1
  const successPct = (item.successful / total) * 100
  const failPct = (item.failed / total) * 100
  return (
    <div className="mb-4 last:mb-0">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-gray-700">{item.channelLabel}</span>
        <span className="text-sm font-medium text-gray-900">{item.sent} 条 ({item.rate})</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2 flex overflow-hidden">
        <div className="bg-green-500 h-2" style={{ width: `${successPct}%` }} />
        <div className="bg-red-400 h-2" style={{ width: `${failPct}%` }} />
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
        if (active) setLoadError(error instanceof Error ? error.message : 'API 数据分析加载失败')
      }
    }
    void load()
    return () => { active = false }
  }, [])

  if (loadError) {
    return <div className="p-6"><div className="rounded-lg border border-red-200 bg-red-50 p-6 text-red-700">{loadError}</div></div>
  }

  if (!data) {
    return <div className="p-6"><div className="rounded-lg border border-gray-200 bg-white p-6 text-center text-gray-600">正在通过 API 加载数据分析...</div></div>
  }

  const { metrics, channelPerformance, topTrips } = data

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">数据分析</h1>
        <p className="text-gray-600">查看通知发送统计与渠道表现</p>
      </div>

      <div className="grid grid-cols-1 gap-4 mb-6 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="通知成功率" value={metrics.notificationSuccessRate} />
        <MetricCard label="平均响应时间" value={metrics.avgResponseTime} />
        <MetricCard label="环比增长" value={metrics.wowGrowth} />
        <MetricCard label="用户满意度" value={metrics.userSatisfaction} />
      </div>

      <div className="grid grid-cols-1 gap-6 mb-6 xl:grid-cols-2">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
            <h2 className="font-semibold text-gray-900">渠道表现</h2>
          </div>
          <div className="p-6">
            {channelPerformance.length === 0 ? (
              <div className="text-center text-gray-400">暂无数据</div>
            ) : (
              channelPerformance.map((item) => (
                <ChannelBar key={item.channel} item={item} />
              ))
            )}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
            <h2 className="font-semibold text-gray-900">热门行程通知</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="px-4 py-3 text-left font-medium text-gray-700">行程名</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-700">通知数</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-700">满意度</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {topTrips.length === 0 ? (
                  <tr><td colSpan={3} className="px-4 py-8 text-center text-gray-400">暂无数据</td></tr>
                ) : (
                  topTrips.map((trip: AnalyticsTopTrip) => (
                    <tr key={trip.name} className="hover:bg-gray-50">
                      <td className="px-4 py-4 text-gray-900">{trip.name}</td>
                      <td className="px-4 py-4 text-right text-gray-700">{trip.notifications}</td>
                      <td className="px-4 py-4 text-right">
                        <span className="text-yellow-600 font-medium">{trip.satisfaction} ⭐</span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
