import { groupMockDataSource } from './mock'
import type { RiskGroup, RiskGroupDetail, RiskGroupStats } from './types'
import { tripsApi } from '../../services/api'
import { adaptTaskFromExecutionTask } from '../tasks/adapters'

export interface GroupRepository {
  listHighRisk(): Promise<RiskGroup[]>
  getById(groupId: string): Promise<RiskGroupDetail | null>
  getStats(): Promise<RiskGroupStats>
}

class MockGroupRepository implements GroupRepository {
  listHighRisk(): Promise<RiskGroup[]> {
    return groupMockDataSource.listHighRisk()
  }

  getById(groupId: string): Promise<RiskGroupDetail | null> {
    return groupMockDataSource.getById(groupId)
  }

  getStats(): Promise<RiskGroupStats> {
    return groupMockDataSource.getStats()
  }
}

class RealGroupRepository implements GroupRepository {
  async listHighRisk(): Promise<RiskGroup[]> {
    const rows = await tripsApi.listExecutionRows({ ownerScope: 'all' })
    return rows
      .filter((row) => row.riskLevel === 'high' || row.riskLevel === 'critical')
      .map((row) => ({
        id: row.tripId,
        groupName: row.tripName,
        routeName: `${row.currentStage}阶段团`,
        departureDate: row.nextNodeDueAt || new Date().toISOString(),
        riskScore: row.riskLevel === 'critical' ? 90 : 80,
        riskLevel: row.riskLevel === 'critical' ? 'critical' : 'high',
        riskTags: [row.dispatchStatus || '调度中', row.currentStage],
        owner: row.ownerName || '待分配',
        pendingTaskCount: row.todoCount,
        blockedTaskCount: row.overdueMinutes > 0 ? 1 : 0,
        summary: `当前阶段：${row.currentStage}，请关注下一通知节点。`,
        tasks: [],
        collaborators: ['运营组', '客服组'],
        timeline: [],
      }))
  }

  async getById(groupId: string): Promise<RiskGroupDetail | null> {
    const [trip, detail] = await Promise.all([tripsApi.get(groupId), tripsApi.getExecutionDetail(groupId)])
    return {
      id: detail.tripId,
      groupName: detail.tripName,
      routeName: `${trip.destination} ${trip.startDate}~${trip.endDate}`,
      departureDate: trip.startDate,
      riskScore: detail.riskLevel === 'critical' ? 92 : detail.riskLevel === 'high' ? 84 : 70,
      riskLevel: detail.riskLevel === 'critical' ? 'critical' : detail.riskLevel === 'high' ? 'high' : 'medium',
      riskTags: [detail.currentStage, detail.riskLevel],
      owner: '运营值守',
      pendingTaskCount: Math.max(detail.todayTotal - detail.todayDone, 0),
      blockedTaskCount: 0,
      summary: `下一触达节点：${detail.nextDispatchAt || '待生成'}。`,
      tasks: detail.tasks.map((task) => task.taskId),
      collaborators: ['值班管家', '地接协调'],
      timeline: [
        { id: `tl-${groupId}-1`, title: '进入执行监控', at: detail.nextDispatchAt || new Date().toISOString(), level: 'high' },
      ],
      taskItems: detail.tasks.map((task) =>
        adaptTaskFromExecutionTask(task, {
          tripId: detail.tripId,
          tripName: detail.tripName,
        }),
      ),
    }
  }

  async getStats(): Promise<RiskGroupStats> {
    const groups = await this.listHighRisk()
    const departingSoon = groups.filter((group) => {
      const diff = new Date(group.departureDate).getTime() - Date.now()
      return diff > 0 && diff <= 48 * 60 * 60 * 1000
    }).length
    return {
      total: groups.length,
      critical: groups.filter((group) => group.riskLevel === 'critical').length,
      departingSoon,
      pendingTasks: groups.reduce((sum, item) => sum + item.pendingTaskCount, 0),
    }
  }
}

class AutoGroupRepository implements GroupRepository {
  private readonly mock = new MockGroupRepository()
  private readonly real = new RealGroupRepository()

  async listHighRisk(): Promise<RiskGroup[]> {
    try {
      return await this.real.listHighRisk()
    } catch {
      return this.mock.listHighRisk()
    }
  }
  async getById(groupId: string): Promise<RiskGroupDetail | null> {
    try {
      return await this.real.getById(groupId)
    } catch {
      return this.mock.getById(groupId)
    }
  }
  async getStats(): Promise<RiskGroupStats> {
    try {
      return await this.real.getStats()
    } catch {
      return this.mock.getStats()
    }
  }
}

export function createGroupRepository(mode: 'mock' | 'real' | 'auto' = 'auto'): GroupRepository {
  if (mode === 'real') return new RealGroupRepository()
  if (mode === 'mock') return new MockGroupRepository()
  return new AutoGroupRepository()
}
