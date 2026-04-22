import { tripsApi } from '../../services/api'
import { type Trip, type TripSchedule } from '../../types/api'
import { type TripDayPlan, toTripItineraryPayload } from './tripDetailMapper'

export interface TripDetailPayload {
  trip: Trip
  schedule: TripSchedule
}

export async function loadTripDetail(tripId: string): Promise<TripDetailPayload> {
  const [trip, schedule] = await Promise.all([tripsApi.get(tripId), tripsApi.getSchedule(tripId)])
  return { trip, schedule }
}

export async function saveTripDays(tripId: string, days: TripDayPlan[]): Promise<Trip> {
  return tripsApi.update(tripId, {
    itinerary: toTripItineraryPayload(days),
  })
}
