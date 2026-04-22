export type TripRuleStageCode = 'pre_trip' | 'on_trip' | 'post_trip' | 'custom' | 'unknown'
export type TripRuleTimeSlotCode = 'morning' | 'afternoon' | 'evening' | 'night' | 'all_day' | 'unknown'
export type TripRuleSceneCode = 'normal' | 'weather_alert' | 'delay' | 'complaint' | 'manual'
export type TripRuleChannelCode = 'sms' | 'wechat_work_group' | 'email'

interface ApiEnvelope<T> {
  code?: number
  data: T
  error?: string
  message?: string
}

export interface TripNotificationTemplate {
  id: string
  name: string
  content: string
  channel: TripRuleChannelCode
  channelLabel: string
  enabled: boolean
}

export interface TripNotificationRule {
  id: string
  name: string
  stage: TripRuleStageCode
  timeSlot: TripRuleTimeSlotCode
  scene: TripRuleSceneCode
  channels: TripRuleChannelCode[]
  templateId: string
  templateName: string
  enabled: boolean
  priority: number
  conditions: Record<string, unknown>
}

export interface TripNotificationRuleWriteInput {
  name: string
  stage: TripRuleStageCode
  timeSlot: TripRuleTimeSlotCode
  scene: TripRuleSceneCode
  channels: TripRuleChannelCode[]
  templateId: string
  enabled: boolean
  priority: number
  conditions?: Record<string, unknown>
}

export interface TripNotificationSnapshot {
  sentCount: number
  pendingCount: number
  failedCount: number
  manualCount: number
  channelBreakdown: Array<{
    channel: TripRuleChannelCode
    sent: number
    pending: number
    failed: number
    manual: number
  }>
}

function toErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    return error.message
  }
  return fallback
}

function normalizeChannel(value: unknown): TripRuleChannelCode {
  const raw = String(value || '').trim().toLowerCase()
  if (raw === 'wechat' || raw === 'wechat_work' || raw === '企业微信') {
    return 'wechat_work_group'
  }
  if (raw === 'email' || raw === '邮件') {
    return 'email'
  }
  return 'sms'
}

function normalizeScene(value: unknown): TripRuleSceneCode {
  const raw = String(value || '').trim().toLowerCase()
  if (raw === 'weather' || raw === 'weather_alert') {
    return 'weather_alert'
  }
  if (raw === 'delay' || raw === 'flight_delay') {
    return 'delay'
  }
  if (raw === 'complaint') {
    return 'complaint'
  }
  if (raw === 'manual') {
    return 'manual'
  }
  return 'normal'
}

function normalizeStage(value: unknown): TripRuleStageCode {
  const raw = String(value || '').trim().toLowerCase()
  if (raw === 'pre_trip' || raw === 'before_departure') {
    return 'pre_trip'
  }
  if (raw === 'on_trip' || raw === 'in_trip' || raw === 'during') {
    return 'on_trip'
  }
  if (raw === 'post_trip' || raw === 'after_trip') {
    return 'post_trip'
  }
  if (raw === 'custom') {
    return 'custom'
  }
  return 'unknown'
}

function normalizeTimeSlot(value: unknown): TripRuleTimeSlotCode {
  const raw = String(value || '').trim().toLowerCase()
  if (raw === 'morning' || raw === 'am') {
    return 'morning'
  }
  if (raw === 'afternoon' || raw === 'pm') {
    return 'afternoon'
  }
  if (raw === 'evening') {
    return 'evening'
  }
  if (raw === 'night') {
    return 'night'
  }
  if (raw === 'all_day' || raw === 'any' || raw === 'anytime') {
    return 'all_day'
  }
  return 'unknown'
}

function channelLabel(channel: TripRuleChannelCode): string {
  if (channel === 'wechat_work_group') {
    return '企业微信'
  }
  if (channel === 'email') {
    return '邮件'
  }
  return '短信'
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...(init?.headers || {}),
    },
  })
  const body = (await response.json()) as ApiEnvelope<T>
  if (!response.ok) {
    const message = body.error || body.message || `请求失败(${response.status})`
    throw new Error(message)
  }
  return body.data
}

function mapTemplate(item: Record<string, unknown>): TripNotificationTemplate {
  const channel = normalizeChannel(item.channel)
  return {
    id: String(item.id || ''),
    name: String(item.name || '未命名模板'),
    content: String(item.content || item.template || ''),
    channel,
    channelLabel: channelLabel(channel),
    enabled: Boolean(item.enabled ?? item.is_active ?? true),
  }
}

function mapRule(item: Record<string, unknown>, templatesById: Map<string, TripNotificationTemplate>): TripNotificationRule {
  const templateId = String(item.template_id || item.templateId || '')
  const templateName = String(item.template_name || item.template || templatesById.get(templateId)?.name || '未绑定模板')
  const rawChannels = Array.isArray(item.channels) ? item.channels : []
  const channels = rawChannels.map((channel) => normalizeChannel(channel))
  const conditions = (item.conditions && typeof item.conditions === 'object') ? (item.conditions as Record<string, unknown>) : {}

  return {
    id: String(item.id || ''),
    name: String(item.name || item.rule_name || item.title || '未命名规则'),
    stage: normalizeStage(item.stage),
    timeSlot: normalizeTimeSlot(item.time_slot || item.timeSlot),
    scene: normalizeScene(item.scene),
    channels: channels.length > 0 ? channels : ['sms'],
    templateId,
    templateName,
    enabled: Boolean(item.enabled ?? item.is_enabled ?? item.isEnabled ?? true),
    priority: Number(item.priority || 100),
    conditions,
  }
}

function ruleMatchesTrip(rule: TripNotificationRule, tripId: string): boolean {
  const byConditionTripId = String(rule.conditions.trip_id || '').trim()
  const byConditionTripCode = String(rule.conditions.trip_code || '').trim()
  return byConditionTripId === tripId || byConditionTripCode === tripId
}

function buildRulePayload(tripId: string, input: TripNotificationRuleWriteInput): Record<string, unknown> {
  const mergedConditions = {
    ...(input.conditions || {}),
    trip_id: tripId,
  }
  return {
    name: input.name,
    stage: input.stage === 'unknown' ? 'custom' : input.stage,
    time_slot: input.timeSlot === 'unknown' ? 'all_day' : input.timeSlot,
    scene: input.scene,
    channels: input.channels,
    template_id: input.templateId,
    enabled: input.enabled,
    priority: input.priority,
    conditions: mergedConditions,
  }
}

export const tripNotificationClient = {
  async listTemplates(): Promise<TripNotificationTemplate[]> {
    const data = await request<{ items?: Array<Record<string, unknown>> } | Array<Record<string, unknown>>>('/api/notifications/templates')
    const items = Array.isArray(data) ? data : (data.items || [])
    return items.map((item) => mapTemplate(item))
  },

  async listRulesByTrip(tripId: string): Promise<TripNotificationRule[]> {
    try {
      const templates = await this.listTemplates()
      const templatesById = new Map(templates.map((template) => [template.id, template]))
      const data = await request<{ items?: Array<Record<string, unknown>> } | Array<Record<string, unknown>>>('/api/notifications/rules')
      const items = Array.isArray(data) ? data : (data.items || [])
      return items.map((item) => mapRule(item, templatesById)).filter((rule) => ruleMatchesTrip(rule, tripId))
    } catch (error) {
      throw new Error(toErrorMessage(error, '加载旅行团通知规则失败'))
    }
  },

  async createRule(tripId: string, input: TripNotificationRuleWriteInput): Promise<void> {
    try {
      await request('/api/notifications/rules', {
        method: 'POST',
        body: JSON.stringify(buildRulePayload(tripId, input)),
      })
    } catch (error) {
      throw new Error(toErrorMessage(error, '新增通知规则失败'))
    }
  },

  async updateRule(tripId: string, ruleId: string, input: TripNotificationRuleWriteInput): Promise<void> {
    try {
      await request(`/api/notifications/rules/${ruleId}`, {
        method: 'PUT',
        body: JSON.stringify(buildRulePayload(tripId, input)),
      })
    } catch (error) {
      throw new Error(toErrorMessage(error, '编辑通知规则失败'))
    }
  },

  async toggleRule(ruleId: string, enabled: boolean): Promise<void> {
    try {
      await request(`/api/notifications/rules/${ruleId}`, {
        method: 'PUT',
        body: JSON.stringify({ enabled }),
      })
    } catch (error) {
      throw new Error(toErrorMessage(error, '启停通知规则失败'))
    }
  },

  async deleteRule(ruleId: string): Promise<void> {
    try {
      await request(`/api/notifications/rules/${ruleId}`, {
        method: 'DELETE',
      })
    } catch (error) {
      throw new Error(toErrorMessage(error, '删除通知规则失败'))
    }
  },

  async getTripStatusSnapshot(tripId: string): Promise<TripNotificationSnapshot> {
    try {
      const [historyData, jobsData] = await Promise.all([
        request<{ items?: Array<Record<string, unknown>> } | Array<Record<string, unknown>>>(`/api/notifications/history?limit=200&trip_id=${encodeURIComponent(tripId)}`),
        request<{ items?: Array<Record<string, unknown>> } | Array<Record<string, unknown>>>(`/api/notifications/jobs?limit=200&trip_id=${encodeURIComponent(tripId)}`),
      ])
      const historyItems = Array.isArray(historyData) ? historyData : (historyData.items || [])
      const jobItems = Array.isArray(jobsData) ? jobsData : (jobsData.items || [])

      const channelBuckets = new Map<TripRuleChannelCode, { sent: number; pending: number; failed: number; manual: number }>()
      const ensureBucket = (channel: TripRuleChannelCode) => {
        if (!channelBuckets.has(channel)) {
          channelBuckets.set(channel, { sent: 0, pending: 0, failed: 0, manual: 0 })
        }
        return channelBuckets.get(channel)!
      }

      for (const item of historyItems) {
        const channel = normalizeChannel(item.channel)
        const status = String(item.status || '').toLowerCase()
        const bucket = ensureBucket(channel)
        if (status === 'sent') {
          bucket.sent += 1
        } else if (status === 'manual_intervention') {
          bucket.manual += 1
        } else {
          bucket.failed += 1
        }
      }

      for (const item of jobItems) {
        const channel = normalizeChannel(item.channel)
        const status = String(item.status || '').toLowerCase()
        const bucket = ensureBucket(channel)
        if (status === 'pending' || status === 'retrying') {
          bucket.pending += 1
        } else if (status === 'manual_intervention') {
          bucket.manual += 1
        } else if (status === 'failed') {
          bucket.failed += 1
        }
      }

      const breakdown = Array.from(channelBuckets.entries()).map(([channel, stats]) => ({
        channel,
        sent: stats.sent,
        pending: stats.pending,
        failed: stats.failed,
        manual: stats.manual,
      }))

      return {
        sentCount: breakdown.reduce((acc, item) => acc + item.sent, 0),
        pendingCount: breakdown.reduce((acc, item) => acc + item.pending, 0),
        failedCount: breakdown.reduce((acc, item) => acc + item.failed, 0),
        manualCount: breakdown.reduce((acc, item) => acc + item.manual, 0),
        channelBreakdown: breakdown,
      }
    } catch (error) {
      throw new Error(toErrorMessage(error, '加载发送状态失败'))
    }
  },
}
