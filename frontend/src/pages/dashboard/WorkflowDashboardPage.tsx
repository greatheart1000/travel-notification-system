import { useEffect, useState } from 'react'
import { Card } from '../../components/Card'
import { PageShell } from '../../components/PageShell'
import { StatusPill } from '../../components/common/StatusPill'
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
    const [cardData, myQueue] = await Promise.all([taskService.getDashboardCards(), taskService.getMyQueue(5)])
    setCards(cardData)
    setQueue(myQueue)
  }

  useEffect(() => {
    void loadData()
  }, [])

  return (
    <PageShell title="Travel Hub 首页工作台" description="按工作流处理任务：待办、逾期、高风险团、待接管。">
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

      <Card title="待我处理" className="mt-6">
        <div className="space-y-3">
          {queue.map((task) => (
            <button
              key={task.id}
              className="flex w-full items-center justify-between rounded-xl border border-slate-200 p-3 text-left"
              onClick={() => onNavigate(`/tasks/${task.id}`)}
            >
              <div>
                <p className="font-semibold text-slate-900">{task.title}</p>
                <p className="text-sm text-slate-500">
                  {task.groupName} · 截止 {new Date(task.dueAt).toLocaleString()}
                </p>
              </div>
              <StatusPill tone={task.status === 'overdue' ? 'danger' : 'info'} label={task.status} />
            </button>
          ))}
        </div>
      </Card>

      <Card title="AI 智能提醒" className="mt-6 border-sky-100 bg-gradient-to-r from-sky-500 to-blue-500 text-white">
        <p className="text-sm text-sky-50">根据天气、航变、投诉热度自动生成的运营建议（当前为静态示意模块）。</p>
      </Card>
    </PageShell>
  )
}
