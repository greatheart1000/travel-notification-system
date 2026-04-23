import type { Task } from './types'

export interface TaskApiResponse {
  id: string
  title: string
  type: string
  status: string
  priority: string
  risk_level?: string
  due_at: string
  departure_date?: string
  assignee_name?: string
  group_id?: string
  group_name?: string
  customer_name?: string
  destination?: string
  tags?: string[]
  ai_suggestion?: string
  history?: Array<{ id: string; action: string; operator: string; at: string; note: string }>
}

export function adaptTaskFromApi(payload: TaskApiResponse): Task {
  return {
    id: payload.id,
    title: payload.title,
    type: payload.type,
    status: (payload.status as Task['status']) ?? 'todo',
    priority: (payload.priority as Task['priority']) ?? 'P1',
    riskLevel: (payload.risk_level as Task['riskLevel']) ?? 'medium',
    dueAt: payload.due_at,
    departureDate: payload.departure_date ?? payload.due_at,
    assignee: payload.assignee_name ?? '',
    groupId: payload.group_id ?? '',
    groupName: payload.group_name ?? '',
    customerName: payload.customer_name ?? '未知客户',
    destination: payload.destination ?? '未知目的地',
    tags: payload.tags ?? [],
    aiSuggestion: payload.ai_suggestion ?? '',
    history: payload.history ?? [],
  }
}
