import { useEffect, useState } from 'react'
import { ArrowLeft } from 'lucide-react'
import { Header } from '../components/Header'
import { Button } from '../components/Button'
import { Card } from '../components/Card'
import { PageState } from '../components/PageState'
import { travelRepository } from '../repositories/travelRepository'
import { notificationRepository } from '../repositories/notificationRepository'
import type { Guest, ItineraryDay, PickupPlan, TravelTeam, NotificationTask } from '../mock/seed/travelSeed'

interface TripDetailProps {
  tripId: string | null
  onBack: () => void
  onOpenTripNotifications?: (tripId: string) => void
}

export function TripDetail({ tripId, onBack, onOpenTripNotifications }: TripDetailProps) {
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
            <Button onClick={() => onOpenTripNotifications?.(team.id)}>通知设置</Button>
          </div>
        </div>

        <div className="mx-auto max-w-7xl px-6 py-6">
          <Card title="旅行行程表">
            <div className="mb-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
              <div className="grid grid-cols-1 gap-2 md:grid-cols-2 xl:grid-cols-4">
                <p><span className="font-medium text-slate-900">团号：</span>{team.teamCode}</p>
                <p><span className="font-medium text-slate-900">团名：</span>{team.name}</p>
                <p><span className="font-medium text-slate-900">出团日期：</span>{team.startDate} 至 {team.endDate}</p>
                <p><span className="font-medium text-slate-900">人数：</span>{guests.length} 人</p>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="min-w-full border border-slate-200 text-sm">
                <thead className="bg-slate-100 text-slate-900">
                  <tr>
                    <th className="border border-slate-200 px-3 py-2 text-left">日期</th>
                    <th className="border border-slate-200 px-3 py-2 text-left">交通工具</th>
                    <th className="border border-slate-200 px-3 py-2 text-left">行程</th>
                    <th className="border border-slate-200 px-3 py-2 text-center">早</th>
                    <th className="border border-slate-200 px-3 py-2 text-center">午</th>
                    <th className="border border-slate-200 px-3 py-2 text-center">晚</th>
                    <th className="border border-slate-200 px-3 py-2 text-left">酒店</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedItinerary.map((day) => (
                    <tr key={day.id} className="align-top odd:bg-white even:bg-slate-50">
                      <td className="border border-slate-200 px-3 py-2">{day.date.slice(5)}</td>
                      <td className="border border-slate-200 px-3 py-2">{day.transport || '-'}</td>
                      <td className="border border-slate-200 px-3 py-2">
                        <p className="font-medium text-slate-900">{day.title}</p>
                        <p className="text-slate-600">{day.route || '-'}</p>
                      </td>
                      <td className="border border-slate-200 px-3 py-2 text-center">{day.noticeMorning ? '√' : '×'}</td>
                      <td className="border border-slate-200 px-3 py-2 text-center">{day.noticeNoon ? '√' : '×'}</td>
                      <td className="border border-slate-200 px-3 py-2 text-center">{day.noticeEvening ? '√' : '×'}</td>
                      <td className="border border-slate-200 px-3 py-2">{day.hotel || '-'}</td>
                    </tr>
                  ))}
                  {sortedItinerary.length === 0 && (
                    <tr>
                      <td className="border border-slate-200 px-3 py-8 text-center text-slate-500" colSpan={7}>
                        暂无已导入行程，请先上传行程表。
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>

          <div className="mt-5 grid grid-cols-1 gap-5 lg:grid-cols-2">
            <Card title="数据联动校验">
              <div className="space-y-2 text-sm text-slate-700">
                <p>每日行程：{itinerary.length} 天</p>
                <p>接送安排：{pickups.length} 条</p>
                <p>通知任务：{tasks.length} 条</p>
                <p>说明：该页与通知执行页均读取真实后端 API 数据。</p>
              </div>
            </Card>
            <Card title="运营状态">
              <div className="space-y-2 text-sm text-slate-700">
                <p>数据完整度：{team.dataCompleteness}%</p>
                <p>是否已导入行程：{team.importedSchedule ? '是' : '否'}</p>
                <p>是否已导入游客：{team.importedGuests ? '是' : '否'}</p>
                <p>今日待办：{team.todayTodoCount}</p>
                <p>下一通知节点：{team.nextNotificationAt}</p>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </>
  )
}
