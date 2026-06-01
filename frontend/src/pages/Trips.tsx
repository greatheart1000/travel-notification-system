import { useEffect, useMemo, useState } from 'react'
import { FigmaTripService, FigmaWeatherService } from '../services/figmaTripService'
import type { MakeTrip, MakeTripStatus, MakeWeatherInfo } from '../data/figmaMockData'
import { TripDetail } from './TripDetail'

interface TripsProps {
  tripId?: string | null
  onOpenTrip?: (tripId: string) => void
  onBackToList?: () => void
}

function editableTripCopy(trip: MakeTrip): MakeTrip {
  return { ...trip }
}

export function Trips({
  tripId = null,
  onOpenTrip,
  onBackToList,
}: TripsProps) {
  const [trips, setTrips] = useState<MakeTrip[]>([])
  const [selectedTrips, setSelectedTrips] = useState<string[]>([])
  const [currentPage, setCurrentPage] = useState(1)
  const [editingTripId, setEditingTripId] = useState<string | null>(null)
  const [editedTrip, setEditedTrip] = useState<MakeTrip | null>(null)
  const [toast, setToast] = useState<string | null>(null)
  const [weatherData, setWeatherData] = useState<MakeWeatherInfo[]>([])
  const [showWarningModal, setShowWarningModal] = useState(false)
  const [selectedTripsForWarning, setSelectedTripsForWarning] = useState<string[]>([])
  const [warningMessageContent, setWarningMessageContent] = useState('')
  const [editableWarnings, setEditableWarnings] = useState<MakeWeatherInfo[]>([])
  const [statusColorMap, setStatusColorMap] = useState<Partial<Record<MakeTripStatus, string>>>({})
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const itemsPerPage = 10

  const warningCities = useMemo(() => weatherData.filter((weather) => weather.warning !== null), [weatherData])

  useEffect(() => {
    if (tripId) return

    let active = true

    const loadApiData = async () => {
      setIsLoading(true)
      setLoadError(null)
      try {
        const [apiTrips, apiWeather, apiStatusColorMap] = await Promise.all([
          FigmaTripService.getAllTrips(),
          FigmaWeatherService.getAllWeather(),
          FigmaTripService.getStatusColorMap(),
        ])
        if (!active) return
        setTrips(apiTrips)
        setWeatherData(apiWeather)
        setStatusColorMap(apiStatusColorMap)
      } catch (error) {
        if (!active) return
        setLoadError(error instanceof Error ? error.message : 'API 数据加载失败')
      } finally {
        if (active) setIsLoading(false)
      }
    }

    void loadApiData()

    return () => {
      active = false
    }
  }, [tripId])

  if (tripId) {
    return (
      <TripDetail
        tripId={tripId}
        onBack={() => onBackToList?.()}
      />
    )
  }

  const refreshTrips = async () => {
    const nextTrips = await FigmaTripService.getAllTrips()
    setTrips(nextTrips)
    return nextTrips
  }

  const handleSelectAll = (checked: boolean) => {
    setSelectedTrips(checked ? trips.map((trip) => trip.id) : [])
  }

  const handleSelectTrip = (selectedTripId: string, checked: boolean) => {
    setSelectedTrips((current) => (
      checked ? [...current, selectedTripId] : current.filter((id) => id !== selectedTripId)
    ))
  }

  const handleEditTrip = (trip: MakeTrip) => {
    setEditingTripId(trip.id)
    setEditedTrip(editableTripCopy(trip))
  }

  const handleSaveTrip = async () => {
    if (!editedTrip) return
    const status = editedTrip.status as MakeTripStatus
    try {
      await FigmaTripService.updateTrip({
        ...editedTrip,
        participants: Number(editedTrip.participants) || 0,
        status,
        statusColor: statusColorMap[status] ?? editedTrip.statusColor,
      })
      await refreshTrips()
      setToast(`保存成功：${editedTrip.name}`)
      setEditingTripId(null)
      setEditedTrip(null)
    } catch (error) {
      setToast(error instanceof Error ? error.message : '保存失败')
    }
  }

  const handleCancelEdit = () => {
    setEditingTripId(null)
    setEditedTrip(null)
  }

  const handleDeleteTrip = async (trip: MakeTrip) => {
    if (!window.confirm(`确定要删除旅行团"${trip.name}"吗？`)) return
    try {
      await FigmaTripService.deleteTrip(trip.id)
      await refreshTrips()
      setSelectedTrips((current) => current.filter((id) => id !== trip.id))
      setToast(`已删除：${trip.name}`)
    } catch (error) {
      setToast(error instanceof Error ? error.message : '删除失败')
    }
  }

  const handleCreateTrip = () => {
    setToast('创建新团为演示按钮：新版 Make 中仅展示入口，未配置弹窗。')
  }

  const buildWarningMessage = (warnings: MakeWeatherInfo[]) => {
    const warningDetails = warnings
      .map((city) => `${city.city}：${city.warning || '天气预警'}，温度 ${city.temp}°C，${city.weather}，${city.wind}`)
      .join('\n')

    return `【天气预警通知】尊敬的游客，您好！\n\n系统检测到以下城市发布极端天气预警：\n\n${warningDetails}\n\n请注意安全，做好防护措施。如有疑问请联系导游。祝您旅途平安！`
  }

  const resetWarningModal = () => {
    setShowWarningModal(false)
    setSelectedTripsForWarning([])
    setWarningMessageContent('')
    setEditableWarnings([])
  }

  const handleShowWarningModal = () => {
    const warnings = warningCities.map((warning) => ({ ...warning }))
    setEditableWarnings(warnings)
    setWarningMessageContent(buildWarningMessage(warnings))
    setSelectedTripsForWarning([])
    setShowWarningModal(true)
  }

  const handleToggleTripForWarning = (tripId: string) => {
    setSelectedTripsForWarning((current) => (
      current.includes(tripId) ? current.filter((id) => id !== tripId) : [...current, tripId]
    ))
  }

  const handleSelectAllTripsForWarning = (checked: boolean) => {
    setSelectedTripsForWarning(checked ? trips.map((trip) => trip.id) : [])
  }

  const handleEditableWarningChange = <Key extends keyof MakeWeatherInfo>(
    index: number,
    key: Key,
    value: MakeWeatherInfo[Key],
  ) => {
    setEditableWarnings((current) => {
      const next = current.map((warning, warningIndex) => (
        warningIndex === index ? { ...warning, [key]: value } : warning
      ))
      setWarningMessageContent(buildWarningMessage(next))
      return next
    })
  }

  const handleSendWarningNotification = () => {
    if (selectedTripsForWarning.length === 0) {
      window.alert('请至少选择一个旅行团！')
      return
    }

    if (!warningMessageContent.trim()) {
      window.alert('短信内容不能为空！')
      return
    }

    const selectedTripNames = trips
      .filter((trip) => selectedTripsForWarning.includes(trip.id))
      .map((trip) => trip.name)
      .join('、')

    setToast(`天气预警短信已模拟发送给 ${selectedTripsForWarning.length} 个旅行团：${selectedTripNames}`)
    resetWarningModal()
  }


  if (isLoading) {
    return (
      <div className="p-6">
        <div className="rounded-lg border border-gray-200 bg-white p-6 text-center text-gray-600">正在通过 API 加载行程数据...</div>
      </div>
    )
  }

  if (loadError) {
    return (
      <div className="p-6">
        <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-red-700">{loadError}</div>
      </div>
    )
  }

  const totalPages = Math.max(1, Math.ceil(trips.length / itemsPerPage))
  const startIndex = (currentPage - 1) * itemsPerPage
  const currentTrips = trips.slice(startIndex, startIndex + itemsPerPage)

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">行程管理</h1>
        <p className="text-gray-600">管理所有旅行团，查看详情和数据分析，配置通知提醒</p>
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 flex-1">
            <span className="text-xl">🌤️</span>
            <div className="flex-1">
              <h2 className="text-sm font-bold text-gray-900 mb-1">新疆旅游城市天气实时监控</h2>
              <div className="flex items-center gap-4 text-xs text-gray-600 flex-wrap">
                {weatherData.map((item) => (
                  <div key={item.city} className="flex items-center gap-1">
                    <span className={item.warning ? 'text-red-600 font-medium' : ''}>{item.city}</span>
                    <span className={item.warning ? 'text-red-600 font-bold' : 'text-gray-900'}>{item.temp}°C</span>
                    {item.warning ? (
                      <span className="ml-1 px-1.5 py-0.5 bg-red-500 text-white rounded text-xs">⚠️{item.warning}</span>
                    ) : null}
                  </div>
                ))}
              </div>
            </div>
          </div>
          {warningCities.length > 0 ? (
            <button
              onClick={handleShowWarningModal}
              className="ml-4 px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 text-sm whitespace-nowrap"
            >
              天气预警提示
            </button>
          ) : null}
        </div>
      </div>

      {toast ? <div className="mb-4 rounded-lg bg-cyan-50 px-4 py-3 text-sm text-cyan-700">{toast}</div> : null}

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
          <h2 className="font-semibold text-gray-900">所有旅行团</h2>
          <button onClick={handleCreateTrip} className="px-4 py-2 bg-cyan-500 text-white rounded-lg hover:bg-cyan-600 text-sm">
            + 创建新团
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[1120px]">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <th className="pl-4 pr-2 py-3 text-left w-[50px]">
                  <input
                    type="checkbox"
                    checked={selectedTrips.length === trips.length && trips.length > 0}
                    onChange={(event) => handleSelectAll(event.target.checked)}
                    className="w-4 h-4 text-cyan-600 rounded focus:ring-cyan-500"
                  />
                </th>
                <th className="px-3 py-3 text-left text-xs font-medium text-gray-600 uppercase tracking-wider">团名</th>
                <th className="px-3 py-3 text-left text-xs font-medium text-gray-600 uppercase tracking-wider">团号</th>
                <th className="px-3 py-3 text-left text-xs font-medium text-gray-600 uppercase tracking-wider">开始日期</th>
                <th className="px-3 py-3 text-left text-xs font-medium text-gray-600 uppercase tracking-wider">结束日期</th>
                <th className="px-3 py-3 text-left text-xs font-medium text-gray-600 uppercase tracking-wider">人数</th>
                <th className="px-3 py-3 text-left text-xs font-medium text-gray-600 uppercase tracking-wider">领队</th>
                <th className="px-3 py-3 text-left text-xs font-medium text-gray-600 uppercase tracking-wider">状态</th>
                <th className="px-3 py-3 text-left text-xs font-medium text-gray-600 uppercase tracking-wider">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {currentTrips.map((trip) => {
                const isEditing = editingTripId === trip.id
                const displayTrip = isEditing && editedTrip ? editedTrip : trip

                return (
                  <tr key={trip.id} className={isEditing ? 'bg-blue-50' : 'hover:bg-gray-50'}>
                    <td className="pl-4 pr-2 py-3">
                      <input
                        type="checkbox"
                        checked={selectedTrips.includes(trip.id)}
                        onChange={(event) => handleSelectTrip(trip.id, event.target.checked)}
                        className="w-4 h-4 text-cyan-600 rounded focus:ring-cyan-500"
                      />
                    </td>
                    <td className="px-3 py-3">
                      {isEditing ? (
                        <input value={displayTrip.name} onChange={(event) => setEditedTrip({ ...editedTrip!, name: event.target.value })} className="w-full px-2 py-1 border border-gray-300 rounded text-xs focus:outline-none focus:ring-2 focus:ring-cyan-500" />
                      ) : (
                        <span className="font-medium text-gray-900">{displayTrip.name}</span>
                      )}
                    </td>
                    <td className="px-3 py-3">
                      {isEditing ? (
                        <input value={displayTrip.code} onChange={(event) => setEditedTrip({ ...editedTrip!, code: event.target.value, teamId: event.target.value })} className="w-full px-2 py-1 border border-gray-300 rounded text-xs focus:outline-none focus:ring-2 focus:ring-cyan-500" />
                      ) : (
                        <span className="text-sm text-gray-600">{displayTrip.code}</span>
                      )}
                    </td>
                    <td className="px-3 py-3">
                      {isEditing ? (
                        <input type="date" value={displayTrip.startDate} onChange={(event) => setEditedTrip({ ...editedTrip!, startDate: event.target.value })} className="w-full px-2 py-1 border border-gray-300 rounded text-xs focus:outline-none focus:ring-2 focus:ring-cyan-500" />
                      ) : <span className="text-sm text-gray-600">{displayTrip.startDate}</span>}
                    </td>
                    <td className="px-3 py-3">
                      {isEditing ? (
                        <input type="date" value={displayTrip.endDate} onChange={(event) => setEditedTrip({ ...editedTrip!, endDate: event.target.value })} className="w-full px-2 py-1 border border-gray-300 rounded text-xs focus:outline-none focus:ring-2 focus:ring-cyan-500" />
                      ) : <span className="text-sm text-gray-600">{displayTrip.endDate}</span>}
                    </td>
                    <td className="px-3 py-3">
                      {isEditing ? (
                        <input type="number" value={displayTrip.participants} onChange={(event) => setEditedTrip({ ...editedTrip!, participants: Number(event.target.value) })} className="w-20 px-2 py-1 border border-gray-300 rounded text-xs focus:outline-none focus:ring-2 focus:ring-cyan-500" />
                      ) : <span className="text-sm text-gray-600">{displayTrip.participants} 人</span>}
                    </td>
                    <td className="px-3 py-3">
                      {isEditing ? (
                        <input value={displayTrip.leader} onChange={(event) => setEditedTrip({ ...editedTrip!, leader: event.target.value })} className="w-full px-2 py-1 border border-gray-300 rounded text-xs focus:outline-none focus:ring-2 focus:ring-cyan-500" />
                      ) : <span className="text-sm text-gray-600">{displayTrip.leader}</span>}
                    </td>
                    <td className="px-3 py-3">
                      {isEditing ? (
                        <select
                          value={displayTrip.status}
                          onChange={(event) => {
                            const status = event.target.value as MakeTripStatus
                            setEditedTrip({ ...editedTrip!, status, statusColor: statusColorMap[status] ?? displayTrip.statusColor })
                          }}
                          className="w-full px-2 py-1 border border-gray-300 rounded text-xs focus:outline-none focus:ring-2 focus:ring-cyan-500"
                        >
                          <option value="进行中">进行中</option>
                          <option value="即将出发">即将出发</option>
                          <option value="招募中">招募中</option>
                          <option value="已满员">已满员</option>
                        </select>
                      ) : (
                        <span className={`px-2 py-1 rounded-full text-xs ${displayTrip.statusColor}`}>{displayTrip.status}</span>
                      )}
                    </td>
                    <td className="px-3 py-3">
                      {isEditing ? (
                        <div className="flex gap-2">
                          <button onClick={handleSaveTrip} className="px-3 py-1 text-xs bg-green-500 text-white rounded hover:bg-green-600">保存</button>
                          <button onClick={handleCancelEdit} className="px-3 py-1 text-xs bg-gray-300 text-gray-700 rounded hover:bg-gray-400">取消</button>
                        </div>
                      ) : (
                        <div className="flex gap-2 flex-wrap">
                          <button onClick={() => onOpenTrip?.(trip.teamId)} className="px-3 py-1 text-xs text-cyan-600 hover:bg-cyan-50 rounded">查看详情</button>
                          <button onClick={() => handleEditTrip(trip)} className="px-3 py-1 text-xs text-blue-600 hover:bg-blue-50 rounded">编辑</button>
                          <button onClick={() => handleDeleteTrip(trip)} className="px-3 py-1 text-xs text-red-600 hover:bg-red-50 rounded">删除</button>
                        </div>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex items-center justify-between">
          <div className="text-sm text-gray-600">共 {trips.length} 条记录，当前第 {currentPage} / {totalPages} 页</div>
          <div className="flex gap-2">
            <button onClick={() => setCurrentPage(1)} disabled={currentPage === 1} className="px-3 py-1 text-sm rounded bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed">第一页</button>
            <button onClick={() => setCurrentPage(currentPage - 1)} disabled={currentPage === 1} className="px-3 py-1 text-sm rounded bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed">上一页</button>
            {Array.from({ length: totalPages }, (_, index) => index + 1).map((page) => (
              <button key={page} onClick={() => setCurrentPage(page)} className={`px-3 py-1 text-sm rounded ${currentPage === page ? 'bg-cyan-500 text-white' : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'}`}>{page}</button>
            ))}
            <button onClick={() => setCurrentPage(currentPage + 1)} disabled={currentPage === totalPages} className="px-3 py-1 text-sm rounded bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed">下一页</button>
            <button onClick={() => setCurrentPage(totalPages)} disabled={currentPage === totalPages} className="px-3 py-1 text-sm rounded bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed">最后一页</button>
          </div>
        </div>
      </div>

      {showWarningModal ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-6">
          <div className="flex max-h-[92vh] w-full max-w-5xl flex-col overflow-hidden rounded-lg bg-white shadow-2xl">
            <div className="border-b border-red-200 bg-red-50 px-8 py-5">
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-4">
                  <span className="text-4xl leading-none">⚠️</span>
                  <div>
                    <h2 className="text-2xl font-bold text-gray-900">发送天气预警短信</h2>
                    <p className="mt-2 text-red-600">
                      检测到 {editableWarnings.length} 个城市发布天气预警：{editableWarnings.map((warning) => warning.city).join('、')}
                    </p>
                  </div>
                </div>
                <button onClick={resetWarningModal} className="text-3xl leading-none text-gray-500 hover:text-gray-700">×</button>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto px-8 py-6">
              <div className="mb-6">
                <h3 className="mb-4 text-xl font-bold text-gray-900">预警内容：</h3>
                <div className="rounded-lg border border-yellow-300 bg-yellow-50 p-4">
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[760px] text-sm">
                      <thead>
                        <tr className="text-left text-xs font-medium text-gray-600">
                          <th className="px-3 py-2">城市</th>
                          <th className="px-3 py-2">预警类型</th>
                          <th className="px-3 py-2">温度</th>
                          <th className="px-3 py-2">天气</th>
                          <th className="px-3 py-2">风力</th>
                        </tr>
                      </thead>
                      <tbody>
                        {editableWarnings.map((warning, index) => (
                          <tr key={`${warning.city}-${index}`} className="align-middle">
                            <td className="px-3 py-2">
                              <input
                                value={warning.city}
                                onChange={(event) => handleEditableWarningChange(index, 'city', event.target.value)}
                                className="w-full rounded border border-yellow-300 bg-white px-2 py-1 font-medium text-red-600 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                              />
                            </td>
                            <td className="px-3 py-2">
                              <input
                                value={warning.warning || ''}
                                onChange={(event) => handleEditableWarningChange(index, 'warning', event.target.value || null)}
                                className="w-full rounded border border-red-200 bg-red-50 px-2 py-1 font-medium text-red-600 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                                placeholder="预警类型"
                              />
                            </td>
                            <td className="px-3 py-2">
                              <div className="flex items-center gap-1">
                                <input
                                  type="number"
                                  value={warning.temp}
                                  onChange={(event) => handleEditableWarningChange(index, 'temp', Number(event.target.value) || 0)}
                                  className="w-20 rounded border border-gray-300 px-2 py-1 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                                />
                                <span className="text-gray-600">°C</span>
                              </div>
                            </td>
                            <td className="px-3 py-2">
                              <input
                                value={warning.weather}
                                onChange={(event) => handleEditableWarningChange(index, 'weather', event.target.value)}
                                className="w-full rounded border border-gray-300 px-2 py-1 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                              />
                            </td>
                            <td className="px-3 py-2">
                              <input
                                value={warning.wind}
                                onChange={(event) => handleEditableWarningChange(index, 'wind', event.target.value)}
                                className="w-full rounded border border-gray-300 px-2 py-1 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                              />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <p className="mt-3 text-xs text-gray-500">💡 提示：可以直接修改预警信息，修改后会自动更新短信内容。</p>
                </div>
              </div>

              <div className="mb-6">
                <div className="mb-3 flex items-center justify-between">
                  <h3 className="text-lg font-bold text-gray-900">短信内容：</h3>
                  <span className="text-xs text-gray-500">{warningMessageContent.length} 字符</span>
                </div>
                <textarea
                  value={warningMessageContent}
                  onChange={(event) => setWarningMessageContent(event.target.value)}
                  className="h-40 w-full resize-none rounded-lg border border-gray-300 px-4 py-3 text-sm leading-6 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                  placeholder="请输入短信内容..."
                />
              </div>

              <div>
                <div className="mb-3 flex items-center justify-between">
                  <h3 className="text-xl font-bold text-gray-900">选择接收旅行团：</h3>
                  <label className="flex cursor-pointer items-center gap-2 text-sm text-gray-600">
                    <input
                      type="checkbox"
                      checked={selectedTripsForWarning.length === trips.length && trips.length > 0}
                      onChange={(event) => handleSelectAllTripsForWarning(event.target.checked)}
                      className="h-4 w-4 rounded text-cyan-600 focus:ring-cyan-500"
                    />
                    全选
                  </label>
                </div>

                <div className="overflow-hidden rounded-lg border border-gray-200">
                  <table className="w-full min-w-[760px] text-sm">
                    <thead>
                      <tr className="border-b border-gray-200 bg-gray-50 text-left text-xs font-medium text-gray-600">
                        <th className="w-16 px-4 py-3">选择</th>
                        <th className="px-4 py-3">团名</th>
                        <th className="px-4 py-3">出发日期</th>
                        <th className="px-4 py-3">人数</th>
                        <th className="px-4 py-3">状态</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {trips.map((trip) => {
                        const checked = selectedTripsForWarning.includes(trip.id)
                        return (
                          <tr
                            key={trip.id}
                            onClick={() => handleToggleTripForWarning(trip.id)}
                            className={`cursor-pointer hover:bg-gray-50 ${checked ? 'bg-blue-50' : ''}`}
                          >
                            <td className="px-4 py-3">
                              <input
                                type="checkbox"
                                checked={checked}
                                onClick={(event) => event.stopPropagation()}
                                onChange={() => handleToggleTripForWarning(trip.id)}
                                className="h-4 w-4 rounded text-cyan-600 focus:ring-cyan-500"
                              />
                            </td>
                            <td className="px-4 py-3 font-medium text-gray-900">{trip.name}</td>
                            <td className="px-4 py-3 text-gray-600">{trip.startDate} 至 {trip.endDate}</td>
                            <td className="px-4 py-3 text-gray-600">{trip.participants} 人</td>
                            <td className="px-4 py-3">
                              <span className={`rounded-full px-2 py-1 text-xs ${trip.statusColor}`}>{trip.status}</span>
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
                <div className="mt-3 text-sm text-gray-600">
                  已选择 <span className="font-bold text-gray-900">{selectedTripsForWarning.length}</span> 个旅行团
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between border-t border-gray-200 bg-gray-50 px-8 py-5">
              <div className="text-sm text-gray-600">
                预计费用：<span className="ml-2 font-bold text-orange-600">¥{(selectedTripsForWarning.length * 0.05).toFixed(2)}</span>
              </div>
              <div className="flex gap-3">
                <button onClick={resetWarningModal} className="rounded-lg border border-gray-300 bg-white px-5 py-2 text-gray-700 hover:bg-gray-50">取消</button>
                <button
                  onClick={handleSendWarningNotification}
                  disabled={selectedTripsForWarning.length === 0 || !warningMessageContent.trim()}
                  className="rounded-lg bg-red-500 px-5 py-2 text-white hover:bg-red-600 disabled:cursor-not-allowed disabled:bg-gray-400"
                >
                  确认发送 ({selectedTripsForWarning.length})
                </button>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}
