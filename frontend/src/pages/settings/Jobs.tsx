import { useCallback, useEffect, useState } from 'react'
import { RefreshCw } from 'lucide-react'
import { PageShell } from '../../components/PageShell'
import { Button } from '../../components/Button'
import { Badge } from '../../components/Badge'
import { getErrorMessage } from '../../services/api'
import { jobsApi, type NotificationJob } from '../../services/commercialApi'

const STATUS_OPTIONS = [
  { value: '', label: '全部状态' },
  { value: 'pending', label: '待发送' },
  { value: 'retrying', label: '重试中' },
  { value: 'sent', label: '已发送' },
  { value: 'failed', label: '失败' },
  { value: 'manual_intervention', label: '待人工处理' },
]

const STATUS_META: Record<string, { label: string; variant: 'success' | 'warning' | 'danger' | 'info' | 'default' }> = {
  pending: { label: '待发送', variant: 'info' },
  processing: { label: '处理中', variant: 'info' },
  retrying: { label: '重试中', variant: 'warning' },
  sent: { label: '已发送', variant: 'success' },
  failed: { label: '失败', variant: 'danger' },
  manual_intervention: { label: '待人工处理', variant: 'danger' },
}

function formatDate(raw: string): string {
  if (!raw) return '-'
  const date = new Date(raw)
  return Number.isNaN(date.getTime()) ? raw : date.toLocaleString('zh-CN', { hour12: false })
}

export function Jobs() {
  const [status, setStatus] = useState('')
  const [jobs, setJobs] = useState<NotificationJob[]>([])
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [requeueing, setRequeueing] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const result = await jobsApi.list(status || undefined)
      setJobs(result.items)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [status])

  useEffect(() => {
    void load()
  }, [load])

  const requeue = async (job: NotificationJob) => {
    setRequeueing(job.job_id)
    setError(null)
    try {
      await jobsApi.requeue(job.job_id)
      setNotice(`任务 ${job.job_id} 已重新入队`)
      await load()
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setRequeueing('')
    }
  }

  return (
    <PageShell
      eyebrow="OPERATIONS"
      title="发送任务"
      description="查看异步发送队列与死信任务。失败任务可重新入队，重放会重置尝试次数并写审计日志。"
      actions={
        <select
          value={status}
          onChange={(event) => setStatus(event.target.value)}
          className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:border-sky-500 focus:outline-none"
        >
          {STATUS_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      }
    >
      {error ? (
        <div role="alert" className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}
      {notice ? (
        <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
          {notice}
        </div>
      ) : null}

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3">任务 ID</th>
              <th className="px-4 py-3">行程 / 团队</th>
              <th className="px-4 py-3">渠道</th>
              <th className="px-4 py-3">状态</th>
              <th className="px-4 py-3">尝试次数</th>
              <th className="px-4 py-3">下次执行</th>
              <th className="px-4 py-3">错误摘要</th>
              <th className="px-4 py-3 text-right">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading ? (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-slate-500">
                  正在加载发送任务...
                </td>
              </tr>
            ) : jobs.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-4 py-10 text-center text-slate-500">
                  当前没有符合条件的发送任务。
                </td>
              </tr>
            ) : (
              jobs.map((job) => {
                const meta = STATUS_META[job.status] ?? { label: job.status, variant: 'default' as const }
                const canRequeue = ['failed', 'manual_intervention', 'retrying'].includes(job.status)
                return (
                  <tr key={job.job_id}>
                    <td className="px-4 py-3 font-mono text-xs text-slate-600">{job.job_id}</td>
                    <td className="px-4 py-3 text-slate-700">
                      {job.trip_id || '-'}
                      <span className="block text-xs text-slate-400">{job.team_id || ''}</span>
                    </td>
                    <td className="px-4 py-3 text-slate-600">{job.channel}</td>
                    <td className="px-4 py-3">
                      <Badge variant={meta.variant}>{meta.label}</Badge>
                    </td>
                    <td className="px-4 py-3 text-slate-600">{job.attempt}</td>
                    <td className="px-4 py-3 text-slate-500">{formatDate(job.next_run_at)}</td>
                    <td className="max-w-[16rem] truncate px-4 py-3 text-xs text-slate-500" title={job.last_error}>
                      {job.last_error || '-'}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {canRequeue ? (
                        <Button
                          size="sm"
                          variant="secondary"
                          loading={requeueing === job.job_id}
                          onClick={() => void requeue(job)}
                        >
                          <span className="flex items-center gap-1">
                            <RefreshCw className="h-3.5 w-3.5" /> 重新入队
                          </span>
                        </Button>
                      ) : (
                        <span className="text-xs text-slate-400">-</span>
                      )}
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
    </PageShell>
  )
}
