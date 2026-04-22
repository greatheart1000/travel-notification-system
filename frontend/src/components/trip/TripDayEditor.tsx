import { Trash2 } from 'lucide-react'
import { Button } from '../Button'
import { type TripDayPlan } from '../../features/trip-management/tripDetailMapper'

interface TripDayEditorProps {
  day: TripDayPlan
  onChange: (next: TripDayPlan) => void
  onDelete: (dayId: string) => void
}

export function TripDayEditor({ day, onChange, onDelete }: TripDayEditorProps) {
  const update = (field: keyof TripDayPlan, value: string) => {
    onChange({ ...day, [field]: value })
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <h4 className="text-lg font-black text-slate-900">{day.title}</h4>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => onDelete(day.id)}
          className="text-red-600 hover:bg-red-50 hover:text-red-700"
        >
          <Trash2 className="mr-1 h-4 w-4" />
          删除
        </Button>
      </div>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
        <label className="text-xs font-semibold text-slate-500">
          日期
          <input
            type="date"
            value={day.date}
            onChange={(e) => update('date', e.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
          />
        </label>
        <label className="text-xs font-semibold text-slate-500">
          出发时间
          <input
            type="time"
            value={day.departureTime}
            onChange={(e) => update('departureTime', e.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
          />
        </label>
        <label className="text-xs font-semibold text-slate-500">
          到达时间
          <input
            type="time"
            value={day.arrivalTime}
            onChange={(e) => update('arrivalTime', e.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
          />
        </label>
        <label className="text-xs font-semibold text-slate-500 md:col-span-2">
          路线
          <input
            type="text"
            value={day.route}
            onChange={(e) => update('route', e.target.value)}
            placeholder="例如：乌鲁木齐 -> 吐鲁番"
            className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
          />
        </label>
        <label className="text-xs font-semibold text-slate-500">
          景点
          <input
            type="text"
            value={day.sightseeing}
            onChange={(e) => update('sightseeing', e.target.value)}
            placeholder="例如：火焰山"
            className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
          />
        </label>
        <label className="text-xs font-semibold text-slate-500">
          交通
          <input
            type="text"
            value={day.transport}
            onChange={(e) => update('transport', e.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
          />
        </label>
        <label className="text-xs font-semibold text-slate-500">
          酒店
          <input
            type="text"
            value={day.hotel}
            onChange={(e) => update('hotel', e.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
          />
        </label>
        <label className="text-xs font-semibold text-slate-500">
          用餐
          <input
            type="text"
            value={day.mealPlan}
            onChange={(e) => update('mealPlan', e.target.value)}
            placeholder="例如：早/中/晚"
            className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
          />
        </label>
        <label className="text-xs font-semibold text-slate-500 md:col-span-2">
          集合提醒
          <input
            type="text"
            value={day.meetingReminder}
            onChange={(e) => update('meetingReminder', e.target.value)}
            placeholder="例如：07:30 大堂集合"
            className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
          />
        </label>
      </div>
    </div>
  )
}
