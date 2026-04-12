import { useEffect, useState } from 'react'
import { Header } from '../components/Header'
import { Card } from '../components/Card'
import { Button } from '../components/Button'
import { PageState } from '../components/PageState'
import { Bell, Clock, Shield, Zap } from 'lucide-react'
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
      setSaveMessage(`保存失败: ${getErrorMessage(error)}`)
    } finally {
      setIsSaving(false)
    }
  }

  if (loadState === 'loading') {
    return (
      <>
        <Header />
        <div className="p-8 max-w-4xl">
          <PageState kind="loading" title="正在加载偏好设置" />
        </div>
      </>
    )
  }

  if (loadState === 'error') {
    return (
      <>
        <Header />
        <div className="p-8 max-w-4xl">
          <PageState
            kind="error"
            title="偏好设置加载失败"
            description={errorMessage}
            onRetry={() => {
              void loadPreferences()
            }}
          />
        </div>
      </>
    )
  }

  if (!preferences) {
    return (
      <>
        <Header />
        <div className="p-8 max-w-4xl">
          <PageState
            kind="empty"
            title="未获取到偏好设置"
            description="后端未返回可用数据"
            onRetry={() => {
              void loadPreferences()
            }}
          />
        </div>
      </>
    )
  }

  const showEmptyHint = loadState === 'empty'

  return (
    <>
      <Header />
      <div className="p-8 max-w-4xl">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">偏好设置</h1>

        {showEmptyHint ? (
          <div className="mb-6">
            <PageState
              kind="empty"
              title="当前未启用任何通知渠道"
              description="至少开启一个渠道后保存，配置才会生效"
              onRetry={() => {
                void loadPreferences()
              }}
            />
          </div>
        ) : null}

        <Card title="通知渠道" className="mb-6">
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
              <div className="flex items-center gap-3">
                <Bell className="w-5 h-5 text-blue-600" />
                <div>
                  <p className="font-medium text-gray-900">短信通知</p>
                  <p className="text-sm text-gray-500">通过短信发送重要通知</p>
                </div>
              </div>
              <input
                type="checkbox"
                checked={preferences.smsEnabled}
                onChange={() => handleToggle('smsEnabled')}
                className="w-5 h-5 rounded"
              />
            </div>

            <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
              <div className="flex items-center gap-3">
                <Bell className="w-5 h-5 text-green-600" />
                <div>
                  <p className="font-medium text-gray-900">企业微信</p>
                  <p className="text-sm text-gray-500">通过企业微信群发送通知</p>
                </div>
              </div>
              <input
                type="checkbox"
                checked={preferences.wechatEnabled}
                onChange={() => handleToggle('wechatEnabled')}
                className="w-5 h-5 rounded"
              />
            </div>

            <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
              <div className="flex items-center gap-3">
                <Bell className="w-5 h-5 text-purple-600" />
                <div>
                  <p className="font-medium text-gray-900">邮件通知</p>
                  <p className="text-sm text-gray-500">通过邮件发送详细信息</p>
                </div>
              </div>
              <input
                type="checkbox"
                checked={preferences.emailEnabled}
                onChange={() => handleToggle('emailEnabled')}
                className="w-5 h-5 rounded"
              />
            </div>
          </div>
        </Card>

        <Card title="静默时段" className="mb-6">
          <div className="space-y-4">
            <div className="flex items-center gap-3 mb-4">
              <Clock className="w-5 h-5 text-orange-600" />
              <p className="text-gray-600">在此时段内不会发送通知</p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">开始时间</label>
                <select
                  value={preferences.quietHourStart}
                  onChange={(event) => handleChange('quietHourStart', event.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {Array.from({ length: 24 }, (_, i) => (
                    <option key={i} value={String(i).padStart(2, '0')}>
                      {String(i).padStart(2, '0')}:00
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">结束时间</label>
                <select
                  value={preferences.quietHourEnd}
                  onChange={(event) => handleChange('quietHourEnd', event.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {Array.from({ length: 24 }, (_, i) => (
                    <option key={i} value={String(i).padStart(2, '0')}>
                      {String(i).padStart(2, '0')}:00
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        </Card>

        <Card title="频率限制" className="mb-6">
          <div className="space-y-4">
            <div className="flex items-center gap-3 mb-4">
              <Zap className="w-5 h-5 text-yellow-600" />
              <p className="text-gray-600">控制通知的发送频率</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">每小时最大通知数</label>
              <input
                type="number"
                value={preferences.maxNotificationsPerHour}
                onChange={(event) => handleChange('maxNotificationsPerHour', toInt(event.target.value, 1))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                min="1"
                max="20"
              />
              <p className="text-xs text-gray-500 mt-1">当每小时通知数超过此值时将进行聚合</p>
            </div>
          </div>
        </Card>

        <Card title="高级设置" className="mb-6">
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
              <div className="flex items-center gap-3">
                <Shield className="w-5 h-5 text-red-600" />
                <div>
                  <p className="font-medium text-gray-900">自动升级</p>
                  <p className="text-sm text-gray-500">自动升级高风险投诉</p>
                </div>
              </div>
              <input
                type="checkbox"
                checked={preferences.autoEscalation}
                onChange={() => handleToggle('autoEscalation')}
                className="w-5 h-5 rounded"
              />
            </div>

            <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
              <div className="flex items-center gap-3">
                <Bell className="w-5 h-5 text-indigo-600" />
                <div>
                  <p className="font-medium text-gray-900">通知聚合</p>
                  <p className="text-sm text-gray-500">聚合相同类型的连续通知</p>
                </div>
              </div>
              <input
                type="checkbox"
                checked={preferences.aggregateNotifications}
                onChange={() => handleToggle('aggregateNotifications')}
                className="w-5 h-5 rounded"
              />
            </div>
          </div>
        </Card>

        {saveMessage ? (
          <p className={`text-sm mb-4 ${saveMessage.startsWith('保存失败') ? 'text-red-600' : 'text-green-600'}`}>
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
      </div>
    </>
  )
}
