import { tripsApi } from '../services/api'
import type { Guest, ItineraryDay, PickupPlan, TravelTeam } from '../mock/seed/travelSeed'

interface TripLookupResult {
  tripId: string
  team: TravelTeam
}

function completenessOf(hasSchedule: boolean, hasGuests: boolean): number {
  if (hasSchedule && hasGuests) return 95
  if (hasSchedule || hasGuests) return 60
  return 30
}

function toTeamStatus(status: string): TravelTeam['status'] {
  if (status === 'in_progress') return 'in_progress'
  if (status === 'completed') return 'completed'
  return 'planned'
}

export const travelRepository = {
  async getTeams(): Promise<TravelTeam[]> {
    const [trips, rows] = await Promise.all([
      tripsApi.list(),
      tripsApi.listExecutionRows({ ownerScope: 'mine' }).catch(() => []),
    ])

    return trips.map((trip) => {
      const row = rows.find((item) => item.tripId === trip.id)
      const hasSchedule = trip.itinerary.length > 0
      const hasGuests = trip.guests.length > 0
      return {
        id: trip.id,
        name: trip.destination,
        teamCode: trip.teamId || trip.id,
        destination: trip.destination,
        startDate: trip.startDate,
        endDate: trip.endDate,
        status: toTeamStatus(trip.status),
        dataCompleteness: completenessOf(hasSchedule, hasGuests),
        importedSchedule: hasSchedule,
        importedGuests: hasGuests,
        guestCount: trip.guests.length || trip.participants,
        todayTodoCount: row?.todoCount ?? 0,
        nextNotificationAt: row?.nextNodeDueAt || '待生成通知节点',
      }
    })
  },

  async getTeamById(teamId: string): Promise<TravelTeam | null> {
    const teams = await this.getTeams()
    return teams.find((team) => team.id === teamId || team.teamCode === teamId) ?? null
  },

  async getGuestsByTeamId(teamId: string): Promise<Guest[]> {
    const trip = await this.resolveTripByTeamId(teamId)
    if (!trip) return []
    const detail = await tripsApi.get(trip.tripId)
    return detail.guests.map((guest, index) => ({
      id: `${detail.id}-guest-${index}`,
      teamId: detail.id,
      name: guest.name,
      phone: guest.phone,
      idNo: '',
      emergencyContact: '',
      notes: guest.notes || '',
    }))
  },

  async getItineraryByTeamId(teamId: string): Promise<ItineraryDay[]> {
    const trip = await this.resolveTripByTeamId(teamId)
    if (!trip) return []
    const detail = await tripsApi.get(trip.tripId)
    return detail.itinerary.map((day, index) => ({
      id: `${detail.id}-day-${index + 1}`,
      teamId: detail.id,
      date: day.date,
      dayIndex: index + 1,
      title: `Day ${index + 1}`,
      city: day.route.split('->').slice(-1)[0]?.trim() || detail.destination,
      route: day.route,
      transport: day.transport,
      hotel: day.hotel,
      meals: '早中晚',
      noticeMorning: `早安提醒：${day.route}`,
      noticeNoon: `中午提醒：${day.transport}`,
      noticeEvening: `晚间提醒：入住${day.hotel}`,
    }))
  },

  async getPickupPlansByTeamId(teamId: string): Promise<PickupPlan[]> {
    const trip = await this.resolveTripByTeamId(teamId)
    if (!trip) return []
    const schedule = await tripsApi.getSchedule(trip.tripId).catch(() => null)
    if (!schedule || schedule.days.length === 0) return []
    const firstDay = schedule.days[0]
    return [{
      id: `${schedule.tripId}-pickup-1`,
      teamId: schedule.tripId,
      date: firstDay.date,
      time: firstDay.segments[0]?.departureTime || '08:00',
      location: firstDay.segments[0]?.from || schedule.destination,
      vehicle: firstDay.transport || '待定',
      driver: schedule.leader.name || '待分配',
      contactPhone: schedule.leader.phone || schedule.contact.phone || '待补充',
      notes: '来自后端行程首段信息',
    }]
  },

  async resolveTripByTeamId(teamId: string): Promise<TripLookupResult | null> {
    const teams = await this.getTeams()
    const matched = teams.find((team) => team.id === teamId || team.teamCode === teamId)
    if (!matched) return null
    return { tripId: matched.id, team: matched }
  },
}
