import { useEffect, useState } from 'react'
import { FigmaAnalyticsService, type MakeAnalyticsData } from '../services/figmaTripService'

export function Analytics() {
  const [analyticsData, setAnalyticsData] = useState<MakeAnalyticsData | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)

  useEffect(() => {
    let active = true

    const loadAnalytics = async () => {
      try {
        const data = await FigmaAnalyticsService.getAnalytics()
        if (active) setAnalyticsData(data)
      } catch (error) {
        if (active) setLoadError(error instanceof Error ? error.message : 'API 数据分析加载失败')
      }
    }

    void loadAnalytics()

    return () => {
      active = false
    }
  }, [])

  if (loadError) {
    return <div className="p-6"><div className="rounded-lg border border-red-200 bg-red-50 p-6 text-red-700">{loadError}</div></div>
  }

  if (!analyticsData) {
    return <div className="p-6"><div className="rounded-lg border border-gray-200 bg-white p-6 text-center text-gray-600">正在通过 API 加载数据分析...</div></div>
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">数据分析</h1>
        <p className="text-gray-600">查看各类数据统计和分析报表</p>
      </div>

      <div className="grid grid-cols-1 gap-4 mb-6 md:grid-cols-2 xl:grid-cols-4">
        {analyticsData.overview.map((item) => (
          <div key={item.label} className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
            <div className="text-gray-600 text-sm mb-2">{item.label}</div>
            <div className="flex items-end justify-between">
              <div className="text-3xl font-bold text-gray-900">{item.value}</div>
              <div className="text-sm text-green-600">{item.trend}</div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 mb-6 xl:grid-cols-2">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
            <h2 className="font-semibold text-gray-900">旅行团状态分布</h2>
          </div>
          <div className="p-6">
            {analyticsData.tripStats.map((stat) => (
              <div key={stat.status} className="mb-4 last:mb-0">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-700">{stat.status}</span>
                  <span className="text-sm font-medium text-gray-900">{stat.count} 个 ({stat.percentage}%)</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div className={`${stat.color} h-2 rounded-full`} style={{ width: `${stat.percentage}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
            <h2 className="font-semibold text-gray-900">通知发送统计</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="px-4 py-3 text-left font-medium text-gray-700">通知类型</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-700">发送数</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-700">成功数</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-700">成功率</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {analyticsData.notificationStats.map((stat) => (
                  <tr key={stat.type} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-gray-900">{stat.type}</td>
                    <td className="px-4 py-3 text-right text-gray-700">{stat.sent}</td>
                    <td className="px-4 py-3 text-right text-gray-700">{stat.success}</td>
                    <td className="px-4 py-3 text-right"><span className="text-green-600 font-medium">{stat.rate}%</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
          <h2 className="font-semibold text-gray-900">近期旅行团表现</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <th className="px-6 py-3 text-left font-medium text-gray-700">团名</th>
                <th className="px-6 py-3 text-right font-medium text-gray-700">参与人数</th>
                <th className="px-6 py-3 text-right font-medium text-gray-700">收入</th>
                <th className="px-6 py-3 text-right font-medium text-gray-700">满意度</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {analyticsData.recentTrips.map((trip) => (
                <tr key={trip.name} className="hover:bg-gray-50">
                  <td className="px-6 py-4 text-gray-900">{trip.name}</td>
                  <td className="px-6 py-4 text-right text-gray-700">{trip.participants} 人</td>
                  <td className="px-6 py-4 text-right text-gray-700">¥{trip.revenue.toLocaleString()}</td>
                  <td className="px-6 py-4 text-right"><span className="text-yellow-600 font-medium">{trip.satisfaction} ⭐</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
