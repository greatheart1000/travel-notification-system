import { useEffect, useState } from 'react'
import { Button } from '../Button'
import { Card } from '../Card'
import { type ProjectNotificationConfig, type Trip } from '../../types/api'

interface TripNotificationConfigFormPanelProps {
  trip: Trip
  config: ProjectNotificationConfig
  saving: boolean
  saveMessage: string | null
  onSave: (draft: ProjectNotificationConfig) => void
}

export function TripNotificationConfigFormPanel({
  trip,
  config,
  saving,
  saveMessage,
  onSave,
}: TripNotificationConfigFormPanelProps) {
  const [draft, setDraft] = useState<ProjectNotificationConfig>(config)

  useEffect(() => {
    setDraft(config)
  }, [config])

  return (
    <Card title="当前旅行团通知配置" className="mb-6 border-amber-100 shadow-[0_14px_40px_rgba(120,53,15,0.08)]">
      <div className="space-y-4">
        <div className="rounded-xl border border-amber-100 bg-amber-50 p-4 text-sm text-amber-800">
          <p className="font-semibold">Travel Hub 当前团配置</p>
          <p className="mt-1">团名：{trip.destination}（团号：{trip.teamId || trip.id}）</p>
        </div>
        {saveMessage ? (
          <p className={`rounded-xl p-3 text-sm ${saveMessage.includes('失败') ? 'bg-red-50 text-red-700' : 'bg-green-50 text-green-700'}`}>
            {saveMessage}
          </p>
        ) : null}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <label className="mb-1 block text-sm text-gray-700">项目名称</label>
            <input
              type="text"
              value={draft.projectName}
              onChange={(event) => setDraft((prev) => ({ ...prev, projectName: event.target.value }))}
              className="w-full rounded-lg border border-gray-300 px-3 py-2"
              placeholder="例如：川西摄影团"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm text-gray-700">人工接管目标</label>
            <input
              type="text"
              value={draft.manualTakeoverTarget}
              onChange={(event) => setDraft((prev) => ({ ...prev, manualTakeoverTarget: event.target.value }))}
              className="w-full rounded-lg border border-gray-300 px-3 py-2"
              placeholder="例如：值班管家A组"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm text-gray-700">短信签名</label>
            <input
              type="text"
              value={draft.smsSignName}
              onChange={(event) => setDraft((prev) => ({ ...prev, smsSignName: event.target.value }))}
              className="w-full rounded-lg border border-gray-300 px-3 py-2"
              placeholder="短信签名"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm text-gray-700">短信服务商</label>
            <input
              type="text"
              value={draft.smsProvider}
              onChange={(event) => setDraft((prev) => ({ ...prev, smsProvider: event.target.value }))}
              className="w-full rounded-lg border border-gray-300 px-3 py-2"
              placeholder="aliyun"
            />
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <label className="inline-flex items-center gap-2 text-sm text-gray-700">
            <input
              type="checkbox"
              checked={draft.weatherEnabled}
              onChange={(event) => setDraft((prev) => ({ ...prev, weatherEnabled: event.target.checked }))}
            />
            启用天气预警自动通知
          </label>
          <Button onClick={() => onSave(draft)} loading={saving}>
            保存当前团配置
          </Button>
        </div>
      </div>
    </Card>
  )
}
