import { useEffect, useRef, useState } from 'react'
import { notificationsApi } from '../services/api'
import type { EmergencyWeatherSummary } from '../types/api'

export function Notifications() {
  const [summary, setSummary] = useState<EmergencyWeatherSummary | null>(null)
  const [content, setContent] = useState('')
  const [loadError, setLoadError] = useState<string | null>(null)
  const [sending, setSending] = useState(false)
  const [sendMessage, setSendMessage] = useState<string | null>(null)
  const contentRef = useRef<HTMLTextAreaElement | null>(null)

  useEffect(() => {
    let active = true

    const loadSummary = async () => {
      try {
        const result = await notificationsApi.getEmergencyWeatherSummary()
        if (!active) return
        setSummary(result)
        setContent(result.generatedNotification)
      } catch (error) {
        if (active) setLoadError(error instanceof Error ? error.message : 'API 天气预警加载失败')
      }
    }

    void loadSummary()

    return () => {
      active = false
    }
  }, [])

  const handleConfirmSend = async () => {
    if (!summary || sending) return
    setSending(true)
    setSendMessage(null)
    try {
      const result = await notificationsApi.sendEmergencyWeather({
        alertId: summary.alertId,
        customContent: content,
        channel: summary.channel,
      })
      setSendMessage(
        result.ok
          ? `已发送 ${result.sentCount} 条（${result.status}）`
          : `发送未完成（${result.status}），请人工核对`,
      )
    } catch (error) {
      setSendMessage(error instanceof Error ? error.message : '发送失败，请重试')
    } finally {
      setSending(false)
    }
  }

  if (loadError) {
    return <div className="p-6"><div className="rounded-lg border border-red-200 bg-red-50 p-6 text-red-700">{loadError}</div></div>
  }

  if (!summary) {
    return <div className="p-6"><div className="rounded-lg border border-gray-200 bg-white p-6 text-center text-gray-600">正在通过 API 加载紧急天气通知...</div></div>
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-2">紧急天气通知</h1>
      <p className="text-gray-600 mb-6">天气风险通知、AI风险分析与 AI生成通知文案预览。</p>
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 bg-red-50 border-b border-red-100">
          <h2 className="font-semibold text-red-900">天气风险通知</h2>
          <p className="text-sm text-red-700 mt-1">
            {summary.title} · {summary.riskLevelLabel} · 影响 {summary.affectedTripCount} 个旅行团
          </p>
        </div>
        <div className="p-6 space-y-4">
          <section>
            <h3 className="text-sm font-semibold text-gray-900 mb-2">天气摘要</h3>
            <p className="text-sm text-gray-700">{summary.weatherSummary}</p>
          </section>
          <section>
            <h3 className="text-sm font-semibold text-gray-900 mb-2">AI风险分析</h3>
            <p className="text-sm text-gray-700">{summary.aiRiskSummary}</p>
          </section>
          <section>
            <h3 className="text-sm font-semibold text-gray-900 mb-2">AI生成通知文案</h3>
            <textarea
              ref={contentRef}
              value={content}
              onChange={(event) => setContent(event.target.value)}
              className="min-h-[160px] w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500"
            />
          </section>
          {sendMessage && (
            <p className="text-sm text-gray-700" role="status">{sendMessage}</p>
          )}
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => contentRef.current?.focus()}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
            >
              编辑后发送
            </button>
            <button
              type="button"
              onClick={() => void handleConfirmSend()}
              disabled={sending}
              className="rounded-lg bg-cyan-500 px-4 py-2 text-sm text-white hover:bg-cyan-600 disabled:opacity-60"
            >
              {sending ? '发送中...' : '确认发送'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
