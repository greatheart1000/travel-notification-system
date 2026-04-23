import type React from 'react'
import type { Task } from '../../modules/tasks/types'
import { StatusPill } from '../common/StatusPill'

interface TaskListItemProps {
  task: Task
  onOpen: (taskId: string) => void
  actionSlot?: React.ReactNode
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

export function TaskListItem({ task, onOpen, actionSlot }: TaskListItemProps) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <button className="text-left" onClick={() => onOpen(task.id)}>
          <p className="text-base font-semibold text-slate-900">{task.title}</p>
          <p className="mt-1 text-sm text-slate-500">
            {task.groupName} · {task.destination} · 截止 {new Date(task.dueAt).toLocaleString()}
          </p>
        </button>
        <StatusPill tone={statusTone(task.status)} label={statusTextMap[task.status]} />
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        {task.tags.map((tag) => (
          <span key={tag} className="rounded-md bg-slate-100 px-2 py-1 text-xs text-slate-600">
            {tag}
          </span>
        ))}
        <span className="rounded-md bg-indigo-50 px-2 py-1 text-xs text-indigo-600">优先级 {task.priority}</span>
      </div>
      {actionSlot ? <div className="mt-3 flex items-center justify-end">{actionSlot}</div> : null}
    </div>
  )
}
