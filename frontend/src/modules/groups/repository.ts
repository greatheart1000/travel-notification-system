import { groupMockDataSource } from './mock'
import type { RiskGroup, RiskGroupDetail, RiskGroupStats } from './types'

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
    throw new Error('RealGroupRepository not implemented yet')
  }

  async getById(): Promise<RiskGroupDetail | null> {
    throw new Error('RealGroupRepository not implemented yet')
  }

  async getStats(): Promise<RiskGroupStats> {
    throw new Error('RealGroupRepository not implemented yet')
  }
}

export function createGroupRepository(mode: 'mock' | 'real' = 'mock'): GroupRepository {
  return mode === 'real' ? new RealGroupRepository() : new MockGroupRepository()
}
