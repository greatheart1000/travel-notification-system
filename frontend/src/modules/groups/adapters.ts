import type { RiskGroup } from './types'

export interface RiskGroupApiResponse {
  id: string
  group_name: string
  route_name: string
  departure_date: string
  risk_score: number
  risk_level: string
  risk_tags?: string[]
  owner?: string
  pending_task_count?: number
  blocked_task_count?: number
  summary?: string
  tasks?: string[]
  collaborators?: string[]
  timeline?: Array<{ id: string; title: string; at: string; level: 'medium' | 'high' | 'critical' }>
}

export function adaptRiskGroupFromApi(payload: RiskGroupApiResponse): RiskGroup {
  return {
    id: payload.id,
    groupName: payload.group_name,
    routeName: payload.route_name,
    departureDate: payload.departure_date,
    riskScore: payload.risk_score,
    riskLevel: (payload.risk_level as RiskGroup['riskLevel']) ?? 'medium',
    riskTags: payload.risk_tags ?? [],
    owner: payload.owner ?? '待分配',
    pendingTaskCount: payload.pending_task_count ?? 0,
    blockedTaskCount: payload.blocked_task_count ?? 0,
    summary: payload.summary ?? '',
    tasks: payload.tasks ?? [],
    collaborators: payload.collaborators ?? [],
    timeline: payload.timeline ?? [],
  }
}
