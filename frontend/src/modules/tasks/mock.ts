import { getDb, takeoverTask, updateTaskStatus } from '../workbench/mockDb'
import type { Task, TaskBucket, TaskListFilters, TaskListStats, TaskStatus } from './types'

function matchesBucket(task: Task, bucket: TaskBucket): boolean {
  if (bucket === 'todo') {
    return ['todo', 'in_progress', 'blocked'].includes(task.status)
  }
  if (bucket === 'overdue') {
    return task.status === 'overdue'
  }
  if (bucket === 'takeover') {
    return task.status === 'pending_takeover'
  }
  return ['todo', 'in_progress', 'overdue', 'blocked'].includes(task.status)
}

function applyFilters(tasks: Task[], filters?: TaskListFilters): Task[] {
  if (!filters) return tasks
  return tasks.filter((task) => {
    const keywordOk =
      !filters.keyword ||
      task.title.includes(filters.keyword) ||
      task.groupName.includes(filters.keyword) ||
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
    const scoped = getDb().tasks.filter((task) => matchesBucket(task, bucket))
    return applyFilters(scoped, filters)
  },

  async getById(taskId: string): Promise<Task | null> {
    return getDb().tasks.find((task) => task.id === taskId) ?? null
  },

  async getStats(bucket: TaskBucket): Promise<TaskListStats> {
    const tasks = getDb().tasks.filter((task) => matchesBucket(task, bucket))
    const now = Date.now()
    const twoHours = 2 * 60 * 60 * 1000
    return {
      total: tasks.length,
      urgent: tasks.filter((task) => task.priority === 'P0').length,
      dueSoon: tasks.filter((task) => new Date(task.dueAt).getTime() - now <= twoHours).length,
      highRisk: tasks.filter((task) => ['high', 'critical'].includes(task.riskLevel)).length,
    }
  },

  async takeover(taskId: string, operator = '张三'): Promise<Task | null> {
    return takeoverTask(taskId, operator)
  },

  async updateStatus(taskId: string, status: TaskStatus): Promise<Task | null> {
    return updateTaskStatus(taskId, status)
  },

  async getDashboardCards(): Promise<{ todo: number; overdue: number; highRisk: number; takeover: number }> {
    const tasks = getDb().tasks
    const groups = getDb().groups
    return {
      todo: tasks.filter((task) => ['todo', 'in_progress', 'blocked'].includes(task.status)).length,
      overdue: tasks.filter((task) => task.status === 'overdue').length,
      highRisk: groups.filter((group) => ['high', 'critical'].includes(group.riskLevel)).length,
      takeover: tasks.filter((task) => task.status === 'pending_takeover').length,
    }
  },

  async getMyQueue(limit = 5): Promise<Task[]> {
    return getDb()
      .tasks.filter((task) => ['todo', 'in_progress', 'overdue'].includes(task.status))
      .slice(0, limit)
  },
}
