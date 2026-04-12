import { useEffect, useState } from 'react'
import { Header } from '../components/Header'
import { Card } from '../components/Card'
import { Button } from '../components/Button'
import { Badge } from '../components/Badge'
import { Modal } from '../components/Modal'
import { PageState } from '../components/PageState'
import { Plus, Send, Copy, Eye, Pencil, Trash2, Power } from 'lucide-react'
import { notificationsApi, getErrorMessage } from '../services/api'
import {
  type ChannelCode,
  type NotificationRule,
  type NotificationRuleStageCode,
  type NotificationRuleTimeSlotCode,
  type NotificationTemplate,
} from '../types/api'

type LoadState = 'loading' | 'ready' | 'error' | 'empty'

interface TemplateFormState {
  name: string
  template: string
  channel: ChannelCode
}

interface RuleFormState {
  name: string
  stage: NotificationRuleStageCode
  timeSlot: NotificationRuleTimeSlotCode
  scene: string
  enabled: boolean
  priority: number
  templateId: string
}

const EMPTY_TEMPLATE_FORM: TemplateFormState = {
  name: '',
  template: '',
  channel: 'sms',
}

const EMPTY_RULE_FORM: RuleFormState = {
  name: '',
  stage: 'pre_trip',
  timeSlot: 'morning',
  scene: '',
  enabled: true,
  priority: 100,
  templateId: '',
}

const RULE_STAGE_OPTIONS: Array<{ value: NotificationRuleStageCode; label: string }> = [
  { value: 'pre_trip', label: '出行前' },
  { value: 'on_trip', label: '出行中' },
  { value: 'post_trip', label: '出行后' },
  { value: 'custom', label: '自定义' },
]

const RULE_TIME_SLOT_OPTIONS: Array<{ value: NotificationRuleTimeSlotCode; label: string }> = [
  { value: 'morning', label: '早间' },
  { value: 'afternoon', label: '下午' },
  { value: 'evening', label: '傍晚' },
  { value: 'night', label: '夜间' },
  { value: 'all_day', label: '全天' },
]

export function Notifications() {
  const [isTemplateModalOpen, setIsTemplateModalOpen] = useState(false)
  const [templates, setTemplates] = useState<NotificationTemplate[]>([])
  const [templateForm, setTemplateForm] = useState<TemplateFormState>(EMPTY_TEMPLATE_FORM)

  const [templateLoadState, setTemplateLoadState] = useState<LoadState>('loading')
  const [templateErrorMessage, setTemplateErrorMessage] = useState('')
  const [templateActionMessage, setTemplateActionMessage] = useState<string | null>(null)
  const [isSending, setIsSending] = useState<string | null>(null)
  const [isTemplateCreating, setIsTemplateCreating] = useState(false)

  const [isRuleModalOpen, setIsRuleModalOpen] = useState(false)
  const [editingRuleId, setEditingRuleId] = useState<string | null>(null)
  const [ruleForm, setRuleForm] = useState<RuleFormState>(EMPTY_RULE_FORM)

  const [ruleLoadState, setRuleLoadState] = useState<LoadState>('loading')
  const [rules, setRules] = useState<NotificationRule[]>([])
  const [ruleErrorMessage, setRuleErrorMessage] = useState('')
  const [ruleActionMessage, setRuleActionMessage] = useState<string | null>(null)
  const [isRuleSaving, setIsRuleSaving] = useState(false)
  const [isRuleTogglingId, setIsRuleTogglingId] = useState<string | null>(null)
  const [isRuleDeletingId, setIsRuleDeletingId] = useState<string | null>(null)

  const loadTemplates = async () => {
    setTemplateLoadState('loading')
    setTemplateErrorMessage('')

    try {
      const list = await notificationsApi.listTemplates()
      setTemplates(list)
      setTemplateLoadState(list.length === 0 ? 'empty' : 'ready')
    } catch (error) {
      setTemplateLoadState('error')
      setTemplateErrorMessage(getErrorMessage(error))
    }
  }

  const loadRules = async () => {
    setRuleLoadState('loading')
    setRuleErrorMessage('')

    try {
      const list = await notificationsApi.listRules()
      setRules(list)
      setRuleLoadState(list.length === 0 ? 'empty' : 'ready')
    } catch (error) {
      setRuleLoadState('error')
      setRuleErrorMessage(getErrorMessage(error))
    }
  }

  useEffect(() => {
    void loadTemplates()
    void loadRules()
  }, [])

  const sendNow = async (templateId: string, channel: ChannelCode) => {
    setIsSending(templateId)
    setTemplateActionMessage(null)

    try {
      await notificationsApi.send({
        templateId,
        channel,
        customerName: '联调用户',
        trip: '联调行程',
      })
      setTemplateActionMessage('通知发送成功')
    } catch (error) {
      setTemplateActionMessage(`发送失败: ${getErrorMessage(error)}`)
    } finally {
      setIsSending(null)
    }
  }

  const createTemplate = async () => {
    if (!templateForm.name.trim() || !templateForm.template.trim()) {
      setTemplateActionMessage('创建失败: 请填写模板名称和模板内容')
      return
    }

    setIsTemplateCreating(true)
    setTemplateActionMessage(null)

    try {
      await notificationsApi.createTemplate({
        name: templateForm.name.trim(),
        template: templateForm.template.trim(),
        channel: templateForm.channel,
      })
      setIsTemplateModalOpen(false)
      setTemplateForm(EMPTY_TEMPLATE_FORM)
      setTemplateActionMessage('模板创建成功')
      await loadTemplates()
    } catch (error) {
      setTemplateActionMessage(`创建失败: ${getErrorMessage(error)}`)
    } finally {
      setIsTemplateCreating(false)
    }
  }

  const openCreateRuleModal = () => {
    setEditingRuleId(null)
    setRuleForm({
      ...EMPTY_RULE_FORM,
      templateId: templates[0]?.id ?? '',
    })
    setIsRuleModalOpen(true)
  }

  const openEditRuleModal = (rule: NotificationRule) => {
    setEditingRuleId(rule.id)
    setRuleForm({
      name: rule.name,
      stage: rule.stage === 'unknown' ? 'custom' : rule.stage,
      timeSlot: rule.timeSlot === 'unknown' ? 'all_day' : rule.timeSlot,
      scene: rule.scene,
      enabled: rule.enabled,
      priority: rule.priority,
      templateId: rule.templateId,
    })
    setIsRuleModalOpen(true)
  }

  const saveRule = async () => {
    if (!ruleForm.name.trim()) {
      setRuleActionMessage('规则保存失败: 请填写规则名称')
      return
    }
    if (!ruleForm.scene.trim()) {
      setRuleActionMessage('规则保存失败: 请填写场景')
      return
    }
    if (!ruleForm.templateId.trim()) {
      setRuleActionMessage('规则保存失败: 请绑定模板')
      return
    }

    setIsRuleSaving(true)
    setRuleActionMessage(null)

    try {
      if (editingRuleId) {
        await notificationsApi.updateRule(editingRuleId, {
          name: ruleForm.name.trim(),
          stage: ruleForm.stage,
          timeSlot: ruleForm.timeSlot,
          scene: ruleForm.scene.trim(),
          enabled: ruleForm.enabled,
          priority: ruleForm.priority,
          templateId: ruleForm.templateId,
        })
        setRuleActionMessage('规则更新成功')
      } else {
        await notificationsApi.createRule({
          name: ruleForm.name.trim(),
          stage: ruleForm.stage,
          timeSlot: ruleForm.timeSlot,
          scene: ruleForm.scene.trim(),
          enabled: ruleForm.enabled,
          priority: ruleForm.priority,
          templateId: ruleForm.templateId,
        })
        setRuleActionMessage('规则创建成功')
      }

      setIsRuleModalOpen(false)
      setEditingRuleId(null)
      await loadRules()
    } catch (error) {
      setRuleActionMessage(`规则保存失败: ${getErrorMessage(error)}`)
    } finally {
      setIsRuleSaving(false)
    }
  }

  const toggleRule = async (rule: NotificationRule) => {
    setIsRuleTogglingId(rule.id)
    setRuleActionMessage(null)

    try {
      await notificationsApi.toggleRule(rule.id, !rule.enabled)
      setRuleActionMessage(`规则已${rule.enabled ? '停用' : '启用'}`)
      await loadRules()
    } catch (error) {
      setRuleActionMessage(`规则启停失败: ${getErrorMessage(error)}`)
    } finally {
      setIsRuleTogglingId(null)
    }
  }

  const deleteRule = async (rule: NotificationRule) => {
    setIsRuleDeletingId(rule.id)
    setRuleActionMessage(null)

    try {
      await notificationsApi.deleteRule(rule.id)
      setRuleActionMessage('规则删除成功')
      await loadRules()
    } catch (error) {
      setRuleActionMessage(`规则删除失败: ${getErrorMessage(error)}`)
    } finally {
      setIsRuleDeletingId(null)
    }
  }

  return (
    <>
      <Header />
      <div className="p-8">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-bold text-gray-900">通知中心</h1>
          <Button onClick={() => setIsTemplateModalOpen(true)}>
            <Plus className="w-5 h-5 inline mr-2" />
            新建模板
          </Button>
        </div>

        {templateActionMessage ? (
          <p className={`text-sm mb-4 ${templateActionMessage.includes('失败') ? 'text-red-600' : 'text-green-600'}`}>
            {templateActionMessage}
          </p>
        ) : null}

        {templateLoadState === 'loading' ? <PageState kind="loading" title="正在加载通知模板" /> : null}

        {templateLoadState === 'error' ? (
          <PageState
            kind="error"
            title="通知模板加载失败"
            description={templateErrorMessage}
            onRetry={() => {
              void loadTemplates()
            }}
          />
        ) : null}

        {templateLoadState === 'empty' ? (
          <PageState
            kind="empty"
            title="暂无通知模板"
            description="当前还没有可用模板"
            onRetry={() => {
              void loadTemplates()
            }}
          />
        ) : null}

        {templateLoadState === 'ready' ? (
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

        <div className="flex items-center justify-between mt-10 mb-4">
          <h2 className="text-2xl font-bold text-gray-900">规则配置</h2>
          <Button onClick={openCreateRuleModal}>
            <Plus className="w-4 h-4 inline mr-2" />
            新建规则
          </Button>
        </div>

        {ruleActionMessage ? (
          <p className={`text-sm mb-4 ${ruleActionMessage.includes('失败') ? 'text-red-600' : 'text-green-600'}`}>
            {ruleActionMessage}
          </p>
        ) : null}

        <Card>
          {ruleLoadState === 'loading' ? <PageState kind="loading" title="正在加载通知规则" /> : null}

          {ruleLoadState === 'error' ? (
            <PageState
              kind="error"
              title="通知规则加载失败"
              description={ruleErrorMessage}
              onRetry={() => {
                void loadRules()
              }}
            />
          ) : null}

          {ruleLoadState === 'empty' ? (
            <PageState
              kind="empty"
              title="暂无通知规则"
              description="可以新建一条规则配置"
              onRetry={() => {
                void loadRules()
              }}
            />
          ) : null}

          {ruleLoadState === 'ready' ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 px-4 font-semibold text-gray-700">规则名称</th>
                    <th className="text-left py-3 px-4 font-semibold text-gray-700">阶段</th>
                    <th className="text-left py-3 px-4 font-semibold text-gray-700">时段</th>
                    <th className="text-left py-3 px-4 font-semibold text-gray-700">场景</th>
                    <th className="text-left py-3 px-4 font-semibold text-gray-700">启停</th>
                    <th className="text-left py-3 px-4 font-semibold text-gray-700">优先级</th>
                    <th className="text-left py-3 px-4 font-semibold text-gray-700">模板</th>
                    <th className="text-left py-3 px-4 font-semibold text-gray-700">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {rules.map((rule) => (
                    <tr key={rule.id} className="border-b border-gray-100 hover:bg-gray-50 transition">
                      <td className="py-3 px-4 font-medium text-gray-900">{rule.name}</td>
                      <td className="py-3 px-4">{rule.stageLabel}</td>
                      <td className="py-3 px-4">{rule.timeSlotLabel}</td>
                      <td className="py-3 px-4 text-gray-700">{rule.scene}</td>
                      <td className="py-3 px-4">
                        <Badge variant={rule.enabled ? 'success' : 'default'}>
                          {rule.enabled ? '启用' : '停用'}
                        </Badge>
                      </td>
                      <td className="py-3 px-4">{rule.priority}</td>
                      <td className="py-3 px-4 text-gray-700">{rule.templateLabel}</td>
                      <td className="py-3 px-4">
                        <div className="flex gap-2">
                          <Button variant="secondary" size="sm" onClick={() => openEditRuleModal(rule)}>
                            <Pencil className="w-3 h-3 inline mr-1" />
                            编辑
                          </Button>
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => {
                              void toggleRule(rule)
                            }}
                            disabled={isRuleTogglingId === rule.id}
                          >
                            <Power className="w-3 h-3 inline mr-1" />
                            {rule.enabled ? '停用' : '启用'}
                          </Button>
                          <Button
                            variant="danger"
                            size="sm"
                            onClick={() => {
                              void deleteRule(rule)
                            }}
                            disabled={isRuleDeletingId === rule.id}
                          >
                            <Trash2 className="w-3 h-3 inline mr-1" />
                            删除
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </Card>

        <Modal
          isOpen={isTemplateModalOpen}
          onClose={() => setIsTemplateModalOpen(false)}
          title="新建通知模板"
          footer={
            <div className="flex gap-2 justify-end">
              <Button variant="secondary" onClick={() => setIsTemplateModalOpen(false)}>
                取消
              </Button>
              <Button
                onClick={() => {
                  void createTemplate()
                }}
                loading={isTemplateCreating}
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
              value={templateForm.name}
              onChange={(event) => setTemplateForm((prev) => ({ ...prev, name: event.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            />
            <select
              value={templateForm.channel}
              onChange={(event) => setTemplateForm((prev) => ({ ...prev, channel: event.target.value as ChannelCode }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            >
              <option value="sms">短信</option>
              <option value="wechat_work_group">企业微信</option>
              <option value="email">邮件</option>
            </select>
            <textarea
              placeholder="模板内容"
              rows={4}
              value={templateForm.template}
              onChange={(event) => setTemplateForm((prev) => ({ ...prev, template: event.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            />
          </div>
        </Modal>

        <Modal
          isOpen={isRuleModalOpen}
          onClose={() => setIsRuleModalOpen(false)}
          title={editingRuleId ? '编辑通知规则' : '新建通知规则'}
          footer={
            <div className="flex gap-2 justify-end">
              <Button variant="secondary" onClick={() => setIsRuleModalOpen(false)}>
                取消
              </Button>
              <Button
                onClick={() => {
                  void saveRule()
                }}
                loading={isRuleSaving}
              >
                保存
              </Button>
            </div>
          }
        >
          <div className="space-y-4">
            <div>
              <label className="block text-sm text-gray-700 mb-1">规则名称</label>
              <input
                type="text"
                value={ruleForm.name}
                onChange={(event) => setRuleForm((prev) => ({ ...prev, name: event.target.value }))}
                placeholder="例如：出发前安全提醒"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-gray-700 mb-1">阶段</label>
                <select
                  value={ruleForm.stage}
                  onChange={(event) =>
                    setRuleForm((prev) => ({ ...prev, stage: event.target.value as NotificationRuleStageCode }))
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                >
                  {RULE_STAGE_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm text-gray-700 mb-1">时段</label>
                <select
                  value={ruleForm.timeSlot}
                  onChange={(event) =>
                    setRuleForm((prev) => ({ ...prev, timeSlot: event.target.value as NotificationRuleTimeSlotCode }))
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                >
                  {RULE_TIME_SLOT_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label className="block text-sm text-gray-700 mb-1">场景</label>
              <input
                type="text"
                value={ruleForm.scene}
                onChange={(event) => setRuleForm((prev) => ({ ...prev, scene: event.target.value }))}
                placeholder="例如：高原天气预警"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-gray-700 mb-1">优先级</label>
                <input
                  type="number"
                  min={1}
                  value={ruleForm.priority}
                  onChange={(event) =>
                    setRuleForm((prev) => ({ ...prev, priority: Number(event.target.value) || 1 }))
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-700 mb-1">状态</label>
                <select
                  value={ruleForm.enabled ? 'enabled' : 'disabled'}
                  onChange={(event) => setRuleForm((prev) => ({ ...prev, enabled: event.target.value === 'enabled' }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                >
                  <option value="enabled">启用</option>
                  <option value="disabled">停用</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-sm text-gray-700 mb-1">绑定模板</label>
              {templates.length > 0 ? (
                <select
                  value={ruleForm.templateId}
                  onChange={(event) => setRuleForm((prev) => ({ ...prev, templateId: event.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                >
                  <option value="">请选择模板</option>
                  {templates.map((template) => (
                    <option key={template.id} value={template.id}>
                      {template.name}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type="text"
                  value={ruleForm.templateId}
                  onChange={(event) => setRuleForm((prev) => ({ ...prev, templateId: event.target.value }))}
                  placeholder="输入模板 ID"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              )}
            </div>
          </div>
        </Modal>
      </div>
    </>
  )
}
