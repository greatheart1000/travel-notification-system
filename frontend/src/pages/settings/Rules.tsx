import { Fragment, useCallback, useEffect, useState } from 'react'
import { BellRing, ChevronDown, ChevronRight, Info, Pencil, Plus, Trash2, Wand2 } from 'lucide-react'
import { PageShell } from '../../components/PageShell'
import { Button } from '../../components/Button'
import { Badge } from '../../components/Badge'
import { Modal } from '../../components/Modal'
import { getErrorMessage, notificationsApi, tripReminderApi } from '../../services/api'
import type { NotificationTemplate } from '../../types/api'
import { useSession } from '../../context/SessionContext'
import {
  rulesApi,
  type NotificationRuleRaw,
} from '../../services/commercialApi'

const STAGE_OPTIONS = [
  { value: 'pre_trip', label: '行前' },
  { value: 'in_trip', label: '行中' },
  { value: 'post_trip', label: '行后' },
]

const TIME_SLOT_OPTIONS = [
  { value: 'morning', label: '早间' },
  { value: 'afternoon', label: '午间' },
  { value: 'evening', label: '晚间' },
  { value: 'night', label: '夜间' },
  { value: 'all_day', label: '全天' },
]

const SCENE_OPTIONS = [
  { value: 'normal', label: '常规通知' },
  { value: 'weather_alert', label: '天气预警' },
  { value: 'delay', label: '行程延误' },
  { value: 'complaint', label: '投诉处理' },
  { value: 'manual', label: '人工触发' },
]

const CHANNEL_OPTIONS = [
  { value: 'sms', label: '短信（仅参团成功）' },
  { value: 'wechat_work_group', label: '企业微信' },
  { value: 'email', label: '邮件（暂未开放）', disabled: true },
]

interface ConditionRow {
  field: string
  op: string
  value: string
}

interface RuleForm {
  id?: string
  name: string
  stage: string
  time_slot: string
  scene: string
  channels: string[]
  template_id: string
  priority: number
  enabled: boolean
  conditions: ConditionRow[]
}

const EMPTY_FORM: RuleForm = {
  name: '',
  stage: 'pre_trip',
  time_slot: 'morning',
  scene: 'normal',
  channels: ['sms'],
  template_id: '',
  priority: 100,
  enabled: true,
  conditions: [],
}

function labelOf(options: { value: string; label: string }[], value: string): string {
  return options.find((item) => item.value === value)?.label ?? value
}

function toRows(conditions: NotificationRuleRaw['conditions']): ConditionRow[] {
  if (!conditions || typeof conditions !== 'object') return []
  return Object.entries(conditions).map(([field, expected]) => {
    if (expected && typeof expected === 'object' && 'op' in (expected as Record<string, unknown>)) {
      const typed = expected as { op?: string; value?: unknown }
      return {
        field,
        op: String(typed.op ?? '=='),
        value: Array.isArray(typed.value) ? typed.value.join(',') : String(typed.value ?? ''),
      }
    }
    return { field, op: '==', value: String(expected ?? '') }
  })
}

function buildConditions(rows: ConditionRow[]): Record<string, unknown> {
  const result: Record<string, unknown> = {}
  for (const row of rows) {
    const field = row.field.trim()
    if (!field) continue
    const raw = row.value.trim()
    if (row.op === 'in') {
      result[field] = { op: row.op, value: raw.split(',').map((item) => item.trim()).filter(Boolean) }
    } else if (raw !== '' && /^-?\d+(\.\d+)?$/.test(raw)) {
      result[field] = { op: row.op, value: Number(raw) }
    } else if (row.op === '==') {
      result[field] = raw
    } else {
      result[field] = { op: row.op, value: raw }
    }
  }
  return result
}

export function Rules() {
  const { user } = useSession()
  const canWrite = user?.role === 'admin' || user?.role === 'operator'
  const [rules, setRules] = useState<NotificationRuleRaw[]>([])
  const [templates, setTemplates] = useState<NotificationTemplate[]>([])
  const [form, setForm] = useState<RuleForm>(EMPTY_FORM)
  const [isOpen, setIsOpen] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [expandedRuleId, setExpandedRuleId] = useState<string | null>(null)
  const [polishingRuleId, setPolishingRuleId] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [ruleList, templateList] = await Promise.all([
        rulesApi.list(),
        notificationsApi.listTemplates().catch(() => []),
      ])
      setRules(ruleList)
      setTemplates(templateList)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const templateFor = (rule: NotificationRuleRaw) =>
    templates.find((template) => template.id === rule.template_id)

  const toggleExpanded = (ruleId: string) => {
    setExpandedRuleId((current) => (current === ruleId ? null : ruleId))
  }

  const polishTemplate = async (rule: NotificationRuleRaw) => {
    const template = templateFor(rule)
    if (!template) return
    setPolishingRuleId(rule.id)
    setError(null)
    try {
      const result = await tripReminderApi.polish({
        content: template.template,
        scene: rule.name,
      })
      await notificationsApi.updateTemplate(template.id, { template: result.content })
      setNotice(result.provider === 'glm' ? '已润色通知模板' : '已按本地规则润色')
      await load()
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setPolishingRuleId('')
    }
  }

  const openCreate = () => {
    setForm({ ...EMPTY_FORM })
    setIsOpen(true)
    setError(null)
  }

  const openEdit = (rule: NotificationRuleRaw) => {
    setForm({
      id: rule.id,
      name: rule.name,
      stage: rule.stage,
      time_slot: rule.time_slot,
      scene: rule.scene,
      channels: rule.channels?.length ? rule.channels : ['sms'],
      template_id: rule.template_id ?? '',
      priority: Number(rule.priority ?? 100),
      enabled: Boolean(rule.enabled),
      conditions: toRows(rule.conditions),
    })
    setIsOpen(true)
    setError(null)
  }

  const submit = async () => {
    if (!form.name.trim()) {
      setError('请填写规则名称')
      return
    }
    if (!form.channels.length) {
      setError('至少选择一个发送渠道')
      return
    }
    setSaving(true)
    setError(null)
    const payload = {
      name: form.name.trim(),
      stage: form.stage,
      time_slot: form.time_slot,
      scene: form.scene,
      channels: form.channels,
      template_id: form.template_id || null,
      priority: Number(form.priority) || 100,
      enabled: form.enabled,
      conditions: buildConditions(form.conditions),
    }
    try {
      if (form.id) {
        await rulesApi.update(form.id, payload)
        setNotice('规则已更新')
      } else {
        await rulesApi.create(payload)
        setNotice('规则已创建')
      }
      setIsOpen(false)
      await load()
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  const toggle = async (rule: NotificationRuleRaw) => {
    try {
      await rulesApi.toggle(rule.id, !Boolean(rule.enabled))
      await load()
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  const remove = async (rule: NotificationRuleRaw) => {
    if (!window.confirm(`确认删除规则「${rule.name}」？`)) return
    try {
      await rulesApi.remove(rule.id)
      setNotice('规则已删除')
      await load()
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  const addCondition = () => {
    setForm((prev) => ({
      ...prev,
      conditions: [...prev.conditions, { field: '', op: '==', value: '' }],
    }))
  }

  const updateCondition = (index: number, patch: Partial<ConditionRow>) => {
    setForm((prev) => ({
      ...prev,
      conditions: prev.conditions.map((row, rowIndex) =>
        rowIndex === index ? { ...row, ...patch } : row,
      ),
    }))
  }

  const removeCondition = (index: number) => {
    setForm((prev) => ({
      ...prev,
      conditions: prev.conditions.filter((_, rowIndex) => rowIndex !== index),
    }))
  }

  return (
    <PageShell
      title="通知规则"
      description="规则决定谁在什么时间收到什么内容；服务通知默认发送到企业微信群。"
      actions={
        canWrite ? (
          <Button size="sm" onClick={openCreate}>
            <span className="flex items-center gap-1">
              <Plus className="h-4 w-4" /> 新建规则
            </span>
          </Button>
        ) : (
          <span className="text-sm text-paper-500">只读模式：仅管理员可修改规则</span>
        )
      }
    >
      {error ? (
        <div role="alert" className="mb-4 rounded-control border border-danger-200 bg-danger-50 px-4 py-3 text-sm text-danger-700">
          {error}
        </div>
      ) : null}
      {notice ? (
        <div className="mb-4 rounded-control border border-success-200 bg-success-50 px-4 py-3 text-sm text-success-700">
          {notice}
        </div>
      ) : null}

      <div className="mb-4 flex items-start gap-2.5 rounded-card border border-accent-100 bg-accent-50/60 px-4 py-3 text-sm text-paper-700">
        <Info className="mt-0.5 h-4 w-4 shrink-0 text-accent-600" />
        <p>
          行程服务通知应全部发送到企业微信群；短信仅用于参团成功通知。未配置群的行程不会自动补发短信，会在「团队执行」页提示管理员处理。
        </p>
      </div>

      <div className="overflow-hidden rounded-card border border-paper-200 bg-white shadow-card">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-paper-200 text-xs font-medium text-paper-500">
            <tr>
              <th className="px-4 py-3">规则名称</th>
              <th className="px-4 py-3">状态</th>
              <th className="px-4 py-3">阶段 / 时段</th>
              <th className="px-4 py-3">场景</th>
              <th className="px-4 py-3">渠道</th>
              <th className="px-4 py-3">优先级</th>
              <th className="px-4 py-3 text-right">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-paper-100">
            {loading ? (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-paper-500">
                  正在加载规则...
                </td>
              </tr>
            ) : rules.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-10 text-center text-paper-500">
                  <BellRing className="mx-auto mb-3 h-6 w-6 text-paper-400" />
                  尚未配置通知规则，系统将沿用默认发送行为。
                </td>
              </tr>
            ) : (
              rules.map((rule) => {
                const template = templateFor(rule)
                const expanded = expandedRuleId === rule.id
                const conditionText = rule.conditions && Object.keys(rule.conditions).length
                  ? JSON.stringify(rule.conditions, null, 2)
                  : '无附加条件'
                return (
                  <Fragment key={rule.id}>
                    <tr className="align-top">
                      <td className="px-4 py-3">
                        <div className="flex items-start gap-2">
                          <button
                            type="button"
                            onClick={() => toggleExpanded(rule.id)}
                            className="mt-0.5 rounded-control p-0.5 text-paper-400 hover:bg-paper-100 hover:text-paper-700"
                            aria-label={expanded ? '收起通知内容' : '展开通知内容'}
                          >
                            {expanded ? (
                              <ChevronDown className="h-4 w-4" />
                            ) : (
                              <ChevronRight className="h-4 w-4" />
                            )}
                          </button>
                          <div className="min-w-0">
                            <div className="font-medium text-paper-900">{rule.name}</div>
                            <p className="mt-1 line-clamp-2 max-w-md text-xs leading-5 text-paper-500">
                              {template?.template || '未绑定通知模板，发送时使用系统默认内容'}
                            </p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        {canWrite ? (
                          <button
                            type="button"
                            onClick={() => void toggle(rule)}
                            className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                              rule.enabled ? 'bg-accent-600' : 'bg-paper-300'
                            }`}
                            aria-label={rule.enabled ? '停用规则' : '启用规则'}
                          >
                            <span
                              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                                rule.enabled ? 'translate-x-4' : 'translate-x-0.5'
                              }`}
                            />
                          </button>
                        ) : (
                          <Badge variant={rule.enabled ? 'success' : 'default'}>
                            {rule.enabled ? '已启用' : '已停用'}
                          </Badge>
                        )}
                      </td>
                      <td className="px-4 py-3 text-paper-600">
                        {labelOf(STAGE_OPTIONS, rule.stage)} / {labelOf(TIME_SLOT_OPTIONS, rule.time_slot)}
                      </td>
                      <td className="px-4 py-3 text-paper-600">{labelOf(SCENE_OPTIONS, rule.scene)}</td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-1">
                          {(rule.channels ?? []).map((channel) => (
                            <Badge key={channel} variant="default">
                              {labelOf(CHANNEL_OPTIONS, channel)}
                            </Badge>
                          ))}
                        </div>
                      </td>
                      <td className="px-4 py-3 tabular-nums text-paper-600">{rule.priority ?? 100}</td>
                      <td className="px-4 py-3">
                        {canWrite ? (
                          <div className="flex justify-end gap-2">
                            <button
                              type="button"
                              onClick={() => openEdit(rule)}
                              className="rounded-control p-1.5 text-paper-500 hover:bg-paper-100 hover:text-paper-900"
                              aria-label="编辑规则"
                            >
                              <Pencil className="h-4 w-4" />
                            </button>
                            <button
                              type="button"
                              onClick={() => void remove(rule)}
                              className="rounded-control p-1.5 text-paper-500 hover:bg-danger-50 hover:text-danger-600"
                              aria-label="删除规则"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </div>
                        ) : (
                          <span className="text-xs text-paper-400">-</span>
                        )}
                      </td>
                    </tr>
                    {expanded ? (
                      <tr>
                        <td colSpan={7} className="bg-paper-50 px-4 py-4">
                          <div className="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
                            <div>
                              <div className="flex flex-wrap items-center justify-between gap-2">
                                <p className="text-xs font-medium text-paper-500">发送到群里的具体内容</p>
                                {canWrite && template ? (
                                  <button
                                    type="button"
                                    onClick={() => void polishTemplate(rule)}
                                    disabled={polishingRuleId === rule.id}
                                    className="inline-flex items-center gap-1.5 rounded-control border border-pink-200 bg-pink-50 px-2.5 py-1.5 text-xs font-medium text-pink-700 transition-colors hover:bg-pink-100 disabled:opacity-50"
                                  >
                                    <Wand2 className="h-3.5 w-3.5" />
                                    {polishingRuleId === rule.id ? '润色中…' : '润色模板'}
                                  </button>
                                ) : null}
                              </div>
                              <pre className="mt-2 max-h-72 overflow-auto whitespace-pre-wrap rounded-card border border-paper-200 bg-white p-4 font-sans text-sm leading-6 text-paper-800">
                                {template?.template || '未绑定通知模板，发送时使用系统默认内容。'}
                              </pre>
                              <p className="mt-2 text-xs text-paper-400">
                                模板为当前企业共用；修改后，所有引用该模板的规则都会同步更新。{"{{变量}}"} 会在发送时自动替换为游客与行程数据。
                              </p>
                            </div>
                            <div className="space-y-3 text-sm">
                              <div>
                                <p className="text-xs font-medium text-paper-500">绑定模板</p>
                                <p className="mt-1 text-paper-800">{template?.name || '未绑定'}</p>
                              </div>
                              <div>
                                <p className="text-xs font-medium text-paper-500">规则条件</p>
                                <pre className="mt-1 max-h-40 overflow-auto whitespace-pre-wrap rounded-control bg-white p-3 font-mono text-xs leading-5 text-paper-600">
                                  {conditionText}
                                </pre>
                              </div>
                            </div>
                          </div>
                        </td>
                      </tr>
                    ) : null}
                  </Fragment>
                )
              })
            )}
          </tbody>
        </table>
      </div>

      <Modal
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        title={form.id ? '编辑通知规则' : '新建通知规则'}
        panelClassName="max-w-3xl"
        footer={
          <div className="flex justify-end gap-3">
            <Button variant="secondary" size="sm" onClick={() => setIsOpen(false)}>
              取消
            </Button>
            <Button size="sm" loading={saving} onClick={() => void submit()}>
              保存规则
            </Button>
          </div>
        }
      >
        <div className="space-y-5">
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block text-sm font-medium text-paper-700">
              规则名称
              <input
                value={form.name}
                onChange={(event) => setForm((prev) => ({ ...prev, name: event.target.value }))}
                className="mt-1 w-full rounded-control border border-paper-300 px-3 py-2 text-sm focus:border-accent-600 focus:outline-none"
                placeholder="例如：行前早间常规提醒"
              />
            </label>
            <label className="block text-sm font-medium text-paper-700">
              优先级（数值越小越优先）
              <input
                type="number"
                value={form.priority}
                onChange={(event) =>
                  setForm((prev) => ({ ...prev, priority: Number(event.target.value) }))
                }
                className="mt-1 w-full rounded-control border border-paper-300 px-3 py-2 text-sm focus:border-accent-600 focus:outline-none"
              />
            </label>
          </div>

          <div className="grid gap-4 sm:grid-cols-3">
            <label className="block text-sm font-medium text-paper-700">
              阶段
              <select
                value={form.stage}
                onChange={(event) => setForm((prev) => ({ ...prev, stage: event.target.value }))}
                className="mt-1 w-full rounded-control border border-paper-300 px-3 py-2 text-sm"
              >
                {STAGE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm font-medium text-paper-700">
              时段
              <select
                value={form.time_slot}
                onChange={(event) => setForm((prev) => ({ ...prev, time_slot: event.target.value }))}
                className="mt-1 w-full rounded-control border border-paper-300 px-3 py-2 text-sm"
              >
                {TIME_SLOT_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm font-medium text-paper-700">
              场景
              <select
                value={form.scene}
                onChange={(event) => setForm((prev) => ({ ...prev, scene: event.target.value }))}
                className="mt-1 w-full rounded-control border border-paper-300 px-3 py-2 text-sm"
              >
                {SCENE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <span className="block text-sm font-medium text-paper-700">发送渠道</span>
              <div className="mt-2 space-y-2">
                {CHANNEL_OPTIONS.map((option) => (
                  <label key={option.value} className="flex items-center gap-2 text-sm text-paper-700">
                    <input
                      type="checkbox"
                      checked={form.channels.includes(option.value)}
                      disabled={option.disabled}
                      onChange={(event) =>
                        setForm((prev) => ({
                          ...prev,
                          channels: event.target.checked
                            ? [...prev.channels, option.value]
                            : prev.channels.filter((item) => item !== option.value),
                        }))
                      }
                    />
                    {option.label}
                  </label>
                ))}
              </div>
            </div>
            <label className="block text-sm font-medium text-paper-700">
              绑定模板
              <select
                value={form.template_id}
                onChange={(event) =>
                  setForm((prev) => ({ ...prev, template_id: event.target.value }))
                }
                className="mt-1 w-full rounded-control border border-paper-300 px-3 py-2 text-sm"
              >
                <option value="">不绑定模板</option>
                {templates.map((template) => (
                  <option key={template.id} value={template.id}>
                    {template.name}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div>
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-paper-700">条件组（全部满足才命中）</span>
              <Button variant="secondary" size="sm" onClick={addCondition}>
                添加条件
              </Button>
            </div>
            {form.conditions.length === 0 ? (
              <p className="mt-2 text-xs text-paper-500">不配置条件时，匹配任意上下文。</p>
            ) : (
              <div className="mt-3 space-y-2">
                {form.conditions.map((row, index) => (
                  <div key={index} className="flex flex-wrap items-center gap-2">
                    <input
                      value={row.field}
                      onChange={(event) => updateCondition(index, { field: event.target.value })}
                      className="w-36 rounded-control border border-paper-300 px-2 py-1.5 text-sm"
                      placeholder="字段名"
                      list="condition-fields"
                    />
                    <select
                      value={row.op}
                      onChange={(event) => updateCondition(index, { op: event.target.value })}
                      className="rounded-control border border-paper-300 px-2 py-1.5 text-sm"
                    >
                      {['==', '!=', '>', '>=', '<', '<=', 'in', 'contains'].map((op) => (
                        <option key={op} value={op}>
                          {op}
                        </option>
                      ))}
                    </select>
                    <input
                      value={row.value}
                      onChange={(event) => updateCondition(index, { value: event.target.value })}
                      className="min-w-[8rem] flex-1 rounded-control border border-paper-300 px-2 py-1.5 text-sm"
                      placeholder={row.op === 'in' ? '多个值用逗号分隔' : '值'}
                    />
                    <button
                      type="button"
                      onClick={() => removeCondition(index)}
                      className="rounded-control p-1.5 text-paper-500 hover:bg-danger-50 hover:text-danger-600"
                      aria-label="删除条件"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
            <datalist id="condition-fields">
              {['destination', 'participants', 'time_node', 'team_id', 'status'].map((field) => (
                <option key={field} value={field} />
              ))}
            </datalist>
          </div>

          <label className="flex items-center gap-2 text-sm text-paper-700">
            <input
              type="checkbox"
              checked={form.enabled}
              onChange={(event) => setForm((prev) => ({ ...prev, enabled: event.target.checked }))}
            />
            启用该规则
          </label>
        </div>
      </Modal>
    </PageShell>
  )
}
