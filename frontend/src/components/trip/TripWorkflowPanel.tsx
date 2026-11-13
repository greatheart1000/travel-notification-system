import { memo, useCallback, useEffect, useState } from 'react'
import {
  CheckCircle,
  ChevronDown,
  ChevronRight,
  Clock,
  Flag,
  MapPin,
  MessageSquare,
  Play,
  Plane,
  RefreshCw,
} from 'lucide-react'

interface Props { tripId: string; onOpenGroupConfig?: () => void }

interface PlaybookStep {
  id: string; stage: string; time_node: string; core_work: string
  action_detail: string; sort_order: number; is_active: boolean
}

interface WfStep { key: string; label: string; time_node: string; action_detail: string; completed: boolean; completed_at: string | null }

const STAGE_META: Record<string, { label: string; icon: typeof Plane }> = {
  pre_trip: { label: '行程前', icon: Plane },
  in_trip: { label: '行程中', icon: MapPin },
  post_trip: { label: '行程后', icon: Flag },
}

const STEP_KEY_MAP: Record<string, string[]> = {
  '游客沟通+行程单处理': ['pre_flight_notice'],
  '资源&物资确认': ['resources_verified'],
  '保险核查+群聊搭建+司导交底': ['insurance_verified', 'group_built'],
  '保险核查': ['insurance_verified'],
  '群聊搭建+司导交底': ['group_built'],
  '本地指引+通用提示': ['day1_guide_sent'],
  '时段性专属温馨提示': ['daily_reminder'],
  '时段性温馨提示': ['daily_reminder'],
  '专项安全提示': ['scene_alert'],
  '特殊游玩场景': ['scene_alert'],
  '三方协调沟通': ['issue_coordination'],
  '全程': ['issue_coordination'],
  '欢送+满意度调研': ['farewell_sent', 'survey_sent'],
  '售后跟进+客户存档': ['follow_up'],
  '群聊解散': ['group_dismissed'],
}

const MESSAGE_STEPS = new Set(['pre_flight_notice', 'group_built', 'day1_guide_sent', 'farewell_sent', 'survey_sent', 'group_dismissed', 'resources_verified', 'insurance_verified', 'daily_reminder', 'scene_alert', 'issue_coordination', 'follow_up'])

export const TripWorkflowPanel = memo(function TripWorkflowPanel({ tripId, onOpenGroupConfig }: Props) {
  const [playbook, setPlaybook] = useState<PlaybookStep[]>([])
  const [wfStatus, setWfStatus] = useState<Record<string, any>>({})
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [message, setMessage] = useState<{ text: string; ok: boolean; showWecomAction?: boolean } | null>(null)
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set())

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const token = localStorage.getItem('access_token') || ''
      const headers = { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }
      const [pbRes, wfRes] = await Promise.all([
        fetch('/api/lifecycle-playbook', { headers }).then(r => r.json()),
        fetch(`/api/trips/${tripId}/workflow-status`, { headers }).then(r => r.json()),
      ])
      setPlaybook(pbRes?.data?.playbook || [])
      setWfStatus(wfRes?.data || {})
    } catch { /* ignore */ }
    finally { setLoading(false) }
  }, [tripId])

  useEffect(() => { fetchData() }, [fetchData])

  const showMsg = useCallback((text: string, ok = true) => {
    setMessage({
      text,
      ok,
      showWecomAction: !ok && /企业微信|Webhook/i.test(text),
    })
    setTimeout(() => setMessage(null), 6000)
  }, [])

  const toggleExpand = useCallback((key: string) => {
    setExpandedSteps(prev => { const next = new Set(prev); if (next.has(key)) next.delete(key); else next.add(key); return next })
  }, [])

  const handleSend = useCallback(async (stepKey: string) => {
    setActionLoading(stepKey)
    try {
      const token = localStorage.getItem('access_token') || ''
      const resp = await fetch(`/api/trips/${tripId}/workflow/execute?step=${stepKey}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }, body: '{}',
      })
      const data = await resp.json()
      if (data.code === 200) { showMsg(data.data?.message || '发送成功'); await fetchData() }
      else showMsg(data.error || data.detail || '发送失败', false)
    } catch (e: any) { showMsg(e?.message || '发送失败', false) }
    finally { setActionLoading(null) }
  }, [tripId, fetchData, showMsg])

  // 将 playbook 与 workflow-status 合并
  const stepsByStage: Record<string, WfStep[]> = { pre_trip: [], in_trip: [], post_trip: [] }
  for (const pb of playbook) {
    const keys = STEP_KEY_MAP[pb.core_work] || [pb.core_work.replace(/\s+/g, '_').toLowerCase()]
    const primaryKey = keys[0] || pb.core_work.replace(/\s+/g, '_').toLowerCase()
    const msgKeys = keys.filter(k => MESSAGE_STEPS.has(k))
    const wfEntry = (wfStatus as any)?.[pb.stage]?.find((s: any) => s.key === primaryKey)
    stepsByStage[pb.stage] = stepsByStage[pb.stage] || []
    stepsByStage[pb.stage].push({
      key: primaryKey, label: pb.core_work, time_node: pb.time_node, action_detail: pb.action_detail,
      completed: wfEntry?.completed || false, completed_at: wfEntry?.completed_at || null,
      _msgKeys: msgKeys,
    } as any)
  }

  const allSteps = [...stepsByStage.pre_trip, ...stepsByStage.in_trip, ...stepsByStage.post_trip]
  const done = allSteps.filter(s => s.completed).length
  const percent = allSteps.length ? Math.round((done / allSteps.length) * 100) : 0
  const currentStage = String(wfStatus.current_stage || '')

  if (loading) {
    return (
      <div className="rounded-card border border-paper-200 bg-white p-6 text-center text-sm text-paper-500">
        加载执行流程
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="rounded-card border border-paper-200 bg-white p-4 shadow-card">
        <div className="mb-2 flex items-center justify-between">
          <span className="text-sm font-medium text-paper-700">执行进度</span>
          <button
            type="button"
            onClick={fetchData}
            className="rounded-control p-1 text-paper-500 transition-colors hover:bg-paper-100 hover:text-paper-900"
            aria-label="刷新执行进度"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
        <div className="flex items-center gap-3">
          <div className="h-1.5 flex-1 overflow-hidden rounded-sm bg-paper-100">
            <div
              className="h-full origin-left bg-accent-600 transition-transform duration-300"
              style={{ transform: `scaleX(${percent / 100})` }}
            />
          </div>
          <span className="text-sm font-medium tabular-nums text-paper-600">
            {done}/{allSteps.length}
          </span>
        </div>
        {currentStage ? (
          <div className="mt-1 text-xs text-paper-500">
            当前阶段：{STAGE_META[currentStage]?.label ?? currentStage}
          </div>
        ) : null}
      </div>

      {message && (
        <div
          className={`rounded-control border px-4 py-3 text-sm ${
            message.ok
              ? 'border-success-200 bg-success-50 text-success-700'
              : 'border-danger-200 bg-danger-50 text-danger-700'
          }`}
        >
          <span>{message.text}</span>
          {message.showWecomAction && onOpenGroupConfig ? (
            <button
              type="button"
              onClick={onOpenGroupConfig}
              className="mt-2 block font-medium text-danger-800 underline underline-offset-2 hover:text-danger-900"
            >
              去群配置填写企业微信 Webhook
            </button>
          ) : null}
        </div>
      )}

      {(['pre_trip', 'in_trip', 'post_trip'] as const).map(stage => {
        const steps = stepsByStage[stage]
        if (!steps?.length) return null
        const meta = STAGE_META[stage]
        const StageIcon = meta.icon
        return (
          <div key={stage}>
            <h3 className="mb-3 flex items-center gap-2 text-base font-semibold text-paper-900">
              <StageIcon className="h-4 w-4 text-paper-500" />
              {meta.label}
              <span className="text-xs font-normal text-paper-400">({steps.length} 项)</span>
            </h3>
            <div className="space-y-3">
              {steps.map(step => {
                const isExpanded = expandedSteps.has(step.key)
                const isBusy = actionLoading === step.key
                return (
                  <div
                    key={step.key}
                    className={`overflow-hidden rounded-card border transition-colors ${
                      step.completed
                        ? 'border-success-200 bg-success-50/40'
                        : 'border-paper-200 bg-white hover:border-paper-300'
                    }`}
                  >
                    <div
                      className="flex cursor-pointer items-start justify-between px-4 py-3"
                      onClick={() => toggleExpand(step.key)}
                    >
                      <div className="flex min-w-0 flex-1 items-start gap-3">
                        {step.completed ? (
                          <CheckCircle className="mt-0.5 h-4 w-4 shrink-0 text-success-600" />
                        ) : (
                          <Clock className="mt-0.5 h-4 w-4 shrink-0 text-paper-400" />
                        )}
                        <div className="min-w-0">
                          <div className="flex items-center gap-2 text-sm font-medium text-paper-900">
                            <span className="rounded-control bg-paper-100 px-1.5 py-0.5 text-xs font-normal tabular-nums text-paper-500">
                              {step.time_node}
                            </span>
                            {step.label}
                          </div>
                          <div className="mt-0.5 line-clamp-1 text-xs text-paper-400">
                            {step.action_detail?.replace(/<br>/g, ' ').slice(0, 80)}
                          </div>
                          {step.completed && step.completed_at ? (
                            <div className="mt-1 text-xs text-success-700">
                              已完成 {step.completed_at.slice(0, 16).replace('T', ' ')}
                            </div>
                          ) : null}
                        </div>
                      </div>
                      <div className="ml-2 flex shrink-0 items-center gap-2">
                        {!step.completed && (
                          <button
                            type="button"
                            onClick={(event) => {
                              event.stopPropagation()
                              void handleSend(step.key)
                            }}
                            disabled={isBusy}
                            className="flex items-center gap-1 rounded-control bg-accent-600 px-2.5 py-1.5 text-sm font-medium text-white transition-colors hover:bg-accent-700 disabled:opacity-50"
                          >
                            {isBusy ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
                            执行
                          </button>
                        )}
                        {isExpanded ? (
                          <ChevronDown className="h-4 w-4 text-paper-400" />
                        ) : (
                          <ChevronRight className="h-4 w-4 text-paper-400" />
                        )}
                      </div>
                    </div>

                    {isExpanded && (
                      <div className="border-t border-paper-200 px-4 pb-4 pt-3">
                        {(step as any)._msgKeys?.length > 0 ? (
                          (step as any)._msgKeys.map((msgKey: string) => (
                            <div key={msgKey} className="mb-3">
                              <div className="mb-2 flex items-center gap-1 text-xs text-paper-500">
                                <MessageSquare className="h-3.5 w-3.5" /> 将发送到企业微信群
                              </div>
                              <PreviewInline tripId={tripId} stepKey={msgKey} />
                            </div>
                          ))
                        ) : (
                          <div className="py-4 text-center text-sm text-paper-400">
                            此步骤为人工确认项，无需发送消息
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        )
      })}
    </div>
  )
})

// ── 消息预览 ─────────────────────────────────────────────────────────────

function PreviewInline({ tripId, stepKey }: { tripId: string; stepKey: string }) {
  const [content, setContent] = useState('加载中…')
  useEffect(() => {
    let active = true
    const token = localStorage.getItem('access_token') || ''
    fetch(`/api/trips/${tripId}/workflow/execute?step=${stepKey}&preview=true`, {
      method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }, body: '{}',
    }).then(r => r.json()).then(d => {
      if (!active) return
      setContent(d?.data?.rendered_content || d?.data?.results?.map((r: any) => r.detail).join('\n') || '（暂无预览）')
    }).catch(() => { if (active) setContent('（加载失败）') })
    return () => { active = false }
  }, [tripId, stepKey])
  return (
    <div className="max-h-60 overflow-y-auto rounded-control border border-paper-200 bg-white p-3">
      <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-paper-700">{content}</pre>
    </div>
  )
}
