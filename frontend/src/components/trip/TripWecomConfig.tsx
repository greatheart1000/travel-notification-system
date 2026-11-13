import { useEffect, useState } from 'react'
import { CheckCircle, Info, Link, Save, Send } from 'lucide-react'
import { Button } from '../Button'
import { wecomApi, tripsApi } from '../../services/api'
import type { Trip } from '../../types/api'

interface Props {
  tripId: string
  readOnly?: boolean
}

export function TripWecomConfig({ tripId, readOnly = false }: Props) {
  const [trip, setTrip] = useState<Trip | null>(null)
  const [webhookUrl, setWebhookUrl] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [message, setMessage] = useState<{ text: string; ok: boolean } | null>(null)

  useEffect(() => {
    ;(async () => {
      setLoading(true)
      try {
        const t = await tripsApi.get(tripId)
        setTrip(t)
        setWebhookUrl(t.webhookUrl || '')
      } catch { /* ignore */ }
      finally { setLoading(false) }
    })()
  }, [tripId])

  const showMsg = (text: string, ok = true) => {
    setMessage({ text, ok })
    setTimeout(() => setMessage(null), 5000)
  }

  const handleSaveWebhook = async () => {
    const trimmed = webhookUrl.trim()
    if (!trimmed) {
      showMsg('请输入 webhook 地址', false)
      return
    }
    if (!trimmed.startsWith('https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=')) {
      showMsg('webhook 地址格式不正确，应以 https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key= 开头', false)
      return
    }
    setSaving(true)
    try {
      await wecomApi.setWebhook(tripId, trimmed)
      showMsg('企业微信群 webhook 已保存')
      setTrip((prev: Trip | null) => prev ? { ...prev, webhookUrl: trimmed } : prev)
    } catch (e: any) {
      showMsg(`保存失败：${e?.message || '未知错误'}`, false)
    } finally {
      setSaving(false)
    }
  }

  const handleTestWebhook = async () => {
    setTesting(true)
    try {
      const result = await wecomApi.testWebhook(tripId)
      showMsg(result.message)
    } catch (e: any) {
      showMsg(`测试失败：${e?.message || '未知错误'}`, false)
    } finally {
      setTesting(false)
    }
  }

  if (loading) return <div className="p-4 text-sm text-paper-500">加载群配置</div>

  const hasConfig = !!(trip?.webhookUrl || trip?.wecomChatId)

  return (
    <div className="space-y-4">
      {message && (
        <div className={`rounded-control border p-3 text-sm ${message.ok ? 'border-success-200 bg-success-50 text-success-700' : 'border-danger-200 bg-danger-50 text-danger-700'}`}>
          {message.text}
        </div>
      )}

      {hasConfig && (
        <div className="space-y-1 rounded-card border border-success-200 bg-success-50 p-3">
          <div className="flex items-center gap-2 text-sm font-medium text-success-700">
            <CheckCircle className="h-4 w-4" /> 群配置已就绪
          </div>
          {trip?.wecomChatId && (
            <div className="text-xs text-success-700">群聊 ID：{trip.wecomChatId}</div>
          )}
          {trip?.webhookUrl && (
            <div className="truncate text-xs text-success-700">webhook：{trip.webhookUrl}</div>
          )}
        </div>
      )}

      <div className="rounded-card border border-paper-200 bg-paper-50 p-3">
        <div className="flex items-start gap-2">
          <Info className="mt-0.5 h-4 w-4 shrink-0 text-paper-500" />
          <div className="space-y-1 text-xs text-paper-600">
            <p className="font-medium text-paper-700">如何配置企业微信群</p>
            <ol className="list-inside list-decimal space-y-0.5">
              <li>在企业微信中创建群聊</li>
              <li>群设置 → 群机器人 → 添加群机器人</li>
              <li>复制机器人的 Webhook 地址</li>
              <li>粘贴到下方输入框，点击保存</li>
            </ol>
          </div>
        </div>
      </div>

      <div className="space-y-2">
        <label className="flex items-center gap-1.5 text-sm font-medium text-paper-700">
          <Link className="h-4 w-4 text-paper-500" /> Webhook 地址
        </label>
        <input
          type="text"
          value={webhookUrl}
          onChange={(e) => setWebhookUrl(e.target.value)}
          placeholder="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=..."
          disabled={readOnly}
          className="w-full rounded-control border border-paper-300 px-3 py-2 font-mono text-sm focus:border-accent-600 focus:outline-none focus:ring-2 focus:ring-accent-100 disabled:bg-paper-50 disabled:text-paper-600"
        />
        {readOnly ? (
          <p className="text-xs text-paper-500">仅管理员可修改群配置</p>
        ) : (
          <div className="flex flex-wrap items-center gap-2">
            <Button onClick={() => void handleSaveWebhook()} loading={saving}>
              <Save className="h-4 w-4" />
              保存 webhook
            </Button>
            <Button
              variant="secondary"
              onClick={() => void handleTestWebhook()}
              disabled={testing || !webhookUrl.trim()}
              loading={testing}
            >
              <Send className="h-4 w-4" />
              测试发送
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
