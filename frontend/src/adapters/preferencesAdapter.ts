import {
  type PreferencesViewModel,
  type PreferencesWritePayloadForMe,
  type PreferencesWritePayloadLegacy,
  type QuietHoursRaw,
  type RawPreferences,
} from '../types/api'
import { normalizeChannel } from './apiAdapter'

const DEFAULT_PREFERENCES: PreferencesViewModel = {
  smsEnabled: true,
  wechatEnabled: true,
  emailEnabled: false,
  quietHourStart: '22',
  quietHourEnd: '08',
  maxNotificationsPerHour: 5,
  autoEscalation: true,
  aggregateNotifications: true,
  allowMarketing: true,
}

function normalizeHourNumber(value: string | number | undefined, fallback: string): string {
  if (value === undefined) {
    return fallback
  }

  if (typeof value === 'number') {
    const hour = Math.max(0, Math.min(23, Math.trunc(value)))
    return String(hour).padStart(2, '0')
  }

  const plain = value.includes(':') ? value.split(':')[0] : value
  const parsed = Number(plain)
  if (Number.isNaN(parsed)) {
    return fallback
  }
  const hour = Math.max(0, Math.min(23, Math.trunc(parsed)))
  return String(hour).padStart(2, '0')
}

function readQuietHours(raw: QuietHoursRaw | undefined): { start: string; end: string } {
  if (!raw) {
    return {
      start: DEFAULT_PREFERENCES.quietHourStart,
      end: DEFAULT_PREFERENCES.quietHourEnd,
    }
  }

  if (Array.isArray(raw)) {
    return {
      start: normalizeHourNumber(raw[0], DEFAULT_PREFERENCES.quietHourStart),
      end: normalizeHourNumber(raw[1], DEFAULT_PREFERENCES.quietHourEnd),
    }
  }

  return {
    start: normalizeHourNumber(raw.start, DEFAULT_PREFERENCES.quietHourStart),
    end: normalizeHourNumber(raw.end, DEFAULT_PREFERENCES.quietHourEnd),
  }
}

export function emptyPreferences(): PreferencesViewModel {
  return { ...DEFAULT_PREFERENCES }
}

export function mapRawPreferences(raw: RawPreferences | null | undefined): PreferencesViewModel {
  if (!raw) {
    return emptyPreferences()
  }

  const channels = new Set((raw.channels ?? []).map((item) => normalizeChannel(item)))
  const quietHours = readQuietHours(raw.quiet_hours)

  return {
    smsEnabled: channels.has('sms'),
    wechatEnabled: channels.has('wechat_work_group'),
    emailEnabled: channels.has('email'),
    quietHourStart: quietHours.start,
    quietHourEnd: quietHours.end,
    maxNotificationsPerHour: raw.max_notifications_per_hour ?? DEFAULT_PREFERENCES.maxNotificationsPerHour,
    autoEscalation: raw.auto_escalation ?? DEFAULT_PREFERENCES.autoEscalation,
    aggregateNotifications: raw.aggregate_notifications ?? DEFAULT_PREFERENCES.aggregateNotifications,
    allowMarketing: raw.allow_marketing ?? DEFAULT_PREFERENCES.allowMarketing,
  }
}

function selectedChannels(viewModel: PreferencesViewModel): string[] {
  const channels: string[] = []

  if (viewModel.smsEnabled) {
    channels.push('sms')
  }
  if (viewModel.wechatEnabled) {
    channels.push('wechat_work_group')
  }
  if (viewModel.emailEnabled) {
    channels.push('email')
  }

  return channels
}

export function toPreferencesPayloadForMe(viewModel: PreferencesViewModel): PreferencesWritePayloadForMe {
  return {
    channels: selectedChannels(viewModel),
    quiet_hours: [Number(viewModel.quietHourStart), Number(viewModel.quietHourEnd)],
    max_notifications_per_hour: viewModel.maxNotificationsPerHour,
    auto_escalation: viewModel.autoEscalation,
    aggregate_notifications: viewModel.aggregateNotifications,
    allow_marketing: viewModel.allowMarketing,
  }
}

export function toPreferencesPayloadLegacy(viewModel: PreferencesViewModel): PreferencesWritePayloadLegacy {
  return {
    channels: selectedChannels(viewModel),
    quiet_hours: {
      start: `${viewModel.quietHourStart}:00`,
      end: `${viewModel.quietHourEnd}:00`,
    },
    max_notifications_per_hour: viewModel.maxNotificationsPerHour,
    auto_escalation: viewModel.autoEscalation,
    aggregate_notifications: viewModel.aggregateNotifications,
  }
}
