import { useEffect, useState } from 'react'
import { ArrowLeft, Bell, BellOff } from 'lucide-react'
import { PageShell } from '../components/PageShell'
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
    return () => {
      active = false
    }
  }, [tripId])

  const backButton = onBackToTrip ? (
    <button
      type="button"
      onClick={onBackToTrip}
      className="inline-flex items-center gap-1.5 text-sm text-paper-500 transition-colors hover:text-paper-900"
    >
      <ArrowLeft className="h-4 w-4" /> 返回团详情
    </button>
  ) : null

  if (isLoading) {
    return (
      <PageShell
        title="通知规则"
        description={trip ? `${trip.name} · 团号 ${trip.code}` : '按行程配置通知规则'}
        actions={backButton}
      >
        <div className="rounded-card border border-paper-200 bg-white p-6 text-center text-sm text-paper-500">
          加载中
        </div>
      </PageShell>
    )
  }

  if (loadError) {
    return (
      <PageShell title="通知规则" actions={backButton}>
        <div className="rounded-card border border-danger-200 bg-danger-50 p-5 text-sm text-danger-700">
          {loadError}
        </div>
      </PageShell>
    )
  }

  const enabledCount = rules.filter((rule) => rule.enabled).length
  const disabledCount = rules.length - enabledCount

  return (
    <PageShell
      title="通知规则"
      description={
        trip
          ? `${trip.name} · 团号 ${trip.code} · ${trip.participants} 人 · 领队 ${trip.leader}`
          : '按行程配置通知规则'
      }
      actions={backButton}
    >
      <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-3">
        <div className="rounded-card border border-paper-200 bg-white p-5 shadow-card">
          <p className="text-sm text-paper-500">已启用规则</p>
          <p className="mt-2 text-2xl font-semibold tabular-nums text-accent-700">{enabledCount}</p>
        </div>
        <div className="rounded-card border border-paper-200 bg-white p-5 shadow-card">
          <p className="text-sm text-paper-500">规则总数</p>
          <p className="mt-2 text-2xl font-semibold tabular-nums text-paper-900">{rules.length}</p>
        </div>
        <div className="rounded-card border border-paper-200 bg-white p-5 shadow-card">
          <p className="text-sm text-paper-500">已停用规则</p>
          <p className="mt-2 text-2xl font-semibold tabular-nums text-paper-900">{disabledCount}</p>
        </div>
      </div>

      <div className="overflow-hidden rounded-card border border-paper-200 bg-white shadow-card">
        <div className="border-b border-paper-200 px-5 py-4">
          <h2 className="text-base font-semibold text-paper-900">通知规则列表</h2>
          <p className="mt-1 text-xs text-paper-500">配置通知触发阶段、时段与场景规则</p>
        </div>

        {rules.length === 0 ? (
          <div className="p-10 text-center text-sm text-paper-500">暂无通知规则，请联系管理员配置</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-paper-200 text-xs font-medium text-paper-500">
                  <th className="px-5 py-3 text-left">规则名称</th>
                  <th className="px-5 py-3 text-left">阶段</th>
                  <th className="px-5 py-3 text-left">时段</th>
                  <th className="px-5 py-3 text-left">场景</th>
                  <th className="px-5 py-3 text-left">绑定模板</th>
                  <th className="px-5 py-3 text-left">优先级</th>
                  <th className="px-5 py-3 text-center">状态</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-paper-100">
                {rules.map((rule) => (
                  <tr key={rule.id} className="transition-colors hover:bg-paper-50">
                    <td className="px-5 py-3 font-medium text-paper-900">{rule.name}</td>
                    <td className="px-5 py-3">
                      <span className="inline-flex rounded-control bg-accent-50 px-2 py-0.5 text-xs text-accent-800">
                        {rule.stageLabel}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-paper-700">{rule.timeSlotLabel}</td>
                    <td className="px-5 py-3 text-paper-700">{rule.scene}</td>
                    <td className="max-w-52 truncate px-5 py-3 text-paper-700">{rule.templateLabel}</td>
                    <td className="px-5 py-3 tabular-nums text-paper-700">{rule.priority}</td>
                    <td className="px-5 py-3 text-center">
                      {rule.enabled ? (
                        <span className="inline-flex items-center gap-1 text-xs text-success-700">
                          <Bell className="h-3 w-3" /> 已启用
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-xs text-paper-500">
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
    </PageShell>
  )
}
