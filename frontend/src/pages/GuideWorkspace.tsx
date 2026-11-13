import { useEffect, useMemo, useState } from 'react'
import {
  AlertTriangle,
  BellRing,
  CloudSun,
  RefreshCw,
  Send,
  Sun,
  Wand2,
} from 'lucide-react'
import { PageShell } from '../components/PageShell'
import { Badge } from '../components/Badge'
import { Button } from '../components/Button'
import { getErrorMessage, guideWorkspaceApi, type GuideWorkspaceData } from '../services/api'

interface Props {
  onOpenTrip: (tripId: string, tab?: string) => void
}

const STAGE_META: Record<
  string,
  { label: string; variant: 'info' | 'success' | 'warning' | 'default' | 'danger' }
> = {
  in_trip: { label: '今日在途', variant: 'success' },
  pre_trip: { label: '行前准备', variant: 'info' },
  post_trip: { label: '行程回访', variant: 'warning' },
  upcoming: { label: '待出发', variant: 'default' },
  cancelled: { label: '已取消', variant: 'default' },
}

const NOTIFICATION_STATUS: Record<string, { label: string; variant: 'success' | 'danger' | 'warning' | 'default' }> = {
  sent: { label: '已发送', variant: 'success' },
  failed: { label: '发送失败', variant: 'danger' },
  manual_intervention: { label: '待处理', variant: 'danger' },
  retrying: { label: '重试中', variant: 'warning' },
  pending: { label: '待发送', variant: 'warning' },
}

function formatDate(raw: string): string {
  if (!raw) return '-'
  const date = new Date(`${raw.slice(0, 10)}T00:00:00`)
  if (Number.isNaN(date.getTime())) return raw
  return `${date.getMonth() + 1}月${date.getDate()}日`
}

function formatDateTime(raw: string): string {
  if (!raw) return '-'
  const date = new Date(raw)
  if (Number.isNaN(date.getTime())) return raw
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

function weekdayLabel(iso: string): string {
  const date = new Date(`${iso}T00:00:00`)
  if (Number.isNaN(date.getTime())) return ''
  return ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][date.getDay()]
}

export function GuideWorkspace({ onOpenTrip }: Props) {
  const [data, setData] = useState<GuideWorkspaceData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshTick, setRefreshTick] = useState(0)

  useEffect(() => {
    let active = true
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const result = await guideWorkspaceApi.get()
        if (active) setData(result)
      } catch (err) {
        if (active) setError(getErrorMessage(err))
      } finally {
        if (active) setLoading(false)
      }
    }
    void load()
    return () => {
      active = false
    }
  }, [refreshTick])

  const todayText = useMemo(() => {
    if (!data?.today) return ''
    return `${formatDate(data.today)} · ${weekdayLabel(data.today)}`
  }, [data?.today])

  return (
    <PageShell
      title="我的工作台"
      description="今天要跟进的行程、要发的提醒，以及已经发送过的内容。"
      actions={
        <Button
          size="sm"
          variant="secondary"
          loading={loading}
          onClick={() => setRefreshTick((value) => value + 1)}
        >
          <RefreshCw className="h-4 w-4" /> 刷新
        </Button>
      }
    >
      {error ? (
        <div role="alert" className="mb-4 rounded-card border border-danger-200 bg-danger-50 p-4 text-sm text-danger-700">
          {error}
        </div>
      ) : null}

      {loading && !data ? (
        <div className="rounded-card border border-paper-200 bg-white p-10 text-center text-sm text-paper-500">
          正在加载今天的工作台
        </div>
      ) : !data || data.trips.length === 0 ? (
        <div className="rounded-card border border-paper-200 bg-white p-10 text-center">
          <Sun className="mx-auto h-8 w-8 text-pink-400" />
          <p className="mt-3 text-base font-medium text-paper-900">今天还没有分配给你的行程</p>
          <p className="mt-1 text-sm text-paper-500">管理员分配行程后，会出现在这里。</p>
        </div>
      ) : (
        <div className="space-y-5">
          <section className="rounded-panel border border-accent-100 bg-accent-50/55 p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="flex items-center gap-1.5 text-xs font-medium text-accent-700">
                  <CloudSun className="h-3.5 w-3.5" /> 今天 · {todayText}
                </p>
                <h2 className="mt-2 text-xl font-semibold text-paper-900">
                  {data.stats.due_today > 0
                    ? `有 ${data.stats.due_today} 个行程需要你跟进`
                    : `${data.trips.length} 个行程待出发`}
                </h2>
                <p className="mt-1 text-sm leading-6 text-paper-600">
                  打开行程可查看按阶段生成的提醒。确认内容后，再发到本团企业微信群。
                </p>
              </div>
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-pink-50 text-pink-600">
                <Wand2 className="h-4 w-4" />
              </div>
            </div>
          </section>

          <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
            {[
              { label: '负责行程', value: data.stats.assigned_trips },
              { label: '今天要跟进', value: data.stats.due_today, strong: true },
              { label: '群待配置', value: data.stats.group_missing },
              { label: '近 7 天失败', value: data.stats.failed_7d, danger: data.stats.failed_7d > 0 },
            ].map(({ label, value, strong, danger }) => (
              <div key={label} className="rounded-card border border-paper-200 bg-white p-4">
                <p className="text-xs text-paper-500">{label}</p>
                <p
                  className={`mt-2 text-2xl font-semibold tabular-nums ${
                    danger ? 'text-danger-600' : strong ? 'text-accent-700' : 'text-paper-900'
                  }`}
                >
                  {value}
                </p>
              </div>
            ))}
          </div>

          {data.stats.weather_alerts > 0 ? (
            <div className="flex items-start gap-2 rounded-card border border-danger-200 bg-danger-50/70 px-4 py-3 text-sm text-danger-700">
              <CloudSun className="mt-0.5 h-4 w-4 shrink-0" />
              <p>
                有 {data.stats.weather_alerts} 个行程目的地发布天气预警。打开对应行程，可查看游客群通知和内部协同提醒。
              </p>
            </div>
          ) : null}

          {data.stats.group_missing > 0 ? (
            <div className="flex items-start gap-2 rounded-card border border-warning-200 bg-warning-50/70 px-4 py-3 text-sm text-warning-800">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <p>
                有 {data.stats.group_missing} 个行程还没有配置企业微信群，暂时无法发送群提醒。请联系管理员在「群配置」中完成配置。
              </p>
            </div>
          ) : null}

          <section>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-paper-900">我的行程</h2>
              <span className="text-xs text-paper-500">按在途、行前、回访排序</span>
            </div>
            <div className="grid gap-3 lg:grid-cols-2">
              {data.trips.map((trip) => {
                const stage = STAGE_META[trip.stage] ?? STAGE_META.upcoming
                const latest = trip.latest_notification
                return (
                  <article
                    key={trip.id}
                    className="rounded-card border border-paper-200 bg-white p-4 transition-colors hover:border-accent-300"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge variant={stage.variant}>{stage.label}</Badge>
                          {trip.group_configured ? (
                            <Badge variant="success">群已配置</Badge>
                          ) : (
                            <Badge variant="warning">群未配置</Badge>
                          )}
                          <Badge variant={trip.send_mode === 'approval' ? 'info' : 'default'}>
                            {trip.send_mode === 'approval' ? '需我确认' : '自动发送'}
                          </Badge>
                          {trip.weather_warning ? (
                            <Badge variant="danger">天气预警</Badge>
                          ) : null}
                        </div>
                        <h3 className="mt-2 truncate text-base font-semibold text-paper-900">{trip.destination}</h3>
                        <p className="mt-0.5 text-xs text-paper-500">
                          {trip.team_id || '未设置团号'} · {trip.start_date} 至 {trip.end_date} · {trip.participants} 人
                        </p>
                      </div>
                      <span className="shrink-0 rounded-control bg-accent-50 px-2 py-1 text-xs font-medium text-accent-700">
                        {trip.stage_label}
                      </span>
                    </div>

                    {trip.weather_warning ? (
                      <p className="mt-2 rounded-control border border-danger-100 bg-danger-50 px-2.5 py-1.5 text-xs text-danger-700">
                        {trip.weather_warning} · 打开行程可查看天气提醒
                      </p>
                    ) : null}

                    {latest ? (
                      <div className="mt-3 rounded-control bg-paper-50 p-3">
                        <div className="flex flex-wrap items-center gap-2 text-xs text-paper-500">
                          <Badge variant={NOTIFICATION_STATUS[latest.status]?.variant ?? 'default'}>
                            {NOTIFICATION_STATUS[latest.status]?.label ?? latest.status}
                          </Badge>
                          <span>{formatDateTime(latest.created_at)}</span>
                        </div>
                        <p className="mt-1.5 line-clamp-2 text-xs leading-5 text-paper-600">
                          {latest.content || '未记录通知内容'}
                        </p>
                      </div>
                    ) : (
                      <p className="mt-3 rounded-control bg-paper-50 px-3 py-2 text-xs text-paper-500">
                        这个行程还没有发送记录
                      </p>
                    )}

                    <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                      <button
                        type="button"
                        onClick={() => onOpenTrip(trip.id)}
                        className="text-xs font-medium text-paper-500 hover:text-paper-800"
                      >
                        查看行程
                      </button>
                      {trip.stage === 'upcoming' || trip.stage === 'cancelled' ? null : (
                        <Button size="sm" onClick={() => onOpenTrip(trip.id, 'plan')}>
                          <Send className="h-4 w-4" /> {trip.action_label}
                        </Button>
                      )}
                    </div>
                  </article>
                )
              })}
            </div>
          </section>

          <section>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="flex items-center gap-2 text-sm font-semibold text-paper-900">
                <BellRing className="h-4 w-4 text-paper-500" /> 最近发送
              </h2>
              <span className="text-xs text-paper-500">显示最近 {data.recent_notifications.length} 条</span>
            </div>
            {data.recent_notifications.length === 0 ? (
              <div className="rounded-card border border-dashed border-paper-300 bg-white p-6 text-center text-sm text-paper-500">
                还没有发送记录。点开行程生成提醒后，发送结果会出现在这里。
              </div>
            ) : (
              <div className="space-y-2">
                {data.recent_notifications.map((item) => (
                  <article
                    key={item.id}
                    className="rounded-card border border-paper-200 bg-white p-3.5"
                  >
                    <div className="flex flex-wrap items-center gap-2 text-xs text-paper-500">
                      <span className="font-medium text-paper-700">{item.trip_label}</span>
                      <span>{formatDateTime(item.created_at)}</span>
                      <Badge variant={NOTIFICATION_STATUS[item.status]?.variant ?? 'default'}>
                        {NOTIFICATION_STATUS[item.status]?.label ?? item.status}
                      </Badge>
                      <span className="ml-auto">企业微信</span>
                    </div>
                    <p className="mt-1.5 line-clamp-2 whitespace-pre-wrap text-sm leading-6 text-paper-800">
                      {item.content || '未记录通知内容'}
                    </p>
                  </article>
                ))}
              </div>
            )}
          </section>
        </div>
      )}
    </PageShell>
  )
}
