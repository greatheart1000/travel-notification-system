export type ChannelCode = 'sms' | 'wechat_work_group' | 'email'

export type TripStatusCode = 'planned' | 'in_progress' | 'completed' | 'cancelled' | 'unknown'

export type NotificationStatusCode =
  | 'sent'
  | 'failed'
  | 'retrying'
  | 'skipped'
  | 'manual_intervention'
  | 'enabled'
  | 'disabled'
  | 'unknown'

export interface ApiEnvelope<T> {
  code: number
  data: T
}

export interface ApiErrorBody {
  code?: number
  error?: string
  message?: string
}

export interface ApiErrorDetail {
  status: number
  code: number
  message: string
  requestUrl?: string
}

export interface AuthLoginResponse {
  access_token: string
  refresh_token?: string
  token_type?: string
  expires_in?: number
}

export interface CurrentUser {
  id: string
  username: string
  email: string
  role: string
  created_at: string
}

export interface RawDashboardStats {
  today_notifications?: number
  active_trips?: number
  total_travelers?: number
  total_users?: number
  pending_notifications?: number
  pending_complaints?: number
  notification_success_rate?: number
  avg_response_time_ms?: number | string
  channel_growth_rate?: number | string
}

export interface DashboardStats {
  todayNotifications: number
  activeTrips: number
  totalTravelers: number
  totalUsers: number
  pendingNotifications: number
  pendingComplaints: number
  notificationSuccessRate: number
  avgResponseTimeMs: number
  channelGrowthRate: number
}

export interface RawTrip {
  id?: string
  destination?: string
  team?: string
  team_id?: string
  start_date?: string
  end_date?: string
  participants?: number | string
  status?: string
  leader_name?: string
  contact_phone?: string
  itinerary?: RawItineraryItem[]
  guests?: RawGuest[]
}

export interface RawTripSchedule {
  trip_id?: string
  team_id?: string
  destination?: string
  start_date?: string
  end_date?: string
  traveler_count?: number | string
  status?: {
    code?: string
    label?: string
  }
  leader?: RawTripContact
  contact?: RawTripContact
  route_summary?: string[]
  days?: RawTripScheduleDay[]
  notification_summary?: RawTripNotificationSummary
}

export interface RawTripContact {
  name?: string
  phone?: string
  notes?: string
}

export interface RawTripScheduleDay {
  day?: number | string
  title?: string
  date?: string
  route?: string
  segments?: RawTripScheduleSegment[]
  hotel?: string
  transport?: string
}

export interface RawTripScheduleSegment {
  departure_time?: string
  arrival_time?: string
  from?: string
  to?: string
  transport?: string
  sightseeing?: string
  hotel?: string
  meal_plan?: string
}

export interface RawTripNotificationSummary {
  recent_count?: number | string
  latest?: Record<string, unknown> | null
  next_hint?: string
}

export interface RawItineraryItem {
  date: string
  transport: string
  route: string
  hotel: string
}

export interface RawGuest {
  name: string
  phone: string
  notes: string
}

export interface Trip {
  id: string
  destination: string
  teamId: string
  startDate: string
  endDate: string
  participants: number
  status: TripStatusCode
  statusLabel: string
  leaderName?: string
  contactPhone?: string
  itinerary: ItineraryItem[]
  guests: Guest[]
}

export interface TripSchedule {
  tripId: string
  teamId: string
  destination: string
  startDate: string
  endDate: string
  travelerCount: number
  status: {
    code: TripStatusCode
    label: string
  }
  leader: TripContact
  contact: TripContact
  routeSummary: string[]
  days: TripScheduleDay[]
  notificationSummary: TripNotificationSummary
}

export interface TripContact {
  name: string
  phone: string
  notes: string
}

export interface TripScheduleDay {
  day: number
  title: string
  date: string
  route: string
  segments: TripScheduleSegment[]
  hotel: string
  transport: string
}

export interface TripScheduleSegment {
  departureTime: string
  arrivalTime: string
  from: string
  to: string
  transport: string
  sightseeing: string
  hotel: string
  mealPlan: string
}

export interface TripNotificationSummary {
  recentCount: number
  latest: Record<string, unknown> | null
  nextHint: string
}

export interface ItineraryItem {
  date: string
  transport: string
  route: string
  hotel: string
}

export interface Guest {
  name: string
  phone: string
  notes: string
}

export interface TripWriteInput {
  destination: string
  teamId: string
  startDate: string
  endDate: string
  participants?: number
  status?: TripStatusCode
  leaderName?: string
  contactPhone?: string
  itinerary?: ItineraryItem[]
  guests?: Guest[]
}

export interface TripImportResult {
  createdCount: number
  skippedCount: number
}

export interface RawNotificationTemplate {
  id?: string
  name?: string
  template?: string
  content?: string
  channel?: string
  status?: string
  status_code?: string
  enabled?: boolean
  is_active?: boolean
  sent_count?: number | string
  success_rate?: string | number
}

export interface NotificationTemplate {
  id: string
  name: string
  template: string
  channel: ChannelCode
  channelLabel: string
  status: NotificationStatusCode
  statusLabel: string
  enabled: boolean
  sentCount: number
  successRate: string
}

export interface CreateTemplateInput {
  name: string
  template: string
  channel: ChannelCode
}

export interface UpdateTemplateInput {
  name?: string
  template?: string
  channel?: ChannelCode
  enabled?: boolean
}

export type NotificationRuleStageCode = 'pre_trip' | 'on_trip' | 'post_trip' | 'custom' | 'unknown'
export type NotificationRuleTimeSlotCode = 'morning' | 'afternoon' | 'evening' | 'night' | 'all_day' | 'unknown'

export interface RawNotificationRule {
  id?: string
  name?: string
  rule_name?: string
  title?: string
  stage?: string
  time_slot?: string
  timeSlot?: string
  scene?: string
  enabled?: boolean
  is_enabled?: boolean
  isEnabled?: boolean
  priority?: number | string
  template_id?: string
  templateId?: string
  template?: string
  template_name?: string
}

export interface NotificationRule {
  id: string
  name: string
  stage: NotificationRuleStageCode
  stageLabel: string
  timeSlot: NotificationRuleTimeSlotCode
  timeSlotLabel: string
  scene: string
  enabled: boolean
  priority: number
  templateId: string
  templateLabel: string
}

export interface NotificationRuleWriteInput {
  name: string
  stage: NotificationRuleStageCode
  timeSlot: NotificationRuleTimeSlotCode
  scene: string
  enabled: boolean
  priority: number
  templateId: string
}

export interface RawProjectNotificationConfig {
  tenant_id?: string
  project_id?: string
  project_name?: string
  weather_enabled?: boolean
  qweather_credential_id?: string
  qweather_location_id?: string
  qweather_lat?: string
  qweather_lon?: string
  weather_alert_thresholds?: Record<string, unknown>
  sms_provider?: string
  sms_sign_name?: string
  sms_template_code_normal?: string
  sms_template_code_weather_alert?: string
  manual_takeover_target?: string
  created_at?: string
  updated_at?: string
}

export interface ProjectNotificationConfig {
  projectId: string
  projectName: string
  weatherEnabled: boolean
  qweatherCredentialId: string
  qweatherLocationId: string
  qweatherLat: string
  qweatherLon: string
  weatherAlertThresholds: Record<string, unknown>
  smsProvider: string
  smsSignName: string
  smsTemplateCodeNormal: string
  smsTemplateCodeWeatherAlert: string
  manualTakeoverTarget: string
  updatedAt: string
}

export interface UpsertTripNotificationConfigInput {
  projectName?: string
  weatherEnabled?: boolean
  qweatherCredentialId?: string
  qweatherLocationId?: string
  qweatherLat?: string
  qweatherLon?: string
  weatherAlertThresholds?: Record<string, unknown>
  smsProvider?: string
  smsSignName?: string
  smsTemplateCodeNormal?: string
  smsTemplateCodeWeatherAlert?: string
  manualTakeoverTarget?: string
}

export interface TripNotificationConfigContext {
  trip: Trip
  projectConfig: ProjectNotificationConfig
}

export interface RawEmergencyWeatherAffectedTrip {
  trip_id?: string
  team_id?: string
  destination?: string
  status?: string
  status_label?: string
  traveler_count?: number | string
  summary?: string
}

export interface RawEmergencyWeatherSummary {
  alert_id?: string
  title?: string
  risk_level?: string
  risk_level_label?: string
  risk_level_badge?: string
  updated_at?: string
  weather_summary?: string
  ai_risk_summary?: string
  affected_trip_count?: number | string
  affected_trips?: RawEmergencyWeatherAffectedTrip[]
  generated_notification?: string
  channel?: string
  requires_confirmation?: boolean
}

export interface EmergencyWeatherAffectedTrip {
  tripId: string
  teamId: string
  destination: string
  status: string
  statusLabel: string
  travelerCount: number
  summary: string
}

export interface EmergencyWeatherSummary {
  alertId: string
  title: string
  riskLevel: string
  riskLevelLabel: string
  riskLevelBadge: 'default' | 'success' | 'warning' | 'danger' | 'info'
  updatedAt: string
  weatherSummary: string
  aiRiskSummary: string
  affectedTripCount: number
  affectedTrips: EmergencyWeatherAffectedTrip[]
  generatedNotification: string
  channel: ChannelCode
  channelLabel: string
  requiresConfirmation: boolean
}

export interface RawRecentNotification {
  id?: string
  customer_name?: string
  trip?: string
  channel?: string
  status?: string
  created_at?: string
}

export interface RecentNotification {
  id: string
  customerName: string
  trip: string
  channel: ChannelCode
  channelLabel: string
  status: NotificationStatusCode
  statusLabel: string
  createdAt: string
}

export interface RawAnalyticsResponse {
  metrics?: {
    notification_success_rate?: string | number
    avg_response_time?: string | number
    wow_growth?: string | number
    user_satisfaction?: string | number
  }
  channel_performance?: Array<{
    name?: string
    channel?: string
    sent?: number
    successful?: number
    failed?: number
    rate?: string | number
    success_rate?: string | number
  }>
  top_trips?: Array<{
    name?: string
    notifications?: number
    satisfaction?: number
  }>
}

export interface AnalyticsMetrics {
  notificationSuccessRate: string
  avgResponseTime: string
  wowGrowth: string
  userSatisfaction: string
}

export interface AnalyticsChannelPerformance {
  channel: ChannelCode
  channelLabel: string
  sent: number
  successful: number
  failed: number
  rate: string
}

export interface AnalyticsTopTrip {
  name: string
  notifications: number
  satisfaction: number
}

export interface AnalyticsData {
  metrics: AnalyticsMetrics
  channelPerformance: AnalyticsChannelPerformance[]
  topTrips: AnalyticsTopTrip[]
}

export type QuietHoursRaw =
  | {
      start: string | number
      end: string | number
    }
  | [number, number]

export interface RawPreferences {
  user_id?: string
  channels?: string[]
  quiet_hours?: QuietHoursRaw
  max_notifications_per_hour?: number
  auto_escalation?: boolean
  aggregate_notifications?: boolean
  allow_marketing?: boolean
}

export interface PreferencesViewModel {
  smsEnabled: boolean
  wechatEnabled: boolean
  emailEnabled: boolean
  quietHourStart: string
  quietHourEnd: string
  maxNotificationsPerHour: number
  autoEscalation: boolean
  aggregateNotifications: boolean
  allowMarketing: boolean
}

export interface PreferencesWritePayloadForMe {
  channels: string[]
  quiet_hours: [number, number]
  max_notifications_per_hour: number
  auto_escalation: boolean
  aggregate_notifications: boolean
  allow_marketing: boolean
}

export interface PreferencesWritePayloadLegacy {
  channels: string[]
  quiet_hours: {
    start: string
    end: string
  }
  max_notifications_per_hour: number
  auto_escalation: boolean
  aggregate_notifications: boolean
}

export interface PageLoadError {
  message: string
  detail?: string
}
