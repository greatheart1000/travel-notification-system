import { useState } from 'react'

interface PendingNotificationsPageProps {
  onNavigate: (path: string) => void
}

const pendingNotifications = [
  { id: 1, trip: '阿勒泰本地冬营团', tripId: 'TEAM-DEMO-POST', type: '行程结束感谢', scheduledTime: '2026-03-17 10:00', recipients: 12, content: '【阿勒泰冬营团】感谢您参加我们的阿勒泰冬营之旅！希望这次旅行给您留下美好回忆...', priority: '普通' },
  { id: 2, trip: '埃塞俄比亚古文明探索团', tripId: 'TEAM-ETHIO-001', type: '出发提醒', scheduledTime: '2026-04-13 18:00', recipients: 8, content: '【埃塞俄比亚探索团】亲爱的游客，您好！后天我们即将开启精彩的埃塞俄比亚之旅...', priority: '重要' },
  { id: 3, trip: '埃塞俄比亚古文明探索团', tripId: 'TEAM-ETHIO-001', type: '签证提醒', scheduledTime: '2026-04-08 10:00', recipients: 8, content: '【埃塞俄比亚探索团】温馨提示：请确认您的签证已经办理完成，出发前请携带护照和签证...', priority: '紧急' },
  { id: 4, trip: '马来半岛美食文化之旅', tripId: 'TEAM-MY-FOOD', type: '缴费提醒', scheduledTime: '2026-04-27 14:00', recipients: 15, content: '【马来半岛美食团】温馨提示：请在出发前3天完成尾款支付，金额：¥5,000...', priority: '重要' },
  { id: 5, trip: '北海道春季赏樱团', tripId: 'TEAM-JP-SPRING', type: '出发提醒', scheduledTime: '2026-04-18 18:00', recipients: 20, content: '【北海道赏樱团】亲爱的游客，您好！后天我们即将开启北海道春季赏樱之旅...', priority: '重要' },
  { id: 6, trip: '云南丽江深度游', tripId: 'TEAM-YUNNAN-001', type: '天气预警', scheduledTime: '2026-04-26 07:00', recipients: 18, content: '【云南丽江团】天气预警：明日有小雨，气温15℃至22℃。请携带雨具，注意保暖...', priority: '普通' },
  { id: 7, trip: '四川九寨沟风光团', tripId: 'TEAM-SICHUAN-002', type: '景区通知', scheduledTime: '2026-04-26 09:00', recipients: 15, content: '【九寨沟风光团】景区通知：九寨沟景区今日游客较多，建议错峰游览，请跟紧领队...', priority: '普通' },
  { id: 8, trip: '阿勒泰本地冬营团', tripId: 'TEAM-DEMO-POST', type: '满意度调查', scheduledTime: '2026-03-18 15:00', recipients: 12, content: '【阿勒泰冬营团】您好！感谢参加本次旅行。为了提升服务质量，请填写满意度调查问卷...', priority: '普通' },
]

function priorityClass(priority: string): string {
  if (priority === '紧急') return 'bg-red-100 text-red-700'
  if (priority === '重要') return 'bg-orange-100 text-orange-700'
  return 'bg-gray-100 text-gray-700'
}

export function PendingNotificationsPage({ onNavigate }: PendingNotificationsPageProps) {
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 5
  const totalPages = Math.max(1, Math.ceil(pendingNotifications.length / itemsPerPage))
  const currentNotifications = pendingNotifications.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage)

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <button onClick={() => onNavigate('/dashboard')} className="text-gray-600 hover:text-gray-900">← 返回仪表盘</button>
            <h1 className="text-2xl font-bold text-gray-900">待发通知</h1>
          </div>
          <p className="text-gray-600">查看所有待发送的通知任务</p>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-gray-900">待发通知列表 ({pendingNotifications.length} 条)</h2>
            <button className="px-4 py-2 bg-cyan-500 text-white rounded-lg hover:bg-cyan-600 text-sm">+ 创建新通知</button>
          </div>
        </div>

        <div className="divide-y divide-gray-200">
          {currentNotifications.map((notification) => (
            <div key={notification.id} className="p-6 hover:bg-gray-50">
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="font-semibold text-gray-900">{notification.type}</h3>
                    <span className={`px-2 py-1 rounded-full text-xs ${priorityClass(notification.priority)}`}>{notification.priority}</span>
                  </div>
                  <div className="text-sm text-gray-600 mb-2"><button onClick={() => onNavigate(`/trips/${notification.tripId}`)} className="text-cyan-600 hover:underline">{notification.trip}</button></div>
                </div>
                <div className="text-right"><div className="text-sm text-gray-600 mb-1">发送时间</div><div className="text-sm font-medium text-gray-900">{notification.scheduledTime}</div></div>
              </div>

              <div className="bg-gray-50 rounded-lg p-4 mb-3"><div className="text-xs text-gray-600 mb-1">通知内容</div><div className="text-sm text-gray-700">{notification.content}</div></div>

              <div className="flex items-center justify-between">
                <div className="text-sm text-gray-600">接收人数: <span className="font-medium text-gray-900">{notification.recipients} 人</span></div>
                <div className="flex gap-2">
                  <button className="px-3 py-1 bg-cyan-500 text-white rounded text-sm hover:bg-cyan-600">立即发送</button>
                  <button className="px-3 py-1 bg-white border border-gray-300 text-gray-700 rounded text-sm hover:bg-gray-50">编辑</button>
                  <button className="px-3 py-1 bg-white border border-gray-300 text-gray-700 rounded text-sm hover:bg-gray-50">预览</button>
                  <button className="px-3 py-1 text-red-600 text-sm hover:underline">删除</button>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex items-center justify-between">
          <div className="text-sm text-gray-600">共 {pendingNotifications.length} 条记录，当前第 {currentPage} / {totalPages} 页</div>
          <div className="flex gap-2">
            <button onClick={() => setCurrentPage(1)} disabled={currentPage === 1} className="px-3 py-1 text-sm rounded bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:bg-gray-200 disabled:text-gray-400">第一页</button>
            <button onClick={() => setCurrentPage(currentPage - 1)} disabled={currentPage === 1} className="px-3 py-1 text-sm rounded bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:bg-gray-200 disabled:text-gray-400">上一页</button>
            {Array.from({ length: totalPages }, (_, index) => index + 1).map((page) => <button key={page} onClick={() => setCurrentPage(page)} className={`px-3 py-1 text-sm rounded ${currentPage === page ? 'bg-cyan-500 text-white' : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'}`}>{page}</button>)}
            <button onClick={() => setCurrentPage(currentPage + 1)} disabled={currentPage === totalPages} className="px-3 py-1 text-sm rounded bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:bg-gray-200 disabled:text-gray-400">下一页</button>
            <button onClick={() => setCurrentPage(totalPages)} disabled={currentPage === totalPages} className="px-3 py-1 text-sm rounded bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:bg-gray-200 disabled:text-gray-400">最后一页</button>
          </div>
        </div>
      </div>
    </div>
  )
}
