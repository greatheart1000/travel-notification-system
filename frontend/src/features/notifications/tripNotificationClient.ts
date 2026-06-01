import { api } from '../../services/api'

const RULES_ENDPOINT = '/api/notifications/rules'
const TEMPLATES_ENDPOINT = '/api/notifications/templates'
const HISTORY_ENDPOINT = '/api/notifications/history'
const JOBS_ENDPOINT = '/api/notifications/jobs'

export interface TripNotificationRulePayload {
  tripId: string
  name: string
  timeSlot: string
  templateId: string
  channel: string
  enabled: boolean
}

function apiPath(endpoint: string): string {
  return endpoint.replace(/^\/api/, '')
}

export const tripNotificationClient = {
  async listRules(tripId: string) {
    return api.get(`${apiPath(RULES_ENDPOINT)}?trip_id=${encodeURIComponent(tripId)}`)
  },

  async saveRule(input: TripNotificationRulePayload) {
    const tripId = input.tripId
    return api.post(apiPath(RULES_ENDPOINT), {
      name: input.name,
      time_slot: input.timeSlot,
      template_id: input.templateId,
      channel: input.channel,
      enabled: input.enabled,
      trip_id: tripId,
      condition: {
        trip_id: tripId,
      },
    })
  },

  async listTemplates() {
    return api.get(apiPath(TEMPLATES_ENDPOINT))
  },

  async listHistory(tripId: string) {
    return api.get(`${apiPath(HISTORY_ENDPOINT)}?trip_id=${encodeURIComponent(tripId)}`)
  },

  async listJobs(tripId: string) {
    return api.get(`${apiPath(JOBS_ENDPOINT)}?trip_id=${encodeURIComponent(tripId)}`)
  },
}
