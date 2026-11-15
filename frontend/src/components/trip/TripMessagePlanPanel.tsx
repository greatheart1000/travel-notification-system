import { useEffect, useMemo, useState } from 'react'
import {
  AlertTriangle,
  CheckCircle2,
  CloudSun,
  Moon,
  RefreshCw,
  Send,
  Sun,
  Wand2,
} from 'lucide-react'
import { Badge } from '../Badge'
import { Button } from '../Button'
import {
  getErrorMessage,
  tripReminderApi,
  type TripMessagePlan,
  type TripMessagePlanItem,
} from '../../services/api'

interface Props {
  tripId: string
  tripName: string
  destination: string
  onToast: (message: string) => void
  onEdit: (content: string) => void
  onOpenGroupConfig?: () => void
}

const SLOT_ICONS: Record<string, typeof Sun> = {
  morning: Sun,
  afternoon: CloudSun,
  evening: Moon,
}

const STATUS_META: Record<
  string,
  { label: string; variant: 'success' | 'danger' | 'warning' | 'default' | 'info'; item: string }
> = {
  sent: { label: '已发送', variant: 'success', item: 'border-l-success-300' },
  failed: { label: '发送失败', variant: 'danger', item: 'border-l-danger-300' },
  pending: { label: '待发送', variant: 'info', item: 'border-l-accent-300' },
  missed: { label: '已错过', variant: 'warning', item: 'border-l-warning-300' },
}

function dateLabel(iso: string): string {
  const date = new Date(`${iso}T00:00:00`)
  if (Number.isNaN(date.getTime())) return iso
  const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  return `${date.getMonth() + 1}月${date.getDate()}日 · ${weekdays[date.getDay()]}`
}

export function TripMessagePlanPanel({
  tripId,
  tripName,
  destination,
  onToast,
  onEdit,
  onOpenGroupConfig,
}: Props) {
  const [plan, setPlan] = useState<TripMessagePlan | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [sendingId, setSendingId] = useState('')
  const [polishingId, setPolishingId] = useState('')

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await tripReminderApi.getTripMessagePlan(tripId)
      setPlan(result)
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

  const groups = useMemo(() => {
    const map = new Map<string, TripMessagePlanItem[]>()
    for (const item of plan?.items ?? []) {
      const list = map.get(item.date) ?? []
      list.push(item)
      map.set(item.date, list)
    }
    return Array.from(map.entries())
  }, [plan])

  const updateItem = (id: string, patch: Partial<TripMessagePlanItem>) => {
    setPlan((current) =>
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

  const sendItem = async (item: TripMessagePlanItem) => {
    setSendingId(item.id)
    setError(null)
    try {
      await tripReminderApi.sendGroupReminder(tripId, {
        message: item.content,
        useAi: false,
        scene: item.title,
        scheduleKey: item.id,
      })
      updateItem(item.id, { status: 'sent' })
      onToast(`已发送「${item.title}」到「${tripName}」企业微信群`)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setSendingId('')
    }
  }

  const polishItem = async (item: TripMessagePlanItem) => {
    setPolishingId(item.id)
    setError(null)
    try {
      const result = await tripReminderApi.polish({
        content: item.content,
        destination,
        scene: item.title,
      })
      updateItem(item.id, { content: result.content })
      onToast(result.provider === 'glm' ? '已润色这条提醒' : '已按本地规则润色')
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setPolishingId('')
    }
  }

  if (loading && !plan) {
    return (
      <div className="rounded-card border border-paper-200 bg-white p-6 text-center text-sm text-paper-500">
        正在生成行程发送计划
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="rounded-panel border border-paper-200 bg-white p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-paper-900">行程发送计划</h2>
          <p className="mt-1 text-xs leading-5 text-paper-500">
            系统按行前、行中每天早/中/晚和行后自动排好消息。你可以逐条润色、修改，或直接发送到企业微信群。
          </p>
        </div>
        <button
          type="button"
          onClick={() => void load()}
          className="inline-flex items-center gap-1.5 rounded-control px-2.5 py-1.5 text-xs text-paper-500 hover:bg-paper-50 hover:text-paper-900"
        >
          <RefreshCw className="h-3.5 w-3.5" /> 刷新计划
        </button>
        </div>
      </div>

      {plan && !plan.group_configured ? (
        <div className="flex items-start gap-2 rounded-card border border-warning-200 bg-warning-50/70 px-4 py-3 text-sm text-warning-800">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <div>
            <p>本团还没有配置企业微信群，计划可以查看，但发送会失败。</p>
            {onOpenGroupConfig ? (
              <button
                type="button"
                onClick={onOpenGroupConfig}
                className="mt-1 font-medium underline underline-offset-2"
              >
                去群配置填写 Webhook
              </button>
            ) : (
              <p className="mt-1 text-xs">请联系管理员在「群配置」中完成配置。</p>
            )}
          </div>
        </div>
      ) : null}

      {error ? (
        <div className="rounded-card border border-danger-200 bg-danger-50 px-4 py-3 text-sm text-danger-700">
          <p>{error}</p>
          {error.includes('Webhook') && onOpenGroupConfig ? (
            <button
              type="button"
              onClick={onOpenGroupConfig}
              className="mt-1 font-medium underline underline-offset-2"
            >
              去群配置填写 Webhook
            </button>
          ) : null}
        </div>
      ) : null}

      <div className="space-y-5">
        {groups.map(([day, items]) => (
          <section key={day}>
            <div className="mb-2 flex items-center gap-2">
              <span className="flex h-6 items-center rounded-full bg-paper-100 px-2.5 text-xs font-medium text-paper-700">
                {dateLabel(day)}
              </span>
              <span className="text-xs text-paper-400">{items.length} 条</span>
              <span className="h-px flex-1 bg-paper-200" />
            </div>
            <div className="space-y-2">
              {items.map((item) => {
                const Icon = SLOT_ICONS[item.slot] ?? Sun
                const status = STATUS_META[item.status] ?? STATUS_META.pending
                return (
                  <article
                    key={item.id}
                    className={`rounded-card border border-l-4 border-paper-200 bg-white p-3.5 sm:p-4 ${status.item}`}
                  >
                    <div className="flex gap-3">
                      <div className="flex w-14 shrink-0 flex-col items-center">
                        <span className="flex h-8 w-8 items-center justify-center rounded-full bg-paper-100 text-paper-600">
                          <Icon className="h-4 w-4" />
                        </span>
                        <span className="mt-1.5 text-xs font-medium tabular-nums text-paper-600">
                          {item.time}
                        </span>
                        <span className="mt-0.5 text-xs text-paper-400">{item.slot_label}</span>
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <h4 className="text-sm font-medium text-paper-900">{item.title}</h4>
                          <Badge variant={status.variant}>{status.label}</Badge>
                          <span className="text-xs text-paper-400">{item.stage_label}</span>
                        </div>
                        <pre className="mt-2 max-h-36 overflow-y-auto whitespace-pre-wrap rounded-control bg-paper-50 p-3 font-sans text-sm leading-6 text-paper-800">
                          {item.content}
                        </pre>
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
                          <Button size="sm" variant="secondary" onClick={() => onEdit(item.content)}>
                            修改后发送
                          </Button>
                          <Button
                            size="sm"
                            loading={sendingId === item.id}
                            disabled={!item.can_send}
                            onClick={() => void sendItem(item)}
                          >
                            {item.status === 'sent' ? (
                              <CheckCircle2 className="h-4 w-4" />
                            ) : (
                              <Send className="h-4 w-4" />
                            )}
                            {item.status === 'sent' ? '再次发送' : '发送到群'}
                          </Button>
                        </div>
                      </div>
                    </div>
                  </article>
                )
              })}
            </div>
          </section>
        ))}
      </div>
    </div>
  )
}
