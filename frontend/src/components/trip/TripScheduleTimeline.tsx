import { Bell, Bus, Clock, Hotel, Utensils } from 'lucide-react'
import { type TripDayPlan } from '../../features/trip-management/tripDetailMapper'

interface TripScheduleTimelineProps {
  days: TripDayPlan[]
  nextHint?: string
}

export function TripScheduleTimeline({ days, nextHint = '' }: TripScheduleTimelineProps) {
  if (days.length === 0) {
    return (
      <div className="rounded-3xl border border-dashed border-blue-200 bg-blue-50/60 p-8 text-center">
        <p className="text-lg font-black text-slate-900">暂无按天行程安排</p>
        <p className="mt-2 text-sm text-slate-500">可在下方“行程安排”编辑区补充路线、交通和酒店信息。</p>
      </div>
    )
  }

  return (
    <div className="rounded-[2rem] border border-blue-100 bg-white p-6 shadow-sm">
      <div className="mb-6 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.28em] text-blue-700">Daily Schedule</p>
          <h2 className="mt-2 text-2xl font-black tracking-tight text-slate-950">完整旅行路径与时间安排</h2>
        </div>
        <div className="rounded-2xl bg-blue-50 px-4 py-3 text-sm text-blue-800">
          <Bell className="mr-2 inline h-4 w-4" />
          {nextHint || '暂无下一条通知建议'}
        </div>
      </div>

      <div className="space-y-5">
        {days.map((day) => (
          <div key={day.id} className="relative rounded-3xl border border-slate-100 bg-slate-50/70 p-5">
            <div className="mb-4 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="text-sm font-black text-blue-700">{day.title || `Day ${day.day}`}</p>
                <h3 className="text-xl font-black text-slate-950">{day.route || '待补充路线'}</h3>
              </div>
              <p className="rounded-full bg-white px-4 py-2 text-sm font-bold text-slate-600 shadow-sm">
                {day.date || '日期待定'}
              </p>
            </div>

            <div className="space-y-3">
              <div className="grid grid-cols-1 gap-3 rounded-2xl bg-white p-4 md:grid-cols-4">
                <div className="flex items-center gap-3">
                  <Clock className="h-4 w-4 text-slate-400" />
                  <span className="text-sm text-slate-600">
                    {day.departureTime || '上午'} - {day.arrivalTime || '全天'}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <Bus className="h-4 w-4 text-blue-600" />
                  <span className="text-sm font-semibold text-slate-800">{day.transport || '交通待定'}</span>
                </div>
                <div className="flex items-center gap-3">
                  <Hotel className="h-4 w-4 text-emerald-600" />
                  <span className="text-sm text-slate-600">{day.hotel || '酒店待定'}</span>
                </div>
                <div className="flex items-center gap-3">
                  <Utensils className="h-4 w-4 text-orange-500" />
                  <span className="text-sm text-slate-600">{day.mealPlan || '用餐待现场确认'}</span>
                </div>
              </div>
              {day.sightseeing ? (
                <p className="text-sm text-slate-600">景点：{day.sightseeing}</p>
              ) : null}
              {day.meetingReminder ? (
                <p className="text-sm text-slate-600">集合提醒：{day.meetingReminder}</p>
              ) : null}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
