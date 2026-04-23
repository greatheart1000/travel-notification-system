import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { ArrowLeft, Bell, CheckCircle2, ClipboardCheck, FileText, ListChecks, Route, Users } from 'lucide-react'
import { Header } from '../components/Header'
import { Button } from '../components/Button'
import { Card } from '../components/Card'
import { PageState } from '../components/PageState'
import { notificationsApi, tripsApi, getErrorMessage } from '../services/api'
import { type Trip, type TripExecutionDetail, type TripExecutionRow } from '../types/api'
import { loadTripDetail } from '../features/trip-management/tripDetailApi'
import { buildImportFlowSnapshot } from '../features/trip-management/tripImportAdapter'

type TripSubPage = 'overview' | 'import-validation' | 'itinerary' | 'guests' | 'transfers' | 'notifications'

interface TripDetailProps {
  tripId: string | null
  onBack: () => void
  onOpenTripNotifications?: (tripId: string) => void
}

const subPages: Array<{ key: TripSubPage; label: string; icon: ReactNode }> = [
  { key: 'overview', label: '团详情总览', icon: <ClipboardCheck className="h-4 w-4" /> },
  { key: 'import-validation', label: '导入校验', icon: <CheckCircle2 className="h-4 w-4" /> },
  { key: 'itinerary', label: '每日行程页', icon: <Route className="h-4 w-4" /> },
  { key: 'guests', label: '客人名单页', icon: <Users className="h-4 w-4" /> },
  { key: 'transfers', label: '接送安排页', icon: <ListChecks className="h-4 w-4" /> },
  { key: 'notifications', label: '通知执行页', icon: <Bell className="h-4 w-4" /> },
]

function SectionTitle({ title, desc }: { title: string; desc: string }) {
  return (
    <div className="mb-3">
      <h3 className="text-base font-semibold text-slate-900">{title}</h3>
      <p className="text-sm text-slate-500">{desc}</p>
    </div>
  )
}

export function TripDetail({ tripId, onBack, onOpenTripNotifications }: TripDetailProps) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [trip, setTrip] = useState<Trip | null>(null)
  const [activeTab, setActiveTab] = useState<TripSubPage>('overview')
  const [executionDetail, setExecutionDetail] = useState<TripExecutionDetail | null>(null)
  const [executionRow, setExecutionRow] = useState<TripExecutionRow | undefined>()
  const [correctedValues, setCorrectedValues] = useState<Record<string, string>>({})
  const [message, setMessage] = useState('')

  useEffect(() => {
    if (!tripId) {
      setLoading(false)
      setTrip(null)
      return
    }
    let active = true
    const run = async () => {
      setLoading(true)
      setError('')
      try {
        const payload = await loadTripDetail(tripId)
        const [rows, detail] = await Promise.all([
          tripsApi.listExecutionRows({ ownerScope: 'mine' }).catch(() => []),
          tripsApi.getExecutionDetail(tripId).catch(() => null),
        ])
        if (!active) return
        setTrip(payload.trip)
        setExecutionDetail(detail)
        setExecutionRow(rows.find((row) => row.tripId === tripId))
      } catch (err) {
        if (!active) return
        setError(getErrorMessage(err))
      } finally {
        if (active) setLoading(false)
      }
    }
    void run()
    return () => {
      active = false
    }
  }, [tripId])

  const flow = useMemo(() => (trip ? buildImportFlowSnapshot(trip, executionRow) : null), [trip, executionRow])

  const notifyNow = async () => {
    if (!tripId || !executionDetail) return
    const node = executionDetail.tasks.find((item) => item.status !== 'done')
    if (!node) {
      setMessage('当前没有待执行通知节点')
      return
    }
    try {
      const preview = await notificationsApi.previewDispatch({ tripId, nodeKey: node.nodeKey, channel: 'sms' })
      const sent = await notificationsApi.dispatchNow({
        tripId,
        nodeKey: node.nodeKey,
        channel: 'sms',
        content: preview.content,
        templateId: preview.templateId,
      })
      setMessage(sent.ok ? '通知发送成功' : '发送失败，已建议转人工')
    } catch (err) {
      setMessage(`发送失败: ${getErrorMessage(err)}`)
    }
  }

  if (loading) {
    return (
      <>
        <Header />
        <div className="p-8"><PageState kind="loading" title="正在加载团详情" /></div>
      </>
    )
  }

  if (error || !trip || !flow) {
    return (
      <>
        <Header />
        <div className="p-8"><PageState kind="error" title="加载失败" description={error || '团不存在'} /></div>
      </>
    )
  }

  const renderOverview = () => (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
      <div className="space-y-6 lg:col-span-2">
        <Card>
          <SectionTitle title="导入结果摘要" desc="第一屏优先确认导入质量，而非手工编辑基础信息。" />
          <div className="grid grid-cols-2 gap-3 text-sm">
            <p>导入来源：Excel / PDF</p>
            <p>解析状态：{flow.missingFields.length === 0 ? '成功' : '部分成功'}</p>
            <p>识别字段数：{flow.recognizedFields.length}</p>
            <p>待补全字段数：{flow.missingFields.length}</p>
          </div>
        </Card>

        <Card>
          <SectionTitle title="每日行程时间线（摘要）" desc="围绕日程执行，下一步进入每日行程页查看详情。" />
          <div className="space-y-3 text-sm">
            {flow.itineraryDigest.length === 0 ? <p>尚未导入行程</p> : flow.itineraryDigest.map((day) => (
              <div key={`${day.date}-${day.route}`} className="rounded border border-slate-200 p-3">
                <p className="font-medium">{day.date}</p>
                <p>交通：{day.transport}</p>
                <p>行程：{day.route}</p>
                <p>餐标：{day.meal}</p>
                <p>酒店：{day.hotel}</p>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <div className="space-y-6">
        <Card>
          <SectionTitle title="客人名单摘要" desc="优先确认联系人完整度。" />
          <div className="space-y-2 text-sm">
            {flow.guestDigest.slice(0, 5).map((guest) => (
              <p key={guest.name}>{guest.name} · {guest.phone} · {guest.status}</p>
            ))}
            {flow.guestDigest.length === 0 ? <p>未导入游客名单</p> : null}
          </div>
        </Card>
        <Card>
          <SectionTitle title="接送安排摘要" desc="来源于导入行程，支持后续人工确认。" />
          <div className="space-y-2 text-sm">
            {flow.pickupDigest.slice(0, 4).map((pickup, idx) => (
              <p key={`${pickup.date}-${idx}`}>{pickup.type} · {pickup.date} · {pickup.location}</p>
            ))}
            {flow.pickupDigest.length === 0 ? <p>暂无接送安排</p> : null}
          </div>
        </Card>
        <Card>
          <SectionTitle title="今日待办" desc="通知执行会自动按行程生成节点。" />
          <p className="text-sm">今日待办：{flow.todayTodo}</p>
          <p className="text-sm">下一通知节点：{flow.nextNode}</p>
        </Card>
      </div>
    </div>
  )

  const renderImportValidation = () => (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
      <Card>
        <SectionTitle title="识别成功字段" desc="可直接确认导入。" />
        <div className="space-y-2 text-sm">
          {flow.recognizedFields.map((field) => <p key={field.key}>{field.label}：{field.value}</p>)}
        </div>
      </Card>
      <Card>
        <SectionTitle title="待确认字段" desc="支持手工修正后再导入。" />
        <div className="space-y-3 text-sm">
          {flow.pendingFields.map((field) => (
            <label key={field.key} className="block">
              <span className="mb-1 block">{field.label}</span>
              <input
                className="w-full rounded border border-slate-300 px-2 py-1"
                value={correctedValues[field.key] ?? field.value}
                onChange={(event) => setCorrectedValues((prev) => ({ ...prev, [field.key]: event.target.value }))}
              />
            </label>
          ))}
        </div>
      </Card>
      <Card>
        <SectionTitle title="缺失字段" desc="缺失项会影响通知可执行性。" />
        <div className="space-y-2 text-sm">
          {flow.missingFields.length === 0 ? <p>无缺失字段</p> : flow.missingFields.map((field) => <p key={field.key}>- {field.label}</p>)}
        </div>
        <div className="mt-4 flex gap-2">
          <Button onClick={() => setMessage('已确认导入（Mock）')}>一键确认导入</Button>
          <Button variant="secondary" onClick={() => setMessage('已保存手动修正（Mock）')}>手动补全</Button>
        </div>
      </Card>
    </div>
  )

  const renderItinerary = () => (
    <Card>
      <SectionTitle title="每日行程页" desc="按天查看路线 / 交通 / 酒店 / 餐标，并生成当天通知。" />
      {flow.itineraryDigest.map((day) => (
        <div key={`${day.date}-${day.route}`} className="mb-3 rounded border border-slate-200 p-3 text-sm">
          <p className="font-medium">{day.date}</p>
          <p>路线：{day.route}</p>
          <p>交通工具：{day.transport}</p>
          <p>酒店：{day.hotel}</p>
          <p>早午晚：{day.meal}</p>
        </div>
      ))}
    </Card>
  )

  const renderGuests = () => (
    <Card>
      <SectionTitle title="客人名单页" desc="支持电话补录、特殊需求备注、入群状态确认。" />
      {flow.guestDigest.map((guest) => (
        <div key={`${guest.name}-${guest.phone}`} className="mb-2 rounded border border-slate-200 p-3 text-sm">
          <p>{guest.name}</p>
          <p>{guest.phone}</p>
          <p>状态：{guest.status}</p>
        </div>
      ))}
    </Card>
  )

  const renderTransfers = () => (
    <Card>
      <SectionTitle title="接送安排页" desc="管理接送地点、班次、司机协同信息。" />
      {flow.pickupDigest.map((pickup, index) => (
        <div key={`${pickup.date}-${index}`} className="mb-2 rounded border border-slate-200 p-3 text-sm">
          <p>{pickup.type}送日期：{pickup.date}</p>
          <p>地点：{pickup.location}</p>
          <p>班次：{pickup.shift}</p>
          <p>说明：{pickup.note}</p>
        </div>
      ))}
    </Card>
  )

  const renderNotifications = () => (
    <Card>
      <SectionTitle title="通知执行页" desc="今日通知任务、规则命中和重发入口。" />
      <div className="space-y-2 text-sm">
        <p>今日任务：{executionDetail?.todayDone ?? 0}/{executionDetail?.todayTotal ?? 0}</p>
        <p>风险等级：{executionDetail?.riskLevel || 'unknown'}</p>
        <p>下次调度：{executionDetail?.nextDispatchAt || '待生成'}</p>
      </div>
      <div className="mt-4 flex gap-2">
        <Button onClick={() => void notifyNow()}>执行当前通知</Button>
        <Button
          variant="secondary"
          onClick={() => {
            if (!tripId) return
            if (onOpenTripNotifications) return onOpenTripNotifications(tripId)
            window.history.pushState({}, '', `/notifications?trip_id=${encodeURIComponent(tripId)}`)
            window.dispatchEvent(new PopStateEvent('popstate'))
          }}
        >
          打开通知中心
        </Button>
      </div>
    </Card>
  )

  return (
    <>
      <Header />
      <div className="min-h-screen bg-slate-50 pb-12">
        <div className="border-b bg-white">
          <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
            <div className="flex items-center gap-3">
              <button onClick={onBack} className="rounded-full p-2 hover:bg-slate-100"><ArrowLeft className="h-4 w-4" /></button>
              <div>
                <h1 className="text-lg font-semibold">{trip.destination}</h1>
                <p className="text-xs text-slate-500">{trip.teamId}</p>
              </div>
            </div>
            <Button variant="secondary" onClick={() => void tripsApi.exportPdf(trip.id, trip.destination)}>
              <FileText className="mr-2 inline h-4 w-4" />导出PDF
            </Button>
          </div>
        </div>

        <div className="mx-auto max-w-7xl space-y-5 px-6 py-6">
          <Card>
            <SectionTitle title="主流程导航" desc="导入文件 → 校验 → 自动生成团详情 → 查看每日行程 → 执行通知" />
            <div className="flex flex-wrap gap-2">
              {subPages.map((item) => (
                <Button key={item.key} variant={activeTab === item.key ? 'primary' : 'secondary'} onClick={() => setActiveTab(item.key)}>
                  <span className="mr-1 inline-flex">{item.icon}</span>{item.label}
                </Button>
              ))}
            </div>
            {message ? <p className="mt-3 text-sm text-sky-700">{message}</p> : null}
          </Card>

          {activeTab === 'overview' ? renderOverview() : null}
          {activeTab === 'import-validation' ? renderImportValidation() : null}
          {activeTab === 'itinerary' ? renderItinerary() : null}
          {activeTab === 'guests' ? renderGuests() : null}
          {activeTab === 'transfers' ? renderTransfers() : null}
          {activeTab === 'notifications' ? renderNotifications() : null}

          <Card>
            <SectionTitle title="基础信息（次级区域）" desc="按要求降级到页面底部，不影响主流程。" />
            <div className="grid grid-cols-1 gap-2 text-sm md:grid-cols-2">
              <p>团号：{trip.teamId || '未识别'}</p>
              <p>线路：{trip.destination || '未识别'}</p>
              <p>出团日期：{trip.startDate || '未识别'}</p>
              <p>人数：{trip.participants || trip.guests.length}</p>
              <p>销售：待补录</p>
              <p>客源地：待补录</p>
            </div>
          </Card>
        </div>
      </div>
    </>
  )
}
