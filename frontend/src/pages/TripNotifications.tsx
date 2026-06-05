import { useEffect, useState } from 'react'
import { ArrowLeft, Bell, BellOff } from 'lucide-react'
import { FigmaTripService } from '../services/figmaTripService'
import { notificationsApi } from '../services/api'
import type { MakeTrip } from '../data/figmaMockData'
import type { NotificationRule } from '../types/api'

interface TripNotificationsProps {
  tripId: string
  onBackToTrip?: () => void
}

export function TripNotifications({ tripId, onBackToTrip }: TripNotificationsProps) {
  const [trip, setTrip] = useState<MakeTrip | undefined>(undefined)
  const [rules, setRules] = useState<NotificationRule[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)

  useEffect(() => {
    let active = true

    const load = async () => {
      setIsLoading(true)
      setLoadError(null)
      try {
        const [tripData, rulesData] = await Promise.all([
          FigmaTripService.getTripById(tripId),
          notificationsApi.listRules(),
        ])
        if (active) {
          setTrip(tripData)
          setRules(rulesData)
        }
      } catch (error) {
        if (active) setLoadError(error instanceof Error ? error.message : '加载失败')
      } finally {
        if (active) setIsLoading(false)
      }
    }

    void load()
    return () => { active = false }
  }, [tripId])

  if (isLoading) {
    return (
      <div className="p-6">
        <button onClick={onBackToTrip} className="mb-4 flex items-center gap-2 text-sm text-cyan-600 hover:text-cyan-700">
          <ArrowLeft className="h-4 w-4" /> 返回团详情
        </button>
        <div className="rounded-lg border border-gray-200 bg-white p-6 text-center text-gray-600">加载中...</div>
      </div>
    )
  }

  if (loadError) {
    return (
      <div className="p-6">
        <button onClick={onBackToTrip} className="mb-4 flex items-center gap-2 text-sm text-cyan-600 hover:text-cyan-700">
          <ArrowLeft className="h-4 w-4" /> 返回团详情
        </button>
        <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-red-700">{loadError}</div>
      </div>
    )
  }

  return (
    <div className="p-6">
      <button onClick={onBackToTrip} className="mb-4 flex items-center gap-2 text-sm text-cyan-600 hover:text-cyan-700">
        <ArrowLeft className="h-4 w-4" /> 返回团详情
      </button>

      {trip && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 mb-6 overflow-hidden">
          <div className="px-6 py-4 bg-gradient-to-r from-cyan-500 to-blue-600 text-white">
            <h1 className="text-2xl font-bold mb-2">{trip.name} - 通知规则</h1>
            <div className="flex flex-wrap gap-4 text-sm opacity-90">
              <span>团号：{trip.code}</span>
              <span>人数：{trip.participants} 人</span>
              <span>领队：{trip.leader}</span>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 mb-6 md:grid-cols-3">
        <div className="rounded-lg border border-green-200 bg-green-50 p-4">
          <div className="text-sm text-green-700">已启用规则</div>
          <div className="mt-2 text-3xl font-bold text-green-700">{rules.filter((r) => r.enabled).length}</div>
        </div>
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
          <div className="text-sm text-gray-700">规则总数</div>
          <div className="mt-2 text-3xl font-bold text-gray-700">{rules.length}</div>
        </div>
        <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-4">
          <div className="text-sm text-yellow-700">已停用规则</div>
          <div className="mt-2 text-3xl font-bold text-yellow-700">{rules.filter((r) => !r.enabled).length}</div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
          <h2 className="font-semibold text-gray-900">通知规则列表</h2>
          <p className="mt-1 text-xs text-gray-500">配置通知触发阶段、时段与场景规则</p>
        </div>

        {rules.length === 0 ? (
          <div className="p-12 text-center text-gray-400">暂无通知规则，请联系管理员配置</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="px-4 py-3 text-left font-medium text-gray-700">规则名称</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-700">阶段</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-700">时段</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-700">场景</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-700">绑定模板</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-700">优先级</th>
                  <th className="px-4 py-3 text-center font-medium text-gray-700">状态</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {rules.map((rule) => (
                  <tr key={rule.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-900">{rule.name}</td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-1 rounded-full text-xs bg-blue-100 text-blue-700">{rule.stageLabel}</span>
                    </td>
                    <td className="px-4 py-3 text-gray-700">{rule.timeSlotLabel}</td>
                    <td className="px-4 py-3 text-gray-700">{rule.scene}</td>
                    <td className="px-4 py-3 text-gray-700 max-w-[200px] truncate">{rule.templateLabel}</td>
                    <td className="px-4 py-3 text-gray-700">{rule.priority}</td>
                    <td className="px-4 py-3 text-center">
                      {rule.enabled ? (
                        <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs bg-green-100 text-green-700">
                          <Bell className="h-3 w-3" /> 已启用
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs bg-gray-100 text-gray-500">
                          <BellOff className="h-3 w-3" /> 已停用
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
