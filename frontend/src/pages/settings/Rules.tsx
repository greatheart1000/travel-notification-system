import { useCallback, useEffect, useState } from 'react'
import { BellRing, Pencil, Plus, Trash2 } from 'lucide-react'
import { PageShell } from '../../components/PageShell'
import { Button } from '../../components/Button'
import { Badge } from '../../components/Badge'
import { Modal } from '../../components/Modal'
import { getErrorMessage, notificationsApi } from '../../services/api'
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
  { value: 'sms', label: '短信' },
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
  const [templates, setTemplates] = useState<{ id: string; name: string }[]>([])
  const [form, setForm] = useState<RuleForm>(EMPTY_FORM)
  const [isOpen, setIsOpen] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [ruleList, templateList] = await Promise.all([
        rulesApi.list(),
        notificationsApi.listTemplates().catch(() => []),
      ])
      setRules(ruleList)
      setTemplates(templateList.map((item) => ({ id: item.id, name: item.name })))
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

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
      eyebrow="SETTINGS"
      title="通知规则"
      description="规则按「阶段 + 时段 + 场景 + 条件」匹配；没有规则时沿用系统默认发送行为。"
      actions={
        canWrite ? (
          <Button size="sm" onClick={openCreate}>
            <span className="flex items-center gap-1">
              <Plus className="h-4 w-4" /> 新建规则
            </span>
          </Button>
        ) : (
          <span className="text-sm text-slate-500">只读模式：仅管理员可修改规则</span>
        )
      }
    >
      {error ? (
        <div role="alert" className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}
      {notice ? (
        <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
          {notice}
        </div>
      ) : null}

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
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
          <tbody className="divide-y divide-slate-100">
            {loading ? (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-slate-500">
                  正在加载规则...
                </td>
              </tr>
            ) : rules.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-10 text-center text-slate-500">
                  <BellRing className="mx-auto mb-3 h-6 w-6 text-slate-400" />
                  尚未配置通知规则，系统将沿用默认发送行为。
                </td>
              </tr>
            ) : (
              rules.map((rule) => (
                <tr key={rule.id}>
                  <td className="px-4 py-3 font-medium text-slate-900">{rule.name}</td>
                  <td className="px-4 py-3">
                    {canWrite ? (
                      <button
                        type="button"
                        onClick={() => void toggle(rule)}
                        className={`relative inline-flex h-5 w-9 items-center rounded-full transition ${
                          rule.enabled ? 'bg-sky-500' : 'bg-slate-300'
                        }`}
                        aria-label={rule.enabled ? '停用规则' : '启用规则'}
                      >
                        <span
                          className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${
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
                  <td className="px-4 py-3 text-slate-600">
                    {labelOf(STAGE_OPTIONS, rule.stage)} / {labelOf(TIME_SLOT_OPTIONS, rule.time_slot)}
                  </td>
                  <td className="px-4 py-3 text-slate-600">{labelOf(SCENE_OPTIONS, rule.scene)}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {(rule.channels ?? []).map((channel) => (
                        <Badge key={channel} variant="info">
                          {labelOf(CHANNEL_OPTIONS, channel)}
                        </Badge>
                      ))}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-slate-600">{rule.priority ?? 100}</td>
                  <td className="px-4 py-3">
                    {canWrite ? (
                      <div className="flex justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => openEdit(rule)}
                          className="rounded p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-900"
                          aria-label="编辑规则"
                        >
                          <Pencil className="h-4 w-4" />
                        </button>
                        <button
                          type="button"
                          onClick={() => void remove(rule)}
                          className="rounded p-1.5 text-slate-500 hover:bg-red-50 hover:text-red-600"
                          aria-label="删除规则"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    ) : (
                      <span className="text-xs text-slate-400">-</span>
                    )}
                  </td>
                </tr>
              ))
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
            <label className="block text-sm font-medium text-slate-700">
              规则名称
              <input
                value={form.name}
                onChange={(event) => setForm((prev) => ({ ...prev, name: event.target.value }))}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none"
                placeholder="例如：行前早间常规提醒"
              />
            </label>
            <label className="block text-sm font-medium text-slate-700">
              优先级（数值越小越优先）
              <input
                type="number"
                value={form.priority}
                onChange={(event) =>
                  setForm((prev) => ({ ...prev, priority: Number(event.target.value) }))
                }
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none"
              />
            </label>
          </div>

          <div className="grid gap-4 sm:grid-cols-3">
            <label className="block text-sm font-medium text-slate-700">
              阶段
              <select
                value={form.stage}
                onChange={(event) => setForm((prev) => ({ ...prev, stage: event.target.value }))}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              >
                {STAGE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm font-medium text-slate-700">
              时段
              <select
                value={form.time_slot}
                onChange={(event) => setForm((prev) => ({ ...prev, time_slot: event.target.value }))}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              >
                {TIME_SLOT_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm font-medium text-slate-700">
              场景
              <select
                value={form.scene}
                onChange={(event) => setForm((prev) => ({ ...prev, scene: event.target.value }))}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
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
              <span className="block text-sm font-medium text-slate-700">发送渠道</span>
              <div className="mt-2 space-y-2">
                {CHANNEL_OPTIONS.map((option) => (
                  <label key={option.value} className="flex items-center gap-2 text-sm text-slate-700">
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
            <label className="block text-sm font-medium text-slate-700">
              绑定模板
              <select
                value={form.template_id}
                onChange={(event) =>
                  setForm((prev) => ({ ...prev, template_id: event.target.value }))
                }
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
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
              <span className="text-sm font-medium text-slate-700">条件组（全部满足才命中）</span>
              <Button variant="secondary" size="sm" onClick={addCondition}>
                添加条件
              </Button>
            </div>
            {form.conditions.length === 0 ? (
              <p className="mt-2 text-xs text-slate-500">不配置条件时，匹配任意上下文。</p>
            ) : (
              <div className="mt-3 space-y-2">
                {form.conditions.map((row, index) => (
                  <div key={index} className="flex flex-wrap items-center gap-2">
                    <input
                      value={row.field}
                      onChange={(event) => updateCondition(index, { field: event.target.value })}
                      className="w-36 rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
                      placeholder="字段名"
                      list="condition-fields"
                    />
                    <select
                      value={row.op}
                      onChange={(event) => updateCondition(index, { op: event.target.value })}
                      className="rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
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
                      className="min-w-[8rem] flex-1 rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
                      placeholder={row.op === 'in' ? '多个值用逗号分隔' : '值'}
                    />
                    <button
                      type="button"
                      onClick={() => removeCondition(index)}
                      className="rounded p-1.5 text-slate-500 hover:bg-red-50 hover:text-red-600"
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

          <label className="flex items-center gap-2 text-sm text-slate-700">
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
