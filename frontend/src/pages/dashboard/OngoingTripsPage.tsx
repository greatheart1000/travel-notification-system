import { useState } from 'react'

interface OngoingTripsPageProps {
  onNavigate: (path: string) => void
}

const ongoingTrips = [
  { id: 'trip-001', teamId: 'TEAM-DEMO-POST', name: '阿勒泰本地冬营团', code: 'TEAM-DEMO-POST', startDate: '2026-03-10', endDate: '2026-03-16', currentDay: 6, totalDays: 7, participants: 12, leader: '王美丽', leaderPhone: '138****1234', currentLocation: '按克', todaySchedule: '按克 → 乌市送机', status: '进行中' },
  { id: 'trip-002', teamId: 'TEAM-YUNNAN-001', name: '云南丽江深度游', code: 'TEAM-YN-001', startDate: '2026-04-23', endDate: '2026-04-28', currentDay: 3, totalDays: 6, participants: 18, leader: '李强', leaderPhone: '139****5678', currentLocation: '大理古城', todaySchedule: '大理古城 → 洱海环游', status: '进行中' },
  { id: 'trip-003', teamId: 'TEAM-SICHUAN-002', name: '四川九寨沟风光团', code: 'TEAM-SC-002', startDate: '2026-04-22', endDate: '2026-04-27', currentDay: 4, totalDays: 6, participants: 15, leader: '张敏', leaderPhone: '137****9012', currentLocation: '九寨沟', todaySchedule: '九寨沟景区深度游览', status: '进行中' },
]

export function OngoingTripsPage({ onNavigate }: OngoingTripsPageProps) {
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 5
  const totalPages = Math.max(1, Math.ceil(ongoingTrips.length / itemsPerPage))
  const currentTrips = ongoingTrips.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage)

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
        {currentTrips.map((trip) => (
          <div key={trip.id} className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
            <div className="p-6">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-1">{trip.name}</h3>
                  <p className="text-sm text-gray-600">{trip.code}</p>
                </div>
                <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm font-medium">{trip.status}</span>
              </div>

              <div className="grid grid-cols-1 gap-6 mb-4 md:grid-cols-4">
                <div>
                  <div className="text-xs text-gray-500 mb-1">行程进度</div>
                  <div className="text-sm font-medium text-gray-900">第 {trip.currentDay} 天 / 共 {trip.totalDays} 天</div>
                  <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
                    <div className="bg-green-500 h-2 rounded-full" style={{ width: `${(trip.currentDay / trip.totalDays) * 100}%` }} />
                  </div>
                </div>
                <div><div className="text-xs text-gray-500 mb-1">出团日期</div><div className="text-sm font-medium text-gray-900">{trip.startDate} ~ {trip.endDate}</div></div>
                <div><div className="text-xs text-gray-500 mb-1">参团人数</div><div className="text-sm font-medium text-gray-900">{trip.participants} 人</div></div>
                <div><div className="text-xs text-gray-500 mb-1">领队信息</div><div className="text-sm font-medium text-gray-900">{trip.leader} ({trip.leaderPhone})</div></div>
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
                <div className="flex items-start gap-3">
                  <span className="text-2xl">📍</span>
                  <div className="flex-1"><div className="text-sm font-medium text-blue-900 mb-1">当前位置</div><div className="text-sm text-blue-700">{trip.currentLocation}</div></div>
                  <div className="flex-1"><div className="text-sm font-medium text-blue-900 mb-1">今日行程</div><div className="text-sm text-blue-700">{trip.todaySchedule}</div></div>
                </div>
              </div>

              <div className="flex gap-3">
                <button onClick={() => onNavigate(`/trips/${trip.teamId}`)} className="px-4 py-2 bg-cyan-500 text-white rounded-lg hover:bg-cyan-600 text-sm">查看详情</button>
                <button className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 text-sm">联系领队</button>
                <button onClick={() => onNavigate(`/trips/${trip.teamId}`)} className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 text-sm">发送通知</button>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-6 bg-white rounded-lg shadow-sm border border-gray-200 px-6 py-4 flex items-center justify-between">
        <div className="text-sm text-gray-600">共 {ongoingTrips.length} 条记录，当前第 {currentPage} / {totalPages} 页</div>
        <div className="flex gap-2">
          <button onClick={() => setCurrentPage(1)} disabled={currentPage === 1} className="px-3 py-1 text-sm rounded bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:bg-gray-200 disabled:text-gray-400">第一页</button>
          <button onClick={() => setCurrentPage(currentPage - 1)} disabled={currentPage === 1} className="px-3 py-1 text-sm rounded bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:bg-gray-200 disabled:text-gray-400">上一页</button>
          {Array.from({ length: totalPages }, (_, index) => index + 1).map((page) => <button key={page} onClick={() => setCurrentPage(page)} className={`px-3 py-1 text-sm rounded ${currentPage === page ? 'bg-cyan-500 text-white' : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'}`}>{page}</button>)}
          <button onClick={() => setCurrentPage(currentPage + 1)} disabled={currentPage === totalPages} className="px-3 py-1 text-sm rounded bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:bg-gray-200 disabled:text-gray-400">下一页</button>
          <button onClick={() => setCurrentPage(totalPages)} disabled={currentPage === totalPages} className="px-3 py-1 text-sm rounded bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:bg-gray-200 disabled:text-gray-400">最后一页</button>
        </div>
      </div>
    </div>
  )
}
