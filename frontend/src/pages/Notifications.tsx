import { useEffect, useState } from 'react'
import { Badge } from '../components/Badge'
import { Button } from '../components/Button'
import { Card } from '../components/Card'
import { Modal } from '../components/Modal'
import { PageShell } from '../components/PageShell'
import { PageState } from '../components/PageState'
import { EmergencyWeatherSummaryPanel } from '../components/notifications/EmergencyWeatherSummaryPanel'
import { TripNotificationConfigFormPanel } from '../components/notifications/TripNotificationConfigFormPanel'
import {
  ArrowLeft,
  Copy,
  Eye,
  Pencil,
  Plus,
  Power,
  Send,
  Trash2,
} from 'lucide-react'
import { getErrorMessage, notificationsApi, tripsApi } from '../services/api'
import {
  type ChannelCode,
  type EmergencyWeatherSummary,
  type NotificationRule,
  type NotificationRuleStageCode,
  type NotificationRuleTimeSlotCode,
  type NotificationTemplate,
  type ProjectNotificationConfig,
  type TripScheduleDay,
  type Trip,
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

interface TripDailyNotificationPreview {
  day: number
  date: string
  route: string
  morning: string
  afternoon: string
  evening: string
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

function SmsCell({ label }: { label: string }) {
  return (
    <p className="max-w-[220px] text-sm leading-6 text-slate-700">{label}</p>
  )
}

function formatUpdatedAt(value: string): string {
  if (!value) {
    return '暂无'
  }
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return value
  }
  return parsed.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function findTimeSlotTemplate(
  rules: NotificationRule[],
  templateById: Map<string, string>,
  slot: NotificationRuleTimeSlotCode,
): string {
  const matchedRule = rules.find((rule) => rule.enabled && (rule.timeSlot === slot || rule.timeSlot === 'all_day'))
  if (!matchedRule) {
    return '—'
  }
  const matchedTemplate = (templateById.get(matchedRule.templateId) || matchedRule.templateLabel || matchedRule.scene).trim()
  return matchedTemplate ? matchedTemplate.slice(0, 48) : '—'
}

function buildTripDailyNotificationPreview(
  days: TripScheduleDay[],
  rules: NotificationRule[],
  templates: NotificationTemplate[],
): TripDailyNotificationPreview[] {
  const templateById = new Map(templates.map((template) => [template.id, template.template]))
  const onTripRules = rules.filter((rule) => rule.stage === 'on_trip' || rule.stage === 'custom')
  return days.map((day) => ({
    day: day.day,
    date: day.date,
    route: day.route || day.title || `Day ${day.day}`,
    morning: findTimeSlotTemplate(onTripRules, templateById, 'morning'),
    afternoon: findTimeSlotTemplate(onTripRules, templateById, 'afternoon'),
    evening: findTimeSlotTemplate(onTripRules, templateById, 'evening'),
  }))
}

interface NotificationsProps {
  tripId?: string | null
  onBackToTrip?: (tripId: string) => void
}

export function Notifications({ tripId = null, onBackToTrip }: NotificationsProps) {
  const [isTemplateModalOpen, setIsTemplateModalOpen] = useState(false)
  const [editingTemplateId, setEditingTemplateId] = useState<string | null>(null)
  const [templates, setTemplates] = useState<NotificationTemplate[]>([])
  const [templateForm, setTemplateForm] = useState<TemplateFormState>(EMPTY_TEMPLATE_FORM)
  const [templateLoadState, setTemplateLoadState] = useState<LoadState>('loading')
  const [templateErrorMessage, setTemplateErrorMessage] = useState('')
  const [templateActionMessage, setTemplateActionMessage] = useState<string | null>(null)
  const [isSending, setIsSending] = useState<string | null>(null)
  const [isTemplateCreating, setIsTemplateCreating] = useState(false)
  const [isTemplateDeletingId, setIsTemplateDeletingId] = useState<string | null>(null)

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

  const [weatherLoadState, setWeatherLoadState] = useState<LoadState>('loading')
  const [weatherSummary, setWeatherSummary] = useState<EmergencyWeatherSummary | null>(null)
  const [weatherErrorMessage, setWeatherErrorMessage] = useState('')
  const [weatherActionMessage, setWeatherActionMessage] = useState<string | null>(null)
  const [isWeatherEditorOpen, setIsWeatherEditorOpen] = useState(false)
  const [weatherDraft, setWeatherDraft] = useState('')
  const [isWeatherSending, setIsWeatherSending] = useState(false)
  const [tripConfigLoadState, setTripConfigLoadState] = useState<LoadState>('empty')
  const [tripConfigError, setTripConfigError] = useState('')
  const [tripConfigContext, setTripConfigContext] = useState<{ trip: Trip; config: ProjectNotificationConfig } | null>(null)
  const [tripConfigSaveMessage, setTripConfigSaveMessage] = useState<string | null>(null)
  const [isTripConfigSaving, setIsTripConfigSaving] = useState(false)
  const [tripScheduleDays, setTripScheduleDays] = useState<TripScheduleDay[]>([])

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

  const loadEmergencyWeather = async () => {
    setWeatherLoadState('loading')
    setWeatherErrorMessage('')
    try {
      const summary = await notificationsApi.getEmergencyWeatherSummary()
      setWeatherSummary(summary)
      setWeatherDraft(summary.generatedNotification)
      setWeatherLoadState('ready')
    } catch (error) {
      setWeatherLoadState('error')
      setWeatherErrorMessage(getErrorMessage(error))
    }
  }

  useEffect(() => {
    void loadTemplates()
    void loadRules()
    void loadEmergencyWeather()
  }, [])

  useEffect(() => {
    if (!tripId) {
      setTripConfigContext(null)
      setTripConfigLoadState('empty')
      setTripConfigError('')
      return
    }

    const loadTripConfigContext = async () => {
      setTripConfigLoadState('loading')
      setTripConfigError('')
      setTripConfigSaveMessage(null)
      setTripScheduleDays([])
      try {
        const [context, schedule] = await Promise.all([
          notificationsApi.getTripConfigContextByTripId(tripId),
          tripsApi.getSchedule(tripId),
        ])
        setTripConfigContext({ trip: context.trip, config: context.projectConfig })
        setTripScheduleDays(schedule.days)
        setTripConfigLoadState('ready')
      } catch (error) {
        setTripConfigLoadState('error')
        setTripConfigError(getErrorMessage(error))
      }
    }

    void loadTripConfigContext()
  }, [tripId])

  const saveTripConfig = async (draft: ProjectNotificationConfig) => {
    if (!tripId) {
      return
    }

    setIsTripConfigSaving(true)
    setTripConfigSaveMessage(null)
    try {
      const saved = await notificationsApi.upsertTripNotificationConfigByTripId(tripId, {
        projectName: draft.projectName,
        weatherEnabled: draft.weatherEnabled,
        qweatherCredentialId: draft.qweatherCredentialId,
        qweatherLocationId: draft.qweatherLocationId,
        qweatherLat: draft.qweatherLat,
        qweatherLon: draft.qweatherLon,
        weatherAlertThresholds: draft.weatherAlertThresholds,
        smsProvider: draft.smsProvider,
        smsSignName: draft.smsSignName,
        smsTemplateCodeNormal: draft.smsTemplateCodeNormal,
        smsTemplateCodeWeatherAlert: draft.smsTemplateCodeWeatherAlert,
        manualTakeoverTarget: draft.manualTakeoverTarget,
      })
      setTripConfigContext((prev) => (prev ? { ...prev, config: saved } : prev))
      setTripConfigSaveMessage('当前团通知配置保存成功')
    } catch (error) {
      setTripConfigSaveMessage(`当前团通知配置保存失败: ${getErrorMessage(error)}`)
    } finally {
      setIsTripConfigSaving(false)
    }
  }

  const sendNow = async (templateId: string, channel: ChannelCode) => {
    setIsSending(templateId)
    setTemplateActionMessage(null)
    try {
      await notificationsApi.send({ templateId, channel, customerName: '联调用户', trip: '联调行程' })
      setTemplateActionMessage('通知发送成功')
    } catch (error) {
      setTemplateActionMessage(`发送失败: ${getErrorMessage(error)}`)
    } finally {
      setIsSending(null)
    }
  }

  const sendEmergencyWeather = async (customContent?: string) => {
    if (!weatherSummary) {
      return
    }
    setIsWeatherSending(true)
    setWeatherActionMessage(null)
    try {
      const result = await notificationsApi.sendEmergencyWeather({
        alertId: weatherSummary.alertId,
        customContent,
        channel: weatherSummary.channel,
      })
      setWeatherActionMessage(`紧急通知发送成功，已触达 ${result.sentCount} 个旅行团`)
      setIsWeatherEditorOpen(false)
    } catch (error) {
      setWeatherActionMessage(`紧急通知发送失败: ${getErrorMessage(error)}`)
    } finally {
      setIsWeatherSending(false)
    }
  }

  const saveTemplate = async () => {
    if (!templateForm.name.trim() || !templateForm.template.trim()) {
      setTemplateActionMessage('创建失败: 请填写模板名称和模板内容')
      return
    }
    setIsTemplateCreating(true)
    setTemplateActionMessage(null)
    try {
      if (editingTemplateId) {
        await notificationsApi.updateTemplate(editingTemplateId, {
          name: templateForm.name.trim(),
          template: templateForm.template.trim(),
          channel: templateForm.channel,
        })
      } else {
        await notificationsApi.createTemplate({
          name: templateForm.name.trim(),
          template: templateForm.template.trim(),
          channel: templateForm.channel,
        })
      }
      setIsTemplateModalOpen(false)
      setEditingTemplateId(null)
      setTemplateForm(EMPTY_TEMPLATE_FORM)
      setTemplateActionMessage(editingTemplateId ? '模板更新成功' : '模板创建成功')
      await loadTemplates()
    } catch (error) {
      setTemplateActionMessage(`模板保存失败: ${getErrorMessage(error)}`)
    } finally {
      setIsTemplateCreating(false)
    }
  }

  const openCreateTemplateModal = () => {
    setEditingTemplateId(null)
    setTemplateForm(EMPTY_TEMPLATE_FORM)
    setIsTemplateModalOpen(true)
  }

  const openEditTemplateModal = (template: NotificationTemplate) => {
    setEditingTemplateId(template.id)
    setTemplateForm({ name: template.name, template: template.template, channel: template.channel })
    setIsTemplateModalOpen(true)
  }

  const deleteTemplate = async (template: NotificationTemplate) => {
    setIsTemplateDeletingId(template.id)
    setTemplateActionMessage(null)
    try {
      await notificationsApi.deleteTemplate(template.id)
      setTemplateActionMessage('模板删除成功')
      await loadTemplates()
    } catch (error) {
      setTemplateActionMessage(`模板删除失败: ${getErrorMessage(error)}`)
    } finally {
      setIsTemplateDeletingId(null)
    }
  }

  const openCreateRuleModal = () => {
    setEditingRuleId(null)
    setRuleForm({ ...EMPTY_RULE_FORM, templateId: templates[0]?.id ?? '' })
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
    if (!ruleForm.name.trim() || !ruleForm.scene.trim() || !ruleForm.templateId.trim()) {
      setRuleActionMessage('规则保存失败: 请填写规则名称、场景并绑定模板')
      return
    }
    setIsRuleSaving(true)
    setRuleActionMessage(null)
    try {
      const payload = {
        name: ruleForm.name.trim(),
        stage: ruleForm.stage,
        timeSlot: ruleForm.timeSlot,
        scene: ruleForm.scene.trim(),
        enabled: ruleForm.enabled,
        priority: ruleForm.priority,
        templateId: ruleForm.templateId,
      }
      if (editingRuleId) {
        await notificationsApi.updateRule(editingRuleId, payload)
        setRuleActionMessage('规则更新成功')
      } else {
        await notificationsApi.createRule(payload)
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

  const timelineRules = rules.slice(0, 5)
  const templateById = new Map(templates.map((template) => [template.id, template.template]))
  const tripDailyPreview = buildTripDailyNotificationPreview(tripScheduleDays, rules, templates)
  const buildSlotMessage = (rule: NotificationRule, slot: NotificationRuleTimeSlotCode): string => {
    if (rule.timeSlot !== slot) {
      return '—'
    }
    const content = (templateById.get(rule.templateId) || rule.scene || rule.templateLabel).trim()
    return content ? content.slice(0, 36) : '未配置内容'
  }

  return (
    <PageShell
      eyebrow="通知中心"
      title={tripId ? '旅行团通知配置中心' : '紧急通知与触发管理中心'}
      description={tripId ? '当前页面已绑定具体旅行团，可直接配置该团通知参数并回跳详情页。' : '统一管理紧急天气通知、旅行团通知时间线与通知模板，页面全部采用简体中文，保留 Travel Hub 现有视觉风格。'}
      actions={
        <>
          {tripId ? (
            <Button
              variant="secondary"
              onClick={() => {
                if (tripId) {
                  onBackToTrip?.(tripId)
                }
              }}
            >
              <ArrowLeft className="mr-2 inline h-4 w-4" />
              返回团详情
            </Button>
          ) : null}
          <Button variant="secondary" onClick={openCreateTemplateModal}>
            <Plus className="mr-2 inline h-4 w-4" />
            新建模板
          </Button>
          <Button onClick={openCreateRuleModal}>
            <Plus className="mr-2 inline h-4 w-4" />
            新建规则
          </Button>
        </>
      }
    >
      {templateActionMessage ? (
        <p className={`mb-4 rounded-xl p-3 text-sm ${templateActionMessage.includes('失败') ? 'bg-red-50 text-red-700' : 'bg-green-50 text-green-700'}`}>
          {templateActionMessage}
        </p>
      ) : null}
      {ruleActionMessage ? (
        <p className={`mb-4 rounded-xl p-3 text-sm ${ruleActionMessage.includes('失败') ? 'bg-red-50 text-red-700' : 'bg-green-50 text-green-700'}`}>
          {ruleActionMessage}
        </p>
      ) : null}

      {tripId ? (
        <>
          {tripConfigLoadState === 'loading' ? (
            <PageState kind="loading" title="正在加载当前团通知配置" />
          ) : null}
          {tripConfigLoadState === 'error' ? (
            <PageState kind="error" title="当前团通知配置加载失败" description={tripConfigError} />
          ) : null}
          {tripConfigLoadState === 'ready' && tripConfigContext ? (
            <div className="space-y-6">
              <TripNotificationConfigFormPanel
                trip={tripConfigContext.trip}
                config={tripConfigContext.config}
                saving={isTripConfigSaving}
                saveMessage={tripConfigSaveMessage}
                onSave={saveTripConfig}
              />
              <Card title="当前旅行团每日通知内容（早 / 中 / 晚）" className="border-blue-100 shadow-[0_14px_40px_rgba(15,23,42,0.06)]">
                {tripDailyPreview.length === 0 ? (
                  <PageState
                    kind="empty"
                    title="当前团暂无按天行程"
                    description="请先在“行程详情 > 每日行程编排”中补充行程日，随后可在此查看每天早中晚通知内容。"
                  />
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[980px] text-sm">
                      <thead>
                        <tr className="bg-blue-50 text-left text-slate-700">
                          <th className="px-4 py-4 font-black">行程日</th>
                          <th className="px-4 py-4 font-black">日期</th>
                          <th className="px-4 py-4 font-black">旅行行程</th>
                          <th className="px-4 py-4 font-black">早间通知</th>
                          <th className="px-4 py-4 font-black">中午通知</th>
                          <th className="px-4 py-4 font-black">晚间通知</th>
                        </tr>
                      </thead>
                      <tbody>
                        {tripDailyPreview.map((item) => (
                          <tr key={`${item.day}-${item.date}`} className="border-b border-slate-100 align-top hover:bg-blue-50/40">
                            <td className="px-4 py-4 font-bold text-slate-900">Day {item.day}</td>
                            <td className="px-4 py-4 text-slate-700">{item.date || '待定'}</td>
                            <td className="px-4 py-4 text-slate-700">{item.route || '待补充路线'}</td>
                            <td className="px-4 py-4"><SmsCell label={item.morning} /></td>
                            <td className="px-4 py-4"><SmsCell label={item.afternoon} /></td>
                            <td className="px-4 py-4"><SmsCell label={item.evening} /></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </Card>
            </div>
          ) : null}
        </>
      ) : null}

      {!tripId ? (
        <>
          <EmergencyWeatherSummaryPanel
            weatherLoadState={weatherLoadState}
            weatherSummary={weatherSummary}
            weatherErrorMessage={weatherErrorMessage}
            weatherActionMessage={weatherActionMessage}
            weatherDraft={weatherDraft}
            isWeatherSending={isWeatherSending}
            onRetry={() => void loadEmergencyWeather()}
            onOpenEditor={() => setIsWeatherEditorOpen(true)}
            onSendNow={() => void sendEmergencyWeather()}
            formatUpdatedAt={formatUpdatedAt}
          />

          <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.25fr_0.75fr]">
            <Card title="旅行团通知时间线管理" className="border-blue-100 shadow-[0_14px_40px_rgba(15,23,42,0.06)]">
              {ruleLoadState === 'loading' ? <PageState kind="loading" title="正在加载通知规则" /> : null}
              {ruleLoadState === 'error' ? <PageState kind="error" title="通知规则加载失败" description={ruleErrorMessage} onRetry={() => void loadRules()} /> : null}
              {ruleLoadState === 'empty' ? <PageState kind="empty" title="暂无通知规则" description="可以新建一条规则配置" onRetry={() => void loadRules()} /> : null}
              {ruleLoadState === 'ready' ? (
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[900px] text-sm">
                    <thead>
                      <tr className="bg-blue-50 text-left text-slate-700">
                        <th className="px-4 py-4 font-black">规则名称</th>
                        <th className="px-4 py-4 font-black">阶段</th>
                        <th className="px-4 py-4 font-black">时段</th>
                        <th className="px-4 py-4 font-black">早间通知</th>
                        <th className="px-4 py-4 font-black">午间通知</th>
                        <th className="px-4 py-4 font-black">晚间通知</th>
                        <th className="px-4 py-4 font-black">操作</th>
                      </tr>
                    </thead>
                    <tbody>
                      {timelineRules.map((rule) => (
                        <tr key={rule.id} className="border-b border-slate-100 align-top hover:bg-blue-50/40">
                          <td className="px-4 py-4">
                            <p className="font-bold text-slate-900">{rule.name}</p>
                            <p className="text-xs text-slate-500">{rule.scene}</p>
                          </td>
                          <td className="px-4 py-4">{rule.stageLabel}</td>
                          <td className="px-4 py-4">{rule.timeSlotLabel}</td>
                          <td className="px-4 py-4"><SmsCell label={buildSlotMessage(rule, 'morning')} /></td>
                          <td className="px-4 py-4"><SmsCell label={buildSlotMessage(rule, 'afternoon')} /></td>
                          <td className="px-4 py-4"><SmsCell label={buildSlotMessage(rule, 'evening')} /></td>
                          <td className="px-4 py-4">
                            <div className="flex flex-wrap gap-2">
                              <Button variant="secondary" size="sm" onClick={() => openEditRuleModal(rule)}>
                                <Pencil className="mr-1 inline h-3 w-3" />编辑
                              </Button>
                              <Button variant="secondary" size="sm" onClick={() => void toggleRule(rule)} disabled={isRuleTogglingId === rule.id}>
                                <Power className="mr-1 inline h-3 w-3" />{rule.enabled ? '停用' : '启用'}
                              </Button>
                              <Button variant="danger" size="sm" onClick={() => void deleteRule(rule)} disabled={isRuleDeletingId === rule.id}>
                                <Trash2 className="mr-1 inline h-3 w-3" />删除
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

            <Card title="通知模板模块" className="border-blue-100">
              {templateLoadState === 'loading' ? <PageState kind="loading" title="正在加载通知模板" /> : null}
              {templateLoadState === 'error' ? <PageState kind="error" title="通知模板加载失败" description={templateErrorMessage} onRetry={() => void loadTemplates()} /> : null}
              {templateLoadState === 'empty' ? <PageState kind="empty" title="暂无通知模板" description="当前还没有可用模板" onRetry={() => void loadTemplates()} /> : null}
              {templateLoadState === 'ready' ? (
                <div className="space-y-3">
                  {templates.slice(0, 6).map((template) => (
                    <div key={template.id} className="rounded-xl border border-slate-100 bg-slate-50 p-4">
                      <div className="mb-2 flex items-start justify-between gap-3">
                        <div>
                          <h3 className="font-bold text-slate-900">{template.name}</h3>
                          <p className="mt-1 line-clamp-2 text-sm text-slate-600">{template.template}</p>
                        </div>
                        <Badge variant={template.enabled ? 'success' : 'default'}>{template.statusLabel}</Badge>
                      </div>
                      <div className="flex items-center justify-between text-xs text-slate-500">
                        <span>{template.channelLabel} · 已发送 {template.sentCount}</span>
                        <div className="flex gap-1">
                          <button className="rounded p-1 hover:bg-white" aria-label="预览模板"><Eye className="h-4 w-4" /></button>
                          <button className="rounded p-1 hover:bg-white" aria-label="复制模板"><Copy className="h-4 w-4" /></button>
                          <button className="rounded p-1 hover:bg-white" onClick={() => openEditTemplateModal(template)} aria-label="编辑模板"><Pencil className="h-4 w-4" /></button>
                          <button className="rounded p-1 text-blue-600 hover:bg-white" onClick={() => void sendNow(template.id, template.channel)} disabled={isSending === template.id} aria-label="发送通知"><Send className="h-4 w-4" /></button>
                          <button className="rounded p-1 text-red-600 hover:bg-white" onClick={() => void deleteTemplate(template)} disabled={isTemplateDeletingId === template.id} aria-label="删除模板"><Trash2 className="h-4 w-4" /></button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : null}
            </Card>
          </div>
        </>
      ) : null}

      <Modal
        isOpen={isWeatherEditorOpen}
        onClose={() => setIsWeatherEditorOpen(false)}
        title="编辑紧急天气通知"
        footer={
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setIsWeatherEditorOpen(false)}>取消</Button>
            <Button onClick={() => void sendEmergencyWeather(weatherDraft)} loading={isWeatherSending}>编辑后发送</Button>
          </div>
        }
      >
        <div className="space-y-4">
          <div className="rounded-2xl border border-slate-100 bg-slate-50 p-4 text-sm text-slate-600">
            <p className="font-semibold text-slate-900">AI 风险分析摘要</p>
            <p className="mt-2 leading-6">{weatherSummary?.aiRiskSummary ?? '暂无摘要'}</p>
          </div>
          <textarea
            rows={8}
            value={weatherDraft}
            onChange={(event) => setWeatherDraft(event.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm leading-6"
            placeholder="请输入要发送的紧急天气通知文案"
          />
        </div>
      </Modal>

      <Modal
        isOpen={isTemplateModalOpen}
        onClose={() => {
          setIsTemplateModalOpen(false)
          setEditingTemplateId(null)
        }}
        title={editingTemplateId ? '编辑通知模板' : '新建通知模板'}
        footer={
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setIsTemplateModalOpen(false)}>取消</Button>
            <Button onClick={() => void saveTemplate()} loading={isTemplateCreating}>保存</Button>
          </div>
        }
      >
        <div className="space-y-4">
          <input type="text" placeholder="模板名称" value={templateForm.name} onChange={(event) => setTemplateForm((prev) => ({ ...prev, name: event.target.value }))} className="w-full rounded-lg border border-gray-300 px-3 py-2" />
          <select value={templateForm.channel} onChange={(event) => setTemplateForm((prev) => ({ ...prev, channel: event.target.value as ChannelCode }))} className="w-full rounded-lg border border-gray-300 px-3 py-2">
            <option value="sms">短信</option>
            <option value="wechat_work_group">企业微信</option>
            <option value="email">邮件</option>
          </select>
          <textarea placeholder="模板内容" rows={4} value={templateForm.template} onChange={(event) => setTemplateForm((prev) => ({ ...prev, template: event.target.value }))} className="w-full rounded-lg border border-gray-300 px-3 py-2" />
        </div>
      </Modal>

      <Modal
        isOpen={isRuleModalOpen}
        onClose={() => setIsRuleModalOpen(false)}
        title={editingRuleId ? '编辑通知规则' : '新建通知规则'}
        footer={
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setIsRuleModalOpen(false)}>取消</Button>
            <Button onClick={() => void saveRule()} loading={isRuleSaving}>保存</Button>
          </div>
        }
      >
        <div className="space-y-4">
          <div>
            <label className="mb-1 block text-sm text-gray-700">规则名称</label>
            <input type="text" value={ruleForm.name} onChange={(event) => setRuleForm((prev) => ({ ...prev, name: event.target.value }))} placeholder="例如：出发前安全提醒" className="w-full rounded-lg border border-gray-300 px-3 py-2" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-sm text-gray-700">阶段</label>
              <select value={ruleForm.stage} onChange={(event) => setRuleForm((prev) => ({ ...prev, stage: event.target.value as NotificationRuleStageCode }))} className="w-full rounded-lg border border-gray-300 px-3 py-2">
                {RULE_STAGE_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm text-gray-700">时段</label>
              <select value={ruleForm.timeSlot} onChange={(event) => setRuleForm((prev) => ({ ...prev, timeSlot: event.target.value as NotificationRuleTimeSlotCode }))} className="w-full rounded-lg border border-gray-300 px-3 py-2">
                {RULE_TIME_SLOT_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label className="mb-1 block text-sm text-gray-700">场景</label>
            <input type="text" value={ruleForm.scene} onChange={(event) => setRuleForm((prev) => ({ ...prev, scene: event.target.value }))} placeholder="例如：高原天气预警" className="w-full rounded-lg border border-gray-300 px-3 py-2" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-sm text-gray-700">优先级</label>
              <input type="number" min={1} value={ruleForm.priority} onChange={(event) => setRuleForm((prev) => ({ ...prev, priority: Number(event.target.value) || 1 }))} className="w-full rounded-lg border border-gray-300 px-3 py-2" />
            </div>
            <div>
              <label className="mb-1 block text-sm text-gray-700">状态</label>
              <select value={ruleForm.enabled ? 'enabled' : 'disabled'} onChange={(event) => setRuleForm((prev) => ({ ...prev, enabled: event.target.value === 'enabled' }))} className="w-full rounded-lg border border-gray-300 px-3 py-2">
                <option value="enabled">启用</option>
                <option value="disabled">停用</option>
              </select>
            </div>
          </div>
          <div>
            <label className="mb-1 block text-sm text-gray-700">绑定模板</label>
            {templates.length > 0 ? (
              <select value={ruleForm.templateId} onChange={(event) => setRuleForm((prev) => ({ ...prev, templateId: event.target.value }))} className="w-full rounded-lg border border-gray-300 px-3 py-2">
                <option value="">请选择模板</option>
                {templates.map((template) => <option key={template.id} value={template.id}>{template.name}</option>)}
              </select>
            ) : (
              <input type="text" value={ruleForm.templateId} onChange={(event) => setRuleForm((prev) => ({ ...prev, templateId: event.target.value }))} placeholder="输入模板 ID" className="w-full rounded-lg border border-gray-300 px-3 py-2" />
            )}
          </div>
        </div>
      </Modal>
    </PageShell>
  )
}
