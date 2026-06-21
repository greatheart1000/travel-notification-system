import { useEffect, useState } from 'react'
import { ArrowLeft, ClipboardList, Users, Calendar, MessageSquare } from 'lucide-react'
import { FigmaTripService } from '../services/figmaTripService'
import type { MakeNotificationRule, MakeTourist } from '../data/figmaMockData'
import { TripWorkflowPanel } from '../components/trip/TripWorkflowPanel'
import { TripStaffForm } from '../components/trip/TripStaffForm'
import { TripWecomConfig } from '../components/trip/TripWecomConfig'

interface TripDetailProps {
  tripId: string | null
  onBack: () => void
}

const TABS = [
  { key: 'detail', label: '行程详情', icon: Calendar },
  { key: 'workflow', label: '执行流程', icon: ClipboardList },
  { key: 'staff', label: '人员配置', icon: Users },
  { key: 'wecom', label: '群配置', icon: MessageSquare },
] as const

function buildNewTourist(index: number): MakeTourist {
  return {
    name: `新游客${index + 1}`,
    age: 30,
    gender: '女',
    phone: '180****0000',
    wechat: 'new_guest_wx',
    idCard: '11010119900101****',
    notes: '',
  }
}

function mealCell(value: string) {
  return <span className={value === '√' ? 'text-green-600 font-bold' : 'text-gray-400'}>{value}</span>
}

export function TripDetail({ tripId, onBack }: TripDetailProps) {
  const [trip, setTrip] = useState<Awaited<ReturnType<typeof FigmaTripService.getTripDetail>>>(undefined)
  const [editingNotificationIndex, setEditingNotificationIndex] = useState<number | null>(null)
  const [editedNotification, setEditedNotification] = useState<MakeNotificationRule | null>(null)
  const [editingTouristIndex, setEditingTouristIndex] = useState<number | null>(null)
  const [editedTourist, setEditedTourist] = useState<MakeTourist | null>(null)
  const [toast, setToast] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(Boolean(tripId))
  const [loadError, setLoadError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<string>('workflow')

  useEffect(() => {
    if (!tripId) {
      setTrip(undefined)
      setIsLoading(false)
      return
    }

    let active = true

    const loadTrip = async () => {
      setIsLoading(true)
      setLoadError(null)
      try {
        const nextTrip = await FigmaTripService.getTripDetail(tripId)
        if (active) setTrip(nextTrip)
      } catch (error) {
        if (active) setLoadError(error instanceof Error ? error.message : 'API 行程详情加载失败')
      } finally {
        if (active) setIsLoading(false)
      }
    }

    void loadTrip()

    return () => {
      active = false
    }
  }, [tripId])

  if (isLoading) {
    return (
      <div className="p-6">
        <button onClick={onBack} className="mb-4 flex items-center gap-2 text-sm text-cyan-600 hover:text-cyan-700">
          <ArrowLeft className="h-4 w-4" /> 返回列表
        </button>
        <div className="rounded-lg border border-gray-200 bg-white p-6 text-center text-gray-600">正在通过 API 加载行程详情...</div>
      </div>
    )
  }

  if (loadError) {
    return (
      <div className="p-6">
        <button onClick={onBack} className="mb-4 flex items-center gap-2 text-sm text-cyan-600 hover:text-cyan-700">
          <ArrowLeft className="h-4 w-4" /> 返回列表
        </button>
        <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-red-700">{loadError}</div>
      </div>
    )
  }

  if (!trip) {
    return (
      <div className="p-6">
        <button onClick={onBack} className="mb-4 flex items-center gap-2 text-sm text-cyan-600 hover:text-cyan-700">
          <ArrowLeft className="h-4 w-4" /> 返回列表
        </button>
        <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-red-700">未找到该旅行团，请返回列表重新选择。</div>
      </div>
    )
  }

  const enabledNotificationCount = trip.notifications.filter((notification) => notification.enabled ?? notification.status === '已启用').length
  const estimatedSmsCost = (trip.tourists.length * enabledNotificationCount * 0.05).toFixed(2)

  const updateTrip = (nextTrip?: Awaited<ReturnType<typeof FigmaTripService.getTripDetail>>) => {
    if (nextTrip) setTrip(nextTrip)
  }

  const handleToggleNotification = async (index: number) => {
    const notification = trip.notifications[index]
    const isEnabled = notification.enabled ?? notification.status === '已启用'
    updateTrip(await FigmaTripService.updateNotification(trip.teamId, index, {
      ...notification,
      enabled: !isEnabled,
      status: isEnabled ? '未启用' : '已启用',
    }))
  }

  const handleEditNotification = (index: number) => {
    setEditingNotificationIndex(index)
    setEditedNotification({ ...trip.notifications[index] })
  }

  const handleConfirmNotification = async (index: number) => {
    const nextNotification = editingNotificationIndex === index && editedNotification ? editedNotification : trip.notifications[index]
    updateTrip(await FigmaTripService.updateNotification(trip.teamId, index, {
      ...nextNotification,
      enabled: true,
      status: '已启用',
    }))
    setEditingNotificationIndex(null)
    setEditedNotification(null)
    setToast('短信通知已确认启用')
  }

  const handleDeleteNotification = async (index: number) => {
    if (!window.confirm(`确认删除“${trip.notifications[index].title}”通知吗？`)) return
    updateTrip(await FigmaTripService.deleteNotification(trip.teamId, index))
    setEditingNotificationIndex(null)
    setEditedNotification(null)
    setToast('短信通知已删除')
  }

  const handleImportTouristsExcel = async () => {
    updateTrip(await FigmaTripService.importTouristsFromExcel(trip.teamId))
    setToast('Excel 导入成功：已通过 API 追加 2 位游客')
  }

  const handleAddTourist = async () => {
    const tourist = buildNewTourist(trip.tourists.length)
    updateTrip(await FigmaTripService.addTourist(trip.teamId, tourist))
    setToast(`已添加游客：${tourist.name}`)
  }

  const handleEditTourist = (index: number) => {
    setEditingTouristIndex(index)
    setEditedTourist({ ...trip.tourists[index] })
  }

  const handleSaveTourist = async () => {
    if (editingTouristIndex === null || !editedTourist) return
    updateTrip(await FigmaTripService.updateTourist(trip.teamId, editingTouristIndex, editedTourist))
    setEditingTouristIndex(null)
    setEditedTourist(null)
    setToast('游客信息已保存')
  }

  const handleCancelTouristEdit = () => {
    setEditingTouristIndex(null)
    setEditedTourist(null)
  }

  const handleDeleteTourist = async (index: number) => {
    if (!window.confirm(`确定要删除游客“${trip.tourists[index].name}”吗？`)) return
    updateTrip(await FigmaTripService.deleteTourist(trip.teamId, index))
    setToast('游客已删除')
  }

  return (
    <div className="p-6">
      <div className="mb-4 flex items-center justify-between">
        <button onClick={onBack} className="flex items-center gap-2 text-sm text-cyan-600 hover:text-cyan-700">
          <ArrowLeft className="h-4 w-4" /> 返回列表
        </button>
      </div>

      {/* Tab 导航 */}
      <div className="flex gap-1 mb-4 border-b">
        {TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`flex items-center gap-1.5 px-4 py-2 text-sm border-b-2 -mb-px transition-colors ${
              activeTab === key
                ? 'border-cyan-500 text-cyan-600 font-medium'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      {/* 执行流程 Tab */}
      {activeTab === 'workflow' && tripId && (
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <TripWorkflowPanel tripId={tripId} currentStage="in_trip" />
        </div>
      )}

      {/* 人员配置 Tab */}
      {activeTab === 'staff' && tripId && (
        <div className="rounded-lg border border-gray-200 bg-white p-4 max-w-lg">
          <TripStaffForm tripId={tripId} />
        </div>
      )}

      {/* 群配置 Tab */}
      {activeTab === 'wecom' && tripId && (
        <div className="rounded-lg border border-gray-200 bg-white p-4 max-w-lg">
          <TripWecomConfig tripId={tripId} />
        </div>
      )}

      {/* 行程详情 Tab */}
      {activeTab === 'detail' && (
      <div className="max-w-none space-y-6">
        <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
          <div className="bg-gradient-to-r from-cyan-500 to-blue-600 px-6 py-4 text-white">
            <h1 className="mb-2 text-2xl font-bold">{trip.name}</h1>
            <div className="flex flex-wrap gap-4 text-sm opacity-90">
              <span>团号：{trip.code}</span>
              <span>日期：{trip.startDate} 至 {trip.endDate}</span>
              <span>人数：{trip.tourists.length} 人</span>
              <span>领队：{trip.leader}</span>
            </div>
          </div>
          <div className="grid grid-cols-1 gap-4 p-6 md:grid-cols-4">
            <div className="rounded-lg bg-cyan-50 p-4">
              <div className="text-sm text-cyan-700">游客人数</div>
              <div className="mt-2 text-3xl font-bold text-cyan-700">{trip.tourists.length}</div>
            </div>
            <div className="rounded-lg bg-green-50 p-4">
              <div className="text-sm text-green-700">行程天数</div>
              <div className="mt-2 text-3xl font-bold text-green-700">{trip.itinerary.length}</div>
            </div>
            <div className="rounded-lg bg-purple-50 p-4">
              <div className="text-sm text-purple-700">启用通知</div>
              <div className="mt-2 text-3xl font-bold text-purple-700">{enabledNotificationCount}</div>
            </div>
            <div className="rounded-lg bg-orange-50 p-4">
              <div className="text-sm text-orange-700">预计短信费</div>
              <div className="mt-2 text-3xl font-bold text-orange-700">¥{estimatedSmsCost}</div>
            </div>
          </div>
        </div>

        {toast ? <div className="rounded-lg bg-cyan-50 px-4 py-3 text-sm text-cyan-700">{toast}</div> : null}

        <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
          <div className="border-b border-gray-200 bg-gray-50 px-6 py-4">
            <div className="flex items-center gap-2">
              <div className="h-5 w-1 rounded-full bg-cyan-500" />
              <h2 className="font-semibold text-gray-900">详细行程</h2>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 bg-gray-50 text-left text-xs font-medium uppercase text-gray-600">
                  <th className="px-4 py-3">日期</th>
                  <th className="px-4 py-3">交通</th>
                  <th className="min-w-[360px] px-4 py-3">行程</th>
                  <th className="px-4 py-3 text-center">早</th>
                  <th className="px-4 py-3 text-center">中</th>
                  <th className="px-4 py-3 text-center">晚</th>
                  <th className="min-w-[180px] px-4 py-3">酒店</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {trip.itinerary.map((day) => (
                  <tr key={`${day.date}-${day.activity}`} className="hover:bg-gray-50">
                    <td className="whitespace-nowrap px-4 py-3 font-medium text-gray-900">{day.date}</td>
                    <td className="whitespace-nowrap px-4 py-3 text-gray-700">{day.type}</td>
                    <td className="px-4 py-3 leading-relaxed text-gray-800">{day.activity}</td>
                    <td className="px-4 py-3 text-center">{mealCell(day.breakfast)}</td>
                    <td className="px-4 py-3 text-center">{mealCell(day.lunch)}</td>
                    <td className="px-4 py-3 text-center">{mealCell(day.dinner)}</td>
                    <td className="px-4 py-3 text-gray-700">{day.hotel}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
          <div className="border-b border-gray-200 bg-gradient-to-r from-purple-50 to-blue-50 px-6 py-4">
            <div className="flex items-center gap-3">
              <div className="text-2xl">🤖</div>
              <div>
                <h2 className="text-lg font-bold text-gray-900">智能短信通知系统</h2>
                <p className="mt-1 text-xs text-gray-600">基于行程自动触发 · 智能模板变量替换 · 多场景覆盖</p>
              </div>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 bg-gray-50 text-left text-xs font-medium uppercase text-gray-600">
                  <th className="w-28 px-4 py-3">阶段</th>
                  <th className="w-32 px-4 py-3">触发时间</th>
                  <th className="w-40 px-4 py-3">通知标题</th>
                  <th className="min-w-[440px] px-4 py-3">短信内容</th>
                  <th className="w-24 px-4 py-3">状态</th>
                  <th className="w-28 px-4 py-3">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {trip.notifications.map((notification, index) => {
                  const isEditing = editingNotificationIndex === index
                  const displayNotification = isEditing && editedNotification ? editedNotification : notification
                  const enabled = displayNotification.enabled ?? displayNotification.status === '已启用'

                  return (
                    <tr key={notification.id || `${notification.title}-${index}`} className="align-top hover:bg-gray-50">
                      <td className="px-4 py-4">
                        <div className="flex items-center gap-3">
                          <span className="text-lg">{displayNotification.icon}</span>
                          <span className="font-medium leading-5 text-gray-800">{displayNotification.phase}</span>
                        </div>
                      </td>
                      <td className="whitespace-pre-line px-4 py-4 leading-5 text-gray-700">{displayNotification.time}</td>
                      <td className="px-4 py-4">
                        <div className="font-medium leading-5 text-gray-900">{displayNotification.title}</div>
                        <span className={`mt-2 inline-flex rounded-full px-2 py-1 text-xs font-medium text-white ${displayNotification.tagColor}`}>
                          {displayNotification.tag}
                        </span>
                      </td>
                      <td className="px-4 py-4 leading-6 text-gray-700">
                        {isEditing ? (
                          <textarea
                            value={displayNotification.content}
                            onChange={(event) => setEditedNotification({ ...editedNotification!, content: event.target.value })}
                            className="min-h-[120px] w-full rounded border border-gray-300 px-3 py-2 text-sm leading-6 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                          />
                        ) : (
                          displayNotification.content
                        )}
                      </td>
                      <td className="px-4 py-4">
                        <label className="flex items-start gap-2 text-green-600">
                          <input
                            type="checkbox"
                            checked={enabled}
                            onChange={() => handleToggleNotification(index)}
                            className="mt-1 h-4 w-4 accent-cyan-500"
                          />
                          <span className="text-sm font-medium leading-5">{enabled ? '已启用' : '未启用'}</span>
                        </label>
                      </td>
                      <td className="px-4 py-4">
                        <div className="flex flex-col items-start gap-2 text-sm">
                          <button onClick={() => handleEditNotification(index)} className="text-blue-600 hover:text-blue-700">
                            编辑
                          </button>
                          <button onClick={() => handleConfirmNotification(index)} className="text-green-600 hover:text-green-700">
                            确认
                          </button>
                          <button onClick={() => handleDeleteNotification(index)} className="text-red-600 hover:text-red-700">
                            删除
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>

        <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
          <div className="border-b border-gray-200 bg-gray-50 px-6 py-4">
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-2">
                <div className="h-5 w-1 rounded bg-cyan-500" />
                <div>
                  <h2 className="font-bold text-gray-900">旅行团游客名单</h2>
                  <p className="mt-1 text-xs text-gray-600">共 {trip.tourists.length} 人，默认短信发送给以下所有游客</p>
                </div>
              </div>
              <div className="flex gap-2">
                <button onClick={handleImportTouristsExcel} className="rounded-lg bg-green-500 px-4 py-2 text-sm text-white hover:bg-green-600">导入Excel</button>
                <button onClick={handleAddTourist} className="rounded-lg bg-cyan-500 px-4 py-2 text-sm text-white hover:bg-cyan-600">添加游客</button>
              </div>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 bg-gray-50 text-left text-xs font-medium uppercase text-gray-600">
                  <th className="px-4 py-3">姓名</th>
                  <th className="px-4 py-3">性别</th>
                  <th className="px-4 py-3">年龄</th>
                  <th className="px-4 py-3">电话</th>
                  <th className="px-4 py-3">微信号</th>
                  <th className="px-4 py-3">身份证</th>
                  <th className="px-4 py-3">备注</th>
                  <th className="px-4 py-3">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {trip.tourists.length > 0 ? trip.tourists.map((tourist, index) => {
                  const isEditing = editingTouristIndex === index
                  const displayTourist = isEditing && editedTourist ? editedTourist : tourist

                  return (
                    <tr key={`${tourist.name}-${index}`} className={isEditing ? 'bg-blue-50' : 'hover:bg-gray-50'}>
                      <td className="px-4 py-3">
                        {isEditing ? <input value={displayTourist.name} onChange={(event) => setEditedTourist({ ...editedTourist!, name: event.target.value })} className="w-full rounded border border-gray-300 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500" /> : <span className="font-medium text-gray-900">{displayTourist.name}</span>}
                      </td>
                      <td className="px-4 py-3">
                        {isEditing ? (
                          <select value={displayTourist.gender} onChange={(event) => setEditedTourist({ ...editedTourist!, gender: event.target.value })} className="w-full rounded border border-gray-300 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500">
                            <option value="男">男</option>
                            <option value="女">女</option>
                          </select>
                        ) : <span className="text-gray-700">{displayTourist.gender}</span>}
                      </td>
                      <td className="px-4 py-3">
                        {isEditing ? <input type="number" value={displayTourist.age} onChange={(event) => setEditedTourist({ ...editedTourist!, age: Number(event.target.value) })} className="w-20 rounded border border-gray-300 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500" /> : <span className="text-gray-700">{displayTourist.age}</span>}
                      </td>
                      <td className="px-4 py-3">
                        {isEditing ? <input value={displayTourist.phone} onChange={(event) => setEditedTourist({ ...editedTourist!, phone: event.target.value })} className="w-full rounded border border-gray-300 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500" /> : <span className="text-gray-700">{displayTourist.phone}</span>}
                      </td>
                      <td className="px-4 py-3">
                        {isEditing ? <input value={displayTourist.wechat || ''} onChange={(event) => setEditedTourist({ ...editedTourist!, wechat: event.target.value })} className="w-full rounded border border-gray-300 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500" /> : <span className="text-green-600">{displayTourist.wechat || '-'}</span>}
                      </td>
                      <td className="px-4 py-3 text-gray-600">{displayTourist.idCard}</td>
                      <td className="px-4 py-3">
                        {isEditing ? <input value={displayTourist.notes} onChange={(event) => setEditedTourist({ ...editedTourist!, notes: event.target.value })} className="w-full rounded border border-gray-300 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500" placeholder="备注" /> : displayTourist.notes ? <span className="rounded bg-yellow-100 px-2 py-1 text-xs text-yellow-800">{displayTourist.notes}</span> : <span className="text-gray-400">-</span>}
                      </td>
                      <td className="px-4 py-3">
                        {isEditing ? (
                          <div className="flex gap-2">
                            <button onClick={handleSaveTourist} className="rounded bg-green-500 px-3 py-1 text-xs text-white hover:bg-green-600">保存</button>
                            <button onClick={handleCancelTouristEdit} className="rounded bg-gray-300 px-3 py-1 text-xs text-gray-700 hover:bg-gray-400">取消</button>
                          </div>
                        ) : (
                          <div className="flex gap-2">
                            <button onClick={() => handleEditTourist(index)} className="rounded px-3 py-1 text-xs text-blue-600 hover:bg-blue-50">编辑</button>
                            <button onClick={() => handleDeleteTourist(index)} className="rounded px-3 py-1 text-xs text-red-600 hover:bg-red-50">删除</button>
                          </div>
                        )}
                      </td>
                    </tr>
                  )
                }) : (
                  <tr>
                    <td colSpan={8} className="px-4 py-8 text-center text-gray-500">暂无游客信息，请点击“添加游客”或“导入Excel”添加</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <div className="border-t border-gray-200 bg-gray-50 px-6 py-4">
            <div className="flex items-center justify-between text-sm">
              <div className="text-gray-600"><span className="font-medium text-gray-900">发送对象：</span>以上所有游客将接收智能短信通知</div>
              <div className="flex items-center gap-4 text-xs text-gray-600">
                <span>总人数：<span className="font-bold text-gray-900">{trip.tourists.length}</span> 人</span>
                <span>预计费用：<span className="font-bold text-orange-600">¥{estimatedSmsCost}</span></span>
              </div>
            </div>
          </div>
        </div>

        <div className="flex justify-center gap-4 pt-4">
          <button onClick={onBack} className="rounded-lg border border-gray-300 bg-white px-6 py-3 font-medium text-gray-700 shadow-sm hover:bg-gray-50">
            返回列表
          </button>
        </div>
      </div>
      )}
    </div>
  )
}
