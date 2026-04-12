import { useEffect, useState } from 'react'
import { Header } from '../components/Header'
import { Card } from '../components/Card'
import { Button } from '../components/Button'
import { Badge } from '../components/Badge'
import { Modal } from '../components/Modal'
import { PageState } from '../components/PageState'
import { Plus, Send, Copy, Eye } from 'lucide-react'
import { notificationsApi, getErrorMessage } from '../services/api'
import { type ChannelCode, type NotificationTemplate } from '../types/api'

type LoadState = 'loading' | 'ready' | 'error' | 'empty'

interface TemplateFormState {
  name: string
  template: string
  channel: ChannelCode
}

const EMPTY_FORM: TemplateFormState = {
  name: '',
  template: '',
  channel: 'sms',
}

export function Notifications() {
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [templates, setTemplates] = useState<NotificationTemplate[]>([])
  const [form, setForm] = useState<TemplateFormState>(EMPTY_FORM)

  const [loadState, setLoadState] = useState<LoadState>('loading')
  const [errorMessage, setErrorMessage] = useState('')
  const [actionMessage, setActionMessage] = useState<string | null>(null)
  const [isSending, setIsSending] = useState<string | null>(null)
  const [isCreating, setIsCreating] = useState(false)

  const loadTemplates = async () => {
    setLoadState('loading')
    setErrorMessage('')

    try {
      const list = await notificationsApi.listTemplates()
      setTemplates(list)
      setLoadState(list.length === 0 ? 'empty' : 'ready')
    } catch (error) {
      setLoadState('error')
      setErrorMessage(getErrorMessage(error))
    }
  }

  useEffect(() => {
    void loadTemplates()
  }, [])

  const sendNow = async (templateId: string, channel: ChannelCode) => {
    setIsSending(templateId)
    setActionMessage(null)

    try {
      await notificationsApi.send({
        templateId,
        channel,
        customerName: '联调用户',
        trip: '联调行程',
      })
      setActionMessage('通知发送成功')
    } catch (error) {
      setActionMessage(`发送失败: ${getErrorMessage(error)}`)
    } finally {
      setIsSending(null)
    }
  }

  const createTemplate = async () => {
    if (!form.name.trim() || !form.template.trim()) {
      setActionMessage('创建失败: 请填写模板名称和模板内容')
      return
    }

    setIsCreating(true)
    setActionMessage(null)

    try {
      await notificationsApi.createTemplate({
        name: form.name.trim(),
        template: form.template.trim(),
        channel: form.channel,
      })
      setIsModalOpen(false)
      setForm(EMPTY_FORM)
      setActionMessage('模板创建成功')
      await loadTemplates()
    } catch (error) {
      setActionMessage(`创建失败: ${getErrorMessage(error)}`)
    } finally {
      setIsCreating(false)
    }
  }

  const pageHeader = (
    <div className="flex items-center justify-between mb-8">
      <h1 className="text-3xl font-bold text-gray-900">通知中心</h1>
      <Button onClick={() => setIsModalOpen(true)}>
        <Plus className="w-5 h-5 inline mr-2" />
        新建模板
      </Button>
    </div>
  )

  return (
    <>
      <Header />
      <div className="p-8">
        {pageHeader}

        {actionMessage ? (
          <p className={`text-sm mb-4 ${actionMessage.includes('失败') ? 'text-red-600' : 'text-green-600'}`}>
            {actionMessage}
          </p>
        ) : null}

        {loadState === 'loading' ? <PageState kind="loading" title="正在加载通知模板" /> : null}

        {loadState === 'error' ? (
          <PageState
            kind="error"
            title="通知模板加载失败"
            description={errorMessage}
            onRetry={() => {
              void loadTemplates()
            }}
          />
        ) : null}

        {loadState === 'empty' ? (
          <PageState
            kind="empty"
            title="暂无通知模板"
            description="当前还没有可用模板"
            onRetry={() => {
              void loadTemplates()
            }}
          />
        ) : null}

        {loadState === 'ready' ? (
          <div className="space-y-4">
            {templates.map((template) => (
              <Card key={template.id}>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-lg font-semibold text-gray-900">{template.name}</h3>
                      <Badge variant={template.enabled ? 'success' : 'default'}>{template.statusLabel}</Badge>
                    </div>
                    <p className="text-gray-600 mb-4">{template.template}</p>
                    <div className="flex items-center gap-6 text-sm text-gray-500">
                      <span>渠道: {template.channelLabel}</span>
                      <span>已发送: {template.sentCount}</span>
                      <span>成功率: {template.successRate}</span>
                    </div>
                  </div>
                  <div className="flex gap-2 ml-4">
                    <button className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition" aria-label="预览模板">
                      <Eye className="w-5 h-5" />
                    </button>
                    <button className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition" aria-label="复制模板">
                      <Copy className="w-5 h-5" />
                    </button>
                    <button
                      className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition disabled:opacity-50"
                      onClick={() => {
                        void sendNow(template.id, template.channel)
                      }}
                      disabled={isSending === template.id}
                      aria-label="发送通知"
                    >
                      <Send className="w-5 h-5" />
                    </button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        ) : null}

        <Modal
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          title="新建通知模板"
          footer={
            <div className="flex gap-2 justify-end">
              <Button variant="secondary" onClick={() => setIsModalOpen(false)}>
                取消
              </Button>
              <Button
                onClick={() => {
                  void createTemplate()
                }}
                loading={isCreating}
              >
                创建
              </Button>
            </div>
          }
        >
          <div className="space-y-4">
            <input
              type="text"
              placeholder="模板名称"
              value={form.name}
              onChange={(event) => setForm((prev) => ({ ...prev, name: event.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            />
            <select
              value={form.channel}
              onChange={(event) => setForm((prev) => ({ ...prev, channel: event.target.value as ChannelCode }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            >
              <option value="sms">短信</option>
              <option value="wechat_work_group">企业微信</option>
              <option value="email">邮件</option>
            </select>
            <textarea
              placeholder="模板内容"
              rows={4}
              value={form.template}
              onChange={(event) => setForm((prev) => ({ ...prev, template: event.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            />
          </div>
        </Modal>
      </div>
    </>
  )
}
