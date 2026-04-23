import { createGroupRepository, type GroupRepository } from './repository'
import type { RiskGroup, RiskGroupDetail, RiskGroupStats } from './types'

export class GroupService {
  constructor(private readonly repository: GroupRepository) {}

  listHighRiskGroups(): Promise<RiskGroup[]> {
    return this.repository.listHighRisk()
  }

  getGroupDetail(groupId: string): Promise<RiskGroupDetail | null> {
    return this.repository.getById(groupId)
  }

  getGroupStats(): Promise<RiskGroupStats> {
    return this.repository.getStats()
  }
}

const repositoryMode = (import.meta.env.VITE_WORKBENCH_DATA_MODE as 'mock' | 'real' | 'auto' | undefined) ?? 'auto'

export const groupService = new GroupService(createGroupRepository(repositoryMode))
