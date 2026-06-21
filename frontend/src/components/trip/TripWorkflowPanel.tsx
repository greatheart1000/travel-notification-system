import { memo, useCallback, useEffect, useState } from 'react'
import { CheckCircle, Clock, Play, RefreshCw, ChevronDown, ChevronRight, MessageSquare } from 'lucide-react'

interface Props { tripId: string }

interface PlaybookStep {
  id: string; stage: string; time_node: string; core_work: string
  action_detail: string; sort_order: number; is_active: boolean
}

interface WfStep { key: string; label: string; time_node: string; action_detail: string; completed: boolean; completed_at: string | null }

const STAGE_ICONS: Record<string, string> = { pre_trip: '🚀', in_trip: '📍', post_trip: '🏁' }
const STAGE_LABELS: Record<string, string> = { pre_trip: '行程前', in_trip: '行程中', post_trip: '行程后' }

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
// 所有步骤都有对应的消息模板
const MESSAGE_STEPS = new Set(['pre_flight_notice', 'group_built', 'day1_guide_sent', 'farewell_sent', 'survey_sent', 'group_dismissed', 'resources_verified', 'insurance_verified', 'daily_reminder', 'scene_alert', 'issue_coordination', 'follow_up'])

export const TripWorkflowPanel = memo(function TripWorkflowPanel({ tripId }: Props) {
  const [playbook, setPlaybook] = useState<PlaybookStep[]>([])
  const [wfStatus, setWfStatus] = useState<Record<string, any>>({})
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [message, setMessage] = useState<{ text: string; ok: boolean } | null>(null)
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
    setMessage({ text, ok }); setTimeout(() => setMessage(null), 4000)
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

  if (loading) return <div className="p-6 text-center text-sm text-gray-500">加载执行流程...</div>

  return (
    <div className="space-y-6">
      {/* 进度条 */}
      <div className="bg-white rounded-xl border p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-semibold text-gray-700">执行进度</span>
          <button onClick={fetchData} className="p-1 hover:bg-gray-100 rounded"><RefreshCw className="h-4 w-4 text-gray-400" /></button>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex-1 bg-gray-200 rounded-full h-2.5">
            <div className="bg-cyan-500 h-2.5 rounded-full transition-all duration-500"
              style={{ width: `${allSteps.length ? Math.round((done / allSteps.length) * 100) : 0}%` }} />
          </div>
          <span className="text-sm font-medium text-gray-600">{done}/{allSteps.length}</span>
        </div>
        {wfStatus.current_stage && (
          <div className="text-xs text-gray-400 mt-1">当前阶段：{STAGE_LABELS[wfStatus.current_stage] || wfStatus.current_stage}</div>
        )}
      </div>

      {message && (
        <div className={`text-sm p-3 rounded-lg ${message.ok ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-700 border border-red-200'}`}>
          {message.text}
        </div>
      )}

      {/* 分阶段 */}
      {(['pre_trip', 'in_trip', 'post_trip'] as const).map(stage => {
        const steps = stepsByStage[stage]
        if (!steps?.length) return null
        return (
          <div key={stage}>
            <h3 className="text-base font-bold text-gray-800 mb-3 flex items-center gap-2">
              <span>{STAGE_ICONS[stage]}</span> {STAGE_LABELS[stage]}
              <span className="text-xs font-normal text-gray-400">({steps.length}项)</span>
            </h3>
            <div className="space-y-3">
              {steps.map(step => {
                const isExpanded = expandedSteps.has(step.key)
                const isBusy = actionLoading === step.key
                return (
                  <div key={step.key}
                    className={`border-2 rounded-xl overflow-hidden transition-all ${
                      step.completed ? 'border-green-300 bg-green-50/40' : 'border-gray-200 bg-white hover:border-cyan-200'
                    }`}>
                    {/* 标题行 */}
                    <div className="flex items-start justify-between px-4 py-3 cursor-pointer" onClick={() => toggleExpand(step.key)}>
                      <div className="flex items-start gap-3 min-w-0 flex-1">
                        {step.completed ? <CheckCircle className="h-5 w-5 text-green-500 flex-shrink-0 mt-0.5" /> : <Clock className="h-5 w-5 text-gray-300 flex-shrink-0 mt-0.5" />}
                        <div className="min-w-0">
                          <div className="text-sm font-semibold flex items-center gap-2">
                            <span className="text-xs px-1.5 py-0.5 bg-gray-100 rounded text-gray-500 font-normal">{step.time_node}</span>
                            {step.label}
                          </div>
                          <div className="text-xs text-gray-400 mt-0.5 line-clamp-1">{step.action_detail?.replace(/<br>/g, ' ').slice(0, 80)}</div>
                          {step.completed && step.completed_at && (
                            <div className="text-xs text-green-600 mt-0.5">✅ 已完成 {step.completed_at.slice(0, 16).replace('T', ' ')}</div>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0 ml-2">
                        {!step.completed && (
                          <button onClick={(e) => { e.stopPropagation(); handleSend(step.key) }} disabled={isBusy}
                            className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-white bg-cyan-600 hover:bg-cyan-700 rounded-lg disabled:opacity-50">
                            {isBusy ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />} 执行
                          </button>
                        )}
                        {isExpanded ? <ChevronDown className="h-5 w-5 text-gray-400" /> : <ChevronRight className="h-5 w-5 text-gray-400" />}
                      </div>
                    </div>

                    {/* 展开显示消息预览 */}
                    {isExpanded && (
                      <div className="px-4 pb-4 border-t border-gray-100 pt-3">
                        {(step as any)._msgKeys?.length > 0 ? (
                          (step as any)._msgKeys.map((msgKey: string) => (
                            <div key={msgKey} className="mb-3">
                              <div className="text-xs font-medium text-gray-500 mb-2 flex items-center gap-1">
                                <MessageSquare className="h-3.5 w-3.5" /> 将发送到企业微信群：
                              </div>
                              <PreviewInline tripId={tripId} stepKey={msgKey} />
                            </div>
                          ))
                        ) : (
                          <div className="text-sm text-gray-400 py-4 text-center">
                            ✅ 此步骤为人工确认项，无需发送消息
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
  const [content, setContent] = useState('加载中...')
  useEffect(() => {
    let active = true
    const token = localStorage.getItem('access_token') || ''
    fetch(`/api/trips/${tripId}/workflow/execute?step=${stepKey}&preview=true`, {
      method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }, body: '{}',
    }).then(r => r.json()).then(d => {
      if (!active) return
      setContent(d?.data?.rendered_content || d?.data?.results?.map((r: any) => r.detail).join('\n') || '(暂无预览)')
    }).catch(() => { if (active) setContent('(加载失败)') })
    return () => { active = false }
  }, [tripId, stepKey])
  return <div className="bg-white rounded-lg border border-gray-200 p-3 max-h-60 overflow-y-auto">
    <pre className="text-sm text-gray-700 whitespace-pre-wrap font-sans leading-relaxed">{content}</pre>
  </div>
}

