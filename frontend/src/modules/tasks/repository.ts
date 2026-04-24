import type { Task, TaskBucket, TaskListFilters, TaskListStats, TaskStatus } from './types'
import { taskMockDataSource } from './mock'
import { dashboardApi, notificationsApi, tripsApi } from '../../services/api'
import { adaptTaskFromExecutionTask, adaptTaskFromWorkbenchTask } from './adapters'

export interface TaskRepository {
  list(bucket: TaskBucket, filters?: TaskListFilters): Promise<Task[]>
  getById(taskId: string): Promise<Task | null>
  getStats(bucket: TaskBucket): Promise<TaskListStats>
  takeover(taskId: string, operator?: string): Promise<Task | null>
  updateStatus(taskId: string, status: TaskStatus): Promise<Task | null>
  complete(taskId: string): Promise<Task | null>
  defer(taskId: string): Promise<Task | null>
  markRisk(taskId: string): Promise<Task | null>
  getDashboardCards(): Promise<{ todo: number; overdue: number; highRisk: number; takeover: number }>
  getMyQueue(limit?: number): Promise<Task[]>
}

export class MockTaskRepository implements TaskRepository {
  list(bucket: TaskBucket, filters?: TaskListFilters): Promise<Task[]> {
    return taskMockDataSource.list(bucket, filters)
  }

  getById(taskId: string): Promise<Task | null> {
    return taskMockDataSource.getById(taskId)
  }

  getStats(bucket: TaskBucket): Promise<TaskListStats> {
    return taskMockDataSource.getStats(bucket)
  }

  takeover(taskId: string, operator?: string): Promise<Task | null> {
    return taskMockDataSource.takeover(taskId, operator)
  }

  updateStatus(taskId: string, status: TaskStatus): Promise<Task | null> {
    return taskMockDataSource.updateStatus(taskId, status)
  }
  complete(taskId: string): Promise<Task | null> {
    return taskMockDataSource.complete(taskId)
  }
  defer(taskId: string): Promise<Task | null> {
    return taskMockDataSource.defer(taskId)
  }
  markRisk(taskId: string): Promise<Task | null> {
    return taskMockDataSource.markRisk(taskId)
  }

  getDashboardCards(): Promise<{ todo: number; overdue: number; highRisk: number; takeover: number }> {
    return taskMockDataSource.getDashboardCards()
  }

  getMyQueue(limit?: number): Promise<Task[]> {
    return taskMockDataSource.getMyQueue(limit)
  }
}

export class RealTaskRepository implements TaskRepository {
  private async fetchTasksFromApi(): Promise<Task[]> {
    const actionItems = await dashboardApi.getWorkbenchActionItems({ limit: 200, ownerScope: 'all' })
    return actionItems.map((item) => adaptTaskFromWorkbenchTask(item))
  }

  async list(bucket: TaskBucket, filters?: TaskListFilters): Promise<Task[]> {
    let tasks = await this.fetchTasksFromApi()
    if (bucket === 'todo') {
      tasks = tasks.filter((task) => ['todo', 'in_progress', 'blocked'].includes(task.status))
    } else if (bucket === 'overdue') {
      tasks = tasks.filter((task) => task.status === 'overdue')
    } else if (bucket === 'takeover') {
      tasks = tasks.filter((task) => task.status === 'pending_takeover')
    } else {
      tasks = tasks.filter((task) => task.status !== 'done')
    }

    if (filters?.keyword) {
      tasks = tasks.filter((task) => `${task.title}${task.teamName}${task.destination}${task.teamCode}`.includes(filters.keyword!))
    }
    if (filters?.riskLevel && filters.riskLevel !== 'all') {
      tasks = tasks.filter((task) => task.riskLevel === filters.riskLevel)
    }
    return tasks
  }

  async getById(taskId: string): Promise<Task | null> {
    const tasks = await this.fetchTasksFromApi()
    const direct = tasks.find((item) => item.id === taskId)
    if (direct) return direct

    const rows = await tripsApi.listExecutionRows({ ownerScope: 'all' })
    for (const row of rows) {
      const detail = await tripsApi.getExecutionDetail(row.tripId)
      const hit = detail.tasks.find((task) => task.taskId === taskId)
      if (hit) {
        return adaptTaskFromExecutionTask(hit, { tripId: detail.tripId, tripName: detail.tripName })
      }
    }
    return null
  }

  async getStats(bucket: TaskBucket): Promise<TaskListStats> {
    const tasks = await this.list(bucket)
    const now = Date.now()
    return {
      total: tasks.length,
      urgent: tasks.filter((task) => task.priority === 'P0').length,
      dueSoon: tasks.filter((task) => new Date(task.dueAt).getTime() - now <= 2 * 60 * 60 * 1000).length,
      highRisk: tasks.filter((task) => ['high', 'critical'].includes(task.riskLevel)).length,
    }
  }

  async takeover(taskId: string, operator = '张三'): Promise<Task | null> {
    await notificationsApi.assignTakeover({
      taskId,
      assigneeUserId: 'u-zhangsan',
      assigneeName: operator,
      note: 'frontend takeover action',
    })
    return this.getById(taskId)
  }

  async updateStatus(taskId: string, status: TaskStatus): Promise<Task | null> {
    if (status === 'done') {
      await notificationsApi.completeTask({ taskId, resultNote: 'done from frontend' })
      return this.getById(taskId)
    }
    if (status === 'pending_takeover') {
      await notificationsApi.assignTakeover({
        taskId,
        assigneeUserId: 'u-zhangsan',
        assigneeName: '任务接管池',
        note: '转派接管',
      })
      return this.getById(taskId)
    }
    if (status === 'in_progress') {
      await notificationsApi.nudgeTask({ taskId, targetRole: 'concierge', message: '开始处理任务' })
    }
    return this.getById(taskId)
  }

  async getDashboardCards(): Promise<{ todo: number; overdue: number; highRisk: number; takeover: number }> {
    const overview = await dashboardApi.getWorkbenchOverview({ ownerScope: 'all' })
    return {
      todo: overview.pendingTasks,
      overdue: overview.overdueTasks,
      highRisk: overview.riskyTrips,
      takeover: overview.pendingTakeovers,
    }
  }
  async getMyQueue(limit = 5): Promise<Task[]> {
    const items = await dashboardApi.getWorkbenchActionItems({ limit, ownerScope: 'mine' })
    return items.map((item) => adaptTaskFromWorkbenchTask(item))
  }

  complete(taskId: string): Promise<Task | null> {
    return this.updateStatus(taskId, 'done')
  }
  defer(taskId: string): Promise<Task | null> {
    return this.updateStatus(taskId, 'todo')
  }
  markRisk(taskId: string): Promise<Task | null> {
    return this.updateStatus(taskId, 'blocked')
  }
}

class AutoTaskRepository implements TaskRepository {
  private readonly mock = new MockTaskRepository()
  private readonly real = new RealTaskRepository()

  async list(bucket: TaskBucket, filters?: TaskListFilters): Promise<Task[]> {
    try {
      return await this.real.list(bucket, filters)
    } catch {
      return this.mock.list(bucket, filters)
    }
  }
  async getById(taskId: string): Promise<Task | null> {
    try {
      return await this.real.getById(taskId)
    } catch {
      return this.mock.getById(taskId)
    }
  }
  async getStats(bucket: TaskBucket): Promise<TaskListStats> {
    try {
      return await this.real.getStats(bucket)
    } catch {
      return this.mock.getStats(bucket)
    }
  }
  async takeover(taskId: string, operator?: string): Promise<Task | null> {
    try {
      return await this.real.takeover(taskId, operator)
    } catch {
      return this.mock.takeover(taskId, operator)
    }
  }
  async updateStatus(taskId: string, status: TaskStatus): Promise<Task | null> {
    try {
      return await this.real.updateStatus(taskId, status)
    } catch {
      return this.mock.updateStatus(taskId, status)
    }
  }
  async complete(taskId: string): Promise<Task | null> {
    try {
      return await this.real.complete(taskId)
    } catch {
      return this.mock.complete(taskId)
    }
  }
  async defer(taskId: string): Promise<Task | null> {
    try {
      return await this.real.defer(taskId)
    } catch {
      return this.mock.defer(taskId)
    }
  }
  async markRisk(taskId: string): Promise<Task | null> {
    try {
      return await this.real.markRisk(taskId)
    } catch {
      return this.mock.markRisk(taskId)
    }
  }
  async getDashboardCards(): Promise<{ todo: number; overdue: number; highRisk: number; takeover: number }> {
    try {
      return await this.real.getDashboardCards()
    } catch {
      return this.mock.getDashboardCards()
    }
  }
  async getMyQueue(limit?: number): Promise<Task[]> {
    try {
      return await this.real.getMyQueue(limit)
    } catch {
      return this.mock.getMyQueue(limit)
    }
  }
}

export function createTaskRepository(mode: 'mock' | 'real' | 'auto' = 'auto'): TaskRepository {
  if (mode === 'real') return new RealTaskRepository()
  if (mode === 'mock') return new MockTaskRepository()
  return new AutoTaskRepository()
}
