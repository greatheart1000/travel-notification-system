import { useEffect, useMemo, useState } from 'react'
import { ArrowLeft, Sparkles } from 'lucide-react'
import { FigmaTripService } from '../services/figmaTripService'
import type { MakeNotificationRule } from '../data/figmaMockData'

interface TripNotificationsProps {
  tripId: string
  onBackToTrip?: () => void
}

function statusClass(status: string): string {
  if (status === '已启用') return 'bg-green-100 text-green-700'
  if (status === '已发送') return 'bg-blue-100 text-blue-700'
  if (status === '待发送') return 'bg-yellow-100 text-yellow-700'
  return 'bg-gray-100 text-gray-600'
}

function buildAiContent(tripName: string, notification: MakeNotificationRule): string {
  return `【${tripName}】${notification.coreWork}：系统已结合当前行程、天气与集合安排生成通知。请游客关注领队最新提示，按时到达集合地点，携带个人证件与必要物品。如需帮助请及时联系领队。祝您旅途顺利！`
}

export function TripNotifications({ tripId, onBackToTrip }: TripNotificationsProps) {
  const [trip, setTrip] = useState<Awaited<ReturnType<typeof FigmaTripService.getTripDetail>>>(undefined)
  const [editingNotificationIndex, setEditingNotificationIndex] = useState<number | null>(null)
  const [editedNotification, setEditedNotification] = useState<MakeNotificationRule | null>(null)
  const [contentMode, setContentMode] = useState<'manual' | 'ai'>('manual')
  const [toast, setToast] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)

  useEffect(() => {
    let active = true

    const loadTrip = async () => {
      setIsLoading(true)
      setLoadError(null)
      try {
        const nextTrip = await FigmaTripService.getTripDetail(tripId)
        if (active) setTrip(nextTrip)
      } catch (error) {
        if (active) setLoadError(error instanceof Error ? error.message : 'API 通知配置加载失败')
      } finally {
        if (active) setIsLoading(false)
      }
    }

    void loadTrip()

    return () => {
      active = false
    }
  }, [tripId])

  const summary = useMemo(() => {
    if (!trip) return { enabled: 0, sent: 0, pending: 0 }
    return {
      enabled: trip.notifications.filter((item) => item.status === '已启用').length,
      sent: trip.notifications.filter((item) => item.status === '已发送').length,
      pending: trip.notifications.filter((item) => item.status === '待发送' || item.status === '未启用').length,
    }
  }, [trip])

  if (isLoading) {
    return (
      <div className="p-6">
        <button onClick={onBackToTrip} className="mb-4 flex items-center gap-2 text-sm text-cyan-600 hover:text-cyan-700">
          <ArrowLeft className="h-4 w-4" /> 返回团详情
        </button>
        <div className="rounded-lg border border-gray-200 bg-white p-6 text-center text-gray-600">正在通过 API 加载通知配置...</div>
      </div>
    )
  }

  if (loadError) {
    return (
      <div className="p-6">
        <button onClick={onBackToTrip} className="mb-4 flex items-center gap-2 text-sm text-cyan-600 hover:text-cyan-700">
          <ArrowLeft className="h-4 w-4" /> 返回团详情
        </button>
        <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-red-700">{loadError}</div>
      </div>
    )
  }

  if (!trip) {
    return (
      <div className="p-6">
        <button onClick={onBackToTrip} className="mb-4 flex items-center gap-2 text-sm text-cyan-600 hover:text-cyan-700">
          <ArrowLeft className="h-4 w-4" /> 返回团详情
        </button>
        <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-red-700">未找到通知配置。</div>
      </div>
    )
  }

  const handleEditNotification = (notification: MakeNotificationRule, index: number) => {
    setEditingNotificationIndex(index)
    setEditedNotification({ ...notification })
    setContentMode('manual')
  }

  const handleGenerateAIContent = () => {
    if (!editedNotification) return
    setEditedNotification({
      ...editedNotification,
      content: buildAiContent(trip.name, editedNotification),
    })
  }

  const handleSaveNotification = async () => {
    if (editingNotificationIndex === null || !editedNotification) return
    const nextTrip = await FigmaTripService.updateNotification(trip.teamId, editingNotificationIndex, editedNotification)
    if (nextTrip) setTrip(nextTrip)
    setToast('通知规则已通过 API 保存')
    setEditingNotificationIndex(null)
    setEditedNotification(null)
  }

  const handleCancelNotificationEdit = () => {
    setEditingNotificationIndex(null)
    setEditedNotification(null)
    setContentMode('manual')
  }

  return (
    <div className="p-6">
      <button onClick={onBackToTrip} className="mb-4 flex items-center gap-2 text-sm text-cyan-600 hover:text-cyan-700">
        <ArrowLeft className="h-4 w-4" /> 返回团详情
      </button>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 mb-6 overflow-hidden">
        <div className="px-6 py-4 bg-gradient-to-r from-cyan-500 to-blue-600 text-white">
          <h1 className="text-2xl font-bold mb-2">{trip.name} - 通知设置</h1>
          <div className="flex flex-wrap gap-4 text-sm opacity-90">
            <span>团号：{trip.code}</span>
            <span>游客：{trip.tourists?.length ?? trip.participants} 人</span>
            <span>领队：{trip.leader}</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 mb-6 md:grid-cols-3">
        <div className="rounded-lg border border-green-200 bg-green-50 p-4">
          <div className="text-sm text-green-700">已启用规则</div>
          <div className="mt-2 text-3xl font-bold text-green-700">{summary.enabled}</div>
        </div>
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
          <div className="text-sm text-blue-700">已发送记录</div>
          <div className="mt-2 text-3xl font-bold text-blue-700">{summary.sent}</div>
        </div>
        <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-4">
          <div className="text-sm text-yellow-700">待确认规则</div>
          <div className="mt-2 text-3xl font-bold text-yellow-700">{summary.pending}</div>
        </div>
      </div>

      {toast ? <div className="mb-4 rounded-lg bg-cyan-50 px-4 py-3 text-sm text-cyan-700">{toast}</div> : null}

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
          <h2 className="font-semibold text-gray-900">通知规则列表</h2>
          <p className="mt-1 text-xs text-gray-500">支持人工设置或 AI 生成短信内容，保存后写入浏览器本地 Mock 数据。</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-[1120px]">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <th className="w-28 px-4 py-3 text-left font-medium text-gray-700 whitespace-nowrap">阶段</th>
                <th className="w-36 px-4 py-3 text-left font-medium text-gray-700 whitespace-nowrap">时间节点</th>
                <th className="w-36 px-4 py-3 text-left font-medium text-gray-700 whitespace-nowrap">核心工作</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700 min-w-[420px]">具体执行动作（短信内容）</th>
                <th className="w-24 px-4 py-3 text-center font-medium text-gray-700 whitespace-nowrap">状态</th>
                <th className="w-28 px-4 py-3 text-center font-medium text-gray-700 whitespace-nowrap">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {trip.notifications.map((notification, index) => {
                const isEditing = editingNotificationIndex === index
                const displayNotification = isEditing && editedNotification ? editedNotification : notification

                return (
                  <tr key={`${notification.phase}-${notification.time}-${notification.coreWork}`} className={isEditing ? 'bg-blue-50' : 'hover:bg-gray-50'}>
                    <td className="px-4 py-3 text-gray-700">{displayNotification.phase}</td>
                    <td className="px-4 py-3 text-gray-700">{displayNotification.time}</td>
                    <td className="px-4 py-3 text-gray-900 font-medium">{displayNotification.coreWork}</td>
                    <td className="px-4 py-3">
                      {isEditing && editedNotification ? (
                        <div className="space-y-2">
                          <div className="flex gap-2 mb-2">
                            <button
                              onClick={() => setContentMode('manual')}
                              className={`px-3 py-1 text-xs rounded ${contentMode === 'manual' ? 'bg-cyan-500 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}
                            >
                              人工设置
                            </button>
                            <button
                              onClick={() => {
                                setContentMode('ai')
                                handleGenerateAIContent()
                              }}
                              className={`px-3 py-1 text-xs rounded inline-flex items-center gap-1 ${contentMode === 'ai' ? 'bg-purple-500 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}
                            >
                              <Sparkles className="h-3 w-3" /> AI生成
                            </button>
                          </div>
                          <textarea
                            value={editedNotification.content}
                            onChange={(event) => setEditedNotification({ ...editedNotification, content: event.target.value })}
                            className="w-full px-3 py-2 border border-gray-300 rounded text-xs leading-relaxed min-h-[100px] focus:outline-none focus:ring-2 focus:ring-cyan-500"
                            placeholder="请输入短信内容或使用AI生成"
                          />
                        </div>
                      ) : (
                        <div className="text-gray-600 text-xs leading-relaxed">{displayNotification.content}</div>
                      )}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`px-2 py-1 rounded-full text-xs ${statusClass(notification.status)}`}>{notification.status}</span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      {isEditing ? (
                        <div className="flex flex-col gap-1">
                          <button onClick={handleSaveNotification} className="px-2 py-1 text-xs bg-green-500 text-white rounded hover:bg-green-600 whitespace-nowrap">保存</button>
                          <button onClick={handleCancelNotificationEdit} className="px-2 py-1 text-xs bg-gray-300 text-gray-700 rounded hover:bg-gray-400 whitespace-nowrap">取消</button>
                        </div>
                      ) : (
                        <button onClick={() => handleEditNotification(notification, index)} className="px-2 py-1 text-xs text-blue-600 hover:bg-blue-50 rounded whitespace-nowrap">编辑</button>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
