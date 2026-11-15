import { useEffect, useMemo, useState } from 'react'
import {
  AlertTriangle,
  CarFront,
  CheckCircle2,
  ConciergeBell,
  RefreshCw,
  Send,
  UserRoundCog,
  Wand2,
} from 'lucide-react'
import { Badge } from '../Badge'
import { Button } from '../Button'
import {
  getErrorMessage,
  tripReminderApi,
  type StaffMessageItem,
  type StaffMessagesResult,
} from '../../services/api'

interface Props {
  tripId: string
  destination: string
  canSend: boolean
  onToast: (message: string) => void
  onOpenStaffConfig?: () => void
  onOpenGroupConfig?: () => void
}

const ROLE_ORDER = ['manager', 'concierge', 'driver']

const ROLE_META: Record<
  string,
  { label: string; hint: string; icon: typeof UserRoundCog; dot: string }
> = {
  manager: {
    label: '团期负责人',
    hint: '统筹行程、处理调整与突发情况',
    icon: UserRoundCog,
    dot: 'bg-accent-500',
  },
  concierge: {
    label: '旅行管家',
    hint: '陪伴游客、讲解与生活提醒',
    icon: ConciergeBell,
    dot: 'bg-pink-400',
  },
  driver: {
    label: '司机',
    hint: '用车安全、路况与集合提醒',
    icon: CarFront,
    dot: 'bg-success-500',
  },
}

const STATUS_META = {
  sent: { label: '已发送', variant: 'success' as const },
  failed: { label: '发送失败', variant: 'danger' as const },
  pending: { label: '待发送', variant: 'info' as const },
}

export function TripStaffMessagesPanel({
  tripId,
  destination,
  canSend,
  onToast,
  onOpenStaffConfig,
  onOpenGroupConfig,
}: Props) {
  const [data, setData] = useState<StaffMessagesResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [sendingId, setSendingId] = useState('')
  const [polishingId, setPolishingId] = useState('')
  const [editingId, setEditingId] = useState('')
  const [drafts, setDrafts] = useState<Record<string, string>>({})

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await tripReminderApi.getStaffMessages(tripId)
      setData(result)
      setDrafts(
        Object.fromEntries(result.items.map((item) => [item.id, item.content])),
      )
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tripId])

  const roleGroups = useMemo(() => {
    const groups = new Map<string, StaffMessageItem[]>()
    for (const item of data?.items ?? []) {
      const list = groups.get(item.role) ?? []
      list.push(item)
      groups.set(item.role, list)
    }
    return ROLE_ORDER.filter((role) => groups.has(role)).map(
      (role) => [role, groups.get(role) ?? []] as const,
    )
  }, [data])

  const updateItem = (id: string, patch: Partial<StaffMessageItem>) => {
    setData((current) =>
      current
        ? {
            ...current,
            items: current.items.map((item) =>
              item.id === id ? { ...item, ...patch } : item,
            ),
          }
        : current,
    )
  }

  const sendItem = async (item: StaffMessageItem) => {
    setSendingId(item.id)
    setError(null)
    try {
      const content = drafts[item.id] ?? item.content
      const result = await tripReminderApi.sendStaffMessage(tripId, item.role, {
        slot: item.slot,
        content,
      })
      updateItem(item.id, { status: 'sent', content: result.content })
      setDrafts((current) => ({ ...current, [item.id]: result.content }))
      setEditingId('')
      onToast(result.message)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setSendingId('')
    }
  }

  const polishItem = async (item: StaffMessageItem) => {
    setPolishingId(item.id)
    setError(null)
    try {
      const result = await tripReminderApi.polish({
        content: drafts[item.id] ?? item.content,
        destination,
        scene: item.title,
      })
      setDrafts((current) => ({ ...current, [item.id]: result.content }))
      updateItem(item.id, { content: result.content })
      setEditingId(item.id)
      onToast(result.provider === 'glm' ? '已润色这条岗位消息' : '已按本地规则润色')
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setPolishingId('')
    }
  }

  return (
    <section className="space-y-3">
      <div className="rounded-panel border border-paper-200 bg-white p-4">
        <div>
          <h2 className="text-sm font-semibold text-paper-900">分岗位消息</h2>
          <p className="mt-1 text-xs leading-5 text-paper-500">
            团期负责人（司导）、旅行管家、司机三条线独立发送。默认发到本团企业微信群；也可在人员配置里给某个岗位单独配置群或手机号。
          </p>
        </div>
        <button
          type="button"
          onClick={() => void load()}
          disabled={loading}
          className="inline-flex items-center gap-1.5 rounded-control px-2.5 py-1.5 text-xs text-paper-500 hover:bg-paper-50 hover:text-paper-900 disabled:opacity-50"
        >
          <RefreshCw className="h-3.5 w-3.5" /> 刷新
        </button>
      </div>

      {data && !data.group_configured ? (
        <div className="flex items-start gap-2 rounded-card border border-warning-200 bg-warning-50/70 px-4 py-3 text-sm text-warning-800">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <div>
            <p>本团还没有配置企业微信群。若岗位没有单独的接收群或手机号，发送会失败。</p>
            {onOpenGroupConfig ? (
              <button
                type="button"
                onClick={onOpenGroupConfig}
                className="mt-1 font-medium underline underline-offset-2"
              >
                去群配置填写 Webhook
              </button>
            ) : null}
          </div>
        </div>
      ) : null}

      {error ? (
        <div className="rounded-card border border-danger-200 bg-danger-50 px-4 py-3 text-sm text-danger-700">
          {error}
        </div>
      ) : null}

      {loading && !data ? (
        <div className="rounded-card border border-paper-200 bg-white p-6 text-center text-sm text-paper-500">
          正在生成分岗位消息
        </div>
      ) : null}

      {roleGroups.map(([role, items]) => {
        const meta = ROLE_META[role] ?? {
          label: items[0]?.role_label || role,
          hint: '',
          icon: UserRoundCog,
          dot: 'bg-paper-400',
        }
        const Icon = meta.icon
        const first = items[0]
        return (
          <article
            key={role}
            className="rounded-card border border-paper-200 bg-white p-4"
          >
            <div className="flex flex-wrap items-start justify-between gap-2 border-b border-paper-100 pb-3">
              <div className="flex items-start gap-2.5">
                <span className="mt-0.5 flex h-8 w-8 items-center justify-center rounded-full bg-paper-100 text-paper-600">
                  <Icon className="h-4 w-4" />
                </span>
                <div>
                  <h3 className="flex items-center gap-2 text-sm font-semibold text-paper-900">
                    <span className={`h-1.5 w-1.5 rounded-full ${meta.dot}`} />
                    {meta.label}
                    {first?.name ? (
                      <span className="ml-2 font-normal text-paper-500">{first.name}</span>
                    ) : null}
                  </h3>
                  <p className="mt-0.5 text-xs text-paper-500">{meta.hint}</p>
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-1.5 text-xs text-paper-500">
                {first?.recipient_label ? <span>{first.recipient_label}</span> : null}
                <Badge variant="default">{first?.channel_label || '企业微信'}</Badge>
                {onOpenStaffConfig ? (
                  <button
                    type="button"
                    onClick={onOpenStaffConfig}
                    className="text-xs font-medium text-accent-700 hover:underline"
                  >
                    配置岗位接收人
                  </button>
                ) : null}
              </div>
            </div>

            <div className="mt-3 space-y-2">
              {items.map((item) => {
                const status = STATUS_META[item.status] ?? STATUS_META.pending
                const editing = editingId === item.id
                const draft = drafts[item.id] ?? item.content
                return (
                  <div key={item.id} className="rounded-control bg-paper-50 p-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-xs font-medium text-paper-800">{item.slot_label}</span>
                      <span className="text-xs tabular-nums text-paper-400">{item.time}</span>
                      <Badge variant={status.variant}>{status.label}</Badge>
                      {!draft.trim() ? (
                        <span className="text-xs text-warning-700">模板缺失，请手动填写</span>
                      ) : null}
                    </div>

                    {editing ? (
                      <textarea
                        value={draft}
                        onChange={(event) =>
                          setDrafts((current) => ({
                            ...current,
                            [item.id]: event.target.value,
                          }))
                        }
                        rows={6}
                        className="mt-2 w-full rounded-control border border-paper-300 bg-white px-3 py-2 text-sm leading-6 text-paper-800 focus:border-accent-400 focus:outline-none focus:ring-2 focus:ring-accent-100"
                        placeholder="填写这条岗位消息的内容"
                      />
                    ) : (
                      <p className="mt-2 line-clamp-3 whitespace-pre-wrap text-sm leading-6 text-paper-700">
                        {draft || '暂无内容'}
                      </p>
                    )}

                    <div className="mt-2 flex flex-wrap items-center justify-end gap-2">
                      <button
                        type="button"
                        onClick={() => void polishItem(item)}
                        disabled={polishingId === item.id}
                        className="inline-flex items-center gap-1.5 rounded-control border border-pink-200 bg-pink-50 px-2.5 py-1.5 text-xs font-medium text-pink-700 hover:bg-pink-100 disabled:opacity-50"
                      >
                        <Wand2 className="h-3.5 w-3.5" />
                        {polishingId === item.id ? '润色中…' : '润色'}
                      </button>
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => setEditingId(editing ? '' : item.id)}
                      >
                        {editing ? '收起' : '编辑'}
                      </Button>
                      <Button
                        size="sm"
                        loading={sendingId === item.id}
                        disabled={!canSend || !draft.trim()}
                        onClick={() => void sendItem(item)}
                      >
                        {item.status === 'sent' ? (
                          <CheckCircle2 className="h-4 w-4" />
                        ) : (
                          <Send className="h-4 w-4" />
                        )}
                        {item.status === 'sent' ? '再次发送' : '单独发送'}
                      </Button>
                    </div>
                  </div>
                )
              })}
            </div>
          </article>
        )
      })}

      {!loading && data && data.items.length === 0 ? (
        <div className="rounded-card border border-dashed border-paper-300 bg-white p-6 text-center text-sm text-paper-500">
          今天还没有可发送的分岗位话术。
        </div>
      ) : null}
    </section>
  )
}
