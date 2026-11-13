import { useEffect, useState } from 'react'
import { ArrowLeft, BellRing, ClipboardList, Users, Calendar, MessageSquare } from 'lucide-react'
import { FigmaTripService } from '../services/figmaTripService'
import type { MakeNotificationRule, MakeTourist } from '../data/figmaMockData'
import { PageShell } from '../components/PageShell'
import { Button } from '../components/Button'
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
  return <span className={value === '√' ? 'text-success-600 font-semibold' : 'text-paper-400'}>{value}</span>
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

  const backButton = (
    <button
      type="button"
      onClick={onBack}
      className="inline-flex items-center gap-1.5 text-sm text-paper-500 transition-colors hover:text-paper-900"
    >
      <ArrowLeft className="h-4 w-4" /> 返回列表
    </button>
  )

  if (isLoading) {
    return (
      <PageShell title="行程详情" actions={backButton}>
        <div className="rounded-card border border-paper-200 bg-white p-6 text-center text-sm text-paper-500">
          正在加载行程详情
        </div>
      </PageShell>
    )
  }

  if (loadError) {
    return (
      <PageShell title="行程详情" actions={backButton}>
        <div className="rounded-card border border-danger-200 bg-danger-50 p-5 text-sm text-danger-700">
          {loadError}
        </div>
      </PageShell>
    )
  }

  if (!trip) {
    return (
      <PageShell title="行程详情" actions={backButton}>
        <div className="rounded-card border border-danger-200 bg-danger-50 p-5 text-sm text-danger-700">
          未找到该旅行团，请返回列表重新选择。
        </div>
      </PageShell>
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
    <PageShell
      title={trip.name}
      description={`团号 ${trip.code} · ${trip.startDate} 至 ${trip.endDate} · ${trip.tourists.length} 人 · 领队 ${trip.leader}`}
      actions={backButton}
    >
      {/* Tab 导航 */}
      <div className="mb-5 flex gap-1 border-b border-paper-200">
        {TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`flex items-center gap-1.5 px-5 py-2 text-sm border-b-2 -mb-px transition-colors ${
              activeTab === key
                ? 'border-accent-600 text-accent-700 font-medium'
                : 'border-transparent text-paper-500 hover:text-paper-900'
            }`}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      {/* 执行流程 Tab */}
      {activeTab === 'workflow' && tripId && (
        <div className="rounded-card border border-paper-200 bg-white p-4">
          <TripWorkflowPanel tripId={tripId} />
        </div>
      )}

      {/* 人员配置 Tab */}
      {activeTab === 'staff' && tripId && (
        <div className="rounded-card border border-paper-200 bg-white p-4 max-w-lg">
          <TripStaffForm tripId={tripId} />
        </div>
      )}

      {/* 群配置 Tab */}
      {activeTab === 'wecom' && tripId && (
        <div className="rounded-card border border-paper-200 bg-white p-4 max-w-lg">
          <TripWecomConfig tripId={tripId} />
        </div>
      )}

      {/* 行程详情 Tab */}
      {activeTab === 'detail' && (
      <div className="max-w-none space-y-6">
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <div className="rounded-card border border-paper-200 bg-white p-4 shadow-card">
            <p className="text-xs text-paper-500">游客人数</p>
            <p className="mt-2 text-2xl font-semibold tabular-nums text-paper-900">{trip.tourists.length}</p>
          </div>
          <div className="rounded-card border border-paper-200 bg-white p-4 shadow-card">
            <p className="text-xs text-paper-500">行程天数</p>
            <p className="mt-2 text-2xl font-semibold tabular-nums text-paper-900">{trip.itinerary.length}</p>
          </div>
          <div className="rounded-card border border-paper-200 bg-white p-4 shadow-card">
            <p className="text-xs text-paper-500">启用通知</p>
            <p className="mt-2 text-2xl font-semibold tabular-nums text-accent-700">{enabledNotificationCount}</p>
          </div>
          <div className="rounded-card border border-paper-200 bg-white p-4 shadow-card">
            <p className="text-xs text-paper-500">预计短信费</p>
            <p className="mt-2 text-2xl font-semibold tabular-nums text-paper-900">¥{estimatedSmsCost}</p>
          </div>
        </div>

        {toast ? (
          <div className="rounded-control border border-accent-200 bg-accent-50 px-5 py-3 text-sm text-accent-800">
            {toast}
          </div>
        ) : null}

        <div className="overflow-hidden rounded-card border border-paper-200 bg-white shadow-card">
          <div className="border-b border-paper-200 px-5 py-3">
            <h2 className="text-base font-semibold text-paper-900">详细行程</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-paper-200 text-left text-xs font-medium text-paper-500">
                  <th className="px-5 py-3">日期</th>
                  <th className="px-5 py-3">交通</th>
                  <th className="min-w-[360px] px-5 py-3">行程</th>
                  <th className="px-5 py-3 text-center">早</th>
                  <th className="px-5 py-3 text-center">中</th>
                  <th className="px-5 py-3 text-center">晚</th>
                  <th className="min-w-[180px] px-5 py-3">酒店</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-paper-100">
                {trip.itinerary.map((day) => (
                  <tr key={`${day.date}-${day.activity}`} className="hover:bg-paper-50">
                    <td className="whitespace-nowrap px-5 py-3 font-medium text-paper-900">{day.date}</td>
                    <td className="whitespace-nowrap px-5 py-3 text-paper-700">{day.type}</td>
                    <td className="px-5 py-3 leading-relaxed text-paper-800">{day.activity}</td>
                    <td className="px-5 py-3 text-center">{mealCell(day.breakfast)}</td>
                    <td className="px-5 py-3 text-center">{mealCell(day.lunch)}</td>
                    <td className="px-5 py-3 text-center">{mealCell(day.dinner)}</td>
                    <td className="px-5 py-3 text-paper-700">{day.hotel}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="overflow-hidden rounded-card border border-paper-200 bg-white shadow-card">
          <div className="border-b border-paper-200 px-5 py-3">
            <div className="flex items-start gap-2.5">
              <BellRing className="mt-0.5 h-4 w-4 text-paper-500" />
              <div>
                <h2 className="text-base font-semibold text-paper-900">智能短信通知系统</h2>
                <p className="mt-1 text-xs text-paper-500">按阶段、时间点和场景发送，内容可在线编辑</p>
              </div>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-paper-200 text-left text-xs font-medium text-paper-500">
                  <th className="w-28 px-5 py-3">阶段</th>
                  <th className="w-32 px-5 py-3">触发时间</th>
                  <th className="w-40 px-5 py-3">通知标题</th>
                  <th className="min-w-[440px] px-5 py-3">短信内容</th>
                  <th className="w-24 px-5 py-3">状态</th>
                  <th className="w-28 px-5 py-3">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-paper-100">
                {trip.notifications.map((notification, index) => {
                  const isEditing = editingNotificationIndex === index
                  const displayNotification = isEditing && editedNotification ? editedNotification : notification
                  const enabled = displayNotification.enabled ?? displayNotification.status === '已启用'

                  return (
                    <tr key={notification.id || `${notification.title}-${index}`} className="align-top hover:bg-paper-50">
                      <td className="px-5 py-3">
                        <div className="flex items-center gap-2.5">
                          <BellRing className="h-4 w-4 text-paper-400" />
                          <span className="font-medium leading-5 text-paper-800">{displayNotification.phase}</span>
                        </div>
                      </td>
                      <td className="whitespace-pre-line px-5 py-3 leading-5 text-paper-700">{displayNotification.time}</td>
                      <td className="px-5 py-3">
                        <div className="font-medium leading-5 text-paper-900">{displayNotification.title}</div>
                        <span className="mt-2 inline-flex rounded-control bg-paper-100 px-2 py-0.5 text-xs font-medium text-paper-600">
                          {displayNotification.tag}
                        </span>
                      </td>
                      <td className="px-5 py-3 leading-6 text-paper-700">
                        {isEditing ? (
                          <textarea
                            value={displayNotification.content}
                            onChange={(event) => setEditedNotification({ ...editedNotification!, content: event.target.value })}
                            className="min-h-32 w-full rounded-control border border-paper-300 px-3 py-2 text-sm leading-6 focus:border-accent-600 focus:outline-none focus:ring-2 focus:ring-accent-100"
                          />
                        ) : (
                          displayNotification.content
                        )}
                      </td>
                      <td className="px-5 py-3">
                        <label className="flex items-start gap-2 text-success-600">
                          <input
                            type="checkbox"
                            checked={enabled}
                            onChange={() => handleToggleNotification(index)}
                            className="mt-1 h-4 w-4 accent-accent-600"
                          />
                          <span className="text-sm font-medium leading-5">{enabled ? '已启用' : '未启用'}</span>
                        </label>
                      </td>
                      <td className="px-5 py-3">
                        <div className="flex flex-col items-start gap-2 text-sm">
                          <button onClick={() => handleEditNotification(index)} className="text-accent-600 hover:text-accent-700">
                            编辑
                          </button>
                          <button onClick={() => handleConfirmNotification(index)} className="text-success-600 hover:text-success-700">
                            确认
                          </button>
                          <button onClick={() => handleDeleteNotification(index)} className="text-danger-600 hover:text-danger-700">
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

        <div className="overflow-hidden rounded-card border border-paper-200 bg-white shadow-card">
          <div className="flex flex-col gap-3 border-b border-paper-200 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-base font-semibold text-paper-900">旅行团游客名单</h2>
              <p className="mt-1 text-xs text-paper-500">共 {trip.tourists.length} 人，默认短信发送给以下所有游客</p>
            </div>
            <div className="flex gap-2">
              <Button size="sm" variant="secondary" onClick={() => void handleImportTouristsExcel()}>
                导入Excel
              </Button>
              <Button size="sm" onClick={() => void handleAddTourist()}>
                添加游客
              </Button>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-paper-200 text-left text-xs font-medium text-paper-500">
                  <th className="px-5 py-3">姓名</th>
                  <th className="px-5 py-3">性别</th>
                  <th className="px-5 py-3">年龄</th>
                  <th className="px-5 py-3">电话</th>
                  <th className="px-5 py-3">微信号</th>
                  <th className="px-5 py-3">身份证</th>
                  <th className="px-5 py-3">备注</th>
                  <th className="px-5 py-3">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-paper-100">
                {trip.tourists.length > 0 ? trip.tourists.map((tourist, index) => {
                  const isEditing = editingTouristIndex === index
                  const displayTourist = isEditing && editedTourist ? editedTourist : tourist

                  return (
                    <tr key={`${tourist.name}-${index}`} className={isEditing ? 'bg-accent-50' : 'hover:bg-paper-50'}>
                      <td className="px-5 py-3">
                        {isEditing ? <input value={displayTourist.name} onChange={(event) => setEditedTourist({ ...editedTourist!, name: event.target.value })} className="w-full rounded-control border border-paper-300 px-2 py-1 text-sm focus:border-accent-600 focus:outline-none focus:ring-2 focus:ring-accent-100" /> : <span className="font-medium text-paper-900">{displayTourist.name}</span>}
                      </td>
                      <td className="px-5 py-3">
                        {isEditing ? (
                          <select value={displayTourist.gender} onChange={(event) => setEditedTourist({ ...editedTourist!, gender: event.target.value })} className="w-full rounded-control border border-paper-300 px-2 py-1 text-sm focus:border-accent-600 focus:outline-none focus:ring-2 focus:ring-accent-100">
                            <option value="男">男</option>
                            <option value="女">女</option>
                          </select>
                        ) : <span className="text-paper-700">{displayTourist.gender}</span>}
                      </td>
                      <td className="px-5 py-3">
                        {isEditing ? <input type="number" value={displayTourist.age} onChange={(event) => setEditedTourist({ ...editedTourist!, age: Number(event.target.value) })} className="w-20 rounded-control border border-paper-300 px-2 py-1 text-sm focus:border-accent-600 focus:outline-none focus:ring-2 focus:ring-accent-100" /> : <span className="text-paper-700">{displayTourist.age}</span>}
                      </td>
                      <td className="px-5 py-3">
                        {isEditing ? <input value={displayTourist.phone} onChange={(event) => setEditedTourist({ ...editedTourist!, phone: event.target.value })} className="w-full rounded-control border border-paper-300 px-2 py-1 text-sm focus:border-accent-600 focus:outline-none focus:ring-2 focus:ring-accent-100" /> : <span className="text-paper-700">{displayTourist.phone}</span>}
                      </td>
                      <td className="px-5 py-3">
                        {isEditing ? <input value={displayTourist.wechat || ''} onChange={(event) => setEditedTourist({ ...editedTourist!, wechat: event.target.value })} className="w-full rounded-control border border-paper-300 px-2 py-1 text-sm focus:border-accent-600 focus:outline-none focus:ring-2 focus:ring-accent-100" /> : <span className="text-success-600">{displayTourist.wechat || '-'}</span>}
                      </td>
                      <td className="px-5 py-3 text-paper-600">{displayTourist.idCard}</td>
                      <td className="px-5 py-3">
                        {isEditing ? <input value={displayTourist.notes} onChange={(event) => setEditedTourist({ ...editedTourist!, notes: event.target.value })} className="w-full rounded-control border border-paper-300 px-2 py-1 text-sm focus:border-accent-600 focus:outline-none focus:ring-2 focus:ring-accent-100" placeholder="备注" /> : displayTourist.notes ? <span className="rounded-control bg-warning-50 px-2 py-0.5 text-xs text-warning-700">{displayTourist.notes}</span> : <span className="text-paper-400">-</span>}
                      </td>
                      <td className="px-5 py-3">
                        {isEditing ? (
                          <div className="flex gap-2">
                            <button onClick={handleSaveTourist} className="rounded-control bg-success-600 px-2.5 py-1 text-xs text-white hover:bg-success-700">保存</button>
                            <button onClick={handleCancelTouristEdit} className="rounded-control border border-paper-300 bg-white px-2.5 py-1 text-xs text-paper-700 hover:bg-paper-50">取消</button>
                          </div>
                        ) : (
                          <div className="flex gap-2">
                            <button onClick={() => handleEditTourist(index)} className="rounded-control px-2.5 py-1 text-xs text-accent-700 hover:bg-accent-50">编辑</button>
                            <button onClick={() => handleDeleteTourist(index)} className="rounded-control px-2.5 py-1 text-xs text-danger-700 hover:bg-danger-50">删除</button>
                          </div>
                        )}
                      </td>
                    </tr>
                  )
                }) : (
                  <tr>
                    <td colSpan={8} className="px-5 py-8 text-center text-paper-500">暂无游客信息，请点击“添加游客”或“导入Excel”添加</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <div className="border-t border-paper-200 bg-paper-50 px-6 py-4">
            <div className="flex items-center justify-between text-sm">
              <div className="text-paper-600"><span className="font-medium text-paper-900">发送对象：</span>以上所有游客将接收智能短信通知</div>
              <div className="flex items-center gap-4 text-xs text-paper-600">
                <span>总人数：<span className="font-semibold text-paper-900">{trip.tourists.length}</span> 人</span>
                <span>预计费用：<span className="font-semibold text-paper-900">¥{estimatedSmsCost}</span></span>
              </div>
            </div>
          </div>
        </div>

        <div className="flex justify-center gap-4 pt-4">
          <Button variant="secondary" onClick={onBack}>
            返回列表
          </Button>
        </div>
      </div>
      )}
    </PageShell>
  )
}
