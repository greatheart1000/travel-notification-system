import { useEffect, useRef, useState } from 'react'
import { Card } from '../components/Card'
import { Button } from '../components/Button'
import { Badge } from '../components/Badge'
import { PageState } from '../components/PageState'
import { PageShell } from '../components/PageShell'
import { ArrowRight, Calendar, FileText, MoreVertical, Plus, Trash2, Upload, Users } from 'lucide-react'
import { tripsApi, getErrorMessage } from '../services/api'
import { type Trip, type TripExecutionRow, type TripStatusCode } from '../types/api'
import { TripDetail } from './TripDetail'
import { buildImportFlowSnapshot } from '../features/trip-management/tripImportAdapter'

type LoadState = 'loading' | 'ready' | 'error' | 'empty'

interface TripsProps {
  tripId?: string | null
  onOpenTrip?: (tripId: string) => void
  onBackToList?: () => void
  onOpenTripNotifications?: (tripId: string) => void
}

function statusBadgeVariant(status: TripStatusCode): 'success' | 'info' | 'default' | 'warning' {
  if (status === 'in_progress') return 'success'
  if (status === 'planned') return 'info'
  if (status === 'completed') return 'default'
  return 'warning'
}

export function Trips({ tripId = null, onOpenTrip, onBackToList, onOpenTripNotifications }: TripsProps) {
  const [isCreating, setIsCreating] = useState(false)
  const excelInputRef = useRef<HTMLInputElement>(null)
  const pdfInputRef = useRef<HTMLInputElement>(null)
  const [trips, setTrips] = useState<Trip[]>([])
  const [loadState, setLoadState] = useState<LoadState>('loading')
  const [errorMessage, setErrorMessage] = useState('')
  const [executionMap, setExecutionMap] = useState<Record<string, TripExecutionRow>>({})
  const [actionMessage, setActionMessage] = useState<string | null>(null)
  const [isImporting, setIsImporting] = useState(false)
  const [openMenuTripId, setOpenMenuTripId] = useState<string | null>(null)

  const loadTrips = async () => {
    setLoadState('loading')
    try {
      const [list, executionRows] = await Promise.all([
        tripsApi.list(),
        tripsApi.listExecutionRows({ ownerScope: 'mine' }).catch(() => [] as TripExecutionRow[]),
      ])
      const byId: Record<string, TripExecutionRow> = {}
      executionRows.forEach((row) => {
        byId[row.tripId] = row
      })
      setExecutionMap(byId)
      setTrips(list)
      setLoadState(list.length === 0 ? 'empty' : 'ready')
      setErrorMessage('')
    } catch (error) {
      setLoadState('error')
      setErrorMessage(getErrorMessage(error))
    }
  }

  useEffect(() => {
    void loadTrips()
  }, [])

  useEffect(() => {
    if (!openMenuTripId) return
    const close = () => setOpenMenuTripId(null)
    window.addEventListener('click', close)
    return () => window.removeEventListener('click', close)
  }, [openMenuTripId])

  const importTrips = async (file: File, source: 'Excel' | 'PDF') => {
    setIsImporting(true)
    setActionMessage(null)
    try {
      const result = await tripsApi.importFile(file)
      await loadTrips()
      setActionMessage(`${source} 导入完成：创建 ${result.createdCount} 条，跳过 ${result.skippedCount} 条`) 
    } catch (error) {
      setActionMessage(`导入失败: ${getErrorMessage(error)}`)
    } finally {
      setIsImporting(false)
      if (excelInputRef.current) excelInputRef.current.value = ''
      if (pdfInputRef.current) pdfInputRef.current.value = ''
    }
  }

  const deleteTrip = async (id: string) => {
    if (!window.confirm('确定要删除这个行程吗？')) return
    try {
      await tripsApi.remove(id)
      await loadTrips()
      setActionMessage('行程已删除')
    } catch (error) {
      setActionMessage(`删除失败: ${getErrorMessage(error)}`)
    }
  }

  const handleBackToList = () => {
    setIsCreating(false)
    onBackToList?.()
    void loadTrips()
  }

  const handleOpenTrip = (id: string) => {
    if (onOpenTrip) return onOpenTrip(id)
    window.history.pushState({}, '', `/trips/${encodeURIComponent(id)}`)
    window.dispatchEvent(new PopStateEvent('popstate'))
  }

  const handleOpenTripNotifications = (id: string) => {
    if (onOpenTripNotifications) return onOpenTripNotifications(id)
    window.history.pushState({}, '', `/notifications?trip_id=${encodeURIComponent(id)}`)
    window.dispatchEvent(new PopStateEvent('popstate'))
  }

  if (tripId || isCreating) {
    return <TripDetail tripId={tripId} onBack={handleBackToList} onOpenTripNotifications={onOpenTripNotifications} />
  }

  return (
    <PageShell
      eyebrow="Trips"
      title="行程管理"
      description="主流程：导入行程单 → 校验导入 → 自动生成团详情 → 执行通知（Excel建议含“行程表+客人表”双sheet）。"
      actions={
        <>
          <input
            ref={excelInputRef}
            type="file"
            accept=".xlsx,.csv"
            className="hidden"
            onChange={(event) => {
              const file = event.target.files?.[0]
              if (file) void importTrips(file, 'Excel')
            }}
          />
          <input
            ref={pdfInputRef}
            type="file"
            accept=".pdf"
            className="hidden"
            onChange={(event) => {
              const file = event.target.files?.[0]
              if (file) void importTrips(file, 'PDF')
            }}
          />
          <Button onClick={() => excelInputRef.current?.click()} loading={isImporting}>
            <Upload className="mr-2 inline h-5 w-5" />Excel导入
          </Button>
          <Button variant="secondary" onClick={() => pdfInputRef.current?.click()} loading={isImporting}>
            <FileText className="mr-2 inline h-5 w-5" />PDF导入
          </Button>
          <Button variant="secondary" onClick={() => setIsCreating(true)}>
            <Plus className="mr-2 inline h-5 w-5" />新建空白团
          </Button>
        </>
      }
    >
      {actionMessage ? <p className="mb-4 rounded-lg bg-slate-100 p-3 text-sm text-slate-700">{actionMessage}</p> : null}
      <p className="mb-4 text-xs text-slate-500">
        Excel 模板建议：Sheet1=行程表（team_id,destination,start_date,end_date,date,route,transport,hotel）；
        Sheet2=客人表（name,phone,notes）。
      </p>

      {loadState === 'loading' ? <PageState kind="loading" title="正在加载行程" /> : null}
      {loadState === 'error' ? <PageState kind="error" title="行程加载失败" description={errorMessage} onRetry={() => void loadTrips()} /> : null}
      {loadState === 'empty' ? <PageState kind="empty" title="暂无行程" description="请先导入 Excel 或 PDF 行程单" onRetry={() => void loadTrips()} /> : null}

      {loadState === 'ready' ? (
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
          {trips.map((trip) => {
            const flow = buildImportFlowSnapshot(trip, executionMap[trip.id])
            const tags: string[] = []
            if (!flow.hasItinerary) tags.push('未导入行程')
            if (!flow.hasGuests) tags.push('待补全游客')
            if (flow.hasItinerary) tags.push('行程已解析')
            if (flow.todayTodo === 0) tags.push('通知未配置')
            if (flow.todayTodo > 0) tags.push('可执行')

            return (
              <Card key={trip.id} className="cursor-pointer" onClick={() => handleOpenTrip(trip.id)}>
                <div className="mb-4 flex items-start justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-slate-900">{trip.destination || '未命名团'}</h3>
                    <p className="font-mono text-xs text-slate-500">{trip.teamId || '无团号'}</p>
                  </div>
                  <Badge variant={statusBadgeVariant(trip.status)}>{trip.statusLabel}</Badge>
                </div>

                <div className="space-y-2 text-sm text-slate-600">
                  <p className="flex items-center gap-2"><Calendar className="h-4 w-4" />{trip.startDate} ~ {trip.endDate}</p>
                  <p className="flex items-center gap-2"><Users className="h-4 w-4" />{trip.guests?.length || trip.participants} 位游客</p>
                  <p>数据完整度：{flow.completeness}%</p>
                  <p>已导入行程：{flow.hasItinerary ? '是' : '否'} · 已导入游客：{flow.hasGuests ? '是' : '否'}</p>
                  <p>今日待办数：{flow.todayTodo} · 下一通知节点：{flow.nextNode}</p>
                </div>

                <div className="mt-3 flex flex-wrap gap-2">
                  {tags.map((tag) => <Badge key={tag} variant="default">{tag}</Badge>)}
                </div>

                <div className="mt-4 flex items-center gap-2 border-t border-slate-200 pt-4" onClick={(event) => event.stopPropagation()}>
                  <Button size="sm" className="flex-1" onClick={() => handleOpenTrip(trip.id)}>
                    进入团详情 <ArrowRight className="ml-1 inline h-4 w-4" />
                  </Button>
                  <Button size="sm" variant="secondary" onClick={() => handleOpenTripNotifications(trip.id)}>通知执行</Button>
                  <div className="relative">
                    <button
                      className="rounded-lg bg-slate-100 p-2 text-slate-600"
                      onClick={(event) => {
                        event.stopPropagation()
                        setOpenMenuTripId((current) => (current === trip.id ? null : trip.id))
                      }}
                    >
                      <MoreVertical className="h-4 w-4" />
                    </button>
                    {openMenuTripId === trip.id ? (
                      <div className="absolute right-0 top-10 z-20 w-36 rounded-lg border border-slate-200 bg-white p-1">
                        <button className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-slate-50" onClick={() => void tripsApi.exportPdf(trip.id, trip.destination)}>
                          <FileText className="h-4 w-4" />导出PDF
                        </button>
                        <button className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-red-600 hover:bg-red-50" onClick={() => void deleteTrip(trip.id)}>
                          <Trash2 className="h-4 w-4" />删除
                        </button>
                      </div>
                    ) : null}
                  </div>
                </div>
              </Card>
            )
          })}
        </div>
      ) : null}
    </PageShell>
  )
}
