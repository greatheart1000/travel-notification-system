import { useEffect, useState } from 'react'
import { Card } from '../../components/Card'
import { PageShell } from '../../components/PageShell'
import { TaskListItem } from '../../components/task/TaskListItem'
import { taskService } from '../../modules/tasks/service'
import type { Task } from '../../modules/tasks/types'

interface WorkflowDashboardPageProps {
  onNavigate: (path: string) => void
}

interface DashboardCards {
  todo: number
  overdue: number
  highRisk: number
  takeover: number
}

const emptyCards: DashboardCards = { todo: 0, overdue: 0, highRisk: 0, takeover: 0 }

export function WorkflowDashboardPage({ onNavigate }: WorkflowDashboardPageProps) {
  const [cards, setCards] = useState<DashboardCards>(emptyCards)
  const [queue, setQueue] = useState<Task[]>([])

  const loadData = async () => {
    const [cardData, myQueue] = await Promise.all([taskService.getDashboardCards(), taskService.getMyQueue(8)])
    setCards(cardData)
    setQueue(myQueue)
  }

  useEffect(() => {
    void loadData()
  }, [])

  return (
    <PageShell title="Travel Hub 首页工作台" description="今日工作队列：让你明确先处理什么、为什么处理、如何闭环。">
      <Card title="今日工作台速览">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
          <button className="rounded-xl bg-slate-50 p-4 text-left" onClick={() => onNavigate('/tasks/todo')}>
            <p className="text-sm text-slate-500">待办任务</p>
            <p className="mt-2 text-3xl font-black text-slate-900">{cards.todo}</p>
          </button>
          <button className="rounded-xl bg-amber-50 p-4 text-left" onClick={() => onNavigate('/tasks/overdue')}>
            <p className="text-sm text-amber-700">逾期任务</p>
            <p className="mt-2 text-3xl font-black text-amber-700">{cards.overdue}</p>
          </button>
          <button className="rounded-xl bg-rose-50 p-4 text-left" onClick={() => onNavigate('/groups/high-risk')}>
            <p className="text-sm text-rose-700">高风险团</p>
            <p className="mt-2 text-3xl font-black text-rose-700">{cards.highRisk}</p>
          </button>
          <button className="rounded-xl bg-violet-50 p-4 text-left" onClick={() => onNavigate('/tasks/takeover')}>
            <p className="text-sm text-violet-700">待接管</p>
            <p className="mt-2 text-3xl font-black text-violet-700">{cards.takeover}</p>
          </button>
        </div>
      </Card>

      <Card title="待我处理（今日工作队列）" className="mt-6">
        <div className="mb-3 flex justify-end">
          <button className="text-sm text-blue-600" onClick={() => onNavigate('/tasks/my-workbench')}>
            查看全部
          </button>
        </div>
        <div className="space-y-3">
          {queue.map((task) => (
            <TaskListItem
              key={task.id}
              task={task}
              onOpen={(taskId) => onNavigate(`/tasks/${taskId}`)}
              onComplete={async (taskId) => {
                await taskService.completeTask(taskId)
                await loadData()
              }}
              onDefer={async (taskId) => {
                await taskService.deferTask(taskId)
                await loadData()
              }}
              onTakeover={
                task.status === 'pending_takeover' || !task.assigneeId
                  ? async (taskId) => {
                      await taskService.takeoverTask(taskId, '张三')
                      await loadData()
                    }
                  : undefined
              }
              onMarkRisk={async (taskId) => {
                await taskService.markTaskRisk(taskId)
                await loadData()
              }}
            />
          ))}
          {queue.length === 0 ? <p className="text-sm text-slate-500">当前没有需要今天优先处理的任务</p> : null}
        </div>
      </Card>

      <Card title="AI 智能提醒" className="mt-6 border-sky-100 bg-gradient-to-r from-sky-500 to-blue-500 text-white">
        <p className="text-sm text-sky-50">根据天气、航变、投诉热度自动生成的运营建议（当前为静态示意模块）。</p>
      </Card>
    </PageShell>
  )
}
