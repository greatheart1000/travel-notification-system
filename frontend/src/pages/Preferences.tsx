import { useEffect, useState } from 'react'
import { Bell, Clock, Mail, MessageSquare, Shield, Users, Zap } from 'lucide-react'
import { PageShell } from '../components/PageShell'
import { Card } from '../components/Card'
import { Button } from '../components/Button'
import { PageState } from '../components/PageState'
import { type PreferencesViewModel } from '../types/api'
import { preferencesApi, getErrorMessage } from '../services/api'

type LoadState = 'loading' | 'ready' | 'error' | 'empty'

function toInt(value: string, fallback: number): number {
  const parsed = Number(value)
  if (Number.isNaN(parsed)) {
    return fallback
  }
  return parsed
}

const inputClass =
  'mt-1 w-full rounded-control border border-paper-300 bg-white px-3 py-2 text-sm text-paper-900 transition-colors focus:border-accent-600 focus:outline-none focus:ring-2 focus:ring-accent-100'

const channelRowClass = 'flex items-center justify-between rounded-control border border-paper-200 p-4'
const toggleClass = 'h-4 w-4 rounded accent-accent-600'

export function Preferences() {
  const [loadState, setLoadState] = useState<LoadState>('loading')
  const [preferences, setPreferences] = useState<PreferencesViewModel | null>(null)
  const [errorMessage, setErrorMessage] = useState<string>('')
  const [isSaving, setIsSaving] = useState(false)
  const [saveMessage, setSaveMessage] = useState<string | null>(null)

  const loadPreferences = async () => {
    setLoadState('loading')
    setErrorMessage('')

    try {
      const data = await preferencesApi.get()
      setPreferences(data)

      const hasAnyChannel = data.smsEnabled || data.wechatEnabled || data.emailEnabled
      setLoadState(hasAnyChannel ? 'ready' : 'empty')
    } catch (error) {
      setLoadState('error')
      setErrorMessage(getErrorMessage(error))
    }
  }

  useEffect(() => {
    void loadPreferences()
  }, [])

  const handleToggle = (key: keyof PreferencesViewModel) => {
    setPreferences((prev) => {
      if (!prev || typeof prev[key] !== 'boolean') {
        return prev
      }
      return {
        ...prev,
        [key]: !(prev[key] as boolean),
      }
    })
    setSaveMessage(null)
  }

  const handleChange = (key: keyof PreferencesViewModel, value: string | number | boolean) => {
    setPreferences((prev) => {
      if (!prev) {
        return prev
      }
      return {
        ...prev,
        [key]: value,
      }
    })
    setSaveMessage(null)
  }

  const handleSave = async () => {
    if (!preferences) {
      return
    }

    setIsSaving(true)
    setSaveMessage(null)

    try {
      const updated = await preferencesApi.update(preferences)
      setPreferences(updated)
      const hasAnyChannel = updated.smsEnabled || updated.wechatEnabled || updated.emailEnabled
      setLoadState(hasAnyChannel ? 'ready' : 'empty')
      setSaveMessage('设置已保存')
    } catch (error) {
      setSaveMessage(`保存失败：${getErrorMessage(error)}`)
    } finally {
      setIsSaving(false)
    }
  }

  if (loadState === 'loading') {
    return (
      <PageShell title="偏好设置" description="配置通知渠道、静默时段与频率限制">
        <PageState kind="loading" title="正在加载偏好设置" />
      </PageShell>
    )
  }

  if (loadState === 'error') {
    return (
      <PageShell title="偏好设置" description="配置通知渠道、静默时段与频率限制">
        <PageState
          kind="error"
          title="偏好设置加载失败"
          description={errorMessage}
          onRetry={() => {
            void loadPreferences()
          }}
        />
      </PageShell>
    )
  }

  if (!preferences) {
    return (
      <PageShell title="偏好设置" description="配置通知渠道、静默时段与频率限制">
        <PageState
          kind="empty"
          title="未获取到偏好设置"
          description="后端未返回可用数据"
          onRetry={() => {
            void loadPreferences()
          }}
        />
      </PageShell>
    )
  }

  const showEmptyHint = loadState === 'empty'

  return (
    <PageShell title="偏好设置" description="配置通知渠道、静默时段与频率限制">
      {showEmptyHint ? (
        <div className="mb-6">
          <PageState
            kind="empty"
            title="当前未启用任何通知渠道"
            description="至少开启一个渠道后保存，配置才会生效"
          />
        </div>
      ) : null}

      <Card title="通知渠道" className="mb-6">
        <div className="space-y-3">
          <div className={channelRowClass}>
            <div className="flex items-center gap-3">
              <MessageSquare className="h-4 w-4 text-paper-500" />
              <div>
                <p className="text-sm font-medium text-paper-900">短信通知</p>
                <p className="text-sm text-paper-500">通过短信发送重要通知</p>
              </div>
            </div>
            <input
              type="checkbox"
              checked={preferences.smsEnabled}
              onChange={() => handleToggle('smsEnabled')}
              className={toggleClass}
              aria-label="启用短信通知"
            />
          </div>

          <div className={channelRowClass}>
            <div className="flex items-center gap-3">
              <Users className="h-4 w-4 text-paper-500" />
              <div>
                <p className="text-sm font-medium text-paper-900">企业微信</p>
                <p className="text-sm text-paper-500">通过企业微信群发送通知</p>
              </div>
            </div>
            <input
              type="checkbox"
              checked={preferences.wechatEnabled}
              onChange={() => handleToggle('wechatEnabled')}
              className={toggleClass}
              aria-label="启用企业微信通知"
            />
          </div>

          <div className={channelRowClass}>
            <div className="flex items-center gap-3">
              <Mail className="h-4 w-4 text-paper-500" />
              <div>
                <p className="text-sm font-medium text-paper-900">邮件通知</p>
                <p className="text-sm text-paper-500">通过邮件发送详细信息</p>
              </div>
            </div>
            <input
              type="checkbox"
              checked={preferences.emailEnabled}
              onChange={() => handleToggle('emailEnabled')}
              className={toggleClass}
              aria-label="启用邮件通知"
            />
          </div>
        </div>
      </Card>

      <Card title="静默时段" className="mb-6">
        <div className="mb-4 flex items-center gap-2.5">
          <Clock className="h-4 w-4 text-paper-500" />
          <p className="text-sm text-paper-600">在此时段内不会发送通知</p>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <label className="block text-sm font-medium text-paper-700">
            开始时间
            <select
              value={preferences.quietHourStart}
              onChange={(event) => handleChange('quietHourStart', event.target.value)}
              className={inputClass}
            >
              {Array.from({ length: 24 }, (_, index) => (
                <option key={index} value={String(index).padStart(2, '0')}>
                  {String(index).padStart(2, '0')}:00
                </option>
              ))}
            </select>
          </label>

          <label className="block text-sm font-medium text-paper-700">
            结束时间
            <select
              value={preferences.quietHourEnd}
              onChange={(event) => handleChange('quietHourEnd', event.target.value)}
              className={inputClass}
            >
              {Array.from({ length: 24 }, (_, index) => (
                <option key={index} value={String(index).padStart(2, '0')}>
                  {String(index).padStart(2, '0')}:00
                </option>
              ))}
            </select>
          </label>
        </div>
      </Card>

      <Card title="频率限制" className="mb-6">
        <div className="mb-4 flex items-center gap-2.5">
          <Zap className="h-4 w-4 text-paper-500" />
          <p className="text-sm text-paper-600">控制通知的发送频率</p>
        </div>

        <label className="block text-sm font-medium text-paper-700">
          每小时最大通知数
          <input
            type="number"
            value={preferences.maxNotificationsPerHour}
            onChange={(event) => handleChange('maxNotificationsPerHour', toInt(event.target.value, 1))}
            className={inputClass}
            min="1"
            max="20"
          />
        </label>
        <p className="mt-1 text-xs text-paper-500">当每小时通知数超过此值时将进行聚合</p>
      </Card>

      <Card title="高级设置" className="mb-6">
        <div className="space-y-3">
          <div className={channelRowClass}>
            <div className="flex items-center gap-3">
              <Shield className="h-4 w-4 text-paper-500" />
              <div>
                <p className="text-sm font-medium text-paper-900">自动升级</p>
                <p className="text-sm text-paper-500">自动升级高风险投诉</p>
              </div>
            </div>
            <input
              type="checkbox"
              checked={preferences.autoEscalation}
              onChange={() => handleToggle('autoEscalation')}
              className={toggleClass}
              aria-label="启用自动升级"
            />
          </div>

          <div className={channelRowClass}>
            <div className="flex items-center gap-3">
              <Bell className="h-4 w-4 text-paper-500" />
              <div>
                <p className="text-sm font-medium text-paper-900">通知聚合</p>
                <p className="text-sm text-paper-500">聚合相同类型的连续通知</p>
              </div>
            </div>
            <input
              type="checkbox"
              checked={preferences.aggregateNotifications}
              onChange={() => handleToggle('aggregateNotifications')}
              className={toggleClass}
              aria-label="启用通知聚合"
            />
          </div>
        </div>
      </Card>

      {saveMessage ? (
        <p
          className={`mb-4 text-sm ${
            saveMessage.startsWith('保存失败') ? 'text-danger-700' : 'text-success-700'
          }`}
        >
          {saveMessage}
        </p>
      ) : null}

      <div className="flex justify-end gap-2">
        <Button
          variant="secondary"
          onClick={() => {
            void loadPreferences()
          }}
          disabled={isSaving}
        >
          重置
        </Button>
        <Button onClick={handleSave} loading={isSaving}>
          保存设置
        </Button>
      </div>
    </PageShell>
  )
}
