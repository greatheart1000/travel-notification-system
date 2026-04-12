import {
  type AnalyticsData,
  type AnalyticsMetrics,
  type ChannelCode,
  type DashboardStats,
  type NotificationRule,
  type NotificationRuleStageCode,
  type NotificationRuleTimeSlotCode,
  type NotificationRuleWriteInput,
  type NotificationStatusCode,
  type NotificationTemplate,
  type RawAnalyticsResponse,
  type RawDashboardStats,
  type RawNotificationRule,
  type RawNotificationTemplate,
  type RawRecentNotification,
  type RawTrip,
  type RecentNotification,
  type Trip,
  type TripStatusCode,
  type TripWriteInput,
} from '../types/api'

const CHANNEL_ALIASES_EXACT: Record<string, ChannelCode> = {
  sms: 'sms',
  SMS: 'sms',
  '短信': 'sms',
  wechat: 'wechat_work_group',
  WECHAT: 'wechat_work_group',
  WECHAT_WORK_GROUP: 'wechat_work_group',
  wechat_work_group: 'wechat_work_group',
  '企业微信': 'wechat_work_group',
  email: 'email',
  EMAIL: 'email',
  '邮件': 'email',
}

const CHANNEL_ALIASES_NORMALIZED: Record<string, ChannelCode> = {
  sms: 'sms',
  wechat: 'wechat_work_group',
  wechat_work_group: 'wechat_work_group',
  email: 'email',
}

const CHANNEL_LABELS: Record<ChannelCode, string> = {
  sms: '短信',
  wechat_work_group: '企业微信',
  email: '邮件',
}

const TRIP_STATUS_ALIASES_EXACT: Record<string, TripStatusCode> = {
  planned: 'planned',
  active: 'in_progress',
  in_progress: 'in_progress',
  completed: 'completed',
  cancelled: 'cancelled',
  '计划中': 'planned',
  '进行中': 'in_progress',
  '已完成': 'completed',
  '已取消': 'cancelled',
}

const TRIP_STATUS_ALIASES_NORMALIZED: Record<string, TripStatusCode> = {
  planned: 'planned',
  active: 'in_progress',
  in_progress: 'in_progress',
  'in-progress': 'in_progress',
  completed: 'completed',
  cancelled: 'cancelled',
}

const TRIP_STATUS_LABELS: Record<TripStatusCode, string> = {
  planned: '计划中',
  in_progress: '进行中',
  completed: '已完成',
  cancelled: '已取消',
  unknown: '未知',
}

const NOTIFICATION_STATUS_ALIASES_EXACT: Record<string, NotificationStatusCode> = {
  sent: 'sent',
  success: 'sent',
  failed: 'failed',
  retrying: 'retrying',
  skipped: 'skipped',
  manual_intervention: 'manual_intervention',
  enabled: 'enabled',
  active: 'enabled',
  disabled: 'disabled',
  inactive: 'disabled',
  '启用': 'enabled',
  '激活': 'enabled',
  '禁用': 'disabled',
  '停用': 'disabled',
}

const NOTIFICATION_STATUS_ALIASES_NORMALIZED: Record<string, NotificationStatusCode> = {
  sent: 'sent',
  success: 'sent',
  failed: 'failed',
  retrying: 'retrying',
  skipped: 'skipped',
  manual_intervention: 'manual_intervention',
  enabled: 'enabled',
  active: 'enabled',
  disabled: 'disabled',
  inactive: 'disabled',
}

const NOTIFICATION_STATUS_LABELS: Record<NotificationStatusCode, string> = {
  sent: '已发送',
  failed: '失败',
  retrying: '重试中',
  skipped: '已跳过',
  manual_intervention: '人工介入',
  enabled: '启用',
  disabled: '停用',
  unknown: '未知',
}

const RULE_STAGE_ALIASES_EXACT: Record<string, NotificationRuleStageCode> = {
  pre_trip: 'pre_trip',
  PRE_TRIP: 'pre_trip',
  '出行前': 'pre_trip',
  on_trip: 'on_trip',
  ON_TRIP: 'on_trip',
  '出行中': 'on_trip',
  post_trip: 'post_trip',
  POST_TRIP: 'post_trip',
  '出行后': 'post_trip',
  custom: 'custom',
  CUSTOM: 'custom',
  '自定义': 'custom',
}

const RULE_STAGE_ALIASES_NORMALIZED: Record<string, NotificationRuleStageCode> = {
  pre_trip: 'pre_trip',
  pretrip: 'pre_trip',
  'pre-trip': 'pre_trip',
  before_trip: 'pre_trip',
  on_trip: 'on_trip',
  ontrip: 'on_trip',
  in_trip: 'on_trip',
  post_trip: 'post_trip',
  posttrip: 'post_trip',
  after_trip: 'post_trip',
  custom: 'custom',
}

const RULE_STAGE_LABELS: Record<NotificationRuleStageCode, string> = {
  pre_trip: '出行前',
  on_trip: '出行中',
  post_trip: '出行后',
  custom: '自定义',
  unknown: '未知阶段',
}

const RULE_TIME_SLOT_ALIASES_EXACT: Record<string, NotificationRuleTimeSlotCode> = {
  morning: 'morning',
  MORNING: 'morning',
  '早间': 'morning',
  afternoon: 'afternoon',
  AFTERNOON: 'afternoon',
  '下午': 'afternoon',
  evening: 'evening',
  EVENING: 'evening',
  '傍晚': 'evening',
  night: 'night',
  NIGHT: 'night',
  '夜间': 'night',
  all_day: 'all_day',
  ALL_DAY: 'all_day',
  '全天': 'all_day',
}

const RULE_TIME_SLOT_ALIASES_NORMALIZED: Record<string, NotificationRuleTimeSlotCode> = {
  morning: 'morning',
  am: 'morning',
  afternoon: 'afternoon',
  pm: 'afternoon',
  evening: 'evening',
  dusk: 'evening',
  night: 'night',
  all_day: 'all_day',
  allday: 'all_day',
  anytime: 'all_day',
}

const RULE_TIME_SLOT_LABELS: Record<NotificationRuleTimeSlotCode, string> = {
  morning: '早间',
  afternoon: '下午',
  evening: '傍晚',
  night: '夜间',
  all_day: '全天',
  unknown: '未知时段',
}

function normalizeAliasKey(value: string | undefined): string {
  return (value ?? '').trim().toLowerCase()
}

function asNumber(value: unknown, fallback = 0): number {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value
  }
  if (typeof value === 'string') {
    const n = Number(value)
    if (Number.isFinite(n)) {
      return n
    }
  }
  return fallback
}

function safeText(value: unknown, fallback = ''): string {
  if (typeof value === 'string') {
    return value
  }
  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value)
  }
  return fallback
}

function fallbackId(prefix: string, parts: Array<string | undefined>): string {
  const token = parts
    .map((item) => (item ?? '').trim())
    .filter(Boolean)
    .join('|')
  return `${prefix}-${token || 'unknown'}`
}

export function normalizeChannel(value: string | undefined): ChannelCode {
  if (!value || !value.trim()) {
    return 'sms'
  }
  return CHANNEL_ALIASES_EXACT[value] ?? CHANNEL_ALIASES_NORMALIZED[normalizeAliasKey(value)] ?? 'sms'
}

export function channelLabel(channel: ChannelCode): string {
  return CHANNEL_LABELS[channel]
}

export function normalizeTripStatus(value: string | undefined): TripStatusCode {
  if (!value || !value.trim()) {
    return 'unknown'
  }
  return (
    TRIP_STATUS_ALIASES_EXACT[value] ??
    TRIP_STATUS_ALIASES_NORMALIZED[normalizeAliasKey(value)] ??
    'unknown'
  )
}

export function tripStatusLabel(status: TripStatusCode): string {
  return TRIP_STATUS_LABELS[status]
}

export function normalizeNotificationStatus(value: string | undefined): NotificationStatusCode {
  if (!value || !value.trim()) {
    return 'unknown'
  }
  return (
    NOTIFICATION_STATUS_ALIASES_EXACT[value] ??
    NOTIFICATION_STATUS_ALIASES_NORMALIZED[normalizeAliasKey(value)] ??
    'unknown'
  )
}

export function notificationStatusLabel(status: NotificationStatusCode): string {
  return NOTIFICATION_STATUS_LABELS[status]
}

export function mapDashboardStats(raw: RawDashboardStats): DashboardStats {
  return {
    todayNotifications: asNumber(raw.today_notifications, 0),
    activeTrips: asNumber(raw.active_trips, 0),
    totalUsers: asNumber(raw.total_users, 0),
    pendingComplaints: asNumber(raw.pending_complaints, 0),
    notificationSuccessRate: asNumber(raw.notification_success_rate, 0),
  }
}

export function mapRawTrip(raw: RawTrip): Trip {
  const status = normalizeTripStatus(raw.status)
  const destination = safeText(raw.destination, '未命名行程')
  const teamId = safeText(raw.team_id ?? raw.team, '')
  const startDate = safeText(raw.start_date, '')
  const endDate = safeText(raw.end_date, '')
  const id = safeText(raw.id, fallbackId('trip', [teamId, destination, startDate, endDate]))

  return {
    id,
    destination,
    teamId,
    startDate,
    endDate,
    participants: asNumber(raw.participants, 0),
    status,
    statusLabel: tripStatusLabel(status),
  }
}

export function toTripWritePayload(input: TripWriteInput): Record<string, string | number> {
  const normalizedStatus = input.status ?? 'planned'
  return {
    destination: input.destination,
    team_id: input.teamId,
    team: input.teamId,
    start_date: input.startDate,
    end_date: input.endDate,
    participants: input.participants ?? 0,
    status: tripStatusLabel(normalizedStatus),
    status_code: normalizedStatus,
  }
}

export function mapRawNotificationTemplate(raw: RawNotificationTemplate): NotificationTemplate {
  const channel = normalizeChannel(raw.channel)
  const status = normalizeNotificationStatus(
    raw.status ?? raw.status_code ?? ((raw.enabled ?? raw.is_active) ? 'enabled' : 'disabled'),
  )
  const id = safeText(raw.id, fallbackId('tpl', [safeText(raw.name), safeText(raw.channel)]))

  return {
    id,
    name: safeText(raw.name, '未命名模板'),
    template: raw.template ?? raw.content ?? '',
    channel,
    channelLabel: channelLabel(channel),
    status,
    statusLabel: notificationStatusLabel(status),
    enabled: raw.enabled ?? raw.is_active ?? status === 'enabled',
    sentCount: asNumber(raw.sent_count, 0),
    successRate: `${raw.success_rate ?? '0%'}`,
  }
}

export function normalizeRuleStage(value: string | undefined): NotificationRuleStageCode {
  if (!value || !value.trim()) {
    return 'unknown'
  }
  return RULE_STAGE_ALIASES_EXACT[value] ?? RULE_STAGE_ALIASES_NORMALIZED[normalizeAliasKey(value)] ?? 'unknown'
}

export function ruleStageLabel(stage: NotificationRuleStageCode): string {
  return RULE_STAGE_LABELS[stage]
}

export function normalizeRuleTimeSlot(value: string | undefined): NotificationRuleTimeSlotCode {
  if (!value || !value.trim()) {
    return 'unknown'
  }
  return (
    RULE_TIME_SLOT_ALIASES_EXACT[value] ??
    RULE_TIME_SLOT_ALIASES_NORMALIZED[normalizeAliasKey(value)] ??
    'unknown'
  )
}

export function ruleTimeSlotLabel(timeSlot: NotificationRuleTimeSlotCode): string {
  return RULE_TIME_SLOT_LABELS[timeSlot]
}

export function mapRawNotificationRule(raw: RawNotificationRule): NotificationRule {
  const stage = normalizeRuleStage(raw.stage)
  const timeSlot = normalizeRuleTimeSlot(raw.time_slot ?? raw.timeSlot)
  const scene = safeText(raw.scene, '未定义场景')
  const name = safeText(raw.name ?? raw.rule_name ?? raw.title, scene || '未命名规则')
  const templateId = safeText(raw.template_id ?? raw.templateId, '')
  const templateLabel = safeText(raw.template_name ?? raw.template, templateId || '未绑定模板')
  const enabled = (raw.enabled ?? raw.is_enabled ?? raw.isEnabled) ?? true
  const priority = asNumber(raw.priority, 100)
  const id = safeText(raw.id, fallbackId('rule', [name, stage, timeSlot, scene, templateId, String(priority)]))

  return {
    id,
    name,
    stage,
    stageLabel: ruleStageLabel(stage),
    timeSlot,
    timeSlotLabel: ruleTimeSlotLabel(timeSlot),
    scene,
    enabled,
    priority,
    templateId,
    templateLabel,
  }
}

export function mapRawRecentNotification(raw: RawRecentNotification): RecentNotification {
  const channel = normalizeChannel(raw.channel)
  const status = normalizeNotificationStatus(raw.status)
  const customerName = safeText(raw.customer_name, '匿名客户')
  const createdAt = safeText(raw.created_at, new Date(0).toISOString())

  return {
    id: safeText(raw.id, fallbackId('notif', [customerName, createdAt, safeText(raw.trip)])),
    customerName,
    trip: safeText(raw.trip, '未指定行程'),
    channel,
    channelLabel: channelLabel(channel),
    status,
    statusLabel: notificationStatusLabel(status),
    createdAt,
  }
}

function canonicalRuleStage(stage: NotificationRuleStageCode): string {
  if (stage === 'unknown') {
    return 'custom'
  }
  return stage
}

function canonicalRuleTimeSlot(timeSlot: NotificationRuleTimeSlotCode): string {
  if (timeSlot === 'unknown') {
    return 'all_day'
  }
  return timeSlot
}

export function toNotificationRuleWritePayload(input: NotificationRuleWriteInput): Record<string, string | number | boolean> {
  const stage = canonicalRuleStage(input.stage)
  const timeSlot = canonicalRuleTimeSlot(input.timeSlot)
  return {
    name: input.name,
    rule_name: input.name,
    title: input.name,
    stage,
    stage_code: stage,
    time_slot: timeSlot,
    timeSlot,
    scene: input.scene,
    enabled: input.enabled,
    is_enabled: input.enabled,
    priority: input.priority,
    template_id: input.templateId,
    templateId: input.templateId,
  }
}

export function toNotificationRulePatchPayload(
  input: Partial<NotificationRuleWriteInput>,
): Record<string, string | number | boolean> {
  const payload: Record<string, string | number | boolean> = {}

  if (input.name !== undefined) {
    payload.name = input.name
    payload.rule_name = input.name
    payload.title = input.name
  }
  if (input.stage !== undefined) {
    const stage = canonicalRuleStage(input.stage)
    payload.stage = stage
    payload.stage_code = stage
  }
  if (input.timeSlot !== undefined) {
    const timeSlot = canonicalRuleTimeSlot(input.timeSlot)
    payload.time_slot = timeSlot
    payload.timeSlot = timeSlot
  }
  if (input.scene !== undefined) {
    payload.scene = input.scene
  }
  if (input.enabled !== undefined) {
    payload.enabled = input.enabled
    payload.is_enabled = input.enabled
  }
  if (input.priority !== undefined) {
    payload.priority = input.priority
  }
  if (input.templateId !== undefined) {
    payload.template_id = input.templateId
    payload.templateId = input.templateId
  }

  return payload
}

function metricToText(value: string | number | undefined): string {
  if (value === undefined || value === null) {
    return '-'
  }
  return String(value)
}

function normalizeAnalyticsMetrics(raw: RawAnalyticsResponse['metrics']): AnalyticsMetrics {
  const source = raw ?? {}
  return {
    notificationSuccessRate: metricToText(source.notification_success_rate),
    avgResponseTime: metricToText(source.avg_response_time),
    wowGrowth: metricToText(source.wow_growth),
    userSatisfaction: metricToText(source.user_satisfaction),
  }
}

export function mapRawAnalytics(raw: RawAnalyticsResponse): AnalyticsData {
  const metrics = raw.metrics ?? {}
  const channelPerformance = raw.channel_performance ?? []
  const topTrips = raw.top_trips ?? []

  return {
    metrics: normalizeAnalyticsMetrics(metrics),
    channelPerformance: channelPerformance.map((item) => {
      const channel = normalizeChannel(item.channel ?? item.name)
      return {
        channel,
        channelLabel: channelLabel(channel),
        sent: asNumber(item.sent, 0),
        successful: asNumber(item.successful, 0),
        failed: asNumber(item.failed, 0),
        rate: metricToText(item.rate ?? item.success_rate),
      }
    }),
    topTrips: topTrips.map((item, index) => ({
      name: safeText(item.name, `行程-${index + 1}`),
      notifications: asNumber(item.notifications, 0),
      satisfaction: asNumber(item.satisfaction, 0),
    })),
  }
}

export function channelCodeForSend(channel: ChannelCode): string {
  if (channel === 'sms') {
    return '短信'
  }
  if (channel === 'wechat_work_group') {
    return '企业微信'
  }
  return '邮件'
}
