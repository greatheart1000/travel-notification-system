import { useEffect, useRef, useState } from 'react'
import { Card } from '../components/Card'
import { Button } from '../components/Button'
import { Badge } from '../components/Badge'
import { PageState } from '../components/PageState'
import { PageShell } from '../components/PageShell'
import { ArrowRight, Calendar, CheckCircle, FileText, MoreVertical, Plus, Trash2, Upload, Users } from 'lucide-react'
import { tripsApi, getErrorMessage } from '../services/api'
import { type Trip, type TripExecutionRow, type TripStatusCode } from '../types/api'
import { TripDetail } from './TripDetail'

type LoadState = 'loading' | 'ready' | 'error' | 'empty'

interface TripsProps {
  tripId?: string | null
  onOpenTrip?: (tripId: string) => void
  onBackToList?: () => void
  onOpenTripNotifications?: (tripId: string) => void
}

function statusBadgeVariant(status: TripStatusCode): 'success' | 'info' | 'default' | 'warning' {
  if (status === 'in_progress') {
    return 'success'
  }
  if (status === 'planned') {
    return 'info'
  }
  if (status === 'completed') {
    return 'default'
  }
  return 'warning'
}

export function Trips({
  tripId = null,
  onOpenTrip,
  onBackToList,
  onOpenTripNotifications,
}: TripsProps) {
  // Navigation State
  const [isCreating, setIsCreating] = useState(false)

  // List State
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [trips, setTrips] = useState<Trip[]>([])
  const [loadState, setLoadState] = useState<LoadState>('loading')
  const [errorMessage, setErrorMessage] = useState('')
  const [executionMap, setExecutionMap] = useState<Record<string, TripExecutionRow>>({})
  const [actionMessage, setActionMessage] = useState<string | null>(null)
  const [isImporting, setIsImporting] = useState(false)
  const [openMenuTripId, setOpenMenuTripId] = useState<string | null>(null)

  const loadTrips = async () => {
    setLoadState('loading')
    setErrorMessage('')

    try {
      const [list, executionRows] = await Promise.all([
        tripsApi.list(),
        tripsApi.listExecutionRows({ ownerScope: 'mine' }).catch(() => [] as TripExecutionRow[]),
      ])
      const executionByTripId: Record<string, TripExecutionRow> = {}
      executionRows.forEach((row) => {
        executionByTripId[row.tripId] = row
      })
      setExecutionMap(executionByTripId)
      setTrips(list)
      setLoadState(list.length === 0 ? 'empty' : 'ready')
    } catch (error) {
      setLoadState('error')
      setErrorMessage(getErrorMessage(error))
    }
  }

  useEffect(() => {
    void loadTrips()
  }, [])

  useEffect(() => {
    if (!openMenuTripId) {
      return
    }
    const handleWindowClick = () => setOpenMenuTripId(null)
    window.addEventListener('click', handleWindowClick)
    return () => window.removeEventListener('click', handleWindowClick)
  }, [openMenuTripId])

  const deleteTrip = async (id: string) => {
    if (!window.confirm('确定要删除这个行程吗？')) return
    setActionMessage(null)

    try {
      await tripsApi.remove(id)
      setActionMessage('行程已删除')
      await loadTrips()
    } catch (error) {
      setActionMessage(`删除失败: ${getErrorMessage(error)}`)
    }
  }

  const markCompleted = async (id: string) => {
    setActionMessage(null)

    try {
      await tripsApi.update(id, { status: 'completed' })
      setActionMessage('行程已标记为完成')
      await loadTrips()
    } catch (error) {
      setActionMessage(`更新失败: ${getErrorMessage(error)}`)
    }
  }

  const importTrips = async (file: File) => {
    setIsImporting(true)
    setActionMessage(null)

    try {
      const result = await tripsApi.importFile(file)
      await loadTrips()
      setActionMessage(`Excel 导入完成: 成功创建 ${result.createdCount} 条，跳过 ${result.skippedCount} 条`)
    } catch (error) {
      setActionMessage(`导入失败: ${getErrorMessage(error)}`)
    } finally {
      setIsImporting(false)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  const handleBackToList = () => {
    setIsCreating(false)
    onBackToList?.()
    void loadTrips() // Refresh list
  }

  const handleOpenTrip = (id: string) => {
    if (onOpenTrip) {
      onOpenTrip(id)
      return
    }
    window.history.pushState({}, '', `/trips/${encodeURIComponent(id)}`)
    window.dispatchEvent(new PopStateEvent('popstate'))
  }

  const handleOpenTripNotifications = (id: string) => {
    if (onOpenTripNotifications) {
      onOpenTripNotifications(id)
      return
    }
    window.history.pushState({}, '', `/notifications?trip_id=${encodeURIComponent(id)}`)
    window.dispatchEvent(new PopStateEvent('popstate'))
  }

  if (tripId || isCreating) {
    return (
      <TripDetail
        tripId={tripId}
        onBack={handleBackToList}
        onOpenTripNotifications={onOpenTripNotifications}
      />
    )
  }

  const pageActions = (
    <>
      <input
        ref={fileInputRef}
        type="file"
        accept=".xlsx,.csv"
        className="hidden"
        onChange={(event) => {
          const file = event.target.files?.[0]
          if (file) {
            void importTrips(file)
          }
        }}
      />
      <Button variant="secondary" onClick={() => fileInputRef.current?.click()} loading={isImporting}>
        <Upload className="mr-2 inline h-5 w-5" />
        Excel导入
      </Button>
      <Button onClick={() => setIsCreating(true)}>
        <Plus className="mr-2 inline h-5 w-5" />
        新建行程
      </Button>
    </>
  )

  return (
    <PageShell
      eyebrow="Trips"
      title="行程管理"
      description="按旅行团卡片化管理团期、客人规模和行程状态。"
      actions={pageActions}
    >
        {actionMessage ? (
          <p className={`mb-6 rounded-xl p-3 text-sm ${actionMessage.includes('失败') ? 'bg-red-50 text-red-700' : 'bg-green-50 text-green-700'}`}>
            {actionMessage}
          </p>
        ) : null}

        {loadState === 'loading' ? (
          <PageState kind="loading" title="正在加载行程" />
        ) : null}

        {loadState === 'error' ? (
          <PageState
            kind="error"
            title="行程加载失败"
            description={errorMessage}
            onRetry={() => {
              void loadTrips()
            }}
          />
        ) : null}

        {loadState === 'empty' ? (
          <PageState
            kind="empty"
            title="暂无行程数据"
            description="可以先创建一条行程"
            onRetry={() => {
              void loadTrips()
            }}
          />
        ) : null}

        {loadState === 'ready' ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {trips.map((trip) => (
              <Card key={trip.id} className="cursor-pointer border-blue-100 shadow-[0_14px_40px_rgba(15,23,42,0.06)] transition hover:-translate-y-0.5 hover:shadow-xl" onClick={() => handleOpenTrip(trip.id)}>
                <div className="mb-4">
                  <div className="flex items-start justify-between mb-2">
                    <h3 className="text-xl font-black tracking-tight text-slate-950">{trip.destination || '未命名'}</h3>
                    <Badge variant={statusBadgeVariant(trip.status)}>{trip.statusLabel}</Badge>
                  </div>
                  <p className="font-mono text-sm uppercase tracking-wide text-slate-500">{trip.teamId}</p>
                </div>

                  <div className="space-y-3 mb-6">
                  <div className="flex items-center gap-3 text-sm text-gray-600">
                    <Calendar className="w-4 h-4 text-blue-600" />
                    <span>
                      {trip.startDate} 至 {trip.endDate}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-sm text-gray-600">
                    <Users className="w-4 h-4 text-blue-600" />
                    <span>{trip.guests?.length || trip.participants} 位客人</span>
                  </div>
                  </div>
                  {executionMap[trip.id] ? (
                    <div className="mb-4 rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-600">
                      <p>执行阶段：{executionMap[trip.id].currentStage}</p>
                      <p>
                        今日待办：{executionMap[trip.id].todoCount}/{executionMap[trip.id].totalCount} ·
                        风险：{executionMap[trip.id].riskLevel}
                      </p>
                    </div>
                  ) : null}

                <div className="flex items-center gap-2 pt-4 border-t border-gray-200" onClick={e => e.stopPropagation()}>
                  <Button size="sm" className="flex-1 rounded-lg shadow-lg shadow-blue-200/60" onClick={() => handleOpenTrip(trip.id)}>
                    详情 <ArrowRight className="ml-1 inline h-4 w-4" />
                  </Button>
                  <Button size="sm" variant="secondary" onClick={() => handleOpenTripNotifications(trip.id)}>
                    通知设置
                  </Button>
                  <div className="relative">
                  <button
                    className="rounded-lg bg-slate-100 p-2 text-slate-500 transition hover:bg-blue-50 hover:text-blue-700"
                    onClick={(event) => {
                      event.stopPropagation()
                      setOpenMenuTripId((current) => current === trip.id ? null : trip.id)
                    }}
                    aria-label="更多操作"
                  >
                    <MoreVertical className="h-4 w-4" />
                  </button>
                    {openMenuTripId === trip.id ? (
                      <div className="absolute right-0 top-11 z-20 w-44 rounded-xl border border-slate-200 bg-white p-1.5 shadow-xl">
                        <button className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-700 hover:bg-slate-50" onClick={() => void tripsApi.exportPdf(trip.id, trip.destination)}>
                          <FileText className="h-4 w-4" />导出 PDF
                        </button>
                        <button className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-700 hover:bg-green-50" onClick={() => void markCompleted(trip.id)}>
                          <CheckCircle className="h-4 w-4 text-green-700" />标记完成
                        </button>
                        <button className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-red-600 hover:bg-red-50" onClick={() => void deleteTrip(trip.id)}>
                          <Trash2 className="h-4 w-4" />删除行程
                        </button>
                      </div>
                    ) : null}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        ) : null}
    </PageShell>
  )
}
