import { Bell, Bus, Clock, Hotel, Utensils } from 'lucide-react'
import { type TripDayPlan } from '../../features/trip-management/tripDetailMapper'

interface TripScheduleTimelineProps {
  days: TripDayPlan[]
  nextHint?: string
}

export function TripScheduleTimeline({ days, nextHint = '' }: TripScheduleTimelineProps) {
  if (days.length === 0) {
    return (
      <div className="rounded-card border border-dashed border-paper-300 bg-paper-50 p-8 text-center">
        <p className="text-base font-medium text-paper-900">暂无按天行程安排</p>
        <p className="mt-2 text-sm text-paper-500">可在下方“行程安排”编辑区补充路线、交通和酒店信息。</p>
      </div>
    )
  }

  return (
    <div className="rounded-card border border-paper-200 bg-white p-5 shadow-card">
      <div className="mb-5 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <h2 className="text-lg font-semibold text-paper-900">完整旅行路径与时间安排</h2>
        <div className="flex items-center gap-2 rounded-control bg-paper-50 px-3 py-2 text-sm text-paper-600">
          <Bell className="h-4 w-4 text-paper-500" />
          {nextHint || '暂无下一条通知建议'}
        </div>
      </div>

      <div className="space-y-4">
        {days.map((day) => (
          <div key={day.id} className="rounded-control border border-paper-200 bg-paper-50/60 p-4">
            <div className="mb-3 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="text-xs text-paper-500">{day.title || `Day ${day.day}`}</p>
                <h3 className="text-base font-semibold text-paper-900">{day.route || '待补充路线'}</h3>
              </div>
              <p className="rounded-control bg-white px-3 py-1 text-sm tabular-nums text-paper-600">
                {day.date || '日期待定'}
              </p>
            </div>

            <div className="space-y-2">
              <div className="grid grid-cols-1 gap-3 rounded-control bg-white p-3 md:grid-cols-4">
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4 text-paper-500" />
                  <span className="text-sm text-paper-600">
                    {day.departureTime || '上午'} - {day.arrivalTime || '全天'}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <Bus className="h-4 w-4 text-paper-500" />
                  <span className="text-sm text-paper-700">{day.transport || '交通待定'}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Hotel className="h-4 w-4 text-paper-500" />
                  <span className="text-sm text-paper-600">{day.hotel || '酒店待定'}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Utensils className="h-4 w-4 text-paper-500" />
                  <span className="text-sm text-paper-600">{day.mealPlan || '用餐待现场确认'}</span>
                </div>
              </div>
              {day.sightseeing ? <p className="text-sm text-paper-600">景点：{day.sightseeing}</p> : null}
              {day.meetingReminder ? (
                <p className="text-sm text-paper-600">集合提醒：{day.meetingReminder}</p>
              ) : null}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
