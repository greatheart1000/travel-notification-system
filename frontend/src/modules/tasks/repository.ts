import type { Task, TaskBucket, TaskListFilters, TaskListStats, TaskStatus } from './types'
import { taskMockDataSource } from './mock'

export interface TaskRepository {
  list(bucket: TaskBucket, filters?: TaskListFilters): Promise<Task[]>
  getById(taskId: string): Promise<Task | null>
  getStats(bucket: TaskBucket): Promise<TaskListStats>
  takeover(taskId: string, operator?: string): Promise<Task | null>
  updateStatus(taskId: string, status: TaskStatus): Promise<Task | null>
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

  getDashboardCards(): Promise<{ todo: number; overdue: number; highRisk: number; takeover: number }> {
    return taskMockDataSource.getDashboardCards()
  }

  getMyQueue(limit?: number): Promise<Task[]> {
    return taskMockDataSource.getMyQueue(limit)
  }
}

export class RealTaskRepository implements TaskRepository {
  async list(): Promise<Task[]> {
    throw new Error('RealTaskRepository not implemented yet')
  }
  async getById(): Promise<Task | null> {
    throw new Error('RealTaskRepository not implemented yet')
  }
  async getStats(): Promise<TaskListStats> {
    throw new Error('RealTaskRepository not implemented yet')
  }
  async takeover(): Promise<Task | null> {
    throw new Error('RealTaskRepository not implemented yet')
  }
  async updateStatus(): Promise<Task | null> {
    throw new Error('RealTaskRepository not implemented yet')
  }
  async getDashboardCards(): Promise<{ todo: number; overdue: number; highRisk: number; takeover: number }> {
    throw new Error('RealTaskRepository not implemented yet')
  }
  async getMyQueue(): Promise<Task[]> {
    throw new Error('RealTaskRepository not implemented yet')
  }
}

export function createTaskRepository(mode: 'mock' | 'real' = 'mock'): TaskRepository {
  return mode === 'real' ? new RealTaskRepository() : new MockTaskRepository()
}
