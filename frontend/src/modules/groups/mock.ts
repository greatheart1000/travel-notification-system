import { getDb } from '../workbench/mockDb'
import type { RiskGroup, RiskGroupDetail, RiskGroupStats } from './types'

export const groupMockDataSource = {
  async listHighRisk(): Promise<RiskGroup[]> {
    return getDb().groups.filter((group) => ['high', 'critical'].includes(group.riskLevel))
  },

  async getById(groupId: string): Promise<RiskGroupDetail | null> {
    const group = getDb().groups.find((item) => item.id === groupId)
    if (!group) return null
    const taskItems = getDb().tasks.filter((task) => group.tasks.includes(task.id))
    return {
      ...group,
      taskItems,
    }
  },

  async getStats(): Promise<RiskGroupStats> {
    const groups = getDb().groups.filter((group) => ['high', 'critical'].includes(group.riskLevel))
    const departingSoon = groups.filter((group) => {
      const diff = new Date(group.departureDate).getTime() - Date.now()
      return diff > 0 && diff <= 48 * 60 * 60 * 1000
    }).length
    return {
      total: groups.length,
      critical: groups.filter((group) => group.riskLevel === 'critical').length,
      departingSoon,
      pendingTasks: groups.reduce((sum, group) => sum + group.pendingTaskCount, 0),
    }
  },
}
