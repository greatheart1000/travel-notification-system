import { useEffect, useState } from 'react'
import { Check, CloudLightning, Copy, RefreshCw, Send, Wand2 } from 'lucide-react'
import { Button } from '../Button'
import { getErrorMessage, tripReminderApi, type ReminderSuggestion } from '../../services/api'

interface Props {
  tripId: string
  tripName: string
  onSent: (message: string) => void
  onEdit: (content: string) => void
  onOpenGroupConfig?: () => void
}

export function SmartReminderCard({
  tripId,
  tripName,
  onSent,
  onEdit,
  onOpenGroupConfig,
}: Props) {
  const [suggestion, setSuggestion] = useState<ReminderSuggestion | null>(null)
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sent, setSent] = useState(false)
  const [activeVariant, setActiveVariant] = useState('tourist')
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    let active = true
    const load = async () => {
      setLoading(true)
      setError(null)
      setSent(false)
      try {
        const result = await tripReminderApi.getReminderSuggestion(tripId)
        if (active) {
          setSuggestion(result.suggestion)
          setActiveVariant(result.suggestion?.variants?.[0]?.key ?? 'tourist')
        }
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
  }, [tripId])

  const regenerate = async () => {
    const result = await tripReminderApi.getReminderSuggestion(tripId)
    setSuggestion(result.suggestion)
    setActiveVariant(result.suggestion?.variants?.[0]?.key ?? 'tourist')
    setSent(false)
  }

  const variants = suggestion?.variants?.length
    ? suggestion.variants
    : suggestion
      ? [{ key: 'tourist', title: '提醒内容', audience: '游客群', content: suggestion.content }]
      : []
  const active = variants.find((variant) => variant.key === activeVariant) ?? variants[0]
  const isWeatherAgent = suggestion?.situation === 'weather_alert' && variants.length > 1

  const copyInternal = async () => {
    if (!active) return
    await navigator.clipboard.writeText(active.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const approveAndSend = async () => {
    if (!suggestion) return
    setSending(true)
    setError(null)
    try {
      await tripReminderApi.sendGroupReminder(tripId, {
        message: suggestion.content,
        useAi: false,
        scene: suggestion.title,
      })
      setSent(true)
      onSent(`已发送提醒到「${tripName}」企业微信群`)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setSending(false)
    }
  }

  if (loading) {
    return (
      <div className="mb-4 flex items-center gap-2 rounded-card border border-paper-200 bg-white px-4 py-3 text-sm text-paper-500">
        <Wand2 className="h-4 w-4 text-pink-500" />
        正在查看行程和天气…
      </div>
    )
  }

  if (error && !suggestion) {
    return (
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2 rounded-card border border-paper-200 bg-white px-4 py-3 text-sm text-paper-500">
        <span>提醒建议暂时不可用：{error}</span>
        <button
          type="button"
          onClick={() => void regenerate()}
          className="inline-flex items-center gap-1.5 text-accent-700 hover:text-accent-800"
        >
          <RefreshCw className="h-3.5 w-3.5" /> 重试
        </button>
      </div>
    )
  }

  if (!suggestion) return null

  return (
    <section className="mb-4 rounded-card border border-paper-200 bg-white">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-paper-100 px-4 py-3">
        <div className="flex min-w-0 items-start gap-2.5">
          <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-pink-50 text-pink-600">
            {isWeatherAgent ? <CloudLightning className="h-4 w-4" /> : <Wand2 className="h-4 w-4" />}
          </span>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-sm font-semibold text-paper-900">
                {isWeatherAgent ? suggestion.title : `提醒建议 · ${suggestion.title}`}
              </h3>
              <span className="rounded-control bg-paper-100 px-2 py-0.5 text-xs text-paper-600">
                {suggestion.reason}
              </span>
            </div>
            <p className="mt-1 text-xs text-paper-500">
              {isWeatherAgent
                ? `已识别天气突发情况，自动生成 ${variants.length} 条消息：游客群通知和内部协同提醒。你确认后再发送。`
                : '系统根据行程阶段、目的地和天气自动生成。你确认内容后再发送到企业微信群。'}
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => void regenerate()}
          className="inline-flex items-center gap-1 rounded-control px-2 py-1 text-xs text-paper-500 transition-colors hover:bg-paper-50 hover:text-paper-800"
        >
          <RefreshCw className="h-3.5 w-3.5" /> 重新生成
        </button>
      </div>

      <div className="px-4 py-3">
        {variants.length > 1 ? (
          <div className="mb-3 flex flex-wrap gap-1 rounded-control bg-paper-50 p-1">
            {variants.map((variant) => (
              <button
                key={variant.key}
                type="button"
                onClick={() => {
                  setActiveVariant(variant.key)
                  setCopied(false)
                }}
                className={`rounded-control px-3 py-1.5 text-xs font-medium transition-colors ${
                  active?.key === variant.key
                    ? 'bg-white text-accent-800 shadow-sm'
                    : 'text-paper-500 hover:text-paper-800'
                }`}
              >
                {variant.title}
                <span className="ml-1 font-normal text-paper-400">· {variant.audience}</span>
              </button>
            ))}
          </div>
        ) : null}
        {error ? (
          <div className="mb-3 rounded-control border border-danger-200 bg-danger-50 px-3 py-2 text-sm text-danger-700">
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
        {sent ? (
          <div className="mb-3 rounded-control border border-success-200 bg-success-50 px-3 py-2 text-sm text-success-700">
            已发送到「{tripName}」企业微信群。
          </div>
        ) : null}
        <pre className="max-h-52 overflow-y-auto whitespace-pre-wrap rounded-control bg-paper-50 p-3 font-sans text-sm leading-6 text-paper-800">
          {active?.content ?? suggestion.content}
        </pre>
        {suggestion.suggested_actions?.length ? (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {suggestion.suggested_actions.map((action) => (
              <span
                key={action}
                className="rounded-control bg-paper-50 px-2 py-1 text-xs text-paper-600"
              >
                {action}
              </span>
            ))}
          </div>
        ) : null}
        <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
          <span className="text-xs text-paper-500">
            {suggestion.provider === 'glm' ? '已使用 GLM 生成' : '已按本地规则整理'}
          </span>
          {active?.key === 'tourist' ? (
            <div className="flex flex-wrap items-center gap-2">
              <Button size="sm" variant="secondary" onClick={() => onEdit(active.content)}>
                修改后发送
              </Button>
              <Button size="sm" loading={sending} onClick={() => void approveAndSend()}>
                <Send className="h-4 w-4" /> 确认发送
              </Button>
            </div>
          ) : (
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs text-paper-500">内部消息不会发送到游客群</span>
              <Button size="sm" variant="secondary" onClick={() => void copyInternal()}>
                {copied ? <Check className="h-4 w-4 text-success-600" /> : <Copy className="h-4 w-4" />}
                {copied ? '已复制' : '复制内部提醒'}
              </Button>
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
