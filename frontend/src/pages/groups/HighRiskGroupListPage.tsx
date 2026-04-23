import { useEffect, useState } from 'react'
import { Card } from '../../components/Card'
import { RiskGroupCard } from '../../components/group/RiskGroupCard'
import { PageShell } from '../../components/PageShell'
import { groupService } from '../../modules/groups/service'
import type { RiskGroup, RiskGroupStats } from '../../modules/groups/types'

interface HighRiskGroupListPageProps {
  onOpenGroup: (groupId: string) => void
}

const emptyStats: RiskGroupStats = { total: 0, critical: 0, departingSoon: 0, pendingTasks: 0 }

export function HighRiskGroupListPage({ onOpenGroup }: HighRiskGroupListPageProps) {
  const [groups, setGroups] = useState<RiskGroup[]>([])
  const [stats, setStats] = useState<RiskGroupStats>(emptyStats)

  useEffect(() => {
    const load = async () => {
      const [items, stat] = await Promise.all([groupService.listHighRiskGroups(), groupService.getGroupStats()])
      setGroups(items)
      setStats(stat)
    }
    void load()
  }, [])

  return (
    <PageShell title="高风险团" description="团视角呈现风险，不降级成普通任务表。">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Card title="高风险团总数">{stats.total}</Card>
        <Card title="极高风险团">{stats.critical}</Card>
        <Card title="48h内出发">{stats.departingSoon}</Card>
        <Card title="待处理任务">{stats.pendingTasks}</Card>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
        {groups.map((group) => (
          <RiskGroupCard key={group.id} group={group} onOpen={onOpenGroup} />
        ))}
      </div>
    </PageShell>
  )
}
