import { useEffect, useMemo, useState } from 'react'
import { FigmaWeatherService } from '../services/figmaTripService'
import type { MakeWeatherInfo } from '../data/figmaMockData'

function buildEmergencyContent(warningCities: MakeWeatherInfo[]): string {
  return `【紧急天气通知】天气摘要：${warningCities.map((city) => `${city.city}${city.warning}`).join('、')}。AI风险分析：受极端天气影响，建议领队调整户外活动并提醒游客保暖防滑。AI生成通知文案：请游客关注领队通知，做好防护，注意安全。`
}

export function Notifications() {
  const [warningCities, setWarningCities] = useState<MakeWeatherInfo[]>([])
  const [content, setContent] = useState('')
  const [loadError, setLoadError] = useState<string | null>(null)

  useEffect(() => {
    let active = true

    const loadWarnings = async () => {
      try {
        const warnings = await FigmaWeatherService.getWarningCities()
        if (!active) return
        setWarningCities(warnings)
        setContent(buildEmergencyContent(warnings))
      } catch (error) {
        if (active) setLoadError(error instanceof Error ? error.message : 'API 天气预警加载失败')
      }
    }

    void loadWarnings()

    return () => {
      active = false
    }
  }, [])

  const weatherSummary = useMemo(() => (
    warningCities.map((city) => `${city.city} ${city.temp}°C ${city.weather} ${city.warning}`).join('；')
  ), [warningCities])

  if (loadError) {
    return <div className="p-6"><div className="rounded-lg border border-red-200 bg-red-50 p-6 text-red-700">{loadError}</div></div>
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-2">紧急天气通知</h1>
      <p className="text-gray-600 mb-6">天气风险通知、AI风险分析与 AI生成通知文案预览。</p>
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 bg-red-50 border-b border-red-100">
          <h2 className="font-semibold text-red-900">天气风险通知</h2>
        </div>
        <div className="p-6 space-y-4">
          <section>
            <h3 className="text-sm font-semibold text-gray-900 mb-2">天气摘要</h3>
            <p className="text-sm text-gray-700">{weatherSummary}</p>
          </section>
          <section>
            <h3 className="text-sm font-semibold text-gray-900 mb-2">AI风险分析</h3>
            <p className="text-sm text-gray-700">暴雪、寒潮和沙尘天气可能影响集合、交通与户外活动，需要提前通知游客并触发人工接管预案。</p>
          </section>
          <section>
            <h3 className="text-sm font-semibold text-gray-900 mb-2">AI生成通知文案</h3>
            <textarea
              value={content}
              onChange={(event) => setContent(event.target.value)}
              className="min-h-[160px] w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500"
            />
          </section>
          <div className="flex justify-end gap-2">
            <button className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50">编辑后发送</button>
            <button className="rounded-lg bg-cyan-500 px-4 py-2 text-sm text-white hover:bg-cyan-600">确认发送</button>
          </div>
        </div>
      </div>
    </div>
  )
}
