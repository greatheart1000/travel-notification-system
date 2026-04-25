import { useEffect, useState } from 'react'
import { ArrowLeft } from 'lucide-react'
import { Header } from '../components/Header'
import { Card } from '../components/Card'
import { PageState } from '../components/PageState'
import { travelRepository } from '../repositories/travelRepository'
import { notificationRepository } from '../repositories/notificationRepository'
import type { Guest, ItineraryDay, PickupPlan, TravelTeam, NotificationTask } from '../mock/seed/travelSeed'

interface TripDetailProps {
  tripId: string | null
  onBack: () => void
}

export function TripDetail({ tripId, onBack }: TripDetailProps) {
  const [loading, setLoading] = useState(true)
  const [team, setTeam] = useState<TravelTeam | null>(null)
  const [guests, setGuests] = useState<Guest[]>([])
  const [itinerary, setItinerary] = useState<ItineraryDay[]>([])
  const [pickups, setPickups] = useState<PickupPlan[]>([])
  const [tasks, setTasks] = useState<NotificationTask[]>([])

  useEffect(() => {
    if (!tripId) return
    let mounted = true
    setLoading(true)
    Promise.all([
      travelRepository.getTeamById(tripId),
      travelRepository.getGuestsByTeamId(tripId),
      travelRepository.getItineraryByTeamId(tripId),
      travelRepository.getPickupPlansByTeamId(tripId),
      notificationRepository.getTasksByTeamId(tripId),
    ]).then(([teamData, guestRows, itineraryRows, pickupRows, taskRows]) => {
      if (!mounted) return
      setTeam(teamData)
      setGuests(guestRows)
      setItinerary(itineraryRows)
      setPickups(pickupRows)
      setTasks(taskRows)
      setLoading(false)
    }).catch(() => mounted && setLoading(false))

    return () => { mounted = false }
  }, [tripId])

  if (!tripId) return <PageState kind="error" title="缺少 teamId" description="请从行程管理列表进入团详情。" />
  if (loading) return <PageState kind="loading" title="正在加载团详情" />
  if (!team) return <PageState kind="error" title="团详情不存在" description={`未找到 teamId=${tripId} 对应的旅行团。`} />

  const sortedItinerary = [...itinerary].sort((a, b) => a.dayIndex - b.dayIndex)

  return (
    <>
      <Header />
      <div className="min-h-screen bg-slate-50 pb-12">
        <div className="border-b bg-white">
          <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
            <div className="flex items-center gap-3">
              <button onClick={onBack} className="rounded-full p-2 hover:bg-slate-100"><ArrowLeft className="h-4 w-4" /></button>
              <div><h1 className="text-lg font-semibold">{team.name}</h1><p className="text-xs text-slate-500">{team.teamCode}</p></div>
            </div>
          </div>
        </div>

        <div className="mx-auto grid max-w-7xl grid-cols-1 gap-5 px-6 py-6 lg:grid-cols-2">
          <Card title="团详情总览"><div className="space-y-2 text-sm text-slate-700">
            <p>团名：{team.name}</p><p>团号：{team.teamCode}</p><p>起止日期：{team.startDate} ~ {team.endDate}</p><p>游客数量：{guests.length}</p>
            <p>数据完整度：{team.dataCompleteness}%</p><p>是否已导入行程：{team.importedSchedule ? '是' : '否'}</p><p>是否已导入游客：{team.importedGuests ? '是' : '否'}</p>
            <p>今日待办：{team.todayTodoCount}</p><p>下一通知节点：{team.nextNotificationAt}</p>
          </div></Card>
          <Card title="数据联动校验"><div className="space-y-2 text-sm text-slate-700">
            <p>每日行程：{itinerary.length} 天</p><p>接送安排：{pickups.length} 条</p><p>通知任务：{tasks.length} 条</p>
            <p>说明：该页读取真实后端 API 数据。</p>
          </div></Card>
        </div>
      </div>
    </>
  )
}
