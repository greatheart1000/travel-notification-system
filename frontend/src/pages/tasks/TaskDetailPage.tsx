import { useEffect, useMemo, useState } from 'react'
import { Button } from '../../components/Button'
import { Card } from '../../components/Card'
import { PageShell } from '../../components/PageShell'
import { taskService } from '../../modules/tasks/service'
import type { Task } from '../../modules/tasks/types'

interface TaskDetailPageProps {
  taskId: string
  onOpenGroup: (groupId: string) => void
  onNavigate: (path: string) => void
}

function dueText(task: Task): string {
  const diffHours = Math.floor((Date.now() - new Date(task.dueAt).getTime()) / (1000 * 60 * 60))
  if (diffHours > 0) return `已逾期 ${diffHours} 小时`
  return `剩余 ${Math.abs(diffHours)} 小时`
}

function mainAction(task: Task, onNavigate: (path: string) => void): { label: string; onClick: () => Promise<void> } {
  if (task.type === 'daily_morning' || task.type === 'daily_noon' || task.type === 'daily_evening') {
    return {
      label: '进入团详情',
      onClick: async () => {
        onNavigate(`/trips/${task.teamId}`)
      },
    }
  }
  if (task.type === 'pre_trip_t3_flight_check') {
    return {
      label: '查看团详情',
      onClick: async () => {
        onNavigate(`/trips/${task.teamId}`)
      },
    }
  }
  if (task.type === 'post_trip_farewell') {
    return {
      label: '填写回访结果',
      onClick: async () => {
        window.alert('已打开回访结果表单（Mock）')
      },
    }
  }
  if (task.status === 'pending_takeover') {
    return {
      label: '接管任务',
      onClick: async () => {
        await taskService.takeoverTask(task.id, '张三')
      },
    }
  }
  return {
    label: '处理任务',
    onClick: async () => {
      await taskService.updateTaskStatus(task.id, 'in_progress')
    },
  }
}

export function TaskDetailPage({ taskId, onOpenGroup, onNavigate }: TaskDetailPageProps) {
  const [task, setTask] = useState<Task | null>(null)

  const load = async () => {
    const detail = await taskService.getTaskDetail(taskId)
    setTask(detail)
  }

  useEffect(() => {
    void load()
  }, [taskId])

  const action = useMemo(() => (task ? mainAction(task, onNavigate) : null), [onNavigate, task])

  if (!task) {
    return (
      <PageShell title="任务详情">
        <p className="text-sm text-paper-500">任务不存在或已删除</p>
      </PageShell>
    )
  }

  return (
    <PageShell title={task.title} description="任务详情（工作队列上下文版）。">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card title="任务与团队上下文">
            <div className="grid grid-cols-2 gap-3 text-sm text-paper-700">
              <p>团名：{task.teamName}</p>
              <p>团号：{task.teamCode}</p>
              <p>目的地：{task.destination}</p>
              <p>出发日期：{new Date(task.departureDate).toLocaleString()}</p>
              <p>当前行程天数：第 {task.currentTripDay} 天</p>
              <p>关联游客数量：{task.travelerCount}</p>
              <p>关联通知节点：{task.linkedNotificationNode}</p>
              <p>任务来源：{task.source}</p>
              <p>截止时间：{new Date(task.dueAt).toLocaleString()}</p>
              <p>逾期状态：{dueText(task)}</p>
              <p>当前负责人：{task.assigneeName || '待分配'}</p>
              <p>推荐动作：{task.recommendedAction}</p>
            </div>
            <Button className="mt-3" onClick={() => onOpenGroup(task.teamId)}>
              查看高风险团详情
            </Button>
          </Card>

          {task.status === 'overdue' ? (
            <Card title="逾期原因与补救建议">
              <p className="text-sm text-paper-700">逾期原因：{task.overdueReason || '待补充逾期说明'}</p>
              <p className="mt-2 text-sm text-paper-700">补救建议：{task.remedySuggestion || '建议立即补触达并同步负责人。'}</p>
            </Card>
          ) : null}

          <Card title="处理记录">
            <div className="space-y-2">
              {task.history.map((item) => (
                <div key={item.id} className="rounded-control border border-paper-100 p-3 text-sm">
                  <p className="font-semibold text-paper-900">{item.action}</p>
                  <p className="text-paper-600">
                    {item.operator} · {new Date(item.at).toLocaleString()}
                  </p>
                  <p className="text-paper-500">{item.note}</p>
                </div>
              ))}
              {task.history.length === 0 ? <p className="text-sm text-paper-500">暂无处理记录</p> : null}
            </div>
          </Card>
        </div>

        <div className="space-y-6">
          <Card title="处理建议">
            <p className="text-sm text-paper-700">{task.aiSuggestion}</p>
          </Card>
          <Card title="操作区">
            <div className="space-y-2">
              {action ? (
                <Button
                  className="w-full"
                  onClick={async () => {
                    await action.onClick()
                    await load()
                  }}
                >
                  {action.label}
                </Button>
              ) : null}
              {task.type === 'pre_trip_t3_flight_check' ? (
                <Button
                  variant="secondary"
                  className="w-full"
                  onClick={async () => {
                    await taskService.completeTask(task.id)
                    await load()
                  }}
                >
                  标记航班已确认
                </Button>
              ) : null}
              <Button
                variant="secondary"
                className="w-full"
                onClick={async () => {
                  await taskService.deferTask(task.id)
                  await load()
                }}
              >
                延期处理
              </Button>
              <Button
                variant="secondary"
                className="w-full"
                onClick={async () => {
                  await taskService.completeTask(task.id)
                  onNavigate('/tasks/my-workbench')
                }}
              >
                标记完成
              </Button>
              <Button
                variant="ghost"
                className="w-full"
                onClick={async () => {
                  await taskService.takeoverTask(task.id, '张三')
                  await load()
                }}
              >
                转派接管
              </Button>
            </div>
          </Card>
        </div>
      </div>
    </PageShell>
  )
}
