import { useEffect, useMemo, useState } from 'react'
import { Card } from '../../components/Card'
import { TaskListItem } from '../../components/task/TaskListItem'
import { PageShell } from '../../components/PageShell'
import { taskService } from '../../modules/tasks/service'
import type { Task, TaskBucket, TaskListFilters, TaskListStats } from '../../modules/tasks/types'

interface TaskBucketPageProps {
  bucket: TaskBucket
  onOpenTask: (taskId: string) => void
}

const bucketTitleMap: Record<TaskBucket, string> = {
  todo: '待办任务',
  overdue: '逾期任务',
  takeover: '待接管任务',
  my: '我的工作台队列',
}

const emptyStats: TaskListStats = { total: 0, urgent: 0, dueSoon: 0, highRisk: 0 }

export function TaskBucketPage({ bucket, onOpenTask }: TaskBucketPageProps) {
  const [tasks, setTasks] = useState<Task[]>([])
  const [stats, setStats] = useState<TaskListStats>(emptyStats)
  const [keyword, setKeyword] = useState('')
  const [riskLevel, setRiskLevel] = useState<TaskListFilters['riskLevel']>('all')
  const [overdueWindow, setOverdueWindow] = useState<TaskListFilters['overdueWindow']>('all')

  const filters = useMemo<TaskListFilters>(
    () => ({ keyword, riskLevel, overdueWindow: bucket === 'overdue' ? overdueWindow : 'all' }),
    [bucket, keyword, overdueWindow, riskLevel],
  )

  const load = async () => {
    const [list, stat] = await Promise.all([taskService.listTasks(bucket, filters), taskService.getTaskStats(bucket)])
    setTasks(list)
    setStats(stat)
  }

  useEffect(() => {
    void load()
  }, [bucket, filters])

  const title = bucketTitleMap[bucket]

  return (
    <PageShell title={title} description="按任务工作流处理，支持完成/延期/接管/标记风险的 mock 闭环。">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Card title="总任务数">{stats.total}</Card>
        <Card title="P0 紧急">{stats.urgent}</Card>
        <Card title="2小时内到期">{stats.dueSoon}</Card>
        <Card title="高风险任务">{stats.highRisk}</Card>
      </div>

      <Card title="筛选" className="mt-6">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
          <input
            className="rounded-control border border-paper-300 px-3 py-2 text-sm"
            placeholder="搜索团号/目的地/任务"
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
          />
          <select
            className="rounded-control border border-paper-300 px-3 py-2 text-sm"
            value={riskLevel}
            onChange={(event) => setRiskLevel(event.target.value as TaskListFilters['riskLevel'])}
          >
            <option value="all">全部风险</option>
            <option value="medium">中风险</option>
            <option value="high">高风险</option>
            <option value="critical">极高风险</option>
          </select>
          {bucket === 'overdue' ? (
            <select
              className="rounded-control border border-paper-300 px-3 py-2 text-sm"
              value={overdueWindow}
              onChange={(event) => setOverdueWindow(event.target.value as TaskListFilters['overdueWindow'])}
            >
              <option value="all">全部逾期时长</option>
              <option value="lt2h">小于2小时</option>
              <option value="2to24h">2-24小时</option>
              <option value="gt24h">大于24小时</option>
            </select>
          ) : null}
        </div>
      </Card>

      <Card title="任务列表" className="mt-6">
        <div className="space-y-3">
          {tasks.map((task) => (
            <TaskListItem
              key={task.id}
              task={task}
              onOpen={onOpenTask}
              onComplete={async (taskId) => {
                await taskService.completeTask(taskId)
                await load()
              }}
              onDefer={async (taskId) => {
                await taskService.deferTask(taskId)
                await load()
              }}
              onTakeover={
                bucket === 'takeover'
                  ? async (taskId) => {
                      await taskService.takeoverTask(taskId, '张三')
                      await load()
                    }
                  : undefined
              }
              onMarkRisk={async (taskId) => {
                await taskService.markTaskRisk(taskId)
                await load()
              }}
            />
          ))}
          {tasks.length === 0 ? <p className="text-sm text-paper-500">当前筛选条件下暂无任务</p> : null}
        </div>
      </Card>
    </PageShell>
  )
}
