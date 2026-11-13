import { useEffect, useState } from 'react'
import { MessageCircle, Send, Wand2 } from 'lucide-react'
import { Button } from '../Button'
import { Modal } from '../Modal'
import { getErrorMessage, tripReminderApi } from '../../services/api'

interface Props {
  isOpen: boolean
  tripId: string
  tripName: string
  onClose: () => void
  onSent: (message: string, provider: string) => void
  onOpenGroupConfig?: () => void
  initialMessage?: string
}

export function TripGroupReminderModal({
  isOpen,
  tripId,
  tripName,
  onClose,
  onSent,
  onOpenGroupConfig,
  initialMessage = '',
}: Props) {
  const [message, setMessage] = useState('')
  const [provider, setProvider] = useState('')
  const [generating, setGenerating] = useState(false)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!isOpen) return
    setMessage(initialMessage)
    setProvider('')
    setError(null)
  }, [isOpen, initialMessage])

  const generate = async () => {
    setGenerating(true)
    setError(null)
    try {
      const result = await tripReminderApi.previewGroupReminder(tripId, {
        message: message.trim() || undefined,
        scene: '每日行程提醒',
      })
      setMessage(result.message)
      setProvider(result.provider)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setGenerating(false)
    }
  }

  const send = async () => {
    if (!message.trim()) {
      setError('请先输入提醒内容，或点击「生成文案」')
      return
    }
    setSending(true)
    setError(null)
    try {
      const result = await tripReminderApi.sendGroupReminder(tripId, {
        message: message.trim(),
        useAi: false,
      })
      onSent(result.message, result.provider)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setSending(false)
    }
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="提醒游客"
      panelClassName="max-w-2xl"
      footer={
        <div className="flex flex-wrap items-center justify-between gap-3">
          <button
            type="button"
            onClick={() => void generate()}
            disabled={generating || sending}
            className="inline-flex items-center gap-1.5 rounded-control border border-pink-200 bg-pink-50 px-3 py-2 text-sm font-medium text-pink-700 transition-colors hover:bg-pink-100 disabled:opacity-50"
          >
            <Wand2 className="h-4 w-4" />
            {generating ? '生成中…' : message.trim() ? '润色' : '生成文案'}
          </button>
          <div className="flex items-center gap-2">
            <Button variant="secondary" size="sm" onClick={onClose}>
              取消
            </Button>
            <Button size="sm" loading={sending} onClick={() => void send()}>
              <Send className="h-4 w-4" /> 发送到企业微信群
            </Button>
          </div>
        </div>
      }
    >
      <div className="space-y-4">
        <div className="rounded-card border border-accent-100 bg-accent-50/60 p-4">
          <div className="flex items-start gap-2.5">
            <MessageCircle className="mt-0.5 h-4 w-4 shrink-0 text-accent-600" />
            <div>
              <p className="text-sm font-medium text-paper-900">{tripName}</p>
              <p className="mt-1 text-xs leading-5 text-paper-600">
                消息会发送到本团企业微信群，所有群成员可见。留空时，系统会结合当日行程生成一版提醒。
              </p>
            </div>
          </div>
        </div>

        {error ? (
          <div className="rounded-control border border-danger-200 bg-danger-50 px-3 py-2.5 text-sm text-danger-700">
            <p>{error}</p>
            {error.includes('Webhook') && onOpenGroupConfig ? (
              <button
                type="button"
                onClick={onOpenGroupConfig}
                className="mt-1.5 font-medium underline underline-offset-2"
              >
                去群配置填写 Webhook
              </button>
            ) : null}
          </div>
        ) : null}

        <label className="block">
          <span className="mb-1.5 flex items-center justify-between text-sm font-medium text-paper-700">
            <span>群提醒内容</span>
            <span className="text-xs font-normal tabular-nums text-paper-400">
              {message.length} / 2000
            </span>
          </span>
          <textarea
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            maxLength={2000}
            rows={9}
            placeholder="可以自己写，也可以留空后点击「生成文案」，系统会结合当日行程生成提醒。"
            className="w-full resize-y rounded-control border border-paper-300 bg-white px-3 py-2.5 text-sm leading-6 text-paper-900 focus:border-accent-500 focus:outline-none focus:ring-2 focus:ring-accent-100"
          />
        </label>

        {provider ? (
          <p className="text-xs text-paper-500">
            {provider === 'glm'
              ? '已使用 GLM 润色。发送前可以继续手动修改。'
              : '已完成本地润色。配置 GLM_API_KEY 后可使用大模型润色。发送前可以继续手动修改。'}
          </p>
        ) : (
          <p className="text-xs text-paper-500">
            建议语气像管家在群里说话：先说明时间和地点，再提醒注意事项。
          </p>
        )}
      </div>
    </Modal>
  )
}
