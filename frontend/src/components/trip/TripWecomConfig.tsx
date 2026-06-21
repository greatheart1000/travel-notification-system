import { useEffect, useState } from 'react'
import { Save, Link, Info, CheckCircle, Send } from 'lucide-react'
import { wecomApi, tripsApi } from '../../services/api'
import type { Trip } from '../../types/api'

interface Props {
  tripId: string
}

export function TripWecomConfig({ tripId }: Props) {
  const [trip, setTrip] = useState<Trip | null>(null)
  const [webhookUrl, setWebhookUrl] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [message, setMessage] = useState<{ text: string; ok: boolean } | null>(null)

  useEffect(() => {
    (async () => {
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
      showMsg(`保存失败: ${e?.message || '未知错误'}`, false)
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
      showMsg(`测试失败: ${e?.message || '未知错误'}`, false)
    } finally {
      setTesting(false)
    }
  }

  if (loading) return <div className="p-4 text-sm text-gray-500">加载群配置...</div>

  const hasConfig = !!(trip?.webhookUrl || trip?.wecomChatId)

  return (
    <div className="space-y-4">
      {message && (
        <div className={`text-sm p-3 rounded-lg ${message.ok ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-700 border border-red-200'}`}>
          {message.text}
        </div>
      )}

      {/* 配置状态 */}
      {hasConfig && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-3 space-y-1">
          <div className="flex items-center gap-2 text-sm font-medium text-green-700">
            <CheckCircle className="h-4 w-4" /> 群配置已就绪
          </div>
          {trip?.wecomChatId && (
            <div className="text-xs text-green-600">群聊 ID：{trip.wecomChatId}</div>
          )}
          {trip?.webhookUrl && (
            <div className="text-xs text-green-600 truncate">webhook：{trip.webhookUrl}</div>
          )}
        </div>
      )}

      {/* 操作说明 */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
        <div className="flex items-start gap-2">
          <Info className="h-4 w-4 text-blue-500 mt-0.5 flex-shrink-0" />
          <div className="text-xs text-blue-700 space-y-1">
            <p className="font-medium">如何配置企业微信群？</p>
            <ol className="list-decimal list-inside space-y-0.5">
              <li>在企业微信中创建群聊</li>
              <li>群设置 → 群机器人 → 添加群机器人</li>
              <li>复制机器人的 <strong>Webhook 地址</strong></li>
              <li>粘贴到下方输入框，点击保存</li>
            </ol>
          </div>
        </div>
      </div>

      {/* Webhook URL 输入 */}
      <div className="space-y-2">
        <label className="text-sm font-medium text-gray-700 flex items-center gap-1.5">
          <Link className="h-4 w-4" /> Webhook 地址
        </label>
        <input
          type="text"
          value={webhookUrl}
          onChange={(e) => setWebhookUrl(e.target.value)}
          placeholder="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=..."
          className="w-full px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-300 font-mono"
        />
        <div className="flex items-center gap-2">
          <button
            onClick={handleSaveWebhook}
            disabled={saving}
            className="flex items-center gap-2 px-4 py-2 text-sm text-white bg-cyan-600 hover:bg-cyan-700 rounded-lg disabled:opacity-50"
          >
            <Save className="h-4 w-4" />
            {saving ? '保存中...' : '保存 webhook'}
          </button>
          <button
            onClick={handleTestWebhook}
            disabled={testing || !webhookUrl.trim()}
            className="flex items-center gap-2 px-4 py-2 text-sm text-cyan-700 bg-cyan-50 border border-cyan-200 hover:bg-cyan-100 rounded-lg disabled:opacity-50"
          >
            <Send className="h-4 w-4" />
            {testing ? '发送中...' : '测试发送'}
          </button>
        </div>
      </div>

    </div>
  )
}
