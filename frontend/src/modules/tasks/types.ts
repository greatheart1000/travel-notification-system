export type TaskStatus = 'todo' | 'in_progress' | 'done' | 'overdue' | 'pending_takeover' | 'blocked'
export type TaskPriority = 'P0' | 'P1' | 'P2'
export type TaskRiskLevel = 'low' | 'medium' | 'high' | 'critical'

export interface TaskHistoryRecord {
  id: string
  action: string
  operator: string
  at: string
  note: string
}

export interface Task {
  id: string
  title: string
  type: string
  status: TaskStatus
  priority: TaskPriority
  riskLevel: TaskRiskLevel
  dueAt: string
  departureDate: string
  assignee: string
  groupId: string
  groupName: string
  customerName: string
  destination: string
  tags: string[]
  aiSuggestion: string
  history: TaskHistoryRecord[]
}

export interface TaskListStats {
  total: number
  urgent: number
  dueSoon: number
  highRisk: number
}

export interface TaskListFilters {
  keyword?: string
  riskLevel?: TaskRiskLevel | 'all'
  overdueWindow?: 'all' | 'lt2h' | '2to24h' | 'gt24h'
}

export type TaskBucket = 'todo' | 'overdue' | 'takeover' | 'my'
