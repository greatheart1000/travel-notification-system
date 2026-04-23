import axios, { AxiosError, type AxiosResponse } from 'axios'
import {
  channelCodeForSend,
  mapDashboardStats,
  mapRawEmergencyWeatherSummary,
  mapRawAnalytics,
  mapRawNotificationRule,
  mapRawNotificationTemplate,
  mapRawRecentNotification,
  mapRawTrip,
  mapRawTripSchedule,
  toNotificationRulePatchPayload,
  toNotificationRuleWritePayload,
  tripStatusLabel,
  toTripWritePayload,
} from '../adapters/apiAdapter'
import {
  clearAuthStorage,
  dispatchAuthStateChanged,
  getAccessToken,
  getRefreshToken,
  setAuthTokens,
} from '../adapters/authAdapter'
import {
  mapRawPreferences,
  toPreferencesPayloadForMe,
  toPreferencesPayloadLegacy,
} from '../adapters/preferencesAdapter'
import {
  type AnalyticsData,
  type ApiEnvelope,
  type ApiErrorBody,
  type ApiErrorDetail,
  type AuthLoginResponse,
  type CreateTemplateInput,
  type CurrentUser,
  type DashboardStats,
  type ChannelCode,
  type CompleteTaskInput,
  type DispatchNowInput,
  type DispatchPreview,
  type DispatchPreviewInput,
  type EmergencyWeatherSummary,
  type NotificationRule,
  type NotificationRuleWriteInput,
  type NotificationTemplate,
  type PreferencesViewModel,
  type ProjectNotificationConfig,
  type RawActionResult,
  type RawAnalyticsResponse,
  type RawDashboardStats,
  type RawDispatchPreview,
  type RawEmergencyWeatherSummary,
  type RawNotificationRule,
  type RawNotificationTemplate,
  type RawTripExecutionDetail,
  type RawTripExecutionRow,
  type RawWorkbenchOverview,
  type RawWorkbenchTask,
  type RawPreferences,
  type RawProjectNotificationConfig,
  type RawRecentNotification,
  type RawTrip,
  type RawTripImportSnapshot,
  type RawTripSchedule,
  type RecentNotification,
  type ActionResult,
  type AssignTakeoverInput,
  type Trip,
  type TripImportSnapshot,
  type TripExecutionDetail,
  type TripExecutionRow,
  type TripImportResult,
  type TripNotificationConfigContext,
  type TripSchedule,
  type TripWriteInput,
  type NudgeTaskInput,
  type RetryDispatchInput,
  type UpsertTripNotificationConfigInput,
  type UpdateTemplateInput,
  type WorkbenchOverview,
  type WorkbenchTask,
} from '../types/api'

const client = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
    'X-Client-Version': '0.1.0',
  },
})

export const api = {
  async get<T>(url: string): Promise<T> {
    const response = await client.get<ApiEnvelope<T>>(url)
    return response.data.data
  },
  async post<T>(url: string, data?: any): Promise<T> {
    const response = await client.post<ApiEnvelope<T>>(url, data)
    return response.data.data
  },
  async put<T>(url: string, data?: any): Promise<T> {
    const response = await client.put<ApiEnvelope<T>>(url, data)
    return response.data.data
  },
  async delete<T>(url: string): Promise<T> {
    const response = await client.delete<ApiEnvelope<T>>(url)
    return response.data.data
  },
}

let refreshRequest: Promise<string | null> | null = null

export class ApiClientError extends Error {
  status: number
  code: number
  requestUrl?: string

  constructor(detail: ApiErrorDetail) {
    super(detail.message)
    this.name = 'ApiClientError'
    this.status = detail.status
    this.code = detail.code
    this.requestUrl = detail.requestUrl
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function normalizeErrorBody(data: unknown): ApiErrorBody {
  if (!isRecord(data)) {
    return {}
  }

  return {
    code: typeof data.code === 'number' ? data.code : undefined,
    error: typeof data.error === 'string' ? data.error : undefined,
    message: typeof data.message === 'string' ? data.message : undefined,
  }
}

function toApiClientError(error: unknown): ApiClientError {
  if (error instanceof ApiClientError) {
    return error
  }

  if (error instanceof AxiosError) {
    const status = error.response?.status ?? 0
    const body = normalizeErrorBody(error.response?.data)
    const message = body.error ?? body.message ?? error.message ?? '请求失败'

    return new ApiClientError({
      status,
      code: body.code ?? status,
      message,
      requestUrl: error.config?.url,
    })
  }

  return new ApiClientError({
    status: 0,
    code: 0,
    message: error instanceof Error ? error.message : '未知错误',
  })
}

export function getErrorMessage(error: unknown): string {
  return toApiClientError(error).message
}

client.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) {
    config.headers = config.headers ?? {}
    ;(config.headers as Record<string, string>).Authorization = `Bearer ${token}`
  }
  return config
})

client.interceptors.response.use(
  (response) => response,
  async (error: unknown) => {
    if (error instanceof AxiosError) {
      const status = error.response?.status ?? 0
      const url = error.config?.url ?? ''
      const originalRequest = error.config

      if (status === 401 && originalRequest && !url.includes('/auth/refresh')) {
        const refreshToken = getRefreshToken()
        if (refreshToken) {
          refreshRequest =
            refreshRequest ??
            client
              .post<ApiEnvelope<AuthLoginResponse>>('/auth/refresh', {
                refresh_token: refreshToken,
              })
              .then((response) => {
                const payload = response.data.data
                setAuthTokens(payload)
                dispatchAuthStateChanged(true)
                return payload.access_token
              })
              .catch(() => {
                clearAuthStorage()
                dispatchAuthStateChanged(false)
                return null
              })
              .finally(() => {
                refreshRequest = null
              })

          const nextAccessToken = await refreshRequest
          if (nextAccessToken) {
            originalRequest.headers = originalRequest.headers ?? {}
            ;(originalRequest.headers as Record<string, string>).Authorization =
              `Bearer ${nextAccessToken}`
            return client.request(originalRequest)
          }
        }
      }
    }

    const normalized = toApiClientError(error)
    if (normalized.status === 401) {
      clearAuthStorage()
      dispatchAuthStateChanged(false)
    }
    return Promise.reject(normalized)
  },
)

async function unwrapData<T>(request: Promise<AxiosResponse<ApiEnvelope<T>>>): Promise<T> {
  const response = await request
  return response.data.data
}

async function unwrapCode(request: Promise<AxiosResponse<{ code: number }>>): Promise<number> {
  const response = await request
  return response.data.code
}

function asArray<T>(value: unknown): T[] {
  return Array.isArray(value) ? (value as T[]) : []
}

function toNumber(value: number | string | undefined, fallback = 0): number {
  const normalized = Number(value)
  return Number.isFinite(normalized) ? normalized : fallback
}

function toActionResult(raw: RawActionResult): ActionResult {
  return {
    ok: Boolean(raw?.ok),
    status: String(raw?.status || 'unknown'),
    message: String(raw?.message || ''),
    taskId: String(raw?.task_id || ''),
    dispatchId: String(raw?.dispatch_id || ''),
  }
}

function mapRawWorkbenchOverview(raw: RawWorkbenchOverview): WorkbenchOverview {
  const now = new Date().toISOString().slice(0, 10)
  return {
    date: String(raw?.date || now),
    timezone: String(raw?.timezone || 'UTC'),
    pendingTasks: toNumber(raw?.pending_tasks),
    overdueTasks: toNumber(raw?.overdue_tasks),
    riskyTrips: toNumber(raw?.risky_trips),
    pendingTakeovers: toNumber(raw?.pending_takeovers),
  }
}

function mapRawWorkbenchTask(raw: RawWorkbenchTask): WorkbenchTask {
  return {
    id: String(raw?.id || ''),
    tripId: String(raw?.trip_id || ''),
    tripName: String(raw?.trip_name || '未命名团'),
    teamId: String(raw?.team_id || ''),
    stage: String(raw?.stage || 'unknown'),
    nodeKey: String(raw?.node_key || ''),
    title: String(raw?.title || '未命名任务'),
    dueAt: String(raw?.due_at || ''),
    ownerRole: String(raw?.owner_role || ''),
    ownerName: String(raw?.owner_name || ''),
    priority: (raw?.priority || 'unknown') as WorkbenchTask['priority'],
    riskLevel: (raw?.risk_level || 'unknown') as WorkbenchTask['riskLevel'],
    status: (raw?.status || 'unknown') as WorkbenchTask['status'],
  }
}

function mapRawTripExecutionRow(raw: RawTripExecutionRow): TripExecutionRow {
  return {
    tripId: String(raw?.trip_id || ''),
    teamId: String(raw?.team_id || ''),
    tripName: String(raw?.trip_name || '未命名团'),
    currentStage: String(raw?.current_stage || 'unknown'),
    todoCount: toNumber(raw?.todo_count),
    totalCount: toNumber(raw?.total_count),
    nextNodeDueAt: String(raw?.next_node_due_at || ''),
    riskLevel: (raw?.risk_level || 'unknown') as TripExecutionRow['riskLevel'],
    dispatchStatus: String(raw?.dispatch_status || 'unknown'),
    ownerName: String(raw?.owner_name || ''),
    overdueMinutes: toNumber(raw?.overdue_minutes),
  }
}

function mapRawTripExecutionDetail(raw: RawTripExecutionDetail): TripExecutionDetail {
  return {
    tripId: String(raw?.trip_id || ''),
    teamId: String(raw?.team_id || ''),
    tripName: String(raw?.trip_name || '未命名团'),
    currentStage: String(raw?.current_stage || 'unknown'),
    todayTotal: toNumber(raw?.today_total),
    todayDone: toNumber(raw?.today_done),
    riskLevel: (raw?.risk_level || 'unknown') as TripExecutionDetail['riskLevel'],
    nextDispatchAt: String(raw?.next_dispatch_at || ''),
    tasks: asArray(raw?.tasks).map((task) => ({
      taskId: String(task?.task_id || ''),
      title: String(task?.title || '未命名任务'),
      stage: String(task?.stage || 'unknown'),
      nodeKey: String(task?.node_key || ''),
      dueAt: String(task?.due_at || ''),
      status: (task?.status || 'unknown') as TripExecutionDetail['tasks'][number]['status'],
      ownerRole: String(task?.owner_role || ''),
      ownerName: String(task?.owner_name || ''),
      evidenceRequired: Boolean(task?.evidence_required),
      dispatchId: String(task?.dispatch_id || ''),
    })),
  }
}

function mapRawDispatchPreview(raw: RawDispatchPreview): DispatchPreview {
  return {
    tripId: String(raw?.trip_id || ''),
    nodeKey: String(raw?.node_key || ''),
    channel: (raw?.channel || 'sms') as ChannelCode,
    templateId: String(raw?.template_id || ''),
    content: String(raw?.content || ''),
    variableCheck: {
      ok: Boolean(raw?.variable_check?.ok),
      missingFields: asArray<string>(raw?.variable_check?.missing_fields),
    },
  }
}

function mapRawTripImportSnapshot(raw: RawTripImportSnapshot): TripImportSnapshot {
  return {
    tripId: String(raw?.trip_id || ''),
    completeness: toNumber(raw?.completeness),
    hasItinerary: Boolean(raw?.has_itinerary),
    hasGuests: Boolean(raw?.has_guests),
    todayTodo: toNumber(raw?.today_todo),
    nextNode: String(raw?.next_node || '待生成通知节点'),
    recognizedFields: asArray(raw?.recognized_fields),
    pendingFields: asArray(raw?.pending_fields),
    missingFields: asArray(raw?.missing_fields),
    itineraryDigest: asArray(raw?.itinerary_digest),
    guestDigest: asArray(raw?.guest_digest),
    pickupDigest: asArray(raw?.pickup_digest),
  }
}

function extractTrip(raw: unknown): RawTrip {
  if (isRecord(raw) && isRecord(raw.trip)) {
    return raw.trip as RawTrip
  }
  return raw as RawTrip
}

function extractTemplate(raw: unknown): RawNotificationTemplate {
  if (isRecord(raw) && isRecord(raw.template)) {
    return raw.template as RawNotificationTemplate
  }
  return raw as RawNotificationTemplate
}

function extractRule(raw: unknown): RawNotificationRule {
  if (isRecord(raw) && isRecord(raw.rule)) {
    return raw.rule as RawNotificationRule
  }
  return raw as RawNotificationRule
}

function toProjectNotificationConfig(
  raw: RawProjectNotificationConfig | undefined,
  fallbackProjectId: string,
): ProjectNotificationConfig {
  return {
    projectId: raw?.project_id || fallbackProjectId,
    projectName: raw?.project_name || '',
    weatherEnabled: Boolean(raw?.weather_enabled ?? true),
    qweatherCredentialId: raw?.qweather_credential_id || '',
    qweatherLocationId: raw?.qweather_location_id || '',
    qweatherLat: raw?.qweather_lat || '',
    qweatherLon: raw?.qweather_lon || '',
    weatherAlertThresholds: raw?.weather_alert_thresholds ?? {},
    smsProvider: raw?.sms_provider || 'aliyun',
    smsSignName: raw?.sms_sign_name || '',
    smsTemplateCodeNormal: raw?.sms_template_code_normal || '',
    smsTemplateCodeWeatherAlert: raw?.sms_template_code_weather_alert || '',
    manualTakeoverTarget: raw?.manual_takeover_target || '',
    updatedAt: String(raw?.updated_at || ''),
  }
}

function toProjectNotificationConfigUpsertPayload(input: UpsertTripNotificationConfigInput): Record<string, unknown> {
  return {
    project_name: input.projectName ?? '',
    weather_enabled: input.weatherEnabled ?? true,
    qweather_credential_id: input.qweatherCredentialId ?? '',
    qweather_location_id: input.qweatherLocationId ?? '',
    qweather_lat: input.qweatherLat ?? '',
    qweather_lon: input.qweatherLon ?? '',
    weather_alert_thresholds: input.weatherAlertThresholds ?? {},
    sms_provider: input.smsProvider ?? 'aliyun',
    sms_sign_name: input.smsSignName ?? '',
    sms_template_code_normal: input.smsTemplateCodeNormal ?? '',
    sms_template_code_weather_alert: input.smsTemplateCodeWeatherAlert ?? '',
    manual_takeover_target: input.manualTakeoverTarget ?? '',
  }
}

const RULE_COLLECTION_ENDPOINTS = [
  '/notifications/rules',
  '/notification-rules',
  '/rules',
  '/trigger-rules',
]

function ruleItemEndpoints(id: string): string[] {
  return RULE_COLLECTION_ENDPOINTS.map((base) => `${base}/${id}`)
}

async function resolveRuleEndpoint<T>(
  resolver: (endpoint: string) => Promise<T>,
  notFoundMessage: string,
): Promise<T> {
  for (const endpoint of RULE_COLLECTION_ENDPOINTS) {
    try {
      return await resolver(endpoint)
    } catch (error) {
      const normalized = toApiClientError(error)
      if (normalized.status === 404) {
        continue
      }
      throw normalized
    }
  }

  throw new ApiClientError({
    status: 404,
    code: 404,
    message: notFoundMessage,
    requestUrl: RULE_COLLECTION_ENDPOINTS.join('|'),
  })
}

async function resolveRuleItemEndpoint<T>(
  id: string,
  resolver: (endpoint: string) => Promise<T>,
  notFoundMessage: string,
): Promise<T> {
  for (const endpoint of ruleItemEndpoints(id)) {
    try {
      return await resolver(endpoint)
    } catch (error) {
      const normalized = toApiClientError(error)
      if (normalized.status === 404) {
        continue
      }
      throw normalized
    }
  }

  throw new ApiClientError({
    status: 404,
    code: 404,
    message: notFoundMessage,
    requestUrl: ruleItemEndpoints(id).join('|'),
  })
}

export const authApi = {
  async login(username: string, password: string): Promise<void> {
    const data = await unwrapData<AuthLoginResponse>(
      client.post('/auth/login', {
        username,
        password,
      }),
    )
    setAuthTokens(data)
    dispatchAuthStateChanged(true)
  },

  async logout(): Promise<void> {
    try {
      await unwrapCode(client.post('/auth/logout'))
    } finally {
      clearAuthStorage()
      dispatchAuthStateChanged(false)
    }
  },

  async refresh(refreshToken: string): Promise<AuthLoginResponse> {
    const data = await unwrapData<AuthLoginResponse>(
      client.post('/auth/refresh', {
        refresh_token: refreshToken,
      }),
    )
    setAuthTokens(data)
    return data
  },

  async me(): Promise<CurrentUser> {
    return unwrapData<CurrentUser>(client.get('/users/me'))
  },
}

export interface SmartSuggestion {
  id: string
  tripId: string
  tripName: string
  type: string
  title: string
  reason: string
  suggestedContent: string
  targetCount: number
  channel: ChannelCode
}

export const dashboardApi = {
  async getWorkbenchOverview(params?: { date?: string; ownerScope?: 'mine' | 'all' }): Promise<WorkbenchOverview> {
    const raw = await unwrapData<RawWorkbenchOverview>(
      client.get('/workbench/today/overview', {
        params: {
          date: params?.date,
          owner_scope: params?.ownerScope,
        },
      }),
    )
    return mapRawWorkbenchOverview(raw)
  },

  async getWorkbenchActionItems(params?: { limit?: number; ownerScope?: 'mine' | 'all' }): Promise<WorkbenchTask[]> {
    const raw = await unwrapData<{ items?: RawWorkbenchTask[] } | RawWorkbenchTask[]>(
      client.get('/workbench/today/action-items', {
        params: {
          limit: params?.limit,
          owner_scope: params?.ownerScope,
        },
      }),
    )
    const items = Array.isArray(raw) ? raw : asArray<RawWorkbenchTask>(raw.items)
    return items.map((item) => mapRawWorkbenchTask(item))
  },

  async getSmartSuggestions(): Promise<SmartSuggestion[]> {
    const raw = await unwrapData<{ items: SmartSuggestion[] }>(client.get('/dashboard/smart-suggestions'))
    return raw.items
  },

  async getStats(): Promise<DashboardStats> {
    const raw = await unwrapData<RawDashboardStats>(client.get('/dashboard/stats'))
    return mapDashboardStats(raw)
  },

  async getRecentNotifications(limit = 10): Promise<RecentNotification[]> {
    const raw = await unwrapData<{ total?: number; items?: RawRecentNotification[] } | RawRecentNotification[]>(
      client.get(`/notifications/recent?limit=${limit}`),
    )
    const items = Array.isArray(raw) ? raw : asArray<RawRecentNotification>(raw.items)
    return items.map((item) => mapRawRecentNotification(item))
  },
}

export const tripsApi = {
  async listExecutionRows(params?: {
    ownerScope?: 'mine' | 'all'
    stage?: string
    riskLevel?: string
    date?: string
  }): Promise<TripExecutionRow[]> {
    const raw = await unwrapData<{ items?: RawTripExecutionRow[] } | RawTripExecutionRow[]>(
      client.get('/trips/execution', {
        params: {
          owner_scope: params?.ownerScope,
          stage: params?.stage,
          risk_level: params?.riskLevel,
          date: params?.date,
        },
      }),
    )
    const items = Array.isArray(raw) ? raw : asArray<RawTripExecutionRow>(raw.items)
    return items.map((item) => mapRawTripExecutionRow(item))
  },

  async getExecutionDetail(id: string): Promise<TripExecutionDetail> {
    const raw = await unwrapData<RawTripExecutionDetail>(client.get(`/trips/${id}/execution`))
    return mapRawTripExecutionDetail(raw)
  },

  async list(): Promise<Trip[]> {
    const raw = await unwrapData<{ total?: number; items?: RawTrip[] } | RawTrip[]>(client.get('/trips'))
    const items = Array.isArray(raw) ? raw : asArray<RawTrip>(raw.items)
    return items.map((item) => mapRawTrip(item))
  },

  async get(id: string): Promise<Trip> {
    const raw = await unwrapData<RawTrip | { trip: RawTrip }>(client.get(`/trips/${id}`))
    return mapRawTrip(extractTrip(raw))
  },

  async getSchedule(id: string): Promise<TripSchedule> {
    const raw = await unwrapData<RawTripSchedule>(client.get(`/trips/${id}/schedule`))
    return mapRawTripSchedule(raw)
  },

  async create(input: TripWriteInput): Promise<Trip> {
    const payload = toTripWritePayload(input)
    const raw = await unwrapData<RawTrip | { trip: RawTrip }>(client.post('/trips', payload))
    return mapRawTrip(extractTrip(raw))
  },

  async update(id: string, input: Partial<TripWriteInput>): Promise<Trip> {
    const payload: Record<string, unknown> = {}

    if (input.destination !== undefined) {
      payload.destination = input.destination
    }
    if (input.teamId !== undefined) {
      payload.team = input.teamId
      payload.team_id = input.teamId
    }
    if (input.startDate !== undefined) {
      payload.start_date = input.startDate
    }
    if (input.endDate !== undefined) {
      payload.end_date = input.endDate
    }
    if (input.participants !== undefined) {
      payload.participants = input.participants
    }
    if (input.status !== undefined) {
      payload.status = tripStatusLabel(input.status)
    }
    if (input.leaderName !== undefined) {
      payload.leader_name = input.leaderName
    }
    if (input.contactPhone !== undefined) {
      payload.contact_phone = input.contactPhone
    }
    if (input.itinerary !== undefined) {
      payload.itinerary = input.itinerary
    }
    if (input.guests !== undefined) {
      payload.guests = input.guests
    }

    const raw = await unwrapData<RawTrip | { trip: RawTrip }>(client.put(`/trips/${id}`, payload))
    return mapRawTrip(extractTrip(raw))
  },

  async remove(id: string): Promise<void> {
    await unwrapCode(client.delete(`/trips/${id}`))
  },

  async exportPdf(id: string, tripName: string): Promise<void> {
    const response = await client.get(`/trips/${id}/export-pdf`, {
      responseType: 'blob',
      headers: {
        Accept: 'application/pdf',
      }
    })

    const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `行程名单_${tripName}.pdf`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  },

  async importFile(file: File): Promise<TripImportResult> {
    const formData = new FormData()
    formData.append('file', file)
    const response = await client.post<ApiEnvelope<{ created_count?: number; skipped_count?: number }>>(
      '/trips/import',
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
      },
    )
    return {
      createdCount: response.data.data.created_count ?? 0,
      skippedCount: response.data.data.skipped_count ?? 0,
    }
  },

  async getImportSnapshot(id: string): Promise<TripImportSnapshot> {
    const raw = await unwrapData<RawTripImportSnapshot>(client.get(`/trips/${id}/import-snapshot`))
    return mapRawTripImportSnapshot(raw)
  },

  async applyImportValidation(id: string, fields: Record<string, string>): Promise<TripImportSnapshot> {
    const raw = await unwrapData<{ snapshot?: RawTripImportSnapshot }>(
      client.put(`/trips/${id}/import-validation`, { fields }),
    )
    return mapRawTripImportSnapshot(raw.snapshot || {})
  },
}

export const notificationsApi = {
  async previewDispatch(input: DispatchPreviewInput): Promise<DispatchPreview> {
    const raw = await unwrapData<RawDispatchPreview>(
      client.post('/notifications/dispatch/preview', {
        trip_id: input.tripId,
        node_key: input.nodeKey,
        channel: channelCodeForSend(input.channel),
        channel_code: input.channel,
        template_id: input.templateId,
      }),
    )
    return mapRawDispatchPreview(raw)
  },

  async dispatchNow(input: DispatchNowInput): Promise<ActionResult> {
    const raw = await unwrapData<RawActionResult>(
      client.post('/notifications/dispatch', {
        trip_id: input.tripId,
        node_key: input.nodeKey,
        channel: channelCodeForSend(input.channel),
        channel_code: input.channel,
        content: input.content,
        template_id: input.templateId,
      }),
    )
    return toActionResult(raw)
  },

  async retryDispatch(input: RetryDispatchInput): Promise<ActionResult> {
    const raw = await unwrapData<RawActionResult>(
      client.post(`/notifications/dispatch/${encodeURIComponent(input.dispatchId)}/retry`, {
        reason: input.reason,
      }),
    )
    return toActionResult(raw)
  },

  async assignTakeover(input: AssignTakeoverInput): Promise<ActionResult> {
    const raw = await unwrapData<RawActionResult>(
      client.post('/workbench/takeovers', {
        task_id: input.taskId,
        assignee_user_id: input.assigneeUserId,
        assignee_name: input.assigneeName,
        deadline_at: input.deadlineAt,
        note: input.note,
      }),
    )
    return toActionResult(raw)
  },

  async completeTask(input: CompleteTaskInput): Promise<ActionResult> {
    const raw = await unwrapData<RawActionResult>(
      client.post(`/workbench/tasks/${encodeURIComponent(input.taskId)}/complete`, {
        result_note: input.resultNote,
        evidence_type: input.evidenceType,
        evidence_ref: input.evidenceRef,
      }),
    )
    return toActionResult(raw)
  },

  async nudgeTask(input: NudgeTaskInput): Promise<ActionResult> {
    const raw = await unwrapData<RawActionResult>(
      client.post(`/workbench/tasks/${encodeURIComponent(input.taskId)}/nudge`, {
        target_role: input.targetRole,
        message: input.message,
      }),
    )
    return toActionResult(raw)
  },

  async getTripConfigContextByTripId(tripId: string): Promise<TripNotificationConfigContext> {
    const raw = await unwrapData<RawProjectNotificationConfig>(
      client.get(`/trips/${encodeURIComponent(tripId)}/notification-config`),
    )
    const trip = await tripsApi.get(tripId)
    const fallbackProjectId = trip.teamId || trip.id
    return {
      trip,
      projectConfig: toProjectNotificationConfig(raw, fallbackProjectId),
    }
  },

  async getTripConfigContext(tripId: string): Promise<TripNotificationConfigContext> {
    const trip = await tripsApi.get(tripId)
    const projectId = trip.teamId || trip.id

    let projectConfigRaw: RawProjectNotificationConfig | null = null
    try {
      projectConfigRaw = await unwrapData<RawProjectNotificationConfig>(
        client.get(`/project-configs/${encodeURIComponent(projectId)}`),
      )
    } catch (error) {
      const normalized = toApiClientError(error)
      if (normalized.status !== 404) {
        throw normalized
      }
    }

    return {
      trip,
      projectConfig: toProjectNotificationConfig(projectConfigRaw ?? undefined, projectId),
    }
  },

  async upsertTripNotificationConfig(
    projectId: string,
    input: UpsertTripNotificationConfigInput,
  ): Promise<ProjectNotificationConfig> {
    const payload = toProjectNotificationConfigUpsertPayload(input)
    const raw = await unwrapData<RawProjectNotificationConfig>(
      client.put(`/project-configs/${encodeURIComponent(projectId)}`, payload),
    )
    return toProjectNotificationConfig(raw, projectId)
  },

  async upsertTripNotificationConfigByTripId(
    tripId: string,
    input: UpsertTripNotificationConfigInput,
  ): Promise<ProjectNotificationConfig> {
    const payload = toProjectNotificationConfigUpsertPayload(input)
    const raw = await unwrapData<RawProjectNotificationConfig>(
      client.put(`/trips/${encodeURIComponent(tripId)}/notification-config`, payload),
    )
    return toProjectNotificationConfig(raw, tripId)
  },

  async getEmergencyWeatherSummary(): Promise<EmergencyWeatherSummary> {
    const raw = await unwrapData<RawEmergencyWeatherSummary>(client.get('/notifications/emergency-weather'))
    return mapRawEmergencyWeatherSummary(raw)
  },

  async sendEmergencyWeather(payload: {
    alertId: string
    customContent?: string
    channel: ChannelCode
  }): Promise<{ ok: boolean; notificationId?: string; sentCount: number; status: string }> {
    const raw = await unwrapData<{
      ok?: boolean
      notification_id?: string
      sent_count?: number
      status?: string
    }>(
      client.post('/notifications/emergency-weather/send', {
        alert_id: payload.alertId,
        custom_content: payload.customContent,
        channel: channelCodeForSend(payload.channel),
      }),
    )

    return {
      ok: Boolean(raw.ok),
      notificationId: raw.notification_id,
      sentCount: Number(raw.sent_count ?? 0),
      status: raw.status ?? 'unknown',
    }
  },

  async listTemplates(): Promise<NotificationTemplate[]> {
    const raw = await unwrapData<{ total?: number; items?: RawNotificationTemplate[] } | RawNotificationTemplate[]>(
      client.get('/notifications/templates'),
    )
    const items = Array.isArray(raw) ? raw : asArray<RawNotificationTemplate>(raw.items)
    return items.map((item) => mapRawNotificationTemplate(item))
  },

  async send(payload: {
    templateId?: string
    customContent?: string
    channel: ChannelCode
    customerName?: string
    customerPhone?: string
    trip?: string
  }): Promise<{ ok: boolean; notificationId?: string }> {
    const raw = await unwrapData<{ ok?: boolean; notification_id?: string }>(
      client.post('/notifications/send', {
        template_id: payload.templateId,
        custom_content: payload.customContent,
        channel: channelCodeForSend(payload.channel),
        channel_code: payload.channel,
        customer_name: payload.customerName,
        customer_phone: payload.customerPhone,
        trip: payload.trip,
      }),
    )

    return {
      ok: Boolean(raw.ok),
      notificationId: raw.notification_id,
    }
  },

  async createTemplate(input: CreateTemplateInput): Promise<NotificationTemplate> {
    const payloadPrimary = {
      name: input.name,
      template: input.template,
      content: input.template,
      channel: channelCodeForSend(input.channel),
      channel_code: input.channel,
    }

    try {
      const raw = await unwrapData<RawNotificationTemplate | { template: RawNotificationTemplate }>(
        client.post('/notifications/templates', payloadPrimary),
      )
      return mapRawNotificationTemplate(extractTemplate(raw))
    } catch (error) {
      const normalized = toApiClientError(error)
      if (normalized.status !== 404) {
        throw normalized
      }
    }

    const payloadFallback = {
      name: input.name,
      content: input.template,
      channel: input.channel,
      notification_type: 'daily_reminder',
      is_active: true,
    }

    try {
      const raw = await unwrapData<RawNotificationTemplate | { template: RawNotificationTemplate }>(
        client.post('/templates', payloadFallback),
      )
      return mapRawNotificationTemplate(extractTemplate(raw))
    } catch (error) {
      const normalized = toApiClientError(error)
      if (normalized.status === 404) {
        throw new ApiClientError({
          status: 404,
          code: 404,
          message: '后端未开放模板创建接口',
          requestUrl: '/notifications/templates|/templates',
        })
      }
      throw normalized
    }
  },

  async updateTemplate(id: string, input: UpdateTemplateInput): Promise<NotificationTemplate> {
    const payload = {
      name: input.name,
      content: input.template,
      channel: input.channel ? channelCodeForSend(input.channel) : undefined,
      is_active: input.enabled,
    }
    const raw = await unwrapData<RawNotificationTemplate | { template: RawNotificationTemplate }>(
      client.put(`/notifications/templates/${id}`, payload),
    )
    return mapRawNotificationTemplate(extractTemplate(raw))
  },

  async deleteTemplate(id: string): Promise<void> {
    await unwrapCode(client.delete(`/notifications/templates/${id}`))
  },

  async listRules(): Promise<NotificationRule[]> {
    return resolveRuleEndpoint(async (endpoint) => {
      const raw = await unwrapData<{ total?: number; items?: RawNotificationRule[] } | RawNotificationRule[]>(
        client.get(endpoint),
      )
      const items = Array.isArray(raw) ? raw : asArray<RawNotificationRule>(raw.items)
      return items.map((item) => mapRawNotificationRule(item))
    }, '后端未开放通知规则查询接口')
  },

  async createRule(input: NotificationRuleWriteInput): Promise<NotificationRule> {
    const payload = toNotificationRuleWritePayload(input)
    return resolveRuleEndpoint(async (endpoint) => {
      const raw = await unwrapData<RawNotificationRule | { rule: RawNotificationRule }>(
        client.post(endpoint, payload),
      )
      return mapRawNotificationRule(extractRule(raw))
    }, '后端未开放通知规则创建接口')
  },

  async updateRule(id: string, input: Partial<NotificationRuleWriteInput>): Promise<NotificationRule> {
    const payload = toNotificationRulePatchPayload(input)
    return resolveRuleItemEndpoint(
      id,
      async (endpoint) => {
        const raw = await unwrapData<RawNotificationRule | { rule: RawNotificationRule }>(
          client.put(endpoint, payload),
        )
        return mapRawNotificationRule(extractRule(raw))
      },
      '后端未开放通知规则更新接口',
    )
  },

  async deleteRule(id: string): Promise<void> {
    await resolveRuleItemEndpoint(
      id,
      async (endpoint) => {
        await unwrapCode(client.delete(endpoint))
      },
      '后端未开放通知规则删除接口',
    )
  },

  async toggleRule(id: string, enabled: boolean): Promise<NotificationRule> {
    try {
      return await resolveRuleItemEndpoint(
        id,
        async (endpoint) => {
          const raw = await unwrapData<RawNotificationRule | { rule: RawNotificationRule }>(
            client.patch(endpoint, { enabled, is_enabled: enabled }),
          )
          return mapRawNotificationRule(extractRule(raw))
        },
        '后端未开放通知规则启停接口',
      )
    } catch (error) {
      const normalized = toApiClientError(error)
      if (normalized.status !== 404 && normalized.status !== 405) {
        throw normalized
      }
    }

    return resolveRuleItemEndpoint(
      id,
      async (endpoint) => {
        const raw = await unwrapData<RawNotificationRule | { rule: RawNotificationRule }>(
          client.put(endpoint, { enabled, is_enabled: enabled }),
        )
        return mapRawNotificationRule(extractRule(raw))
      },
      '后端未开放通知规则启停接口',
    )
  },
}

export const analyticsApi = {
  async metrics(): Promise<AnalyticsData> {
    const raw = await unwrapData<RawAnalyticsResponse>(client.get('/analytics/metrics'))
    return mapRawAnalytics(raw)
  },
}

async function readPreferencesByMeEndpoint(): Promise<PreferencesViewModel> {
  const raw = await unwrapData<RawPreferences>(client.get('/preferences/me'))
  return mapRawPreferences(raw)
}

async function readPreferencesByLegacyEndpoint(): Promise<PreferencesViewModel> {
  const raw = await unwrapData<RawPreferences>(client.get('/preferences'))
  return mapRawPreferences(raw)
}

async function updatePreferencesByMeEndpoint(data: PreferencesViewModel): Promise<PreferencesViewModel> {
  const raw = await unwrapData<RawPreferences>(
    client.put('/preferences/me', toPreferencesPayloadForMe(data)),
  )
  return mapRawPreferences(raw)
}

async function updatePreferencesByLegacyEndpoint(data: PreferencesViewModel): Promise<PreferencesViewModel> {
  const raw = await unwrapData<RawPreferences>(
    client.put('/preferences', toPreferencesPayloadLegacy(data)),
  )
  return mapRawPreferences(raw)
}

export const preferencesApi = {
  async get(): Promise<PreferencesViewModel> {
    try {
      return await readPreferencesByMeEndpoint()
    } catch (error) {
      const normalized = toApiClientError(error)
      if (normalized.status === 404) {
        return readPreferencesByLegacyEndpoint()
      }
      throw normalized
    }
  },

  async update(data: PreferencesViewModel): Promise<PreferencesViewModel> {
    try {
      return await updatePreferencesByMeEndpoint(data)
    } catch (error) {
      const normalized = toApiClientError(error)
      if (normalized.status === 404) {
        return updatePreferencesByLegacyEndpoint(data)
      }
      throw normalized
    }
  },
}
