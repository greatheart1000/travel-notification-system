import type {
  MakeNotificationRule,
  MakeTourist,
  MakeTrip,
  MakeTripDetail,
  MakeTripStatus,
  MakeWeatherInfo,
  mockAnalyticsData,
} from '../data/figmaMockData'

const FIGMA_API_BASE_URL = ''

export type MakeAnalyticsData = typeof mockAnalyticsData
export type MakeStatusColorMap = Record<MakeTripStatus, string>

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T
}

async function requestJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  headers.set('Accept', 'application/json')

  const response = await fetch(`${FIGMA_API_BASE_URL}${path}`, {
    ...init,
    headers,
  })

  if (!response.ok) {
    throw new Error(`API ${init.method ?? 'GET'} ${path} failed with ${response.status}`)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}

function withoutDetailFields(detail: MakeTripDetail): MakeTrip {
  const { itinerary, tourists, notifications, ...trip } = detail
  return clone(trip)
}

export class FigmaTripService {
  static async getAllTrips(): Promise<MakeTrip[]> {
    return requestJson<MakeTrip[]>('/api/trips')
  }

  static async getTripById(id: string): Promise<MakeTrip | undefined> {
    const trips = await FigmaTripService.getAllTrips()
    return trips.find((trip) => trip.id === id)
  }

  static async getTripByTeamId(teamId: string): Promise<MakeTrip | undefined> {
    const trips = await FigmaTripService.getAllTrips()
    return trips.find((trip) => trip.teamId === teamId || trip.id === teamId || trip.code === teamId)
  }

  static async getTripDetail(teamId: string): Promise<MakeTripDetail | undefined> {
    try {
      return await requestJson<MakeTripDetail>(`/api/trips/${encodeURIComponent(teamId)}`)
    } catch (error) {
      if (error instanceof Error && error.message.includes(' 404')) return undefined
      throw error
    }
  }

  static async getTripsPaginated(page: number, pageSize: number): Promise<{
    data: MakeTrip[]
    total: number
    totalPages: number
    currentPage: number
  }> {
    const trips = await FigmaTripService.getAllTrips()
    const total = trips.length
    const totalPages = Math.max(1, Math.ceil(total / pageSize))
    const currentPage = Math.min(Math.max(page, 1), totalPages)
    const startIndex = (currentPage - 1) * pageSize
    const data = trips.slice(startIndex, startIndex + pageSize)

    return { data, total, totalPages, currentPage }
  }

  static async updateTrip(updatedTrip: MakeTrip): Promise<MakeTrip | undefined> {
    const trip = await requestJson<MakeTrip>(`/api/trips/${encodeURIComponent(updatedTrip.teamId || updatedTrip.id)}`, {
      method: 'PUT',
      body: JSON.stringify(updatedTrip),
    })
    return trip
  }

  static async deleteTrip(tripId: string): Promise<void> {
    await requestJson<void>(`/api/trips/${encodeURIComponent(tripId)}`, { method: 'DELETE' })
  }

  static async updateNotification(
    teamId: string,
    index: number,
    notification: MakeNotificationRule,
  ): Promise<MakeTripDetail | undefined> {
    return requestJson<MakeTripDetail>(
      `/api/trips/${encodeURIComponent(teamId)}/notifications/${index}`,
      {
        method: 'PUT',
        body: JSON.stringify(notification),
      },
    )
  }

  static async deleteNotification(teamId: string, index: number): Promise<MakeTripDetail | undefined> {
    return requestJson<MakeTripDetail>(
      `/api/trips/${encodeURIComponent(teamId)}/notifications/${index}`,
      { method: 'DELETE' },
    )
  }

  static async updateTourist(teamId: string, index: number, tourist: MakeTourist): Promise<MakeTripDetail | undefined> {
    return requestJson<MakeTripDetail>(
      `/api/trips/${encodeURIComponent(teamId)}/tourists/${index}`,
      {
        method: 'PUT',
        body: JSON.stringify(tourist),
      },
    )
  }

  static async addTourist(teamId: string, tourist: MakeTourist): Promise<MakeTripDetail | undefined> {
    return requestJson<MakeTripDetail>(`/api/trips/${encodeURIComponent(teamId)}/tourists`, {
      method: 'POST',
      body: JSON.stringify(tourist),
    })
  }

  static async deleteTourist(teamId: string, index: number): Promise<MakeTripDetail | undefined> {
    return requestJson<MakeTripDetail>(
      `/api/trips/${encodeURIComponent(teamId)}/tourists/${index}`,
      { method: 'DELETE' },
    )
  }

  static async importTouristsFromExcel(teamId: string): Promise<MakeTripDetail | undefined> {
    return requestJson<MakeTripDetail>(`/api/trips/${encodeURIComponent(teamId)}/imported-tourists`, {
      method: 'POST',
    })
  }

  static async reset(): Promise<void> {
    await requestJson<void>('/api/mock-data/reset', { method: 'POST' })
  }

  static async getSeedTrips(): Promise<MakeTrip[]> {
    return requestJson<MakeTrip[]>('/api/mock-data/mockTrips')
  }

  static async getStatusColorMap(): Promise<MakeStatusColorMap> {
    return requestJson<MakeStatusColorMap>('/api/mock-data/makeStatusColorMap')
  }

  static tripSummaryFromDetail(detail: MakeTripDetail): MakeTrip {
    return withoutDetailFields(detail)
  }
}

export class FigmaWeatherService {
  static async getAllWeather(): Promise<MakeWeatherInfo[]> {
    return requestJson<MakeWeatherInfo[]>('/api/weather')
  }

  static async getWarningCities(): Promise<MakeWeatherInfo[]> {
    return requestJson<MakeWeatherInfo[]>('/api/weather/warnings')
  }

  static async getWeatherByCity(city: string): Promise<MakeWeatherInfo | undefined> {
    const weather = await FigmaWeatherService.getAllWeather()
    return weather.find((item) => item.city === city)
  }
}

export class FigmaAnalyticsService {
  static async getAnalytics(): Promise<MakeAnalyticsData> {
    return requestJson<MakeAnalyticsData>('/api/analytics')
  }
}
