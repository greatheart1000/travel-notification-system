import { useEffect, useMemo, useState } from 'react'
import {
  AlertTriangle,
  ArrowUpRight,
  BellRing,
  CalendarDays,
  RefreshCw,
  Send,
  UsersRound,
} from 'lucide-react'
import { PageShell } from '../components/PageShell'
import { Badge } from '../components/Badge'
import { Button } from '../components/Button'
import { getErrorMessage, tripReminderApi } from '../services/api'
import {
  teamOverviewApi,
  type TeamMemberOverview,
  type TeamNotificationSummary,
  type TeamOverview,
  type TeamTripSummary,
} from '../services/commercialApi'

interface Props {
  onOpenTrip: (tripId: string, tab?: string) => void
}

const ROLE_LABELS: Record<string, string> = {
  guide: '导游',
  user: '成员',
  concierge: '管家',
  ops: '运营',
  cs: '客服',
  sales: '销售',
}

const TRIP_STATUS_LABELS: Record<string, string> = {
  planned: '待出发',
  in_progress: '进行中',
  completed: '已结束',
  cancelled: '已取消',
}

const CHANNEL_LABELS: Record<string, string> = {
  wechat_work_group: '企业微信',
  sms: '短信',
  email: '邮件',
}

const NOTIFICATION_STATUS_LABELS: Record<string, string> = {
  sent: '已发送',
  failed: '失败',
  pending: '待发送',
  retrying: '重试中',
  manual_intervention: '待人工处理',
}

function formatDateTime(raw: string): string {
  if (!raw) return '-'
  const date = new Date(raw)
  return Number.isNaN(date.getTime())
    ? raw
    : date.toLocaleString('zh-CN', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
      })
}

function displayName(member: { username: string; display_name?: string }): string {
  return member.display_name || member.username
}

function initials(name: string): string {
  return name.trim().slice(0, 2).toUpperCase() || '成'
}

function statusBadgeVariant(status: string): 'success' | 'warning' | 'danger' | 'default' | 'info' {
  if (status === 'sent') return 'success'
  if (status === 'failed' || status === 'manual_intervention') return 'danger'
  if (status === 'retrying' || status === 'pending') return 'warning'
  return 'default'
}

function TripCard({
  trip,
  onOpen,
}: {
  trip: TeamTripSummary
  onOpen: (tripId: string) => void
}) {
  return (
    <button
      type="button"
      onClick={() => onOpen(trip.id)}
      className="group w-full rounded-card border border-paper-200 bg-white p-4 text-left transition-colors hover:border-accent-300"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-paper-900">{trip.destination}</p>
          <p className="mt-0.5 text-xs text-paper-500">{trip.team_id || '未设置团号'}</p>
        </div>
        <ArrowUpRight className="h-4 w-4 shrink-0 text-paper-400 transition-colors group-hover:text-accent-600" />
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-xs text-paper-600">
        <span className="inline-flex items-center gap-1">
          <CalendarDays className="h-3.5 w-3.5 text-paper-400" />
          {trip.start_date || '-'} 至 {trip.end_date || '-'}
        </span>
        <span>{trip.participants} 人</span>
        <span>{TRIP_STATUS_LABELS[trip.status] ?? trip.status}</span>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        {trip.webhook_configured ? (
          <Badge variant="success">企业微信群已配置</Badge>
        ) : (
          <Badge variant="warning">未配置企业微信群</Badge>
        )}
        <Badge variant={trip.send_mode === 'approval' ? 'info' : 'default'}>
          {trip.send_mode === 'approval' ? '需确认发送' : '自动发送'}
        </Badge>
      </div>
    </button>
  )
}

function MemberPanel({
  member,
  onOpenTrip,
  onResend,
  resendingId,
}: {
  member: TeamMemberOverview
  onOpenTrip: (tripId: string) => void
  onResend: (notification: TeamNotificationSummary) => void
  resendingId: string
}) {
  return (
    <div className="space-y-5">
      <div className="rounded-panel border border-paper-200 bg-white p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-accent-50 text-sm font-semibold text-accent-800">
              {initials(displayName(member))}
            </div>
            <div className="min-w-0">
              <h2 className="truncate text-lg font-semibold text-paper-900">{displayName(member)}</h2>
              <p className="mt-0.5 text-sm text-paper-500">
                {ROLE_LABELS[member.role] ?? member.role}
                {member.phone ? ` · ${member.phone}` : ''}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-4 text-sm">
            <div>
              <p className="text-xs text-paper-500">负责行程</p>
              <p className="mt-0.5 text-xl font-semibold tabular-nums text-paper-900">
                {member.assigned_trips.length}
              </p>
            </div>
            <div>
              <p className="text-xs text-paper-500">通知记录</p>
              <p className="mt-0.5 text-xl font-semibold tabular-nums text-paper-900">
                {member.notification_count}
              </p>
            </div>
            <Badge variant={member.status === 'disabled' ? 'default' : 'success'}>
              {member.status === 'disabled' ? '已停用' : '启用中'}
            </Badge>
          </div>
        </div>
      </div>

      <div>
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-paper-900">负责的旅行团</h3>
          <span className="text-xs text-paper-500">点击行程查看通知配置与执行</span>
        </div>
        {member.assigned_trips.length > 0 ? (
          <div className="grid gap-3 md:grid-cols-2">
            {member.assigned_trips.map((trip) => (
              <TripCard key={trip.id} trip={trip} onOpen={onOpenTrip} />
            ))}
          </div>
        ) : (
          <div className="rounded-card border border-dashed border-paper-300 bg-white p-6 text-center text-sm text-paper-500">
            还没有分配行程。可在行程详情「人员配置」中分配。
          </div>
        )}
      </div>

      <div>
        <div className="mb-3 flex items-center justify-between">
          <h3 className="flex items-center gap-2 text-sm font-semibold text-paper-900">
            <BellRing className="h-4 w-4 text-paper-500" />
            该导游负责行程的通知内容
          </h3>
          <span className="text-xs text-paper-500">
            共 {member.notification_count} 条，显示最近 {member.recent_notifications.length} 条
          </span>
        </div>
        {member.recent_notifications.length > 0 ? (
          <div className="space-y-3">
            {member.recent_notifications.map((notification) => (
              <article
                key={notification.id || `${notification.trip_id}-${notification.created_at}`}
                className="rounded-card border border-paper-200 bg-white p-4"
              >
                <div className="flex flex-wrap items-center gap-2 text-xs text-paper-500">
                  <span className="font-medium text-paper-700">
                    {notification.trip_label || notification.trip_id || '未关联行程'}
                  </span>
                  <span>·</span>
                  <span>{formatDateTime(notification.created_at)}</span>
                  <Badge variant="info">{CHANNEL_LABELS[notification.channel] ?? notification.channel}</Badge>
                  <Badge variant={statusBadgeVariant(notification.status)}>
                    {NOTIFICATION_STATUS_LABELS[notification.status] ?? notification.status}
                  </Badge>
                  <span>对象：{notification.customer_name || '群成员'}</span>
                  <span className="ml-auto">发送人：{notification.operator_name || '系统自动'}</span>
                </div>
                <pre className="mt-3 max-h-44 overflow-y-auto whitespace-pre-wrap rounded-control bg-paper-50 p-3 font-sans text-sm leading-6 text-paper-800">
                  {notification.content || '未记录通知内容（历史数据）'}
                </pre>
                {notification.status !== 'sent' && notification.channel === 'wechat_work_group' && notification.content ? (
                  <div className="mt-2 flex justify-end">
                    <button
                      type="button"
                      onClick={() => onResend(notification)}
                      disabled={resendingId === notification.id}
                      className="inline-flex items-center gap-1.5 rounded-control border border-accent-200 bg-accent-50 px-2.5 py-1.5 text-xs font-medium text-accent-700 hover:bg-accent-100 disabled:opacity-50"
                    >
                      <Send className="h-3.5 w-3.5" />
                      {resendingId === notification.id ? '重发中…' : '重发到群'}
                    </button>
                  </div>
                ) : null}
              </article>
            ))}
          </div>
        ) : (
          <div className="rounded-card border border-dashed border-paper-300 bg-white p-6 text-center text-sm text-paper-500">
            该导游负责的行程还没有发送记录，发送后会在这里显示具体内容。
          </div>
        )}
      </div>
    </div>
  )
}

export function TeamExecution({ onOpenTrip }: Props) {
  const [overview, setOverview] = useState<TeamOverview | null>(null)
  const [selectedId, setSelectedId] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshTick, setRefreshTick] = useState(0)
  const [notice, setNotice] = useState<string | null>(null)
  const [resendingId, setResendingId] = useState('')

  useEffect(() => {
    let active = true
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const data = await teamOverviewApi.get()
        if (!active) return
        setOverview(data)
        setSelectedId((current) => {
          if (current && data.members.some((member) => member.id === current)) {
            return current
          }
          const firstWithTrips = [...data.members].sort(
            (left, right) =>
              right.assigned_trips.length - left.assigned_trips.length ||
              right.notification_count - left.notification_count,
          )[0]
          return firstWithTrips?.id ?? data.members[0]?.id ?? ''
        })
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

  const selectedMember = useMemo(
    () => overview?.members.find((member) => member.id === selectedId) ?? null,
    [overview, selectedId],
  )

  const resendNotification = async (notification: {
    id: string
    trip_id: string
    trip_label: string
    content: string
  }) => {
    if (!notification.trip_id || !notification.content) return
    if (!window.confirm(`重新发送到「${notification.trip_label || notification.trip_id}」的企业微信群？`)) {
      return
    }
    setResendingId(notification.id)
    setError(null)
    setNotice(null)
    try {
      await tripReminderApi.sendGroupReminder(notification.trip_id, {
        message: notification.content,
        useAi: false,
        scene: '失败通知重发',
      })
      setNotice('已重新发送到企业微信群')
      setRefreshTick((value) => value + 1)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setResendingId('')
    }
  }

  return (
    <PageShell
      title="团队执行"
      description="查看每位导游负责的旅行团、实际发送的通知内容和触达状态。"
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
      {notice ? (
        <div className="mb-4 rounded-card border border-success-200 bg-success-50 p-4 text-sm text-success-700">
          {notice}
        </div>
      ) : null}
      {loading ? (
        <div className="rounded-card border border-paper-200 bg-white p-10 text-center text-sm text-paper-500">
          正在加载团队执行数据
        </div>
      ) : !overview || overview.members.length === 0 ? (
        <div className="rounded-card border border-paper-200 bg-white p-10 text-center">
          <UsersRound className="mx-auto h-7 w-7 text-paper-400" />
          <p className="mt-3 text-base font-medium text-paper-900">还没有团队成员</p>
          <p className="mt-1 text-sm text-paper-500">先在「团队成员」中创建导游账号，再分配行程。</p>
        </div>
      ) : (
        <div className="space-y-5">
          <div className="grid grid-cols-2 gap-3 xl:grid-cols-5">
            {[
              { label: '团队成员', value: overview.stats.members },
              { label: '已分配行程', value: overview.stats.assigned_trips },
              { label: '未分配行程', value: overview.stats.unassigned_trips },
              {
                label: '7 日通知',
                value: overview.stats.notifications_7d,
                hint: overview.stats.failed_7d > 0 ? `失败 ${overview.stats.failed_7d}` : '全部正常',
                hintDanger: overview.stats.failed_7d > 0,
              },
              { label: '未配置群', value: overview.stats.trips_without_group },
            ].map(({ label, value, hint, hintDanger }) => (
              <div key={label} className="rounded-card border border-paper-200 bg-white p-4">
                <p className="text-xs text-paper-500">{label}</p>
                <p className="mt-2 text-2xl font-semibold tabular-nums text-paper-900">{value}</p>
                {hint ? (
                  <p className={`mt-1 text-xs ${hintDanger ? 'text-danger-600' : 'text-paper-500'}`}>{hint}</p>
                ) : null}
              </div>
            ))}
          </div>

          {overview.stats.failed_7d > 0 ? (
            <div className="flex items-start gap-2.5 rounded-card border border-danger-200 bg-danger-50/70 px-4 py-3 text-sm text-danger-700">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <p>
                最近 7 天有 {overview.stats.failed_7d} 条通知发送失败。可在下方导游通知内容中查看原文并「重发到群」。
              </p>
            </div>
          ) : null}

          {overview.trips_without_group.length > 0 ? (
            <div className="rounded-card border border-warning-200 bg-warning-50/70 p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-start gap-2 text-sm font-medium text-warning-800">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                  有 {overview.trips_without_group.length} 个行程未配置企业微信群，自动提醒和手动群提醒都无法送达
                </div>
                <span className="text-xs text-warning-700">点击行程完成群配置</span>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {overview.trips_without_group.slice(0, 6).map((trip) => (
                  <button
                    key={trip.id}
                    type="button"
                    onClick={() => onOpenTrip(trip.id, 'wecom')}
                    className="inline-flex items-center gap-1.5 rounded-control border border-warning-200 bg-white px-3 py-1.5 text-xs text-paper-700 hover:border-warning-300"
                  >
                    {trip.destination}
                    <ArrowUpRight className="h-3.5 w-3.5 text-warning-600" />
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          <div className="grid gap-5 xl:grid-cols-[300px_minmax(0,1fr)]">
            <div className="rounded-card border border-paper-200 bg-white p-3">
              <div className="px-2 py-2">
                <h2 className="text-sm font-semibold text-paper-900">导游与成员</h2>
                <p className="mt-0.5 text-xs text-paper-500">按负责行程查看通知内容</p>
              </div>
              <div className="mt-1 grid grid-cols-2 gap-1 sm:grid-cols-3 xl:grid-cols-1">
                {overview.members.map((member) => {
                  const active = member.id === selectedId
                  return (
                    <button
                      key={member.id}
                      type="button"
                      onClick={() => setSelectedId(member.id)}
                      className={`flex w-full items-center gap-3 rounded-control px-3 py-3 text-left transition-colors ${
                        active
                          ? 'bg-accent-50 text-accent-900'
                          : 'text-paper-700 hover:bg-paper-50'
                      }`}
                    >
                      <span
                        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
                          active
                            ? 'bg-accent-100 text-accent-800'
                            : 'bg-paper-100 text-paper-600'
                        }`}
                      >
                        {initials(displayName(member))}
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-medium">{displayName(member)}</span>
                        <span className="block text-xs text-paper-500">
                          {member.assigned_trips.length} 个团 · {member.notification_count} 条通知
                        </span>
                      </span>
                    </button>
                  )
                })}
              </div>
            </div>

            {selectedMember ? (
              <MemberPanel
                member={selectedMember}
                onOpenTrip={onOpenTrip}
                onResend={resendNotification}
                resendingId={resendingId}
              />
            ) : (
              <div className="rounded-card border border-paper-200 bg-white p-8 text-center text-sm text-paper-500">
                请选择一位导游
              </div>
            )}
          </div>

          {overview.unassigned_trips.length > 0 ? (
            <div className="rounded-card border border-warning-200 bg-warning-50/60 p-4">
              <div className="flex items-center gap-2 text-sm font-medium text-warning-800">
                <AlertTriangle className="h-4 w-4" />
                还有 {overview.unassigned_trips.length} 个行程没有分配给导游
              </div>
              <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
                {overview.unassigned_trips.slice(0, 6).map((trip) => {
                  const latest = overview.recent_notifications.find(
                    (notification) => notification.trip_id === trip.id,
                  )
                  return (
                    <button
                      key={trip.id}
                      type="button"
                      onClick={() => onOpenTrip(trip.id, 'staff')}
                      className="flex items-start justify-between gap-3 rounded-control border border-warning-200 bg-white px-3 py-2.5 text-left text-sm hover:border-warning-300"
                    >
                      <span className="min-w-0">
                        <span className="block truncate font-medium text-paper-900">{trip.destination}</span>
                        <span className="block text-xs text-paper-500">
                          {trip.start_date} 至 {trip.end_date}
                        </span>
                        {latest?.content ? (
                          <span className="mt-1 block line-clamp-2 text-xs leading-5 text-paper-600">
                            {latest.content}
                          </span>
                        ) : null}
                      </span>
                      <ArrowUpRight className="mt-0.5 h-4 w-4 shrink-0 text-warning-600" />
                    </button>
                  )
                })}
              </div>
            </div>
          ) : null}
        </div>
      )}
    </PageShell>
  )
}
