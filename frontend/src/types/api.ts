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

export interface TripImportSnapshotField {
  key: string
  label: string
  value: string
}

export interface TripImportMissingField {
  key: string
  label: string
}

export interface TripImportItineraryDigest {
  date: string
  transport: string
  route: string
  hotel: string
  meal: string
}

export interface TripImportGuestDigest {
  name: string
  phone: string
  status: string
}

export interface TripImportPickupDigest {
  type: '接' | '送'
  date: string
  location: string
  shift: string
  note: string
}

export interface RawTripImportSnapshot {
  trip_id?: string
  completeness?: number | string
  has_itinerary?: boolean
  has_guests?: boolean
  today_todo?: number | string
  next_node?: string
  recognized_fields?: TripImportSnapshotField[]
  pending_fields?: TripImportSnapshotField[]
  missing_fields?: TripImportMissingField[]
  itinerary_digest?: TripImportItineraryDigest[]
  guest_digest?: TripImportGuestDigest[]
  pickup_digest?: TripImportPickupDigest[]
}

export interface TripImportSnapshot {
  tripId: string
  completeness: number
  hasItinerary: boolean
  hasGuests: boolean
  todayTodo: number
  nextNode: string
  recognizedFields: TripImportSnapshotField[]
  pendingFields: TripImportSnapshotField[]
  missingFields: TripImportMissingField[]
  itineraryDigest: TripImportItineraryDigest[]
  guestDigest: TripImportGuestDigest[]
  pickupDigest: TripImportPickupDigest[]
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

export type WorkbenchRiskLevel = 'low' | 'medium' | 'high' | 'critical' | 'unknown'
export type WorkbenchPriority = 'p0' | 'p1' | 'p2' | 'unknown'
export type WorkbenchTaskStatus =
  | 'todo'
  | 'in_progress'
  | 'blocked'
  | 'overdue'
  | 'done'
  | 'handover_in_progress'
  | 'unknown'

export interface RawWorkbenchOverview {
  date?: string
  timezone?: string
  pending_tasks?: number | string
  overdue_tasks?: number | string
  risky_trips?: number | string
  pending_takeovers?: number | string
}

export interface WorkbenchOverview {
  date: string
  timezone: string
  pendingTasks: number
  overdueTasks: number
  riskyTrips: number
  pendingTakeovers: number
}

export interface RawWorkbenchTask {
  id?: string
  trip_id?: string
  trip_name?: string
  team_id?: string
  stage?: string
  node_key?: string
  title?: string
  due_at?: string
  owner_role?: string
  owner_name?: string
  priority?: string
  risk_level?: string
  status?: string
}

export interface WorkbenchTask {
  id: string
  tripId: string
  tripName: string
  teamId: string
  stage: string
  nodeKey: string
  title: string
  dueAt: string
  ownerRole: string
  ownerName: string
  priority: WorkbenchPriority
  riskLevel: WorkbenchRiskLevel
  status: WorkbenchTaskStatus
}

export interface RawTripExecutionRow {
  trip_id?: string
  team_id?: string
  trip_name?: string
  current_stage?: string
  todo_count?: number | string
  total_count?: number | string
  next_node_due_at?: string
  risk_level?: string
  dispatch_status?: string
  owner_name?: string
  overdue_minutes?: number | string
}

export interface TripExecutionRow {
  tripId: string
  teamId: string
  tripName: string
  currentStage: string
  todoCount: number
  totalCount: number
  nextNodeDueAt: string
  riskLevel: WorkbenchRiskLevel
  dispatchStatus: string
  ownerName: string
  overdueMinutes: number
}

export interface RawExecutionTask {
  task_id?: string
  title?: string
  stage?: string
  node_key?: string
  due_at?: string
  status?: string
  owner_role?: string
  owner_name?: string
  evidence_required?: boolean
  dispatch_id?: string
}

export interface ExecutionTask {
  taskId: string
  title: string
  stage: string
  nodeKey: string
  dueAt: string
  status: WorkbenchTaskStatus
  ownerRole: string
  ownerName: string
  evidenceRequired: boolean
  dispatchId: string
}

export interface RawTripExecutionDetail {
  trip_id?: string
  team_id?: string
  trip_name?: string
  current_stage?: string
  today_total?: number | string
  today_done?: number | string
  risk_level?: string
  next_dispatch_at?: string
  tasks?: RawExecutionTask[]
}

export interface TripExecutionDetail {
  tripId: string
  teamId: string
  tripName: string
  currentStage: string
  todayTotal: number
  todayDone: number
  riskLevel: WorkbenchRiskLevel
  nextDispatchAt: string
  tasks: ExecutionTask[]
}

export interface DispatchPreviewInput {
  tripId: string
  nodeKey: string
  channel: ChannelCode
  templateId?: string
}

export interface RawDispatchPreview {
  trip_id?: string
  node_key?: string
  channel?: string
  template_id?: string
  content?: string
  variable_check?: {
    ok?: boolean
    missing_fields?: string[]
  }
}

export interface DispatchPreview {
  tripId: string
  nodeKey: string
  channel: ChannelCode
  templateId: string
  content: string
  variableCheck: {
    ok: boolean
    missingFields: string[]
  }
}

export interface DispatchNowInput {
  tripId: string
  nodeKey: string
  channel: ChannelCode
  content?: string
  templateId?: string
}

export interface RetryDispatchInput {
  dispatchId: string
  reason?: string
}

export interface AssignTakeoverInput {
  taskId: string
  assigneeUserId: string
  assigneeName?: string
  deadlineAt?: string
  note?: string
}

export interface CompleteTaskInput {
  taskId: string
  resultNote?: string
  evidenceType?: 'none' | 'receipt' | 'screenshot' | 'external_link'
  evidenceRef?: string
}

export interface NudgeTaskInput {
  taskId: string
  targetRole?: string
  message?: string
}

export interface RawActionResult {
  ok?: boolean
  status?: string
  message?: string
  task_id?: string
  dispatch_id?: string
}

export interface ActionResult {
  ok: boolean
  status: string
  message: string
  taskId: string
  dispatchId: string
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
