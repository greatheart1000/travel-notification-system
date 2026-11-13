import { useState } from 'react'
import { Bot, ShieldCheck, UserCheck } from 'lucide-react'
import { getErrorMessage, tripReminderApi, type TripSendMode } from '../../services/api'

interface Props {
  tripId: string
  mode: TripSendMode
  canEdit: boolean
  onChange: (mode: TripSendMode) => void
  onToast: (message: string) => void
}

const OPTIONS: Array<{
  key: TripSendMode
  title: string
  description: string
  icon: typeof Bot
  activeClass: string
}> = [
  {
    key: 'auto',
    title: '自动发送',
    description: '到达计划时间后，系统直接把早/中/晚提醒发到本团企业微信群。',
    icon: Bot,
    activeClass: 'border-accent-300 bg-accent-50',
  },
  {
    key: 'approval',
    title: '需我确认',
    description: '系统只生成发送计划，到点不自动发。你检查或修改后，再逐条发送。',
    icon: UserCheck,
    activeClass: 'border-accent-300 bg-accent-50',
  },
]

export function TripSendModeToggle({ tripId, mode, canEdit, onChange, onToast }: Props) {
  const [saving, setSaving] = useState<TripSendMode | null>(null)
  const [error, setError] = useState<string | null>(null)

  const change = async (next: TripSendMode) => {
    if (next === mode || saving) return
    setSaving(next)
    setError(null)
    try {
      const result = await tripReminderApi.updateSendMode(tripId, next)
      onChange(result.send_mode)
      onToast(result.message)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setSaving(null)
    }
  }

  return (
    <section className="rounded-panel border border-paper-200 bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2 text-sm font-semibold text-paper-900">
            <ShieldCheck className="h-4 w-4 text-accent-600" />
            本团发送模式
          </h2>
          <p className="mt-1 text-xs leading-5 text-paper-500">
            每团可以单独设置。导游对不熟悉的团可先改成「需我确认」，避免自动消息发错。
          </p>
        </div>
        <span className="rounded-control bg-paper-100 px-2.5 py-1 text-xs font-medium text-paper-700">
          当前：{mode === 'approval' ? '需我确认' : '自动发送'}
        </span>
      </div>

      <div className="mt-3 grid gap-2 sm:grid-cols-2">
        {OPTIONS.map(({ key, title, description, icon: Icon, activeClass }) => {
          const active = mode === key
          return (
            <button
              key={key}
              type="button"
              disabled={!canEdit || saving !== null}
              onClick={() => void change(key)}
              className={`rounded-control border p-3 text-left transition-colors ${
                active
                  ? activeClass
                  : 'border-paper-200 bg-white hover:border-accent-300'
              } ${!canEdit ? 'cursor-default opacity-70' : ''}`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="flex items-center gap-1.5 text-sm font-medium text-paper-900">
                  <Icon className="h-4 w-4 text-accent-600" />
                  {title}
                </span>
                <span
                  className={`h-2 w-2 rounded-full ${active ? 'bg-accent-500' : 'bg-paper-300'}`}
                />
              </div>
              <p className="mt-1 text-xs leading-5 text-paper-500">{description}</p>
              {saving === key ? (
                <p className="mt-1 text-xs text-accent-700">正在切换…</p>
              ) : null}
            </button>
          )
        })}
      </div>

      {!canEdit ? (
        <p className="mt-2 text-xs text-paper-400">只有该团负责人或管理员可以切换发送模式。</p>
      ) : null}
      {mode === 'approval' ? (
        <p className="mt-2 rounded-control border border-warning-200 bg-warning-50 px-3 py-2 text-xs text-warning-800">
          已暂停自动群发。可发送的提醒会留在「行程发送计划」里，等你确认。
        </p>
      ) : null}
      {error ? <p className="mt-2 text-xs text-danger-600">{error}</p> : null}
    </section>
  )
}
