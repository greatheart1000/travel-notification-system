import { useEffect, useState } from 'react'
import { Header } from '../components/Header'
import { Card } from '../components/Card'
import { Button } from '../components/Button'
import { Badge } from '../components/Badge'
import { Modal } from '../components/Modal'
import { Plus, Send, Copy, Eye } from 'lucide-react'
import { notificationsApi } from '../services/api'

export function Notifications() {
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [notifications, setNotifications] = useState<any[]>([])
  const [form, setForm] = useState({ name: '', template: '', channel: '短信' })

  const loadTemplates = async () => {
    const res = await notificationsApi.listTemplates()
    setNotifications(res.data.items)
  }

  useEffect(() => {
    loadTemplates()
  }, [])

  const sendNow = async (templateId: string, channel: string) => {
    await notificationsApi.send({ template_id: templateId, channel, customer_name: '联调用户', trip: '联调行程' })
    alert('发送成功')
  }

  return (
    <>
      <Header />
      <div className="p-8">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-bold text-gray-900">通知中心</h1>
          <Button onClick={() => setIsModalOpen(true)}>
            <Plus className="w-5 h-5 inline mr-2" />
            新建模板
          </Button>
        </div>

        <div className="space-y-4">
          {notifications.map((notif) => (
            <Card key={notif.id}>
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-lg font-semibold text-gray-900">{notif.name}</h3>
                    <Badge variant={notif.status === '启用' ? 'success' : 'default'}>{notif.status}</Badge>
                  </div>
                  <p className="text-gray-600 mb-4">{notif.template}</p>
                  <div className="flex items-center gap-6 text-sm text-gray-500">
                    <span>渠道: {notif.channel}</span>
                    <span>已发送: {notif.sent_count}</span>
                    <span>成功率: {notif.success_rate}</span>
                  </div>
                </div>
                <div className="flex gap-2 ml-4">
                  <button className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition"><Eye className="w-5 h-5" /></button>
                  <button className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition"><Copy className="w-5 h-5" /></button>
                  <button className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition" onClick={() => sendNow(notif.id, notif.channel)}><Send className="w-5 h-5" /></button>
                </div>
              </div>
            </Card>
          ))}
        </div>

        <Modal
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          title="新建通知模板"
          footer={<div className="flex gap-2 justify-end"><Button variant="secondary" onClick={() => setIsModalOpen(false)}>取消</Button><Button onClick={() => { setIsModalOpen(false); setForm({ name: '', template: '', channel: '短信' }) }}>创建</Button></div>}
        >
          <div className="space-y-4">
            <input type="text" placeholder="模板名称" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg" />
            <select value={form.channel} onChange={(e) => setForm({ ...form, channel: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg"><option>短信</option><option>企业微信</option><option>邮件</option></select>
            <textarea placeholder="模板内容" rows={4} value={form.template} onChange={(e) => setForm({ ...form, template: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg" />
          </div>
        </Modal>
      </div>
    </>
  )
}
