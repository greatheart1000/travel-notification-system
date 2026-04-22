import { useEffect, useState } from 'react'
import { Button } from '../Button'
import {
  type TripNotificationRule,
  type TripNotificationRuleChannelCode,
  type TripNotificationRuleSceneCode,
  type TripNotificationRuleStageCode,
  type TripNotificationRuleTimeSlotCode,
  type TripNotificationRuleWriteInput,
  type TripNotificationTemplate,
} from '../../features/notifications/tripNotificationClient'

interface TripNotificationRuleFormProps {
  tripId: string
  templates: TripNotificationTemplate[]
  initialRule?: TripNotificationRule | null
  saving?: boolean
  onSubmit: (input: TripNotificationRuleWriteInput) => void | Promise<void>
  onCancel: () => void
}

const stageOptions: Array<{ value: TripNotificationRuleStageCode; label: string }> = [
  { value: 'pre_trip', label: '行前' },
  { value: 'on_trip', label: '行中' },
  { value: 'post_trip', label: '行后' },
  { value: 'custom', label: '自定义' },
]

const timeSlotOptions: Array<{ value: TripNotificationRuleTimeSlotCode; label: string }> = [
  { value: 'morning', label: '早间' },
  { value: 'afternoon', label: '午间' },
  { value: 'evening', label: '晚间' },
  { value: 'night', label: '夜间' },
  { value: 'all_day', label: '全天' },
]

const sceneOptions: Array<{ value: TripNotificationRuleSceneCode; label: string }> = [
  { value: 'normal', label: '常规提醒' },
  { value: 'weather_alert', label: '天气预警' },
  { value: 'delay', label: '延误变更' },
  { value: 'complaint', label: '投诉跟进' },
  { value: 'manual', label: '人工介入' },
]

const channelOptions: Array<{ value: TripNotificationRuleChannelCode; label: string }> = [
  { value: 'sms', label: '短信' },
  { value: 'wechat_work_group', label: '企业微信' },
  { value: 'email', label: '邮件' },
]

function nextDefaultTemplateId(templates: TripNotificationTemplate[], channel: TripNotificationRuleChannelCode): string {
  const byChannel = templates.find((template) => template.channel === channel && template.enabled)
  if (byChannel) {
    return byChannel.id
  }
  return templates[0]?.id || ''
}

export function TripNotificationRuleForm({
  tripId,
  templates,
  initialRule = null,
  saving = false,
  onSubmit,
  onCancel,
}: TripNotificationRuleFormProps) {
  const [name, setName] = useState(initialRule?.name || '')
  const [stage, setStage] = useState<TripNotificationRuleStageCode>(initialRule?.stage === 'unknown' ? 'custom' : (initialRule?.stage || 'pre_trip'))
  const [timeSlot, setTimeSlot] = useState<TripNotificationRuleTimeSlotCode>(initialRule?.timeSlot === 'unknown' ? 'all_day' : (initialRule?.timeSlot || 'morning'))
  const [scene, setScene] = useState<TripNotificationRuleSceneCode>(initialRule?.scene || 'normal')
  const [enabled, setEnabled] = useState<boolean>(initialRule?.enabled ?? true)
  const [priority, setPriority] = useState<number>(initialRule?.priority ?? 100)
  const [channels, setChannels] = useState<TripNotificationRuleChannelCode[]>(initialRule?.channels || ['sms'])
  const [templateId, setTemplateId] = useState<string>(
    initialRule?.templateId || nextDefaultTemplateId(templates, initialRule?.channels?.[0] || 'sms'),
  )
  const [formMessage, setFormMessage] = useState<string>('')

  useEffect(() => {
    if (!templateId) {
      setTemplateId(nextDefaultTemplateId(templates, channels[0] || 'sms'))
    }
  }, [channels, templateId, templates])

  const toggleChannel = (channel: TripNotificationRuleChannelCode) => {
    setChannels((prev) => {
      if (prev.includes(channel)) {
        const next = prev.filter((item) => item !== channel)
        return next.length > 0 ? next : prev
      }
      return [...prev, channel]
    })
  }

  const submit = () => {
    if (!name.trim()) {
      setFormMessage('请填写规则名称')
      return
    }
    if (!templateId.trim()) {
      setFormMessage('请选择绑定模板')
      return
    }
    if (channels.length === 0) {
      setFormMessage('至少选择一个通知渠道')
      return
    }
    setFormMessage('')
    void onSubmit({
      name: name.trim(),
      stage,
      timeSlot,
      scene,
      channels,
      templateId,
      enabled,
      priority: Number.isFinite(priority) ? priority : 100,
      conditions: {
        trip_id: tripId,
      },
    })
  }

  return (
    <div className="rounded-xl border border-blue-100 bg-blue-50/50 p-4">
      <p className="mb-3 text-sm font-semibold text-slate-900">{initialRule ? '编辑通知规则' : '新增通知规则'}</p>
      <div className="grid gap-3 md:grid-cols-2">
        <div>
          <label className="mb-1 block text-xs text-slate-600">规则名称</label>
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="例如：出发前 1 天群提醒"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs text-slate-600">绑定模板</label>
          <select
            value={templateId}
            onChange={(event) => setTemplateId(event.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="">请选择模板</option>
            {templates.map((template) => (
              <option key={template.id} value={template.id}>
                {template.name}（{template.channelLabel}）
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs text-slate-600">阶段</label>
          <select
            value={stage}
            onChange={(event) => setStage(event.target.value as TripNotificationRuleStageCode)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          >
            {stageOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs text-slate-600">时间点</label>
          <select
            value={timeSlot}
            onChange={(event) => setTimeSlot(event.target.value as TripNotificationRuleTimeSlotCode)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          >
            {timeSlotOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs text-slate-600">场景</label>
          <select
            value={scene}
            onChange={(event) => setScene(event.target.value as TripNotificationRuleSceneCode)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          >
            {sceneOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs text-slate-600">优先级</label>
          <input
            type="number"
            min={1}
            value={priority}
            onChange={(event) => setPriority(Number(event.target.value))}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
        </div>
      </div>

      <div className="mt-3">
        <label className="mb-1 block text-xs text-slate-600">通知渠道</label>
        <div className="flex flex-wrap gap-2">
          {channelOptions.map((option) => {
            const checked = channels.includes(option.value)
            return (
              <button
                key={option.value}
                type="button"
                onClick={() => toggleChannel(option.value)}
                className={`rounded-full border px-3 py-1 text-xs ${
                  checked ? 'border-blue-600 bg-blue-600 text-white' : 'border-slate-300 bg-white text-slate-700'
                }`}
              >
                {option.label}
              </button>
            )
          })}
        </div>
      </div>

      <div className="mt-3">
        <label className="mb-1 block text-xs text-slate-600">启用状态</label>
        <select
          value={enabled ? 'enabled' : 'disabled'}
          onChange={(event) => setEnabled(event.target.value === 'enabled')}
          className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm md:w-56"
        >
          <option value="enabled">启用</option>
          <option value="disabled">停用</option>
        </select>
      </div>

      {formMessage ? <p className="mt-3 text-xs text-red-600">{formMessage}</p> : null}

      <div className="mt-4 flex flex-wrap justify-end gap-2">
        <Button variant="secondary" onClick={onCancel}>
          取消
        </Button>
        <Button onClick={submit} loading={saving}>
          保存规则
        </Button>
      </div>
    </div>
  )
}
