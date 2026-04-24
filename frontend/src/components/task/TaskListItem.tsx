import { Button } from '../Button'
import { StatusPill } from '../common/StatusPill'
import type { Task } from '../../modules/tasks/types'

interface TaskListItemProps {
  task: Task
  onOpen: (taskId: string) => void
  onComplete?: (taskId: string) => Promise<void>
  onDefer?: (taskId: string) => Promise<void>
  onTakeover?: (taskId: string) => Promise<void>
  onMarkRisk?: (taskId: string) => Promise<void>
}

function statusTone(status: Task['status']): 'neutral' | 'warning' | 'danger' | 'success' | 'info' {
  if (status === 'overdue') return 'danger'
  if (status === 'pending_takeover') return 'warning'
  if (status === 'done') return 'success'
  if (status === 'in_progress') return 'info'
  return 'neutral'
}

const statusTextMap: Record<Task['status'], string> = {
  todo: '待办',
  in_progress: '处理中',
  done: '已完成',
  overdue: '已逾期',
  pending_takeover: '待接管',
  blocked: '阻塞',
}

function formatRelativeDue(task: Task): string {
  const diffMs = new Date(task.dueAt).getTime() - Date.now()
  const absHours = Math.max(1, Math.floor(Math.abs(diffMs) / (1000 * 60 * 60)))
  return diffMs < 0 ? `已逾期 ${absHours} 小时` : `剩余 ${absHours} 小时`
}

function queueReasons(task: Task): string {
  const reasons: string[] = []
  if (task.status === 'overdue') reasons.push('逾期')
  if (task.riskLevel === 'high' || task.riskLevel === 'critical') reasons.push('高风险')
  if (task.status === 'pending_takeover' || !task.assigneeId) reasons.push('待接管')
  if (new Date(task.dueAt).getTime() - Date.now() <= 24 * 60 * 60 * 1000) reasons.push('24小时内到期')
  return reasons.join(' / ') || '今日队列'
}

export function TaskListItem({ task, onOpen, onComplete, onDefer, onTakeover, onMarkRisk }: TaskListItemProps) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <button className="text-left" onClick={() => onOpen(task.id)}>
          <p className="text-base font-semibold text-slate-900">{task.title}</p>
          <p className="mt-1 text-sm text-slate-500">
            {task.teamName}（{task.teamCode}）· {task.destination}
          </p>
        </button>
        <StatusPill tone={statusTone(task.status)} label={statusTextMap[task.status]} />
      </div>

      <div className="mt-3 grid grid-cols-1 gap-2 text-xs text-slate-600 md:grid-cols-2">
        <p>出发日期：{new Date(task.departureDate).toLocaleString()}</p>
        <p>截止时间：{new Date(task.dueAt).toLocaleString()}</p>
        <p>{formatRelativeDue(task)}</p>
        <p>风险等级：{task.riskLevel.toUpperCase()} · 类型：{task.type}</p>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <span className="rounded-md bg-slate-100 px-2 py-1 text-xs text-slate-600">推荐动作：{task.recommendedAction}</span>
        <span className="rounded-md bg-amber-50 px-2 py-1 text-xs text-amber-700">进入原因：{queueReasons(task)}</span>
      </div>

      <div className="mt-3 flex flex-wrap items-center justify-end gap-2">
        <Button onClick={() => onOpen(task.id)}>处理</Button>
        {onComplete ? (
          <Button variant="secondary" onClick={() => void onComplete(task.id)}>
            完成
          </Button>
        ) : null}
        {onDefer ? (
          <Button variant="secondary" onClick={() => void onDefer(task.id)}>
            延期
          </Button>
        ) : null}
        {onTakeover ? (
          <Button variant="secondary" onClick={() => void onTakeover(task.id)}>
            接管
          </Button>
        ) : null}
        {onMarkRisk ? (
          <Button variant="ghost" onClick={() => void onMarkRisk(task.id)}>
            标记风险
          </Button>
        ) : null}
      </div>
    </div>
  )
}
