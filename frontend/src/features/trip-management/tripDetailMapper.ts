import { type Trip, type TripSchedule } from '../../types/api'

export interface TripDayPlan {
  id: string
  day: number
  title: string
  date: string
  route: string
  departureTime: string
  arrivalTime: string
  sightseeing: string
  transport: string
  hotel: string
  mealPlan: string
  meetingReminder: string
}

export interface TripDetailViewModel {
  tripId: string
  destination: string
  teamId: string
  statusCode: string
  statusLabel: string
  startDate: string
  endDate: string
  travelerCount: number
  leaderName: string
  contactPhone: string
  routeOverview: string
  routeSummary: string[]
  days: TripDayPlan[]
}

function safeText(value: unknown): string {
  return typeof value === 'string' ? value : ''
}

function toDayId(day: number, date: string): string {
  return `day-${day}-${date || 'na'}`
}

function renumberDays(days: TripDayPlan[]): TripDayPlan[] {
  return days.map((day, index) => ({
    ...day,
    id: toDayId(index + 1, day.date),
    day: index + 1,
    title: `Day ${index + 1}`,
  }))
}

function fromScheduleDays(schedule: TripSchedule): TripDayPlan[] {
  return schedule.days.map((day, index) => {
    const firstSegment = day.segments[0]
    return {
      id: toDayId(day.day || index + 1, day.date),
      day: day.day || index + 1,
      title: day.title || `Day ${index + 1}`,
      date: day.date,
      route: day.route,
      departureTime: firstSegment?.departureTime || '',
      arrivalTime: firstSegment?.arrivalTime || '',
      sightseeing: firstSegment?.sightseeing || day.route || '',
      transport: firstSegment?.transport || day.transport || '',
      hotel: firstSegment?.hotel || day.hotel || '',
      mealPlan: firstSegment?.mealPlan || '',
      meetingReminder: '',
    }
  })
}

function fromTripItinerary(trip: Trip): TripDayPlan[] {
  return trip.itinerary.map((item, index) => {
    const raw = item as unknown as Record<string, unknown>
    return {
      id: toDayId(index + 1, item.date),
      day: index + 1,
      title: safeText(raw.day_title) || `Day ${index + 1}`,
      date: item.date,
      route: item.route,
      departureTime: safeText(raw.departure_time),
      arrivalTime: safeText(raw.arrival_time),
      sightseeing: safeText(raw.sightseeing) || item.route,
      transport: item.transport,
      hotel: item.hotel,
      mealPlan: safeText(raw.meal_plan),
      meetingReminder: safeText(raw.meeting_reminder),
    }
  })
}

export function mergeTripDetail(trip: Trip, schedule: TripSchedule): TripDetailViewModel {
  const scheduleDays = fromScheduleDays(schedule)
  const tripDays = fromTripItinerary(trip)
  const days = scheduleDays.length > 0 ? scheduleDays : tripDays
  const normalizedDays = renumberDays(days)
  const routeSummary = schedule.routeSummary.length > 0 ? schedule.routeSummary : [trip.destination]
  const travelerCount = schedule.travelerCount || trip.guests.length || trip.participants

  return {
    tripId: trip.id,
    destination: trip.destination,
    teamId: trip.teamId,
    statusCode: schedule.status.code || trip.status,
    statusLabel: schedule.status.label || trip.statusLabel,
    startDate: trip.startDate || schedule.startDate,
    endDate: trip.endDate || schedule.endDate,
    travelerCount,
    leaderName: schedule.leader.name || trip.leaderName || '未配置',
    contactPhone: schedule.contact.phone || schedule.leader.phone || trip.contactPhone || '暂无联系方式',
    routeOverview: routeSummary.join(' -> '),
    routeSummary,
    days: normalizedDays,
  }
}

export function buildDayDraft(current: TripDayPlan[]): TripDayPlan {
  const day = current.length + 1
  return {
    id: toDayId(day, ''),
    day,
    title: `Day ${day}`,
    date: '',
    route: '',
    departureTime: '',
    arrivalTime: '',
    sightseeing: '',
    transport: '大巴',
    hotel: '',
    mealPlan: '',
    meetingReminder: '',
  }
}

export function upsertDay(days: TripDayPlan[], next: TripDayPlan): TripDayPlan[] {
  const updated = days.map((day) => (day.id === next.id ? next : day))
  return renumberDays(updated)
}

export function removeDay(days: TripDayPlan[], dayId: string): TripDayPlan[] {
  return renumberDays(days.filter((day) => day.id !== dayId))
}

export function toTripItineraryPayload(days: TripDayPlan[]): Array<Record<string, string>> {
  return renumberDays(days).map((day) => ({
    date: day.date,
    transport: day.transport,
    route: day.route,
    hotel: day.hotel,
    day_title: day.title,
    departure_time: day.departureTime,
    arrival_time: day.arrivalTime,
    sightseeing: day.sightseeing,
    meal_plan: day.mealPlan,
    meeting_reminder: day.meetingReminder,
  }))
}
