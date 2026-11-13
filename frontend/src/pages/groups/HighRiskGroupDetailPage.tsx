import { useEffect, useState } from 'react'
import { Button } from '../../components/Button'
import { Card } from '../../components/Card'
import { PageShell } from '../../components/PageShell'
import { groupService } from '../../modules/groups/service'
import type { RiskGroupDetail } from '../../modules/groups/types'

interface HighRiskGroupDetailPageProps {
  groupId: string
  onOpenTask: (taskId: string) => void
}

export function HighRiskGroupDetailPage({ groupId, onOpenTask }: HighRiskGroupDetailPageProps) {
  const [group, setGroup] = useState<RiskGroupDetail | null>(null)

  useEffect(() => {
    const load = async () => {
      const detail = await groupService.getGroupDetail(groupId)
      setGroup(detail)
    }
    void load()
  }, [groupId])

  if (!group) {
    return (
      <PageShell title="高风险团详情">
        <p className="text-sm text-paper-500">未找到对应团信息</p>
      </PageShell>
    )
  }

  return (
    <PageShell title={group.groupName} description="高风险团详情（Mock联调预留版）。">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card title="团基础信息">
            <div className="grid grid-cols-2 gap-3 text-sm text-paper-700">
              <p>线路：{group.routeName}</p>
              <p>出发：{new Date(group.departureDate).toLocaleString()}</p>
              <p>风险分：{group.riskScore}</p>
              <p>风险等级：{group.riskLevel}</p>
              <p>负责人：{group.owner}</p>
              <p>协作人：{group.collaborators.join('、')}</p>
            </div>
          </Card>

          <Card title="风险摘要">
            <p className="text-sm text-paper-700">{group.summary}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {group.riskTags.map((tag) => (
                <span key={tag} className="rounded-md bg-danger-50 px-2 py-1 text-xs text-danger-700">
                  {tag}
                </span>
              ))}
            </div>
          </Card>

          <Card title="风险事件时间线">
            <div className="space-y-2">
              {group.timeline.map((event) => (
                <div key={event.id} className="rounded-control border border-paper-100 p-3 text-sm">
                  <p className="font-semibold text-paper-900">{event.title}</p>
                  <p className="text-paper-600">
                    {event.level.toUpperCase()} · {new Date(event.at).toLocaleString()}
                  </p>
                </div>
              ))}
            </div>
          </Card>

          <Card title="团下任务列表">
            <div className="space-y-2">
              {group.taskItems.map((task) => (
                <button
                  key={task.id}
                  className="w-full rounded-control border border-paper-100 p-3 text-left"
                  onClick={() => onOpenTask(task.id)}
                >
                  <p className="font-semibold text-paper-900">{task.title}</p>
                  <p className="text-sm text-paper-500">{task.status} · 截止 {new Date(task.dueAt).toLocaleString()}</p>
                </button>
              ))}
            </div>
          </Card>
        </div>

        <div className="space-y-6">
          <Card title="建议动作区">
            <div className="space-y-2">
              <Button className="w-full">启动预案</Button>
              <Button className="w-full">创建任务包</Button>
              <Button className="w-full">发送团级通知</Button>
            </div>
          </Card>
        </div>
      </div>
    </PageShell>
  )
}
