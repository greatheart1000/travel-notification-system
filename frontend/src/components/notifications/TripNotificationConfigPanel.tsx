import { useEffect, useState } from 'react'
import { TripNotificationRuleForm } from './TripNotificationRuleForm'
import { TripNotificationStatusTable } from './TripNotificationStatusTable'
import { FigmaTripService } from '../../services/figmaTripService'

interface TripNotificationConfigPanelProps {
  tripId: string
  onBackToTrip: () => void
  tripLabel?: string
}

export function TripNotificationConfigPanel({ tripId, onBackToTrip, tripLabel }: TripNotificationConfigPanelProps) {
  const [trip, setTrip] = useState<Awaited<ReturnType<typeof FigmaTripService.getTripDetail>>>(undefined)

  useEffect(() => {
    let active = true

    const loadTrip = async () => {
      const nextTrip = await FigmaTripService.getTripDetail(tripId)
      if (active) setTrip(nextTrip)
    }

    void loadTrip()

    return () => {
      active = false
    }
  }, [tripId])

  const rules = trip?.notifications ?? []

  return (
    <div className="p-6">
      <button onClick={onBackToTrip} className="mb-4 text-sm text-accent-600 hover:text-accent-700">返回团详情</button>
      <div className="rounded-control border border-paper-200 bg-white shadow-card">
        <div className="border-b border-paper-200 bg-paper-50 px-6 py-4">
          <h2 className="text-lg font-semibold text-paper-900">按旅行团配置通知</h2>
          <p className="mt-1 text-sm text-paper-500">{tripLabel ?? trip?.name ?? tripId}</p>
        </div>
        <div className="p-6">
          <TripNotificationRuleForm mode="create" />
          <div className="mt-6 overflow-x-auto">
            <table className="w-full min-w-[880px] text-sm">
              <thead>
                <tr className="border-b border-paper-200 bg-paper-50">
                  <th className="px-4 py-3 text-left font-medium text-paper-700">规则名称</th>
                  <th className="px-4 py-3 text-left font-medium text-paper-700">时间点</th>
                  <th className="px-4 py-3 text-left font-medium text-paper-700">绑定模板</th>
                  <th className="px-4 py-3 text-left font-medium text-paper-700">渠道</th>
                  <th className="px-4 py-3 text-left font-medium text-paper-700">启用状态</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-paper-200">
                {rules.map((rule) => (
                  <tr key={`${rule.phase}-${rule.time}-${rule.coreWork}`}>
                    <td className="px-4 py-3 text-paper-900">{rule.coreWork}</td>
                    <td className="px-4 py-3 text-paper-700">{rule.time}</td>
                    <td className="px-4 py-3 text-paper-700">{rule.phase}模板</td>
                    <td className="px-4 py-3 text-paper-700">短信</td>
                    <td className="px-4 py-3 text-paper-700">{rule.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <TripNotificationStatusTable />
        </div>
      </div>
    </div>
  )
}
