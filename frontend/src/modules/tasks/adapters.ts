import type { Task } from './types'
import type { ExecutionTask, WorkbenchTask } from '../../types/api'

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

function normalizeStatus(status?: string): Task['status'] {
  if (status === 'handover_in_progress') return 'pending_takeover'
  if (status === 'todo' || status === 'in_progress' || status === 'done' || status === 'overdue' || status === 'blocked') {
    return status
  }
  return 'todo'
}

export function adaptTaskFromWorkbenchTask(payload: WorkbenchTask): Task {
  return {
    id: payload.id,
    title: payload.title,
    type: payload.nodeKey || payload.stage || 'workbench_task',
    status: normalizeStatus(payload.status),
    priority: payload.priority === 'p0' ? 'P0' : payload.priority === 'p2' ? 'P2' : 'P1',
    riskLevel: payload.riskLevel === 'unknown' ? 'medium' : payload.riskLevel,
    dueAt: payload.dueAt || new Date().toISOString(),
    departureDate: payload.dueAt || new Date().toISOString(),
    assignee: payload.ownerName || '',
    groupId: payload.tripId,
    groupName: payload.tripName,
    customerName: '待补充',
    destination: payload.tripName,
    tags: [payload.stage || '行程任务'],
    aiSuggestion: '建议优先核对通知节点和触达结果，必要时发起人工接管。',
    history: [],
  }
}

export function adaptTaskFromExecutionTask(payload: ExecutionTask, tripMeta: { tripId: string; tripName: string }): Task {
  return {
    id: payload.taskId,
    title: payload.title,
    type: payload.nodeKey || payload.stage || 'execution_task',
    status: normalizeStatus(payload.status),
    priority: 'P1',
    riskLevel: 'medium',
    dueAt: payload.dueAt || new Date().toISOString(),
    departureDate: payload.dueAt || new Date().toISOString(),
    assignee: payload.ownerName || '',
    groupId: tripMeta.tripId,
    groupName: tripMeta.tripName,
    customerName: '待补充',
    destination: tripMeta.tripName,
    tags: [payload.stage || '行程任务'],
    aiSuggestion: '建议结合团进度与天气变化，确认是否需要追加提醒。',
    history: [],
  }
}
