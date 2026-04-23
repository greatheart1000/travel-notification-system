import { useEffect, useState } from 'react'
import { Button } from '../../components/Button'
import { Card } from '../../components/Card'
import { PageShell } from '../../components/PageShell'
import { taskService } from '../../modules/tasks/service'
import type { Task, TaskStatus } from '../../modules/tasks/types'

interface TaskDetailPageProps {
  taskId: string
  onOpenGroup: (groupId: string) => void
}

const actionStatusMap: Array<{ label: string; status: TaskStatus }> = [
  { label: '标记完成', status: 'done' },
  { label: '延期处理', status: 'in_progress' },
  { label: '转派接管', status: 'pending_takeover' },
  { label: '标记风险', status: 'blocked' },
]

export function TaskDetailPage({ taskId, onOpenGroup }: TaskDetailPageProps) {
  const [task, setTask] = useState<Task | null>(null)

  const load = async () => {
    const detail = await taskService.getTaskDetail(taskId)
    setTask(detail)
  }

  useEffect(() => {
    void load()
  }, [taskId])

  if (!task) {
    return (
      <PageShell title="任务详情">
        <p className="text-sm text-slate-500">任务不存在或已删除</p>
      </PageShell>
    )
  }

  return (
    <PageShell title={task.title} description="任务详情（Mock版，可平滑切换真实 API）。">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card title="基本信息">
            <div className="grid grid-cols-2 gap-3 text-sm text-slate-700">
              <p>任务类型：{task.type}</p>
              <p>状态：{task.status}</p>
              <p>优先级：{task.priority}</p>
              <p>风险等级：{task.riskLevel}</p>
              <p>截止时间：{new Date(task.dueAt).toLocaleString()}</p>
              <p>出发日期：{new Date(task.departureDate).toLocaleString()}</p>
            </div>
          </Card>

          <Card title="行程上下文">
            <p className="text-sm text-slate-700">关联团：{task.groupName}</p>
            <p className="mt-2 text-sm text-slate-700">目的地：{task.destination}</p>
            <Button className="mt-3" onClick={() => onOpenGroup(task.groupId)}>
              查看高风险团详情
            </Button>
          </Card>

          <Card title="客户信息">
            <p className="text-sm text-slate-700">客户姓名：{task.customerName}</p>
            <p className="mt-2 text-sm text-slate-700">当前负责人：{task.assignee || '待分配'}</p>
          </Card>

          <Card title="处理记录">
            <div className="space-y-2">
              {task.history.map((item) => (
                <div key={item.id} className="rounded-lg border border-slate-100 p-3 text-sm">
                  <p className="font-semibold text-slate-900">{item.action}</p>
                  <p className="text-slate-600">
                    {item.operator} · {new Date(item.at).toLocaleString()}
                  </p>
                  <p className="text-slate-500">{item.note}</p>
                </div>
              ))}
              {task.history.length === 0 ? <p className="text-sm text-slate-500">暂无处理记录</p> : null}
            </div>
          </Card>
        </div>

        <div className="space-y-6">
          <Card title="AI 建议区">
            <p className="text-sm text-slate-700">{task.aiSuggestion}</p>
          </Card>
          <Card title="操作区">
            <div className="space-y-2">
              {actionStatusMap.map((item) => (
                <Button
                  key={item.label}
                  className="w-full"
                  onClick={async () => {
                    await taskService.updateTaskStatus(task.id, item.status)
                    await load()
                  }}
                >
                  {item.label}
                </Button>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </PageShell>
  )
}
