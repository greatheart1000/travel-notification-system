import { useState } from 'react'
import { Header } from '../components/Header'
import { Card } from '../components/Card'
import { Button } from '../components/Button'
import { Badge } from '../components/Badge'
import { Modal } from '../components/Modal'
import { Plus, Send, Copy, Eye } from 'lucide-react'

export function Notifications() {
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [notifications] = useState([
    {
      id: 1,
      name: '每日提醒',
      template: '{{customer_name}}，您好，明日行程请注意保暖并准时集合。',
      channel: '短信',
      status: '启用',
      sentCount: 1234,
      successRate: '98.5%',
    },
    {
      id: 2,
      name: '出发前24小时',
      template: '尊敬的{{customer_name}}，您的{{destination}}行程将于24小时后出发...',
      channel: '企业微信',
      status: '启用',
      sentCount: 856,
      successRate: '99.2%',
    },
    {
      id: 3,
      name: '行程延迟通知',
      template: '由于{{reason}}，您的行程将延迟{{delay_hours}}小时出发...',
      channel: '短信',
      status: '禁用',
      sentCount: 45,
      successRate: '97.8%',
    },
  ])

  return (
    <>
      <Header />
      <div className="p-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-bold text-gray-900">通知中心</h1>
          <Button onClick={() => setIsModalOpen(true)}>
            <Plus className="w-5 h-5 inline mr-2" />
            新建模板
          </Button>
        </div>

        {/* Notification Templates */}
        <div className="space-y-4">
          {notifications.map((notif) => (
            <Card key={notif.id}>
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-lg font-semibold text-gray-900">{notif.name}</h3>
                    <Badge variant={notif.status === '启用' ? 'success' : 'default'}>
                      {notif.status}
                    </Badge>
                  </div>
                  <p className="text-gray-600 mb-4">{notif.template}</p>
                  <div className="flex items-center gap-6 text-sm text-gray-500">
                    <span>渠道: {notif.channel}</span>
                    <span>已发送: {notif.sentCount}</span>
                    <span>成功率: {notif.successRate}</span>
                  </div>
                </div>
                <div className="flex gap-2 ml-4">
                  <button className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition">
                    <Eye className="w-5 h-5" />
                  </button>
                  <button className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition">
                    <Copy className="w-5 h-5" />
                  </button>
                  <button className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition">
                    <Send className="w-5 h-5" />
                  </button>
                </div>
              </div>
            </Card>
          ))}
        </div>

        {/* Create Template Modal */}
        <Modal
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          title="新建通知模板"
          footer={
            <div className="flex gap-2 justify-end">
              <Button variant="secondary" onClick={() => setIsModalOpen(false)}>
                取消
              </Button>
              <Button onClick={() => setIsModalOpen(false)}>
                创建
              </Button>
            </div>
          }
        >
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                模板名称
              </label>
              <input
                type="text"
                placeholder="例：每日提醒"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                发送渠道
              </label>
              <select className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
                <option>短信</option>
                <option>企业微信</option>
                <option>邮件</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                模板内容 (支持 {{variable}} 格式)
              </label>
              <textarea
                placeholder="例：{{customer_name}}，您好，明日行程请注意保暖并准时集合。"
                rows={4}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </Modal>
      </div>
    </>
  )
}
