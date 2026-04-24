import { useEffect, useState } from 'react'
import { ArrowLeft } from 'lucide-react'
import { Badge } from '../components/Badge'
import { Button } from '../components/Button'
import { Card } from '../components/Card'
import { PageShell } from '../components/PageShell'
import { PageState } from '../components/PageState'
import { notificationRepository } from '../repositories/notificationRepository'
import { travelRepository } from '../repositories/travelRepository'
import { travelDemoService } from '../services/travel/travelDemoService'
import type { Guest, ItineraryDay, NotificationTask, TravelTeam } from '../mock/seed/travelSeed'

interface NotificationsProps {
  tripId?: string | null
  onBackToTrip?: (tripId: string) => void
}

const statusLabel = { pending: '待执行', completed: '已完成', takeover: '人工接管' }

export function Notifications({ tripId = null, onBackToTrip }: NotificationsProps) {
  const [loading, setLoading] = useState(true)
  const [team, setTeam] = useState<TravelTeam | null>(null)
  const [config, setConfig] = useState<any>(null)
  const [itinerary, setItinerary] = useState<ItineraryDay[]>([])
  const [guests, setGuests] = useState<Guest[]>([])
  const [tasks, setTasks] = useState<NotificationTask[]>([])

  const load = async () => {
    if (!tripId) return
    setLoading(true)
    const [teamData, cfg, itineraryRows, guestRows] = await Promise.all([
      travelRepository.getTeamById(tripId),
      travelDemoService.getNotificationConfig(tripId).catch(() => null),
      travelRepository.getItineraryByTeamId(tripId),
      travelRepository.getGuestsByTeamId(tripId),
    ])
    let taskRows = await notificationRepository.getTasksByTeamId(tripId)
    if (taskRows.length === 0 && itineraryRows.length > 0) {
      taskRows = await notificationRepository.generateTasksForTeam(tripId)
    }
    setTeam(teamData)
    setConfig(cfg)
    setItinerary(itineraryRows)
    setGuests(guestRows)
    setTasks(taskRows)
    setLoading(false)
  }

  useEffect(() => {
    void load()
  }, [tripId])

  if (!tripId) return <PageShell eyebrow="通知中心" title="旅行团通知配置中心" description="请从行程管理页选择具体旅行团进入通知执行。" />
  if (loading) return <PageState kind="loading" title="正在加载通知执行页" />
  if (!team) return <PageState kind="error" title="旅行团不存在" description={`未找到 teamId=${tripId} 的数据`} />

  return (
    <PageShell eyebrow="通知中心" title="旅行团通知配置中心" description="当前页面已绑定具体旅行团，可直接配置该团通知参数并回跳详情页。"
      actions={<Button variant="secondary" onClick={() => onBackToTrip?.(tripId)}><ArrowLeft className="mr-2 inline h-4 w-4" />返回团详情</Button>}>
      <Card title="当前旅行团信息"><div className="grid grid-cols-1 gap-2 text-sm lg:grid-cols-2">
        <p>团名：{team.name}</p><p>团号：{team.teamCode}</p><p>出发日期：{team.startDate}</p><p>游客数：{guests.length}</p><p>当前通知状态：{config?.currentNotificationStatus ?? '待配置'}</p>
      </div></Card>

      <Card title="通知配置区" className="mt-5">{config ? <div className="grid grid-cols-1 gap-2 text-sm lg:grid-cols-2">
        <p>项目名称：{config.projectName}</p><p>人工接管目标：{config.manualTakeoverTarget}</p><p>短信签名：{config.smsSignName}</p><p>短信服务商：{config.smsProvider}</p><p>是否启用天气预警自动通知：{config.weatherAlertEnabled ? '是' : '否'}</p>
      </div> : <p className="text-sm text-amber-700">当前团未配置通知参数，请先补充通知配置。</p>}</Card>

      <Card title="每日通知内容（早 / 中 / 晚）" className="mt-5">{itinerary.length === 0 ? <p className="text-sm text-amber-700">请先导入每日行程</p> : <div className="space-y-3">{itinerary.map((day) => (
        <div key={day.id} className="rounded-lg border border-slate-200 p-3 text-sm"><p className="font-semibold">{day.date} · Day {day.dayIndex} · {day.title}</p><p>早间通知：{day.noticeMorning || '—'}</p><p>中午通知：{day.noticeNoon || '—'}</p><p>晚间通知：{day.noticeEvening || '—'}</p></div>
      ))}</div>}</Card>

      <Card title="待执行通知任务" className="mt-5">
        {guests.length === 0 ? <p className="mb-3 text-sm text-amber-700">请先导入游客名单</p> : null}
        {tasks.length === 0 ? <p className="text-sm text-amber-700">当前无通知任务；若存在行程将自动生成默认任务。</p> : <div className="space-y-3">{tasks.map((task) => (
          <div key={task.id} className="rounded-lg border border-slate-200 p-3 text-sm"><div className="flex items-center justify-between"><p className="font-semibold">{task.title}</p><Badge variant="default">{statusLabel[task.status]}</Badge></div>
            <p>发送时间：{task.scheduledAt}</p><p>发送渠道：{task.channel}</p><p>接收对象：{task.targetGroup}</p><p>内容：{task.content}</p>
            <div className="mt-2 flex gap-2"><Button size="sm" variant="secondary">预览</Button>
              <Button size="sm" onClick={() => travelDemoService.completeTask(task.id).then(load)}>标记完成</Button>
              <Button size="sm" variant="ghost" onClick={() => travelDemoService.takeoverTask(task.id).then(load)}>人工接管</Button></div>
          </div>
        ))}</div>}
      </Card>
    </PageShell>
  )
}
