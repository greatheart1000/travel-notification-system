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
  teamId: string
  teamName: string
  teamCode: string
  destination: string
  departureDate: string
  dueAt: string
  assigneeId: string
  assigneeName: string
  source: string
  relatedDayId?: string
  relatedNotificationTaskId?: string
  recommendedAction: string
  aiSuggestion: string
  linkedNotificationNode: string
  currentTripDay: number
  travelerCount: number
  overdueReason?: string
  remedySuggestion?: string
  tags: string[]
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
