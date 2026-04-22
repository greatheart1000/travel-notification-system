import { AlertTriangle, Eye, Pencil, Send, ShieldAlert } from 'lucide-react'
import { Badge } from '../Badge'
import { Button } from '../Button'
import { Card } from '../Card'

type BadgeVariant = 'default' | 'success' | 'warning' | 'danger' | 'info'

export interface EmergencyWeatherTripSummary {
  tripId: string
  teamId: string
  destination: string
  statusLabel: string
  travelerCount: number
  summary: string
}

export interface EmergencyWeatherPanelSummary {
  title: string
  todayWeatherSummary: string
  riskLevelLabel: string
  riskLevelBadge?: BadgeVariant
  affectedRegion: string
  affectedTripCount: number
  affectedTrips: EmergencyWeatherTripSummary[]
  aiRiskSummary: string
  touristNotification: string
  internalNotification: string
  suggestedActions: string[]
  requiresConfirmation?: boolean
}

interface EmergencyWeatherPanelProps {
  summary: EmergencyWeatherPanelSummary
  draftContent: string
  onEdit: () => void
  onSend: () => void
  onDefer: () => void
  onViewDetail: () => void
}

export function EmergencyWeatherPanel({
  summary,
  draftContent,
  onEdit,
  onSend,
  onDefer,
  onViewDetail,
}: EmergencyWeatherPanelProps) {
  const riskBadge = summary.riskLevelBadge ?? 'warning'

  return (
    <Card className="overflow-hidden border-red-200 bg-[linear-gradient(135deg,rgba(254,242,242,1),rgba(255,255,255,0.96))] shadow-[0_18px_48px_rgba(127,29,29,0.08)]">
      <div className="space-y-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="flex items-start gap-3">
            <div className="rounded-2xl bg-red-600 p-3 text-white shadow-lg shadow-red-200">
              <ShieldAlert className="h-6 w-6" />
            </div>
            <div>
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <Badge variant={riskBadge}>{summary.riskLevelLabel}</Badge>
                <Badge variant="info">AI已完成判断</Badge>
              </div>
              <h2 className="text-2xl font-black text-slate-950">紧急天气预警</h2>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-700">
                {summary.title}。当前流程已支持天气获取、风险判断、AI 文案生成，并在人工确认后发送通知。
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="secondary" onClick={onViewDetail}>
              <Eye className="mr-2 inline h-4 w-4" />
              查看详情
            </Button>
            <Button variant="secondary" onClick={onEdit}>
              <Pencil className="mr-2 inline h-4 w-4" />
              编辑文案
            </Button>
            <Button variant="danger" onClick={onSend}>
              <Send className="mr-2 inline h-4 w-4" />
              发送通知
            </Button>
            <Button variant="secondary" onClick={onDefer}>
              暂不发送
            </Button>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-4">
          <div className="rounded-2xl border border-red-100 bg-white/80 p-4">
            <p className="text-xs font-bold tracking-[0.22em] text-red-500">今日天气摘要</p>
            <p className="mt-2 text-sm font-semibold text-slate-900">{summary.todayWeatherSummary}</p>
          </div>
          <div className="rounded-2xl border border-red-100 bg-white/80 p-4">
            <p className="text-xs font-bold tracking-[0.22em] text-red-500">风险等级</p>
            <p className="mt-2 text-sm font-semibold text-slate-900">{summary.riskLevelLabel}</p>
          </div>
          <div className="rounded-2xl border border-red-100 bg-white/80 p-4">
            <p className="text-xs font-bold tracking-[0.22em] text-red-500">影响区域</p>
            <p className="mt-2 text-sm font-semibold text-slate-900">{summary.affectedRegion}</p>
          </div>
          <div className="rounded-2xl border border-red-100 bg-white/80 p-4">
            <p className="text-xs font-bold tracking-[0.22em] text-red-500">受影响旅行团数量</p>
            <p className="mt-2 text-sm font-semibold text-slate-900">{summary.affectedTripCount} 个</p>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-6 xl:grid-cols-[0.95fr_1.05fr]">
          <div className="space-y-4">
            <div className="rounded-3xl border border-blue-100 bg-blue-50/70 p-5">
              <div className="mb-3 flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-blue-600" />
                <h3 className="text-base font-black text-slate-900">AI 风险分析</h3>
              </div>
              <p className="text-sm leading-6 text-slate-700">{summary.aiRiskSummary}</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {summary.suggestedActions.map((action) => (
                  <span key={action} className="rounded-full bg-white px-3 py-1 text-xs text-slate-700">
                    {action}
                  </span>
                ))}
              </div>
            </div>

            <div className="rounded-3xl border border-slate-200 bg-slate-950 p-5 text-white shadow-[0_18px_48px_rgba(15,23,42,0.18)]">
              <p className="text-xs font-bold tracking-[0.22em] text-red-200">游客通知文案</p>
              <p className="mt-2 whitespace-pre-wrap text-sm leading-7 text-slate-100">{draftContent || summary.touristNotification}</p>
              <p className="mt-4 text-xs font-bold tracking-[0.22em] text-blue-200">领队/内部通知文案</p>
              <p className="mt-2 whitespace-pre-wrap text-sm leading-7 text-slate-100">{summary.internalNotification}</p>
            </div>
          </div>

          <div className="rounded-3xl border border-slate-200 bg-white/90 p-5">
            <div className="mb-4 flex items-center gap-2">
              <h3 className="text-base font-black text-slate-900">受影响旅行团摘要</h3>
            </div>
            <div className="space-y-3">
              {summary.affectedTrips.map((trip) => (
                <div key={trip.tripId} className="rounded-2xl border border-slate-100 bg-slate-50 p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-bold text-slate-900">{trip.destination}</p>
                    <Badge variant="default">{trip.teamId}</Badge>
                    <Badge variant="info">{trip.statusLabel}</Badge>
                  </div>
                  <p className="mt-2 text-sm text-slate-600">{trip.summary}</p>
                  <p className="mt-2 text-xs text-slate-500">旅客人数：{trip.travelerCount} 人</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </Card>
  )
}
