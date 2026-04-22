import { useEffect, useMemo, useState } from 'react'
import { ArrowLeft, Pencil, Plus, Power, Trash2 } from 'lucide-react'
import { Badge } from '../Badge'
import { Button } from '../Button'
import { Card } from '../Card'
import { PageState } from '../PageState'
import { TripNotificationRuleForm } from './TripNotificationRuleForm'
import { TripNotificationStatusTable } from './TripNotificationStatusTable'
import {
  tripNotificationClient,
  type TripNotificationRule,
  type TripNotificationRuleWriteInput,
  type TripNotificationSnapshot,
  type TripNotificationTemplate,
} from '../../features/notifications/tripNotificationClient'

interface TripNotificationConfigPanelProps {
  tripId: string
  onBackToTrip?: () => void
  tripLabel?: string
}

type LoadState = 'loading' | 'ready' | 'empty' | 'error'

function stageLabel(stage: string): string {
  if (stage === 'pre_trip') {
    return '行前'
  }
  if (stage === 'on_trip') {
    return '行中'
  }
  if (stage === 'post_trip') {
    return '行后'
  }
  if (stage === 'custom') {
    return '自定义'
  }
  return '未知'
}

function timeSlotLabel(timeSlot: string): string {
  if (timeSlot === 'morning') {
    return '早间'
  }
  if (timeSlot === 'afternoon') {
    return '午间'
  }
  if (timeSlot === 'evening') {
    return '晚间'
  }
  if (timeSlot === 'night') {
    return '夜间'
  }
  if (timeSlot === 'all_day') {
    return '全天'
  }
  return '未知'
}

function sceneLabel(scene: string): string {
  if (scene === 'weather_alert') {
    return '天气预警'
  }
  if (scene === 'delay') {
    return '延误变更'
  }
  if (scene === 'complaint') {
    return '投诉跟进'
  }
  if (scene === 'manual') {
    return '人工介入'
  }
  return '常规提醒'
}

function channelLabel(code: string): string {
  if (code === 'wechat_work_group') {
    return '企业微信'
  }
  if (code === 'email') {
    return '邮件'
  }
  return '短信'
}

export function TripNotificationConfigPanel({ tripId, onBackToTrip, tripLabel }: TripNotificationConfigPanelProps) {
  const [rules, setRules] = useState<TripNotificationRule[]>([])
  const [templates, setTemplates] = useState<TripNotificationTemplate[]>([])
  const [snapshot, setSnapshot] = useState<TripNotificationSnapshot | null>(null)

  const [ruleLoadState, setRuleLoadState] = useState<LoadState>('loading')
  const [ruleError, setRuleError] = useState('')
  const [actionMessage, setActionMessage] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [isRefreshingStatus, setIsRefreshingStatus] = useState(false)
  const [togglingRuleId, setTogglingRuleId] = useState<string | null>(null)
  const [deletingRuleId, setDeletingRuleId] = useState<string | null>(null)

  const [isFormVisible, setIsFormVisible] = useState(false)
  const [editingRule, setEditingRule] = useState<TripNotificationRule | null>(null)

  const loadData = async () => {
    setRuleLoadState('loading')
    setRuleError('')
    try {
      const [templateList, ruleList, statusSnapshot] = await Promise.all([
        tripNotificationClient.listTemplates(),
        tripNotificationClient.listRulesByTrip(tripId),
        tripNotificationClient.getTripStatusSnapshot(tripId),
      ])
      setTemplates(templateList)
      setRules(ruleList)
      setSnapshot(statusSnapshot)
      setRuleLoadState(ruleList.length > 0 ? 'ready' : 'empty')
    } catch (error) {
      setRuleLoadState('error')
      setRuleError(error instanceof Error ? error.message : '加载失败')
    }
  }

  useEffect(() => {
    void loadData()
  }, [tripId])

  const refreshStatus = async () => {
    setIsRefreshingStatus(true)
    try {
      const statusSnapshot = await tripNotificationClient.getTripStatusSnapshot(tripId)
      setSnapshot(statusSnapshot)
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : '刷新状态失败')
    } finally {
      setIsRefreshingStatus(false)
    }
  }

  const templateUsageCount = useMemo(() => {
    const map = new Map<string, number>()
    for (const rule of rules) {
      if (!rule.templateId) {
        continue
      }
      map.set(rule.templateId, (map.get(rule.templateId) || 0) + 1)
    }
    return map
  }, [rules])

  const openCreateForm = () => {
    setEditingRule(null)
    setIsFormVisible(true)
    setActionMessage('')
  }

  const openEditForm = (rule: TripNotificationRule) => {
    setEditingRule(rule)
    setIsFormVisible(true)
    setActionMessage('')
  }

  const handleSaveRule = async (input: TripNotificationRuleWriteInput) => {
    setIsSaving(true)
    setActionMessage('')
    try {
      if (editingRule) {
        await tripNotificationClient.updateRule(tripId, editingRule.id, input)
        setActionMessage('通知规则已更新')
      } else {
        await tripNotificationClient.createRule(tripId, input)
        setActionMessage('通知规则已新增')
      }
      setEditingRule(null)
      setIsFormVisible(false)
      await loadData()
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : '保存规则失败')
    } finally {
      setIsSaving(false)
    }
  }

  const toggleRule = async (rule: TripNotificationRule) => {
    setTogglingRuleId(rule.id)
    setActionMessage('')
    try {
      await tripNotificationClient.toggleRule(rule.id, !rule.enabled)
      setActionMessage(`规则已${rule.enabled ? '停用' : '启用'}`)
      await loadData()
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : '启停规则失败')
    } finally {
      setTogglingRuleId(null)
    }
  }

  const removeRule = async (rule: TripNotificationRule) => {
    setDeletingRuleId(rule.id)
    setActionMessage('')
    try {
      await tripNotificationClient.deleteRule(rule.id)
      setActionMessage('通知规则已删除')
      await loadData()
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : '删除规则失败')
    } finally {
      setDeletingRuleId(null)
    }
  }

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-blue-100 bg-[linear-gradient(135deg,rgba(239,246,255,1),rgba(255,255,255,1))] p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold tracking-[0.2em] text-blue-700">Travel Hub</p>
            <h2 className="mt-1 text-2xl font-black text-slate-900">按旅行团配置通知</h2>
            <p className="mt-2 text-sm text-slate-600">
              当前旅行团：<span className="font-semibold text-slate-900">{tripLabel || tripId}</span>
            </p>
            <p className="text-xs text-slate-500">团号：{tripId}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {onBackToTrip ? (
              <Button variant="secondary" onClick={onBackToTrip}>
                <ArrowLeft className="mr-1 inline h-4 w-4" />
                返回行程
              </Button>
            ) : null}
            <Button variant="secondary" onClick={() => void refreshStatus()} loading={isRefreshingStatus}>
              刷新状态
            </Button>
            <Button onClick={openCreateForm}>
              <Plus className="mr-1 inline h-4 w-4" />
              新增规则
            </Button>
          </div>
        </div>
      </div>

      {actionMessage ? (
        <p
          className={`rounded-lg p-3 text-sm ${
            actionMessage.includes('失败') ? 'bg-red-50 text-red-700' : 'bg-green-50 text-green-700'
          }`}
        >
          {actionMessage}
        </p>
      ) : null}

      {isFormVisible ? (
        <TripNotificationRuleForm
          tripId={tripId}
          templates={templates}
          initialRule={editingRule}
          saving={isSaving}
          onSubmit={handleSaveRule}
          onCancel={() => {
            setIsFormVisible(false)
            setEditingRule(null)
          }}
        />
      ) : null}

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.35fr_0.65fr]">
        <Card title="旅行团通知规则" className="border-blue-100">
          {ruleLoadState === 'loading' ? <PageState kind="loading" title="正在加载通知规则" /> : null}
          {ruleLoadState === 'error' ? (
            <PageState kind="error" title="通知规则加载失败" description={ruleError} onRetry={() => void loadData()} />
          ) : null}
          {ruleLoadState === 'empty' ? (
            <PageState kind="empty" title="当前旅行团暂无通知规则" description="点击“新增规则”开始配置" onRetry={() => void loadData()} />
          ) : null}
          {ruleLoadState === 'ready' ? (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[980px] text-sm">
                <thead>
                  <tr className="bg-blue-50 text-left text-slate-700">
                    <th className="px-3 py-2 font-semibold">规则名称</th>
                    <th className="px-3 py-2 font-semibold">时间点</th>
                    <th className="px-3 py-2 font-semibold">场景</th>
                    <th className="px-3 py-2 font-semibold">绑定模板</th>
                    <th className="px-3 py-2 font-semibold">渠道</th>
                    <th className="px-3 py-2 font-semibold">启用状态</th>
                    <th className="px-3 py-2 font-semibold">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {rules.map((rule) => (
                    <tr key={rule.id} className="border-b border-slate-100 align-top">
                      <td className="px-3 py-3">
                        <p className="font-semibold text-slate-900">{rule.name}</p>
                        <p className="text-xs text-slate-500">优先级：{rule.priority}</p>
                      </td>
                      <td className="px-3 py-3">
                        <p>{stageLabel(rule.stage)}</p>
                        <p className="text-xs text-slate-500">{timeSlotLabel(rule.timeSlot)}</p>
                      </td>
                      <td className="px-3 py-3">{sceneLabel(rule.scene)}</td>
                      <td className="px-3 py-3">
                        <p className="font-medium text-slate-900">{rule.templateName || '未绑定模板'}</p>
                        <p className="text-xs text-slate-500">{rule.templateId || '-'}</p>
                      </td>
                      <td className="px-3 py-3">
                        <div className="flex flex-wrap gap-1">
                          {rule.channels.map((channel) => (
                            <Badge key={`${rule.id}-${channel}`} variant="info">
                              {channelLabel(channel)}
                            </Badge>
                          ))}
                        </div>
                      </td>
                      <td className="px-3 py-3">
                        <Badge variant={rule.enabled ? 'success' : 'default'}>{rule.enabled ? '启用' : '停用'}</Badge>
                      </td>
                      <td className="px-3 py-3">
                        <div className="flex flex-wrap gap-2">
                          <Button variant="secondary" size="sm" onClick={() => openEditForm(rule)}>
                            <Pencil className="mr-1 inline h-3 w-3" />
                            编辑
                          </Button>
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => void toggleRule(rule)}
                            disabled={togglingRuleId === rule.id}
                          >
                            <Power className="mr-1 inline h-3 w-3" />
                            {rule.enabled ? '停用' : '启用'}
                          </Button>
                          <Button
                            variant="danger"
                            size="sm"
                            onClick={() => void removeRule(rule)}
                            disabled={deletingRuleId === rule.id}
                          >
                            <Trash2 className="mr-1 inline h-3 w-3" />
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

        <div className="space-y-6">
          <Card title="模板绑定情况" className="border-blue-100">
            {templates.length === 0 ? (
              <p className="text-sm text-slate-500">暂无可用模板</p>
            ) : (
              <div className="space-y-3">
                {templates.map((template) => {
                  const bindCount = templateUsageCount.get(template.id) || 0
                  return (
                    <div key={template.id} className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <p className="text-sm font-semibold text-slate-900">{template.name}</p>
                          <p className="mt-1 text-xs text-slate-500 line-clamp-2">{template.content}</p>
                        </div>
                        <Badge variant={template.enabled ? 'success' : 'default'}>
                          {template.enabled ? '可用' : '停用'}
                        </Badge>
                      </div>
                      <p className="mt-2 text-xs text-slate-600">
                        渠道：{template.channelLabel} · 绑定规则：{bindCount} 条
                      </p>
                    </div>
                  )
                })}
              </div>
            )}
          </Card>

          <TripNotificationStatusTable snapshot={snapshot} />
        </div>
      </div>
    </div>
  )
}
