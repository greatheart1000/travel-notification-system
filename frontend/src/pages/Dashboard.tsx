import { useEffect, useState } from 'react'
import { Badge } from '../components/Badge'
import { Button } from '../components/Button'
import { Card } from '../components/Card'
import { MetricTile } from '../components/MetricTile'
import { Modal } from '../components/Modal'
import { PageShell } from '../components/PageShell'
import { PageState } from '../components/PageState'
import { Activity, Bell, CheckCircle2, Globe2, Sparkles, Users } from 'lucide-react'
import { dashboardApi, getErrorMessage, notificationsApi, type SmartSuggestion } from '../services/api'
import { type DashboardStats, type RecentNotification } from '../types/api'

type LoadState = 'loading' | 'ready' | 'error' | 'empty'

const DEFAULT_STATS: DashboardStats = {
  todayNotifications: 0,
  activeTrips: 0,
  totalTravelers: 0,
  totalUsers: 0,
  pendingNotifications: 0,
  pendingComplaints: 0,
  notificationSuccessRate: 0,
  avgResponseTimeMs: 0,
  channelGrowthRate: 0,
}

function isStatsEmpty(stats: DashboardStats): boolean {
  return (
    stats.todayNotifications === 0 &&
    stats.activeTrips === 0 &&
    stats.totalTravelers === 0 &&
    stats.totalUsers === 0 &&
    stats.pendingNotifications === 0 &&
    stats.pendingComplaints === 0 &&
    stats.notificationSuccessRate === 0
  )
}

function formatTime(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

export function Dashboard() {
  const [loadState, setLoadState] = useState<LoadState>('loading')
  const [stats, setStats] = useState<DashboardStats>(DEFAULT_STATS)
  const [recentNotifications, setRecentNotifications] = useState<RecentNotification[]>([])
  const [suggestions, setSuggestions] = useState<SmartSuggestion[]>([])
  const [workbenchOverview, setWorkbenchOverview] = useState({
    pendingTasks: 0,
    overdueTasks: 0,
    riskyTrips: 0,
    pendingTakeovers: 0,
  })
  const [actionItems, setActionItems] = useState<
    Array<{ id: string; title: string; tripName: string; status: string; dueAt: string }>
  >([])
  const [errorMessage, setErrorMessage] = useState('')
  const [sendModalOpen, setSendModalOpen] = useState(false)
  const [activeSuggestion, setActiveSuggestion] = useState<SmartSuggestion | null>(null)
  const [sendingMsg, setSendingMsg] = useState(false)
  const [sendResultMsg, setSendResultMsg] = useState('')

  const loadData = async () => {
    setLoadState('loading')
    setErrorMessage('')

    try {
      const [statsData, recentData, suggData] = await Promise.all([
        dashboardApi.getStats(),
        dashboardApi.getRecentNotifications(10),
        dashboardApi.getSmartSuggestions(),
      ])
      const [overviewData, actionData] = await Promise.all([
        dashboardApi.getWorkbenchOverview({ ownerScope: 'mine' }),
        dashboardApi.getWorkbenchActionItems({ ownerScope: 'mine', limit: 5 }),
      ])

      setStats(statsData)
      setRecentNotifications(recentData)
      setSuggestions(suggData)
      setWorkbenchOverview({
        pendingTasks: overviewData.pendingTasks,
        overdueTasks: overviewData.overdueTasks,
        riskyTrips: overviewData.riskyTrips,
        pendingTakeovers: overviewData.pendingTakeovers,
      })
      setActionItems(
        actionData.map((item) => ({
          id: item.id,
          title: item.title,
          tripName: item.tripName,
          status: item.status,
          dueAt: item.dueAt,
        })),
      )
      setLoadState(isStatsEmpty(statsData) && recentData.length === 0 && suggData.length === 0 ? 'empty' : 'ready')
    } catch (error) {
      setLoadState('error')
      setErrorMessage(getErrorMessage(error))
    }
  }

  const handleOpenSmartSend = (suggestion: SmartSuggestion) => {
    setActiveSuggestion(suggestion)
    setSendResultMsg('')
    setSendModalOpen(true)
  }

  const executeSmartSend = async () => {
    if (!activeSuggestion) return
    setSendingMsg(true)
    setSendResultMsg('')
    try {
      const textarea = document.getElementById('ai-msg-textarea') as HTMLTextAreaElement
      const finalContent = textarea ? textarea.value : activeSuggestion.suggestedContent

      await notificationsApi.send({
        channel: activeSuggestion.channel,
        customerName: '全团游客',
        trip: activeSuggestion.tripId,
        customContent: finalContent,
      })
      setSendResultMsg('智能提示已成功下发至全团')
      setTimeout(() => {
        setSendModalOpen(false)
        setSuggestions((items) => items.filter((item) => item.id !== activeSuggestion.id))
      }, 1600)
    } catch (err) {
      setSendResultMsg(`下发失败: ${getErrorMessage(err)}`)
    } finally {
      setSendingMsg(false)
    }
  }

  useEffect(() => {
    void loadData()
  }, [])

  if (loadState === 'loading') {
    return (
      <PageShell title="Travel Hub Main Dashboard Overview" description="正在同步行程与通知运营数据">
        <PageState kind="loading" title="正在加载仪表盘" />
      </PageShell>
    )
  }

  if (loadState === 'error') {
    return (
      <PageShell title="Travel Hub Main Dashboard Overview">
        <PageState kind="error" title="仪表盘加载失败" description={errorMessage} onRetry={() => void loadData()} />
      </PageShell>
    )
  }

  if (loadState === 'empty') {
    return (
      <PageShell title="Travel Hub Main Dashboard Overview">
        <PageState kind="empty" title="仪表盘暂无数据" description="暂时没有统计与通知记录" onRetry={() => void loadData()} />
      </PageShell>
    )
  }

  return (
    <PageShell
      eyebrow="Operations"
      title="Travel Hub Main Dashboard Overview"
      description="Welcome back, Zhang San. 这里是行程、旅客和通知触达的实时运营摘要。"
      actions={<Button onClick={() => void loadData()}>刷新数据</Button>}
    >
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <MetricTile
          title="Active Trips"
          value={String(stats.activeTrips)}
          detail="当前未完成团期"
          trend="实时同步"
          trendTone="good"
          icon={Globe2}
        />
        <MetricTile
          title="Total Travelers"
          value={String(stats.totalTravelers || stats.totalUsers)}
          detail="已纳入服务的客人"
          trend={`${stats.notificationSuccessRate}% 通知成功率`}
          trendTone="good"
          icon={Users}
        />
        <MetricTile
          title="Pending Notifications"
          value={String(stats.pendingNotifications || stats.pendingComplaints)}
          detail="等待重试或人工确认"
          trend={stats.pendingNotifications > 0 ? '需关注' : '无积压'}
          trendTone={stats.pendingNotifications > 0 ? 'warn' : 'neutral'}
          icon={Bell}
        />
      </div>

      <Card title="今日工作台速览" className="mt-8 border-blue-100 shadow-[0_14px_40px_rgba(15,23,42,0.06)]">
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <div className="rounded-xl bg-slate-50 p-4">
            <p className="text-xs text-slate-500">待办任务</p>
            <p className="mt-1 text-2xl font-black text-slate-900">{workbenchOverview.pendingTasks}</p>
          </div>
          <div className="rounded-xl bg-amber-50 p-4">
            <p className="text-xs text-amber-700">逾期任务</p>
            <p className="mt-1 text-2xl font-black text-amber-700">{workbenchOverview.overdueTasks}</p>
          </div>
          <div className="rounded-xl bg-rose-50 p-4">
            <p className="text-xs text-rose-700">高风险团</p>
            <p className="mt-1 text-2xl font-black text-rose-700">{workbenchOverview.riskyTrips}</p>
          </div>
          <div className="rounded-xl bg-violet-50 p-4">
            <p className="text-xs text-violet-700">待接管</p>
            <p className="mt-1 text-2xl font-black text-violet-700">{workbenchOverview.pendingTakeovers}</p>
          </div>
        </div>
        <div className="mt-5">
          <p className="mb-2 text-xs font-black uppercase tracking-[0.18em] text-slate-500">待我处理</p>
          {actionItems.length === 0 ? (
            <p className="text-sm text-slate-500">当前没有待处理任务</p>
          ) : (
            <div className="space-y-2">
              {actionItems.map((item) => (
                <div key={item.id} className="flex items-center justify-between rounded-lg border border-slate-100 px-3 py-2">
                  <div>
                    <p className="text-sm font-semibold text-slate-900">{item.title}</p>
                    <p className="text-xs text-slate-500">{item.tripName} · 截止 {formatTime(item.dueAt)}</p>
                  </div>
                  <Badge variant={item.status === 'overdue' ? 'warning' : 'info'}>{item.status}</Badge>
                </div>
              ))}
            </div>
          )}
        </div>
      </Card>

      {suggestions.length > 0 ? (
        <section className="mt-8 rounded-2xl border border-sky-100 bg-gradient-to-r from-sky-500 to-blue-500 p-6 text-white shadow-2xl shadow-sky-900/20">
          <div className="mb-5 flex items-center justify-between gap-4">
            <div>
              <h2 className="flex items-center gap-2 text-2xl font-black">
                <Sparkles className="h-6 w-6 text-sky-100" />
                AI 智能管家提醒
              </h2>
              <p className="mt-1 text-sm text-sky-100">根据天气、行程节点和模板规则生成的运营建议。</p>
            </div>
          </div>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {suggestions.map((sugg) => (
              <div key={sugg.id} className="rounded-2xl bg-white/12 p-5 ring-1 ring-white/15 backdrop-blur">
                <div className="mb-3 flex items-start justify-between gap-4">
                  <h3 className="text-lg font-bold">{sugg.title}</h3>
                  <Badge variant={sugg.type === 'weather_alert' ? 'warning' : 'info'}>
                    {sugg.tripName} / {sugg.targetCount}人
                  </Badge>
                </div>
                <p className="mb-4 rounded-xl bg-white/10 p-3 text-sm leading-6 text-sky-50">{sugg.reason}</p>
                <Button onClick={() => handleOpenSmartSend(sugg)} className="w-full bg-white text-sky-700 hover:bg-sky-50">
                  一键预览并发送
                </Button>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      <Card title="Recent Activities" className="mt-8 overflow-hidden border-blue-100 shadow-[0_14px_40px_rgba(15,23,42,0.06)]">
        {recentNotifications.length === 0 ? (
          <PageState kind="empty" title="暂无最近通知" description="可稍后重试刷新" onRetry={() => void loadData()} />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-blue-50/80 text-left text-xs font-black uppercase tracking-[0.18em] text-slate-500">
                  <th className="px-4 py-4">Activity</th>
                  <th className="px-4 py-4">Date</th>
                  <th className="px-4 py-4">Channel</th>
                  <th className="px-4 py-4">Status</th>
                </tr>
              </thead>
              <tbody>
                {recentNotifications.map((notif) => (
                  <tr key={notif.id} className="border-b border-slate-100 transition hover:bg-blue-50/40">
                    <td className="px-4 py-4">
                      <div className="font-bold text-slate-900">Notification Sent: {notif.trip}</div>
                      <div className="text-xs text-slate-500">{notif.customerName}</div>
                    </td>
                    <td className="px-4 py-4 text-slate-600">{formatTime(notif.createdAt)}</td>
                    <td className="px-4 py-4 text-slate-600">{notif.channelLabel}</td>
                    <td className="px-4 py-4">
                      <div className="inline-flex items-center gap-2">
                        {notif.status === 'sent' ? (
                          <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                        ) : (
                          <Activity className="h-5 w-5 text-amber-600" />
                        )}
                        <Badge variant={notif.status === 'sent' ? 'success' : 'warning'}>{notif.statusLabel}</Badge>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Modal
        isOpen={sendModalOpen}
        onClose={() => setSendModalOpen(false)}
        title={activeSuggestion?.title || '发送智能提示'}
        footer={
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setSendModalOpen(false)}>
              取消
            </Button>
            <Button onClick={executeSmartSend} loading={sendingMsg}>
              确认下发全团
            </Button>
          </div>
        }
      >
        <div className="space-y-4">
          {sendResultMsg ? (
            <div className={`rounded-lg p-3 text-sm ${sendResultMsg.includes('失败') ? 'bg-red-50 text-red-600' : 'bg-green-50 text-green-600'}`}>
              {sendResultMsg}
            </div>
          ) : null}
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-gray-700">发送范围</label>
            <input
              type="text"
              readOnly
              value={`${activeSuggestion?.tripName || ''} (共 ${activeSuggestion?.targetCount || 0} 人)`}
              className="w-full cursor-not-allowed rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-gray-500"
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-gray-700">建议通知内容</label>
            <textarea
              key={activeSuggestion?.id}
              id="ai-msg-textarea"
              className="min-h-[120px] w-full rounded-lg border border-blue-200 bg-blue-50/30 px-3 py-2 leading-relaxed text-gray-800 outline-none focus:ring-2 focus:ring-blue-500"
              defaultValue={activeSuggestion?.suggestedContent}
            />
            <p className="mt-1 flex items-center gap-1 text-xs text-gray-400">
              <Sparkles size={12} /> 可在发送前修改上方内容。
            </p>
          </div>
        </div>
      </Modal>
    </PageShell>
  )
}
