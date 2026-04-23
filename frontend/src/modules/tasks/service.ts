import { createTaskRepository, type TaskRepository } from './repository'
import type { Task, TaskBucket, TaskListFilters, TaskListStats, TaskStatus } from './types'

export class TaskService {
  constructor(private readonly repository: TaskRepository) {}

  listTasks(bucket: TaskBucket, filters?: TaskListFilters): Promise<Task[]> {
    return this.repository.list(bucket, filters)
  }

  getTaskDetail(taskId: string): Promise<Task | null> {
    return this.repository.getById(taskId)
  }

  getTaskStats(bucket: TaskBucket): Promise<TaskListStats> {
    return this.repository.getStats(bucket)
  }

  getDashboardCards(): Promise<{ todo: number; overdue: number; highRisk: number; takeover: number }> {
    return this.repository.getDashboardCards()
  }

  getMyQueue(limit?: number): Promise<Task[]> {
    return this.repository.getMyQueue(limit)
  }

  takeoverTask(taskId: string, operator?: string): Promise<Task | null> {
    return this.repository.takeover(taskId, operator)
  }

  updateTaskStatus(taskId: string, status: TaskStatus): Promise<Task | null> {
    return this.repository.updateStatus(taskId, status)
  }
}

const repositoryMode = (import.meta.env.VITE_WORKBENCH_DATA_MODE as 'mock' | 'real' | 'auto' | undefined) ?? 'auto'

export const taskService = new TaskService(createTaskRepository(repositoryMode))
