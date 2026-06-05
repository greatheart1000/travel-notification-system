import { useEffect, useState } from 'react'
import { FigmaTripService } from '../../services/figmaTripService'
import type { MakeTrip } from '../../data/figmaMockData'

interface OngoingTripsPageProps {
  onNavigate: (path: string) => void
}

export function OngoingTripsPage({ onNavigate }: OngoingTripsPageProps) {
  const [trips, setTrips] = useState<MakeTrip[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 5

  useEffect(() => {
    let active = true
    const load = async () => {
      setLoading(true)
      try {
        const all = await FigmaTripService.getAllTrips()
        if (active) {
          const ongoing = all.filter((t) => t.status === '进行中' || t.status === '即将出发')
          setTrips(ongoing)
        }
      } catch (e) {
        if (active) setError(e instanceof Error ? e.message : '加载失败')
      } finally {
        if (active) setLoading(false)
      }
    }
    void load()
    return () => { active = false }
  }, [])

  const totalPages = Math.max(1, Math.ceil(trips.length / itemsPerPage))
  const currentTrips = trips.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage)

  if (loading) return <div className="p-6 text-center text-gray-500">加载中...</div>
  if (error) return <div className="p-6 text-center text-red-500">{error}</div>

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <button onClick={() => onNavigate('/dashboard')} className="text-gray-600 hover:text-gray-900">← 返回仪表盘</button>
            <h1 className="text-2xl font-bold text-gray-900">进行中的旅行团</h1>
          </div>
          <p className="text-gray-600">查看所有正在进行的旅行团实时状态</p>
        </div>
      </div>

      <div className="grid gap-4">
        {currentTrips.length === 0 && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center text-gray-400">暂无进行中的旅行团</div>
        )}
        {currentTrips.map((trip) => (
          <div key={trip.id} className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
            <div className="p-6">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-1">{trip.name}</h3>
                  <p className="text-sm text-gray-600">{trip.code}</p>
                </div>
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${trip.statusColor}`}>{trip.status}</span>
              </div>

              <div className="grid grid-cols-1 gap-6 mb-4 md:grid-cols-4">
                <div><div className="text-xs text-gray-500 mb-1">出团日期</div><div className="text-sm font-medium text-gray-900">{trip.startDate} ~ {trip.endDate}</div></div>
                <div><div className="text-xs text-gray-500 mb-1">参团人数</div><div className="text-sm font-medium text-gray-900">{trip.participants} 人</div></div>
                <div><div className="text-xs text-gray-500 mb-1">领队信息</div><div className="text-sm font-medium text-gray-900">{trip.leader}</div></div>
                <div><div className="text-xs text-gray-500 mb-1">团号</div><div className="text-sm font-medium text-gray-900">{trip.code}</div></div>
              </div>

              <div className="flex gap-3">
                <button onClick={() => onNavigate(`/trips/${trip.id}`)} className="px-4 py-2 bg-cyan-500 text-white rounded-lg hover:bg-cyan-600 text-sm">查看详情</button>
                <button onClick={() => onNavigate(`/trips/${trip.id}/notifications`)} className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 text-sm">发送通知</button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {trips.length > itemsPerPage && (
        <div className="mt-6 bg-white rounded-lg shadow-sm border border-gray-200 px-6 py-4 flex items-center justify-between">
          <div className="text-sm text-gray-600">共 {trips.length} 条记录，当前第 {currentPage} / {totalPages} 页</div>
          <div className="flex gap-2">
            <button onClick={() => setCurrentPage(1)} disabled={currentPage === 1} className="px-3 py-1 text-sm rounded bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:bg-gray-200 disabled:text-gray-400">第一页</button>
            <button onClick={() => setCurrentPage(currentPage - 1)} disabled={currentPage === 1} className="px-3 py-1 text-sm rounded bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:bg-gray-200 disabled:text-gray-400">上一页</button>
            {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
              <button key={page} onClick={() => setCurrentPage(page)} className={`px-3 py-1 text-sm rounded ${currentPage === page ? 'bg-cyan-500 text-white' : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'}`}>{page}</button>
            ))}
            <button onClick={() => setCurrentPage(currentPage + 1)} disabled={currentPage === totalPages} className="px-3 py-1 text-sm rounded bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:bg-gray-200 disabled:text-gray-400">下一页</button>
            <button onClick={() => setCurrentPage(totalPages)} disabled={currentPage === totalPages} className="px-3 py-1 text-sm rounded bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:bg-gray-200 disabled:text-gray-400">最后一页</button>
          </div>
        </div>
      )}
    </div>
  )
}
