import { completeTask, deferTask, getDb, markTaskRisk, takeoverTask, updateTaskStatus } from '../workbench/mockDb'
import type { Task, TaskBucket, TaskListFilters, TaskListStats, TaskStatus } from './types'

const CURRENT_USER_ID = 'u-zhangsan'

function hoursUntil(dateText: string): number {
  return (new Date(dateText).getTime() - Date.now()) / (1000 * 60 * 60)
}

function matchesBucket(task: Task, bucket: TaskBucket): boolean {
  if (bucket === 'todo') {
    return task.assigneeId === CURRENT_USER_ID && task.status === 'todo'
  }
  if (bucket === 'overdue') {
    return task.assigneeId === CURRENT_USER_ID && task.status === 'overdue'
  }
  if (bucket === 'takeover') {
    return task.status === 'pending_takeover' || !task.assigneeId
  }
  if (bucket === 'my') {
    return matchesMyQueue(task)
  }
  return task.status !== 'done'
}

function matchesMyQueue(task: Task): boolean {
  if (task.status === 'done') return false
  const mine = task.assigneeId === CURRENT_USER_ID && ['todo', 'overdue', 'pending_takeover', 'blocked'].includes(task.status)
  const highRisk = task.riskLevel === 'high' || task.riskLevel === 'critical'
  const dueSoon = hoursUntil(task.dueAt) <= 24
  return mine || highRisk || dueSoon
}

function sortMyQueue(tasks: Task[]): Task[] {
  return [...tasks].sort((a, b) => {
    const overdueA = a.status === 'overdue' ? 1 : 0
    const overdueB = b.status === 'overdue' ? 1 : 0
    if (overdueA !== overdueB) return overdueB - overdueA

    const highRiskA = ['high', 'critical'].includes(a.riskLevel) ? 1 : 0
    const highRiskB = ['high', 'critical'].includes(b.riskLevel) ? 1 : 0
    if (highRiskA !== highRiskB) return highRiskB - highRiskA

    const takeoverA = a.status === 'pending_takeover' ? 1 : 0
    const takeoverB = b.status === 'pending_takeover' ? 1 : 0
    if (takeoverA !== takeoverB) return takeoverB - takeoverA

    const dueDiff = new Date(a.dueAt).getTime() - new Date(b.dueAt).getTime()
    if (dueDiff !== 0) return dueDiff

    return new Date(a.departureDate).getTime() - new Date(b.departureDate).getTime()
  })
}

function applyFilters(tasks: Task[], filters?: TaskListFilters): Task[] {
  if (!filters) return tasks
  return tasks.filter((task) => {
    const keywordOk =
      !filters.keyword ||
      task.title.includes(filters.keyword) ||
      task.teamName.includes(filters.keyword) ||
      task.teamCode.includes(filters.keyword) ||
      task.destination.includes(filters.keyword)

    const riskOk = !filters.riskLevel || filters.riskLevel === 'all' || task.riskLevel === filters.riskLevel

    let overdueWindowOk = true
    if (filters.overdueWindow && filters.overdueWindow !== 'all') {
      const overdueHours = (Date.now() - new Date(task.dueAt).getTime()) / (1000 * 60 * 60)
      if (filters.overdueWindow === 'lt2h') overdueWindowOk = overdueHours > 0 && overdueHours < 2
      if (filters.overdueWindow === '2to24h') overdueWindowOk = overdueHours >= 2 && overdueHours <= 24
      if (filters.overdueWindow === 'gt24h') overdueWindowOk = overdueHours > 24
    }

    return keywordOk && riskOk && overdueWindowOk
  })
}

export const taskMockDataSource = {
  async list(bucket: TaskBucket, filters?: TaskListFilters): Promise<Task[]> {
    const allTasks = getDb().tasks.filter((task) => matchesBucket(task, bucket))
    const ordered = bucket === 'my' ? sortMyQueue(allTasks) : allTasks
    return applyFilters(ordered, filters)
  },

  async getById(taskId: string): Promise<Task | null> {
    return getDb().tasks.find((task) => task.id === taskId) ?? null
  },

  async getStats(bucket: TaskBucket): Promise<TaskListStats> {
    const tasks = await this.list(bucket)
    const now = Date.now()
    const twoHours = 2 * 60 * 60 * 1000
    return {
      total: tasks.length,
      urgent: tasks.filter((task) => task.priority === 'P0').length,
      dueSoon: tasks.filter((task) => new Date(task.dueAt).getTime() - now <= twoHours).length,
      highRisk: tasks.filter((task) => ['high', 'critical'].includes(task.riskLevel)).length,
    }
  },

  async takeover(taskId: string, assigneeId = CURRENT_USER_ID, assigneeName = '张三'): Promise<Task | null> {
    return takeoverTask(taskId, assigneeId, assigneeName)
  },

  async updateStatus(taskId: string, status: TaskStatus): Promise<Task | null> {
    return updateTaskStatus(taskId, status)
  },

  async complete(taskId: string): Promise<Task | null> {
    return completeTask(taskId)
  },

  async defer(taskId: string): Promise<Task | null> {
    return deferTask(taskId)
  },

  async markRisk(taskId: string): Promise<Task | null> {
    return markTaskRisk(taskId)
  },

  async getWorkbenchCards(): Promise<{ todo: number; overdue: number; highRisk: number; takeover: number }> {
    const tasks = getDb().tasks
    const highRiskTeams = new Set(
      tasks.filter((task) => ['high', 'critical'].includes(task.riskLevel)).map((task) => task.teamId),
    )

    return {
      todo: tasks.filter((task) => task.status === 'todo' && task.assigneeId === CURRENT_USER_ID).length,
      overdue: tasks.filter((task) => task.status === 'overdue' && task.assigneeId === CURRENT_USER_ID).length,
      highRisk: highRiskTeams.size,
      takeover: tasks.filter((task) => task.status === 'pending_takeover' || !task.assigneeId).length,
    }
  },

  async getMyQueue(limit = 8): Promise<Task[]> {
    const queue = sortMyQueue(getDb().tasks.filter((task) => matchesMyQueue(task)))
    return queue.slice(0, limit)
  },
}
