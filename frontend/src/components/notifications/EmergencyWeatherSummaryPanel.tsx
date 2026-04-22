import { AlertTriangle, Clock3, Pencil, ShieldAlert, Sparkles, Users } from 'lucide-react'
import { Badge } from '../Badge'
import { Button } from '../Button'
import { Card } from '../Card'
import { PageState } from '../PageState'
import { type EmergencyWeatherSummary } from '../../types/api'

type LoadState = 'loading' | 'ready' | 'error' | 'empty'

interface EmergencyWeatherSummaryPanelProps {
  weatherLoadState: LoadState
  weatherSummary: EmergencyWeatherSummary | null
  weatherErrorMessage: string
  weatherActionMessage: string | null
  weatherDraft: string
  isWeatherSending: boolean
  onRetry: () => void
  onOpenEditor: () => void
  onSendNow: () => void
  formatUpdatedAt: (value: string) => string
}

export function EmergencyWeatherSummaryPanel({
  weatherLoadState,
  weatherSummary,
  weatherErrorMessage,
  weatherActionMessage,
  weatherDraft,
  isWeatherSending,
  onRetry,
  onOpenEditor,
  onSendNow,
  formatUpdatedAt,
}: EmergencyWeatherSummaryPanelProps) {
  const riskBadgeVariant = weatherSummary?.riskLevelBadge ?? 'warning'

  return (
    <div className="mb-6">
      {weatherActionMessage ? (
        <p className={`mb-4 rounded-xl p-3 text-sm ${weatherActionMessage.includes('失败') ? 'bg-red-50 text-red-700' : 'bg-green-50 text-green-700'}`}>
          {weatherActionMessage}
        </p>
      ) : null}
      <Card className="overflow-hidden border-red-200 bg-[linear-gradient(135deg,rgba(254,242,242,1),rgba(255,255,255,0.96))] shadow-[0_18px_48px_rgba(127,29,29,0.08)]">
        {weatherLoadState === 'loading' ? <PageState kind="loading" title="正在生成紧急天气通知" description="正在汇总天气、风险和受影响旅行团数据" /> : null}
        {weatherLoadState === 'error' ? (
          <PageState kind="error" title="紧急天气通知加载失败" description={weatherErrorMessage} onRetry={onRetry} />
        ) : null}
        {weatherLoadState === 'ready' && weatherSummary ? (
          <div className="space-y-6">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div className="flex items-start gap-3">
                <div className="rounded-2xl bg-red-600 p-3 text-white shadow-lg shadow-red-200">
                  <ShieldAlert className="h-6 w-6" />
                </div>
                <div>
                  <div className="mb-2 flex flex-wrap items-center gap-2">
                    <Badge variant={riskBadgeVariant}>{weatherSummary.riskLevelLabel}</Badge>
                    <Badge variant="info">AI已完成判断</Badge>
                  </div>
                  <h2 className="text-2xl font-black text-slate-950">紧急天气通知</h2>
                  <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-700">
                    {weatherSummary.title}。当前模块已支持天气摘要、AI风险分析、受影响旅行团摘要与 AI 生成通知文案预览，发送前可二次编辑。
                  </p>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button variant="secondary" onClick={onOpenEditor}>
                  <Pencil className="mr-2 inline h-4 w-4" />
                  编辑后发送
                </Button>
                <Button variant="danger" onClick={onSendNow} loading={isWeatherSending}>
                  <AlertTriangle className="mr-2 inline h-4 w-4" />
                  确认发送
                </Button>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-4">
              <div className="rounded-2xl border border-red-100 bg-white/80 p-4">
                <p className="text-xs font-bold tracking-[0.22em] text-red-500">预警标题</p>
                <p className="mt-2 text-sm font-semibold text-slate-900">{weatherSummary.title}</p>
              </div>
              <div className="rounded-2xl border border-red-100 bg-white/80 p-4">
                <p className="text-xs font-bold tracking-[0.22em] text-red-500">风险等级</p>
                <p className="mt-2 text-sm font-semibold text-slate-900">{weatherSummary.riskLevelLabel}</p>
              </div>
              <div className="rounded-2xl border border-red-100 bg-white/80 p-4">
                <p className="text-xs font-bold tracking-[0.22em] text-red-500">更新时间</p>
                <p className="mt-2 text-sm font-semibold text-slate-900">{formatUpdatedAt(weatherSummary.updatedAt)}</p>
              </div>
              <div className="rounded-2xl border border-red-100 bg-white/80 p-4">
                <p className="text-xs font-bold tracking-[0.22em] text-red-500">受影响旅行团数量</p>
                <p className="mt-2 text-sm font-semibold text-slate-900">{weatherSummary.affectedTripCount} 个</p>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-6 xl:grid-cols-[0.95fr_1.05fr]">
              <div className="space-y-4">
                <div className="rounded-3xl border border-red-100 bg-white/90 p-5">
                  <div className="mb-3 flex items-center gap-2">
                    <Clock3 className="h-4 w-4 text-red-500" />
                    <h3 className="text-base font-black text-slate-900">天气摘要</h3>
                  </div>
                  <p className="text-sm leading-6 text-slate-700">{weatherSummary.weatherSummary}</p>
                </div>
                <div className="rounded-3xl border border-blue-100 bg-blue-50/70 p-5">
                  <div className="mb-3 flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-blue-600" />
                    <h3 className="text-base font-black text-slate-900">AI风险分析</h3>
                  </div>
                  <p className="text-sm leading-6 text-slate-700">{weatherSummary.aiRiskSummary}</p>
                </div>
              </div>

              <div className="rounded-3xl border border-slate-200 bg-white/90 p-5">
                <div className="mb-4 flex items-center gap-2">
                  <Users className="h-4 w-4 text-slate-500" />
                  <h3 className="text-base font-black text-slate-900">受影响旅行团摘要</h3>
                </div>
                <div className="space-y-3">
                  {weatherSummary.affectedTrips.map((trip) => (
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

            <div className="rounded-3xl border border-slate-200 bg-slate-950 p-5 text-white shadow-[0_18px_48px_rgba(15,23,42,0.18)]">
              <div className="mb-3 flex items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-bold tracking-[0.22em] text-red-200">AI生成通知文案</p>
                  <p className="mt-2 text-sm text-slate-300">推荐发送渠道：{weatherSummary.channelLabel}</p>
                </div>
                <Button variant="secondary" size="sm" onClick={onOpenEditor}>
                  <Pencil className="mr-1 inline h-3 w-3" />
                  编辑文案
                </Button>
              </div>
              <p className="whitespace-pre-wrap text-sm leading-7 text-slate-100">{weatherDraft}</p>
            </div>
          </div>
        ) : null}
      </Card>
    </div>
  )
}
