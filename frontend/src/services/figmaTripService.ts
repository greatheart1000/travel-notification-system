import { api } from './api'
import type {
  MakeNotificationRule,
  MakeTourist,
  MakeTrip,
  MakeTripDetail,
  MakeTripStatus,
  MakeWeatherInfo,
  mockAnalyticsData,
} from '../data/figmaMockData'
import {
  makeStatusColorMap,
  mockWeather,
} from '../data/figmaMockData'

export type MakeAnalyticsData = typeof mockAnalyticsData
export type MakeStatusColorMap = Record<MakeTripStatus, string>

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T
}

// ---- backend status ⇄ frontend status ----
const TO_BACKEND_STATUS: Record<string, string> = {
  '招募中': 'planned',
  '进行中': 'in_progress',
  '已满员': 'completed',
  '即将出发': 'planned',
}

const FROM_BACKEND_STATUS: Record<string, MakeTripStatus> = {
  planned: '招募中',
  in_progress: '进行中',
  completed: '已满员',
  cancelled: '已满员',
}

function mapRawToTrip(raw: any): MakeTrip {
  const status: MakeTripStatus = FROM_BACKEND_STATUS[raw.status] ?? '招募中'
  return {
    id: String(raw.id ?? ''),
    teamId: String(raw.team_id ?? raw.team ?? ''),
    name: String(raw.destination ?? '未命名团'),
    code: String(raw.team ?? raw.team_id ?? ''),
    startDate: String(raw.start_date ?? ''),
    endDate: String(raw.end_date ?? ''),
    participants: Number(raw.participants ?? 0),
    leader: String(raw.leader_name ?? ''),
    status,
    statusColor: makeStatusColorMap[status],
  }
}

function mapRawToDetail(raw: any): MakeTripDetail {
  const guests: any[] = Array.isArray(raw.guests) ? raw.guests : []
  return {
    ...mapRawToTrip(raw),
    itinerary: Array.isArray(raw.itinerary) ? raw.itinerary : [],
    tourists: guests.map((g: any) => ({
      name: String(g.name ?? ''),
      age: Number(g.age ?? 0),
      gender: String(g.gender ?? ''),
      phone: String(g.phone ?? ''),
      idCard: String(g.id_card ?? ''),
      notes: String(g.notes ?? ''),
      wechat: g.wechat ?? '',
    })),
    notifications: [],
  }
}

// ================================================================
// FIGMA TRIP SERVICE —  calls REAL backend API
// ================================================================

export class FigmaTripService {
  // ---- READ ----
  static async getAllTrips(): Promise<MakeTrip[]> {
    const data: any = await api.get('/trips')
    const items: any[] = Array.isArray(data) ? data : (data?.items ?? [])
    return items.map(mapRawToTrip)
  }

  static async getTripById(id: string): Promise<MakeTrip | undefined> {
    try {
      const raw: any = await api.get(`/trips/${encodeURIComponent(id)}`)
      return mapRawToTrip(raw)
    } catch {
      return undefined
    }
  }

  static async getTripByTeamId(teamId: string): Promise<MakeTrip | undefined> {
    const trips = await FigmaTripService.getAllTrips()
    return trips.find((t) => t.teamId === teamId || t.id === teamId || t.code === teamId)
  }

  static async getTripDetail(tripId: string): Promise<MakeTripDetail | undefined> {
    try {
      const data: any = await api.get(`/trips/${encodeURIComponent(tripId)}`)
      return mapRawToDetail(data)
    } catch {
      return undefined
    }
  }

  static async getTripsPaginated(page: number, pageSize: number) {
    const trips = await FigmaTripService.getAllTrips()
    const total = trips.length
    const totalPages = Math.max(1, Math.ceil(total / pageSize))
    const currentPage = Math.min(Math.max(page, 1), totalPages)
    const start = (currentPage - 1) * pageSize
    return { data: trips.slice(start, start + pageSize), total, totalPages, currentPage }
  }

  // ---- WRITE (real API) ----
  static async createTrip(input: {
    name: string
    teamId: string
    startDate: string
    endDate: string
    participants?: number
    leader?: string
  }): Promise<MakeTrip | undefined> {
    const payload: Record<string, any> = {
      destination: input.name,
      team: input.teamId,
      team_id: input.teamId,
      start_date: input.startDate,
      end_date: input.endDate,
      participants: input.participants ?? 0,
      leader_name: input.leader ?? '',
      status: 'planned',
    }
    const data: any = await api.post('/trips', payload)
    const raw = data?.trip ?? data
    return mapRawToTrip(raw)
  }

  static async updateTrip(t: MakeTrip): Promise<MakeTrip | undefined> {
    const payload: Record<string, any> = {}
    if (t.name) payload.destination = t.name
    if (t.teamId) { payload.team = t.teamId; payload.team_id = t.teamId }
    if (t.startDate) payload.start_date = t.startDate
    if (t.endDate) payload.end_date = t.endDate
    if (t.participants != null) payload.participants = Number(t.participants)
    if (t.leader) payload.leader_name = t.leader
    payload.status = TO_BACKEND_STATUS[t.status] ?? 'planned'
    const data: any = await api.put(`/trips/${encodeURIComponent(t.teamId || t.id)}`, payload)
    const raw = data?.trip ?? data
    return mapRawToTrip(raw ?? t)
  }

  static async deleteTrip(tripId: string): Promise<void> {
    await api.delete(`/trips/${encodeURIComponent(tripId)}`)
  }

  // ---- notification/tourist (stubs) ----
  static async updateNotification(_tid: string, _idx: number, _n: MakeNotificationRule) { return undefined }
  static async deleteNotification(_tid: string, _idx: number) { return undefined }
  static async updateTourist(_tid: string, _idx: number, _t: MakeTourist) { return undefined }
  static async addTourist(_tid: string, _t: MakeTourist) { return undefined }
  static async deleteTourist(_tid: string, _idx: number) { return undefined }
  static async importTouristsFromExcel(_tid: string) { return undefined }

  // ---- local ----
  static async reset(): Promise<void> { /* no-op */ }
  static async getSeedTrips(): Promise<MakeTrip[]> { return FigmaTripService.getAllTrips() }
  static async getStatusColorMap(): Promise<MakeStatusColorMap> { return { ...makeStatusColorMap } }

  static tripSummaryFromDetail(d: MakeTripDetail): MakeTrip {
    const { itinerary: _, tourists: __, notifications: ___, ...trip } = d
    return clone(trip)
  }
}

// ---- weather (real API: /api/weather/xinjiang) ----
export class FigmaWeatherService {
  static async getAllWeather(): Promise<MakeWeatherInfo[]> {
    try {
      const data: any = await api.get('/weather/xinjiang')
      return data?.cities ?? clone(mockWeather)
    } catch {
      return clone(mockWeather)
    }
  }

  static async getWarningCities(): Promise<MakeWeatherInfo[]> {
    const all = await FigmaWeatherService.getAllWeather()
    return all.filter((w) => w.warning !== null)
  }

  static async getWeatherByCity(city: string): Promise<MakeWeatherInfo | undefined> {
    const all = await FigmaWeatherService.getAllWeather()
    return all.find((w) => w.city === city)
  }
}

// ---- analytics (real API) ----
export class FigmaAnalyticsService {
  static async getAnalytics(): Promise<MakeAnalyticsData> {
    try {
      return (await api.get('/analytics/metrics')) as any
    } catch {
      return clone(mockAnalyticsData)
    }
  }
}
