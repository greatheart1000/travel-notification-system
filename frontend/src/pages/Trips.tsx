import { useEffect, useMemo, useState } from 'react'
import { AlertTriangle, CloudSun, Info, Plus } from 'lucide-react'
import { FigmaTripService, FigmaWeatherService } from '../services/figmaTripService'
import type { MakeTrip, MakeTripStatus, MakeWeatherInfo } from '../data/figmaMockData'
import { makeStatusColorMap } from '../data/figmaMockData'
import { PageShell } from '../components/PageShell'
import { Button } from '../components/Button'
import { useSession } from '../context/SessionContext'
import { tripReminderApi } from '../services/api'
import { TripDetail } from './TripDetail'

function computeDisplayStatus(startDate: string, endDate: string): MakeTripStatus {
  if (!startDate || !endDate) return '招募中'
  const today = new Date().toISOString().slice(0, 10)
  if (today < startDate) return '招募中'
  if (today <= endDate) return '进行中'
  return '已结束'
}

// Module-level cache — persists across navigations within the same session
let cachedTrips: MakeTrip[] | null = null
let cachedWeather: MakeWeatherInfo[] | null = null

interface TripsProps {
  tripId?: string | null
  initialTab?: string
  onOpenTrip?: (tripId: string) => void
  onBackToList?: () => void
}

function editableTripCopy(trip: MakeTrip): MakeTrip {
  return { ...trip }
}

function assigneeLabel(trip: MakeTrip): string {
  const names = (trip.assignedUsers ?? [])
    .map((user) => user.displayName || user.username)
    .filter(Boolean)
  return names.join('、') || trip.leader || ''
}

interface WeatherWarningGroup {
  key: string
  title: string
  short: string
  cities: MakeWeatherInfo[]
}

function groupWeatherWarnings(warnings: MakeWeatherInfo[]): WeatherWarningGroup[] {
  const groups = new Map<string, WeatherWarningGroup>()
  for (const warning of warnings) {
    const title = (warning.warning_title || warning.warning || '天气预警').trim()
    const short = warning.warning || title
    const existing = groups.get(title)
    if (existing) {
      existing.cities.push(warning)
      continue
    }
    groups.set(title, { key: title, title, short, cities: [warning] })
  }
  return Array.from(groups.values())
}

export function Trips({
  tripId = null,
  initialTab,
  onOpenTrip,
  onBackToList,
}: TripsProps) {
  const { user } = useSession()
  const isAdmin = user?.role === 'admin'
  const [trips, setTrips] = useState<MakeTrip[]>([])
  const [selectedTrips, setSelectedTrips] = useState<string[]>([])
  const [currentPage, setCurrentPage] = useState(1)
  const [editingTripId, setEditingTripId] = useState<string | null>(null)
  const [editedTrip, setEditedTrip] = useState<MakeTrip | null>(null)
  const [toast, setToast] = useState<string | null>(null)
  const [weatherData, setWeatherData] = useState<MakeWeatherInfo[]>([])
  const [weatherUnavailable, setWeatherUnavailable] = useState(false)
  const [showWarningModal, setShowWarningModal] = useState(false)
  const [selectedTripsForWarning, setSelectedTripsForWarning] = useState<string[]>([])
  const [warningMessageContent, setWarningMessageContent] = useState('')
  const [editableWarnings, setEditableWarnings] = useState<MakeWeatherInfo[]>([])
  const [isLoading, setIsLoading] = useState(!cachedTrips)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [isCreating, setIsCreating] = useState(false)
  const [sendingWarning, setSendingWarning] = useState(false)
  const [newTrip, setNewTrip] = useState<MakeTrip>({
    id: '', teamId: '', name: '', code: '', startDate: '', endDate: '',
    participants: 0, leader: '', status: '招募中', statusColor: makeStatusColorMap['招募中'] ?? '', assignedUserIds: [],
  })
  const itemsPerPage = 10

  const warningCities = useMemo(() => weatherData.filter((weather) => weather.warning !== null), [weatherData])
  const warningGroups = useMemo(() => groupWeatherWarnings(warningCities), [warningCities])
  const editableWarningGroups = useMemo(() => groupWeatherWarnings(editableWarnings), [editableWarnings])

  useEffect(() => {
    if (tripId) return

    let active = true

    const loadApiData = async () => {
      // Show cached data immediately if available
      if (cachedTrips) {
        setTrips(cachedTrips)
        if (cachedWeather) setWeatherData(cachedWeather)
      }
      setIsLoading(!cachedTrips)
      setLoadError(null)
      try {
        const apiTrips = await FigmaTripService.getAllTrips()
        if (!active) return
        cachedTrips = apiTrips
        setTrips(apiTrips)
      } catch (error) {
        if (!active) return
        setLoadError(error instanceof Error ? error.message : 'API 数据加载失败')
      } finally {
        if (active) setIsLoading(false)
      }

      // 天气是增强信息：失败不阻塞行程列表。
      try {
        const apiWeather = await FigmaWeatherService.getAllWeather()
        if (!active) return
        cachedWeather = apiWeather
        setWeatherData(apiWeather)
        setWeatherUnavailable(false)
      } catch {
        if (!active) return
        setWeatherUnavailable(true)
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
        initialTab={initialTab}
        onBack={() => onBackToList?.()}
      />
    )
  }

  const refreshTrips = async () => {
    const nextTrips = await FigmaTripService.getAllTrips()
    cachedTrips = nextTrips
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
    try {
      await FigmaTripService.updateTrip({
        ...editedTrip,
        participants: Number(editedTrip.participants) || 0,
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
    setIsCreating(true)
  }

  const handleCancelCreate = () => {
    setIsCreating(false)
    setNewTrip({
      id: '', teamId: '', name: '', code: '', startDate: '', endDate: '',
      participants: 0, leader: '', status: '招募中', statusColor: makeStatusColorMap['招募中'] ?? '', assignedUserIds: [],
    })
  }

  const handleSaveNewTrip = async () => {
    if (!newTrip.name.trim() || !newTrip.code.trim() || !newTrip.startDate || !newTrip.endDate) {
      setToast('请填写团名、团号、开始日期和结束日期')
      return
    }
    try {
      await FigmaTripService.createTrip({
        name: newTrip.name,
        teamId: newTrip.code,
        startDate: newTrip.startDate,
        endDate: newTrip.endDate,
        participants: newTrip.participants,
        leader: newTrip.leader,
      })
      await refreshTrips()
      setToast(`创建成功：${newTrip.name}`)
      handleCancelCreate()
    } catch (error) {
      setToast(error instanceof Error ? error.message : '创建失败')
    }
  }

  const buildWarningMessage = (warnings: MakeWeatherInfo[]) => {
    const warningDetails = groupWeatherWarnings(warnings)
      .map((group) => {
        const cityLines = group.cities
          .map((city) => `· ${city.city}：${city.temp}°C，${city.weather}，${city.wind}`)
          .join('\n')
        return `【${group.title}】\n影响城市：\n${cityLines}`
      })
      .join('\n\n')

    return `【天气预警通知】检测到以下天气预警：\n\n${warningDetails}\n\n请注意安全，做好防护。如有疑问请联系领队。`
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

  const handleSendWarningNotification = async () => {
    if (selectedTripsForWarning.length === 0) {
      setToast('请至少选择一个旅行团')
      return
    }

    if (!warningMessageContent.trim()) {
      setToast('提醒内容不能为空')
      return
    }

    const selectedTrips = trips.filter((trip) => selectedTripsForWarning.includes(trip.id))
    setSendingWarning(true)
    const results = await Promise.allSettled(
      selectedTrips.map((trip) =>
        tripReminderApi.sendGroupReminder(trip.id, {
          message: warningMessageContent,
          useAi: false,
          scene: '天气预警',
        }),
      ),
    )
    setSendingWarning(false)
    const failed = results
      .map((result, index) => ({ result, trip: selectedTrips[index] }))
      .filter(({ result }) => result.status === 'rejected')
    const sentCount = results.length - failed.length
    if (failed.length === 0) {
      setToast(`天气预警已发送到 ${sentCount} 个旅行团的企业微信群`)
      resetWarningModal()
      return
    }
    const firstError = failed[0].result.status === 'rejected'
      ? failed[0].result.reason
      : null
    const reason = firstError instanceof Error ? firstError.message : '群未配置或发送失败'
    if (sentCount > 0) {
      setToast(`已发送 ${sentCount} 个，${failed.length} 个失败：${failed.map(({ trip }) => trip.name).join('、')}。${reason}`)
    } else {
      setToast(`发送失败：${reason}`)
    }
  }


  const totalPages = Math.max(1, Math.ceil(trips.length / itemsPerPage))
  const startIndex = (currentPage - 1) * itemsPerPage
  const currentTrips = trips.slice(startIndex, startIndex + itemsPerPage)

  return (
    <PageShell title="行程管理" description="管理所有旅行团，查看行程详情和通知配置">
      {loadError ? (
        <div className="rounded-card border border-danger-200 bg-danger-50 p-5 text-sm text-danger-700">{loadError}</div>
      ) : isLoading && trips.length === 0 ? (
        <div className="surface-soft p-12 text-center">
          <div className="inline-block h-6 w-6 animate-spin rounded-full border-2 border-paper-200 border-t-accent-600" />
          <p className="mt-3 text-sm text-paper-500">加载中</p>
        </div>
      ) : (
        <>

      <div className="mb-6 rounded-panel border border-accent-100 bg-accent-50/55 p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex w-full flex-1 items-start gap-3 sm:items-center">
            <CloudSun className="mt-0.5 h-4 w-4 shrink-0 text-paper-500 sm:mt-0" />
            <div className="flex-1">
              <h2 className="mb-1 text-sm font-semibold text-paper-900">新疆旅游城市天气实时监控</h2>
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-paper-600">
                {weatherData.map((item) => (
                  <div key={item.city} className="flex items-center gap-1">
                    <span className={item.warning ? 'font-medium text-danger-700' : ''}>{item.city}</span>
                    <span className={item.warning ? 'font-semibold tabular-nums text-danger-700' : 'tabular-nums text-paper-900'}>{item.temp}°C</span>
                    {item.warning ? (
                      <span
                        className="ml-1 inline-flex items-center gap-1 rounded-control bg-danger-50 px-1.5 py-0.5 text-xs text-danger-700"
                        title={item.warning_title || item.warning}
                      >
                        <AlertTriangle className="h-3 w-3" />
                      </span>
                    ) : null}
                  </div>
                ))}
              </div>
              {warningGroups.length > 0 ? (
                <div className="mt-2 space-y-1 border-t border-paper-100 pt-2">
                  {warningGroups.map((group) => (
                    <div key={group.key} className="flex flex-wrap items-start gap-x-2 gap-y-1 text-xs text-danger-700">
                      <span className="inline-flex items-center gap-1 font-medium">
                        <AlertTriangle className="h-3.5 w-3.5" />
                        {group.title}
                      </span>
                      <span className="text-paper-600">
                        影响 {group.cities.length} 个城市：{group.cities.map((city) => city.city).join('、')}
                      </span>
                    </div>
                  ))}
                </div>
              ) : null}
              {weatherUnavailable ? (
                <p className="mt-1 flex items-center gap-1 text-xs text-paper-500">
                  <Info className="h-3.5 w-3.5" />
                  天气服务暂不可用，行程数据不受影响
                </p>
              ) : weatherData.length === 0 ? (
                <p className="mt-1 text-xs text-paper-500">暂无天气数据</p>
              ) : weatherData.some((item) => item.source === 'mock') ? (
                <p className="mt-1 flex items-center gap-1 text-xs text-paper-500">
                  <Info className="h-3.5 w-3.5" />
                  天气服务未配置，当前展示模拟数据
                </p>
              ) : null}
            </div>
          </div>
          {warningCities.length > 0 ? (
            <Button size="sm" variant="danger-outline" onClick={handleShowWarningModal} className="self-start sm:self-auto">
              天气预警提示（{warningGroups.length} 条）
            </Button>
          ) : null}
        </div>
      </div>

      {toast ? (
        <div className="mb-4 rounded-control border border-accent-200 bg-accent-50 px-4 py-3 text-sm text-accent-800">
          {toast}
        </div>
      ) : null}

      <div className="overflow-hidden rounded-card border border-paper-200 bg-white">
        <div className="flex items-center justify-between border-b border-paper-200 px-5 py-4">
          <h2 className="text-base font-semibold text-paper-900">所有旅行团</h2>
          {isAdmin ? (
            <Button size="sm" onClick={handleCreateTrip}>
              <Plus className="h-4 w-4" /> 创建新团
            </Button>
          ) : null}
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[820px]">
            <thead>
              <tr className="border-b border-paper-200 bg-paper-50">
                <th className="pl-4 pr-2 py-3 text-left w-12">
                  <input
                    type="checkbox"
                    checked={selectedTrips.length === trips.length && trips.length > 0}
                    onChange={(event) => handleSelectAll(event.target.checked)}
                    className="h-4 w-4 rounded accent-accent-600"
                  />
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-paper-500">团名</th>
                <th className="hidden px-4 py-3 text-left text-xs font-medium text-paper-500 2xl:table-cell">团号</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-paper-500">开始日期</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-paper-500">结束日期</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-paper-500">人数</th>
                <th className="hidden px-4 py-3 text-left text-xs font-medium text-paper-500 xl:table-cell">负责导游</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-paper-500">状态</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-paper-500">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-paper-100">
              {isCreating && (
                <tr className="bg-success-50">
                  <td className="pl-4 pr-2 py-3"></td>
                  <td className="px-4 py-3">
                    <input value={newTrip.name} onChange={(e) => setNewTrip({ ...newTrip, name: e.target.value })} placeholder="团名" className="w-full rounded-control border border-paper-300 px-2 py-1 text-xs focus:border-accent-600 focus:outline-none focus:ring-2 focus:ring-accent-100" />
                  </td>
                  <td className="px-4 py-3">
                    <input value={newTrip.code} onChange={(e) => setNewTrip({ ...newTrip, code: e.target.value })} placeholder="团号" className="w-full rounded-control border border-paper-300 px-2 py-1 text-xs focus:border-accent-600 focus:outline-none focus:ring-2 focus:ring-accent-100" />
                  </td>
                  <td className="px-4 py-3">
                    <input type="date" value={newTrip.startDate} onChange={(e) => setNewTrip({ ...newTrip, startDate: e.target.value })} className="w-full rounded-control border border-paper-300 px-2 py-1 text-xs focus:border-accent-600 focus:outline-none focus:ring-2 focus:ring-accent-100" />
                  </td>
                  <td className="px-4 py-3">
                    <input type="date" value={newTrip.endDate} onChange={(e) => setNewTrip({ ...newTrip, endDate: e.target.value })} className="w-full rounded-control border border-paper-300 px-2 py-1 text-xs focus:border-accent-600 focus:outline-none focus:ring-2 focus:ring-accent-100" />
                  </td>
                  <td className="px-4 py-3">
                    <input type="number" value={newTrip.participants} onChange={(e) => setNewTrip({ ...newTrip, participants: Number(e.target.value) })} className="w-20 rounded-control border border-paper-300 px-2 py-1 text-xs focus:border-accent-600 focus:outline-none focus:ring-2 focus:ring-accent-100" />
                  </td>
                  <td className="px-4 py-3">
                    <input value={newTrip.leader} onChange={(e) => setNewTrip({ ...newTrip, leader: e.target.value })} placeholder="负责人/导游" className="w-full rounded-control border border-paper-300 px-2 py-1 text-xs focus:border-accent-600 focus:outline-none focus:ring-2 focus:ring-accent-100" />
                  </td>
                  <td className="px-4 py-3 text-xs text-paper-400">
                    {newTrip.startDate && newTrip.endDate ? (
                      <span className={`rounded-control px-2 py-0.5 text-xs ${makeStatusColorMap[computeDisplayStatus(newTrip.startDate, newTrip.endDate)]}`}>
                        {computeDisplayStatus(newTrip.startDate, newTrip.endDate)}
                      </span>
                    ) : '—'}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      <button onClick={handleSaveNewTrip} className="rounded-control bg-success-600 px-2 py-1 text-xs text-white hover:bg-success-700">保存</button>
                      <button onClick={handleCancelCreate} className="rounded-control border border-paper-300 bg-white px-2 py-1 text-xs text-paper-700 hover:bg-paper-50">取消</button>
                    </div>
                  </td>
                </tr>
              )}
              {currentTrips.map((trip) => {
                const isEditing = editingTripId === trip.id
                const displayTrip = isEditing && editedTrip ? editedTrip : trip

                return (
                  <tr
                    key={trip.id}
                    onClick={() => {
                      if (!isEditing) onOpenTrip?.(trip.id)
                    }}
                    className={isEditing ? 'bg-accent-50' : 'cursor-pointer hover:bg-paper-50'}
                  >
                    <td className="pl-4 pr-2 py-3">
                      <input
                        type="checkbox"
                        checked={selectedTrips.includes(trip.id)}
                        onClick={(event) => event.stopPropagation()}
                        onChange={(event) => handleSelectTrip(trip.id, event.target.checked)}
                        className="h-4 w-4 rounded accent-accent-600"
                      />
                    </td>
                    <td className="px-4 py-3">
                      {isEditing ? (
                        <input value={displayTrip.name} onChange={(event) => setEditedTrip({ ...editedTrip!, name: event.target.value })} className="w-full rounded-control border border-paper-300 px-2 py-1 text-xs focus:border-accent-600 focus:outline-none focus:ring-2 focus:ring-accent-100" />
                      ) : (
                        <span className="font-medium text-paper-900">{displayTrip.name}</span>
                      )}
                    </td>
                    <td className={`${isEditing ? 'table-cell' : 'hidden 2xl:table-cell'} px-4 py-3`}>
                      {isEditing ? (
                        <input value={displayTrip.code} onChange={(event) => setEditedTrip({ ...editedTrip!, code: event.target.value, teamId: event.target.value })} className="w-full rounded-control border border-paper-300 px-2 py-1 text-xs focus:border-accent-600 focus:outline-none focus:ring-2 focus:ring-accent-100" />
                      ) : (
                        <span className="text-sm text-paper-600">{displayTrip.code}</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {isEditing ? (
                        <input type="date" value={displayTrip.startDate} onChange={(event) => setEditedTrip({ ...editedTrip!, startDate: event.target.value })} className="w-full rounded-control border border-paper-300 px-2 py-1 text-xs focus:border-accent-600 focus:outline-none focus:ring-2 focus:ring-accent-100" />
                      ) : <span className="text-sm text-paper-600">{displayTrip.startDate}</span>}
                    </td>
                    <td className="px-4 py-3">
                      {isEditing ? (
                        <input type="date" value={displayTrip.endDate} onChange={(event) => setEditedTrip({ ...editedTrip!, endDate: event.target.value })} className="w-full rounded-control border border-paper-300 px-2 py-1 text-xs focus:border-accent-600 focus:outline-none focus:ring-2 focus:ring-accent-100" />
                      ) : <span className="text-sm text-paper-600">{displayTrip.endDate}</span>}
                    </td>
                    <td className="px-4 py-3">
                      {isEditing ? (
                        <input type="number" value={displayTrip.participants} onChange={(event) => setEditedTrip({ ...editedTrip!, participants: Number(event.target.value) })} className="w-20 rounded-control border border-paper-300 px-2 py-1 text-xs focus:border-accent-600 focus:outline-none focus:ring-2 focus:ring-accent-100" />
                      ) : <span className="text-sm text-paper-600">{displayTrip.participants} 人</span>}
                    </td>
                    <td className={`${isEditing ? 'table-cell' : 'hidden xl:table-cell'} px-4 py-3`}>
                      {isEditing ? (
                        <input value={displayTrip.leader} onChange={(event) => setEditedTrip({ ...editedTrip!, leader: event.target.value })} className="w-full rounded-control border border-paper-300 px-2 py-1 text-xs focus:border-accent-600 focus:outline-none focus:ring-2 focus:ring-accent-100" />
                      ) : assigneeLabel(displayTrip) ? (
                        <span className="text-sm text-paper-600">{assigneeLabel(displayTrip)}</span>
                      ) : (
                        <span className="text-xs font-medium text-warning-700">未分配</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {(() => {
                        const s = computeDisplayStatus(displayTrip.startDate, displayTrip.endDate)
                        return <span className={`rounded-control px-2 py-0.5 text-xs ${makeStatusColorMap[s]}`}>{s}</span>
                      })()}
                    </td>
                    <td className="px-4 py-3">
                      {isEditing ? (
                        <div className="flex gap-2">
                          <button onClick={handleSaveTrip} className="rounded-control bg-success-600 px-2.5 py-1 text-xs text-white hover:bg-success-700">保存</button>
                          <button onClick={handleCancelEdit} className="rounded-control border border-paper-300 bg-white px-2.5 py-1 text-xs text-paper-700 hover:bg-paper-50">取消</button>
                        </div>
                      ) : (
                        <div className="flex gap-2 flex-wrap">
                          <button onClick={(event) => { event.stopPropagation(); onOpenTrip?.(trip.id) }} className="rounded-control px-2.5 py-1 text-xs text-accent-700 hover:bg-accent-50">查看详情</button>
                          {isAdmin ? (
                            <>
                              <button onClick={(event) => { event.stopPropagation(); handleEditTrip(trip) }} className="rounded-control px-2.5 py-1 text-xs text-accent-700 hover:bg-accent-50">编辑</button>
                              <button onClick={(event) => { event.stopPropagation(); handleDeleteTrip(trip) }} className="rounded-control px-2.5 py-1 text-xs text-danger-700 hover:bg-danger-50">删除</button>
                            </>
                          ) : null}
                        </div>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        <div className="flex flex-col gap-3 border-t border-paper-200 bg-paper-50 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <div className="text-sm text-paper-600">共 {trips.length} 条记录，当前第 {currentPage} / {totalPages} 页</div>
          <div className="flex max-w-full gap-2 overflow-x-auto pb-1 sm:pb-0">
            <button onClick={() => setCurrentPage(1)} disabled={currentPage === 1} className="rounded-control px-2.5 py-1 text-sm bg-white border border-paper-300 text-paper-700 hover:bg-paper-50 disabled:bg-paper-200 disabled:text-paper-400 disabled:cursor-not-allowed">第一页</button>
            <button onClick={() => setCurrentPage(currentPage - 1)} disabled={currentPage === 1} className="rounded-control px-2.5 py-1 text-sm bg-white border border-paper-300 text-paper-700 hover:bg-paper-50 disabled:bg-paper-200 disabled:text-paper-400 disabled:cursor-not-allowed">上一页</button>
            {Array.from({ length: totalPages }, (_, index) => index + 1).map((page) => (
              <button key={page} onClick={() => setCurrentPage(page)} className={`rounded-control px-2.5 py-1 text-sm ${currentPage === page ? 'bg-accent-600 text-white' : 'bg-white border border-paper-300 text-paper-700 hover:bg-paper-50'}`}>{page}</button>
            ))}
            <button onClick={() => setCurrentPage(currentPage + 1)} disabled={currentPage === totalPages} className="rounded-control px-2.5 py-1 text-sm bg-white border border-paper-300 text-paper-700 hover:bg-paper-50 disabled:bg-paper-200 disabled:text-paper-400 disabled:cursor-not-allowed">下一页</button>
            <button onClick={() => setCurrentPage(totalPages)} disabled={currentPage === totalPages} className="rounded-control px-2.5 py-1 text-sm bg-white border border-paper-300 text-paper-700 hover:bg-paper-50 disabled:bg-paper-200 disabled:text-paper-400 disabled:cursor-not-allowed">最后一页</button>
          </div>
        </div>
      </div>

      {showWarningModal ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-paper-950/40 p-6">
          <div className="flex max-h-[92vh] w-full max-w-5xl flex-col overflow-hidden rounded-panel border border-paper-200 bg-white shadow-raised">
            <div className="border-b border-paper-200 px-6 py-4">
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="mt-0.5 h-5 w-5 text-danger-600" />
                  <div>
                    <h2 className="text-lg font-semibold text-paper-900">发送天气预警到企业微信群</h2>
                    <p className="mt-1 text-sm text-danger-700">
                      检测到 {editableWarningGroups.length} 条天气预警，影响 {editableWarnings.length} 个城市：
                      {editableWarnings.map((warning) => warning.city).join('、')}
                    </p>
                  </div>
                </div>
                <button
                  onClick={resetWarningModal}
                  className="rounded-control p-1 text-xl leading-none text-paper-500 transition-colors hover:bg-paper-100 hover:text-paper-900"
                  aria-label="关闭"
                >
                  ×
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto px-6 py-5">
              <div className="mb-6">
                <h3 className="mb-3 text-base font-semibold text-paper-900">预警内容</h3>
                <div className="space-y-3 rounded-card border border-warning-200 bg-warning-50 p-4">
                  {editableWarningGroups.map((group) => (
                    <div key={group.key} className="overflow-hidden rounded-card border border-warning-200 bg-white">
                      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-warning-200 bg-warning-100/60 px-3 py-2">
                        <div className="flex items-center gap-2 text-sm font-medium text-danger-700">
                          <AlertTriangle className="h-4 w-4 shrink-0" />
                          {group.title}
                        </div>
                        <span className="text-xs text-paper-600">{group.cities.length} 个城市受影响</span>
                      </div>
                      <div className="overflow-x-auto">
                        <table className="w-full min-w-[560px] text-sm">
                          <thead>
                            <tr className="text-left text-xs font-medium text-paper-600">
                              <th className="px-3 py-2">城市</th>
                              <th className="px-3 py-2">温度</th>
                              <th className="px-3 py-2">天气</th>
                              <th className="px-3 py-2">风力</th>
                            </tr>
                          </thead>
                          <tbody>
                            {group.cities.map((warning) => {
                              const index = editableWarnings.indexOf(warning)
                              return (
                                <tr key={`${warning.city}-${index}`} className="align-middle">
                                  <td className="px-3 py-2">
                                    <input
                                      value={warning.city}
                                      onChange={(event) => handleEditableWarningChange(index, 'city', event.target.value)}
                                      className="w-full rounded-control border border-warning-300 bg-white px-2 py-1 text-sm font-medium text-paper-900 focus:border-accent-600 focus:outline-none focus:ring-2 focus:ring-accent-100"
                                    />
                                  </td>
                                  <td className="px-3 py-2">
                                    <div className="flex items-center gap-1">
                                      <input
                                        type="number"
                                        value={warning.temp}
                                        onChange={(event) => handleEditableWarningChange(index, 'temp', Number(event.target.value) || 0)}
                                        className="w-20 rounded-control border border-paper-300 px-2 py-1 text-sm focus:border-accent-600 focus:outline-none focus:ring-2 focus:ring-accent-100"
                                      />
                                      <span className="text-paper-600">°C</span>
                                    </div>
                                  </td>
                                  <td className="px-3 py-2">
                                    <input
                                      value={warning.weather}
                                      onChange={(event) => handleEditableWarningChange(index, 'weather', event.target.value)}
                                      className="w-full rounded-control border border-paper-300 px-2 py-1 text-sm focus:border-accent-600 focus:outline-none focus:ring-2 focus:ring-accent-100"
                                    />
                                  </td>
                                  <td className="px-3 py-2">
                                    <input
                                      value={warning.wind}
                                      onChange={(event) => handleEditableWarningChange(index, 'wind', event.target.value)}
                                      className="w-full rounded-control border border-paper-300 px-2 py-1 text-sm focus:border-accent-600 focus:outline-none focus:ring-2 focus:ring-accent-100"
                                    />
                                  </td>
                                </tr>
                              )
                            })}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  ))}
                  <p className="flex items-center gap-1.5 text-xs text-paper-600">
                    <Info className="h-3.5 w-3.5" />
                    同一条预警只展示一次，影响城市合并列出；修改后会自动更新群提醒内容。
                  </p>
                </div>
              </div>

              <div className="mb-6">
                <div className="mb-3 flex items-center justify-between">
                  <h3 className="text-base font-semibold text-paper-900">群提醒内容</h3>
                  <span className="text-xs tabular-nums text-paper-500">{warningMessageContent.length} 字符</span>
                </div>
                <textarea
                  value={warningMessageContent}
                  onChange={(event) => setWarningMessageContent(event.target.value)}
                  className="h-40 w-full resize-none rounded-control border border-paper-300 px-4 py-3 text-sm leading-6 focus:border-accent-600 focus:outline-none focus:ring-2 focus:ring-accent-100"
                  placeholder="请输入群提醒内容"
                />
              </div>

              <div>
                <div className="mb-3 flex items-center justify-between">
                  <h3 className="text-base font-semibold text-paper-900">选择接收旅行团</h3>
                  <label className="flex cursor-pointer items-center gap-2 text-sm text-paper-600">
                    <input
                      type="checkbox"
                      checked={selectedTripsForWarning.length === trips.length && trips.length > 0}
                      onChange={(event) => handleSelectAllTripsForWarning(event.target.checked)}
                      className="h-4 w-4 rounded accent-accent-600"
                    />
                    全选
                  </label>
                </div>

                <div className="overflow-hidden rounded-card border border-paper-200">
                  <table className="w-full min-w-[760px] text-sm">
                    <thead>
                      <tr className="border-b border-paper-200 text-left text-xs font-medium text-paper-500">
                        <th className="w-16 px-5 py-3">选择</th>
                        <th className="px-5 py-3">团名</th>
                        <th className="px-5 py-3">出发日期</th>
                        <th className="px-5 py-3">人数</th>
                        <th className="px-5 py-3">状态</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-paper-100">
                      {trips.map((trip) => {
                        const checked = selectedTripsForWarning.includes(trip.id)
                        return (
                          <tr
                            key={trip.id}
                            onClick={() => handleToggleTripForWarning(trip.id)}
                            className={`cursor-pointer transition-colors hover:bg-paper-50 ${checked ? 'bg-accent-50' : ''}`}
                          >
                            <td className="px-5 py-3">
                              <input
                                type="checkbox"
                                checked={checked}
                                onClick={(event) => event.stopPropagation()}
                                onChange={() => handleToggleTripForWarning(trip.id)}
                                className="h-4 w-4 rounded accent-accent-600"
                              />
                            </td>
                            <td className="px-5 py-3 font-medium text-paper-900">{trip.name}</td>
                            <td className="px-5 py-3 text-paper-600">{trip.startDate} 至 {trip.endDate}</td>
                            <td className="px-5 py-3 tabular-nums text-paper-600">{trip.participants} 人</td>
                            <td className="px-5 py-3">
                              {(() => { const s = computeDisplayStatus(trip.startDate, trip.endDate); return <span className={`rounded-control px-2 py-0.5 text-xs ${makeStatusColorMap[s]}`}>{s}</span> })()}
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
                <div className="mt-3 text-sm text-paper-600">
                  已选择 <span className="font-semibold tabular-nums text-paper-900">{selectedTripsForWarning.length}</span> 个旅行团
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between border-t border-paper-200 bg-paper-50 px-6 py-4">
              <div className="text-sm text-paper-600">
                发送渠道：<span className="ml-2 font-semibold text-paper-900">企业微信群</span>
              </div>
              <div className="flex gap-3">
                <Button variant="secondary" onClick={resetWarningModal}>取消</Button>
                <Button
                  variant="danger"
                  onClick={() => void handleSendWarningNotification()}
                  loading={sendingWarning}
                  disabled={selectedTripsForWarning.length === 0 || !warningMessageContent.trim()}
                >
                  发送到群 ({selectedTripsForWarning.length})
                </Button>
              </div>
            </div>
          </div>
        </div>
      ) : null}
      </>
    )}
    </PageShell>
  )
}
