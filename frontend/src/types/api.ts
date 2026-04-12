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
  total_users?: number
  pending_complaints?: number
  notification_success_rate?: number
}

export interface DashboardStats {
  todayNotifications: number
  activeTrips: number
  totalUsers: number
  pendingComplaints: number
  notificationSuccessRate: number
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
}

export interface TripWriteInput {
  destination: string
  teamId: string
  startDate: string
  endDate: string
  participants?: number
  status?: TripStatusCode
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
