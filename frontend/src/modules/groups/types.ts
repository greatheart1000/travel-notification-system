import type { Task } from '../tasks/types'

export type GroupRiskLevel = 'medium' | 'high' | 'critical'

export interface RiskTimelineEvent {
  id: string
  title: string
  at: string
  level: GroupRiskLevel
}

export interface RiskGroup {
  id: string
  groupName: string
  routeName: string
  departureDate: string
  riskScore: number
  riskLevel: GroupRiskLevel
  riskTags: string[]
  owner: string
  pendingTaskCount: number
  blockedTaskCount: number
  summary: string
  tasks: string[]
  collaborators: string[]
  timeline: RiskTimelineEvent[]
}

export interface RiskGroupDetail extends RiskGroup {
  taskItems: Task[]
}

export interface RiskGroupStats {
  total: number
  critical: number
  departingSoon: number
  pendingTasks: number
}
