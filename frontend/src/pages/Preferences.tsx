import { useState } from 'react'
import { Header } from '../components/Header'
import { Card } from '../components/Card'
import { Button } from '../components/Button'
import { Bell, Clock, Shield, Zap } from 'lucide-react'

export function Preferences() {
  const [preferences, setPreferences] = useState({
    smsEnabled: true,
    wechatEnabled: true,
    emailEnabled: false,
    quietHourStart: '22',
    quietHourEnd: '08',
    maxNotificationsPerHour: 5,
    autoEscalation: true,
    aggregateNotifications: true,
  })

  const handleToggle = (key: keyof typeof preferences) => {
    setPreferences({
      ...preferences,
      [key]: !preferences[key],
    })
  }

  const handleChange = (key: keyof typeof preferences, value: any) => {
    setPreferences({
      ...preferences,
      [key]: value,
    })
  }

  return (
    <>
      <Header />
      <div className="p-8 max-w-4xl">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">偏好设置</h1>

        {/* Notification Channels */}
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

        {/* Quiet Hours */}
        <Card title="静默时段" className="mb-6">
          <div className="space-y-4">
            <div className="flex items-center gap-3 mb-4">
              <Clock className="w-5 h-5 text-orange-600" />
              <p className="text-gray-600">在此时段内不会发送通知</p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  开始时间
                </label>
                <select
                  value={preferences.quietHourStart}
                  onChange={(e) => handleChange('quietHourStart', e.target.value)}
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
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  结束时间
                </label>
                <select
                  value={preferences.quietHourEnd}
                  onChange={(e) => handleChange('quietHourEnd', e.target.value)}
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

        {/* Rate Limiting */}
        <Card title="频率限制" className="mb-6">
          <div className="space-y-4">
            <div className="flex items-center gap-3 mb-4">
              <Zap className="w-5 h-5 text-yellow-600" />
              <p className="text-gray-600">控制通知的发送频率</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                每小时最大通知数
              </label>
              <input
                type="number"
                value={preferences.maxNotificationsPerHour}
                onChange={(e) => handleChange('maxNotificationsPerHour', parseInt(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                min="1"
                max="20"
              />
              <p className="text-xs text-gray-500 mt-1">
                当每小时通知数超过此值时将进行聚合
              </p>
            </div>
          </div>
        </Card>

        {/* Advanced Settings */}
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

        {/* Save Button */}
        <div className="flex justify-end gap-2">
          <Button variant="secondary">重置</Button>
          <Button>保存设置</Button>
        </div>
      </div>
    </>
  )
}
