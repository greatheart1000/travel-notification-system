import { api } from './api'
import { dispatchAuthStateChanged, setAuthTokens } from '../adapters/authAdapter'
import type { AuthLoginResponse } from '../types/api'

export interface CommercialUser {
  id: string
  username: string
  email: string
  phone?: string
  role: string
  tenant_id: string
  status?: string
  created_at?: string
}

export interface TenantInfo {
  tenant_id: string
  name: string
  status: string
  contact_name?: string
  contact_phone?: string
  contact_email?: string
  invoice_title?: string
  tax_id?: string
  invoice_address?: string
  invoice_phone?: string
  invoice_bank_name?: string
  invoice_bank_account?: string
  invoice_email?: string
}

export interface Plan {
  code: string
  name: string
  price_cents: number
  price_yuan: string
  currency: string
  sms_quota: number
  period_days: number
  features: string[]
  is_free: boolean
}

export interface Subscription {
  tenant_id: string
  plan_code: string
  status: string
  started_at: string
  current_period_start: string
  current_period_end: string
  cancel_at_period_end: boolean
  last_order_no: string
}

export interface Usage {
  tenant_id: string
  period: string
  plan_code: string
  plan_name: string
  sms_used: number
  sms_quota: number
  sms_remaining: number
  usage_ratio: number
  subscription_status: string
  current_period_end: string
}

export interface PaymentMethod {
  code: string
  name: string
}

export interface BillingOrder {
  order_no: string
  tenant_id: string
  plan_code: string
  amount_cents: number
  currency: string
  provider: string
  status: 'pending' | 'paid' | 'closed' | 'refunded' | 'failed'
  pay_url: string
  created_at: string
  paid_at: string
  expires_at: string
  refund_status?: 'none' | 'refunded' | 'failed'
  refund_mode?: 'manual' | 'gateway' | ''
  refund_amount_cents?: number
  refund_reason?: string
  refund_error?: string
  refunded_at?: string
  refunded_by?: string
  refund_trade_no?: string
}

export interface PlansResponse {
  plans: Plan[]
  payment_methods: PaymentMethod[]
  currency: string
  trial_days: number
  trial_sms_quota: number
}

export interface SubscriptionResponse {
  tenant_id: string
  subscription: Subscription
  plan: Plan
  usage: Usage
  payment_methods: PaymentMethod[]
}

export interface TenantNotificationConfig {
  tenant_id: string
  wechat_webhook_url: string
  sms_provider: string
  sms_sign_name: string
  sms_template_code: string
  sms_credential_id: string
  updated_at?: string
}

export interface NotificationRuleRaw {
  id: string
  name: string
  stage: string
  time_slot: string
  scene: string
  channels?: string[]
  template_id?: string | null
  enabled?: boolean
  priority?: number
  conditions?: Record<string, unknown> | null
  trip_id?: string | null
}

export interface NotificationJob {
  job_id: string
  task_id: string
  trip_id: string
  team_id?: string
  tenant_id: string
  channel: string
  status: string
  attempt: number
  next_run_at: string
  last_error: string
}

export interface TenantUser {
  id: string
  username: string
  display_name?: string
  email: string
  phone?: string
  role: string
  tenant_id: string
  status?: string
  created_at?: string
}

export interface OperatorTenant {
  tenant_id: string
  name: string
  status: string
  plan_code?: string
  plan_name?: string
  subscription_status?: string
  sms_used?: number
  sms_quota?: number
}

export interface OperatorOverview {
  period: string
  tenants: number
  active_subscriptions: number
  paid_orders: number
  revenue_cents: number
  revenue_cents_total: number
  revenue_cents_this_period: number
  sms_used_this_period: number
  orders: BillingOrder[]
}

export const operatorApi = {
  async listTenants() {
    return api.get<{ total: number; items: OperatorTenant[] }>('/operator/tenants')
  },
  async overview() {
    return api.get<OperatorOverview>('/operator/billing/overview')
  },
  async activatePlan(tenantId: string, planCode: string, days?: number) {
    return api.post<Subscription>(
      `/operator/tenants/${encodeURIComponent(tenantId)}/activate-plan`,
      { plan_code: planCode, days: days ?? null },
    )
  },
  async runDunning() {
    return api.post<{
      enabled: boolean
      checked: number
      sent: number
      skipped: number
      failed: number
      reason?: string
    }>('/operator/billing/dunning/run')
  },
  async refundOrder(
    orderNo: string,
    options: { downgrade?: boolean; mode?: 'manual' | 'gateway'; reason?: string } = {},
  ) {
    return api.post<BillingOrder>(
      `/operator/orders/${encodeURIComponent(orderNo)}/refund`,
      {
        downgrade: options.downgrade ?? false,
        mode: options.mode ?? 'manual',
        reason: options.reason ?? '',
      },
    )
  },
}

export const commercialAuthApi = {
  async sendSmsCode(phone: string, purpose: 'login' | 'register' | 'reset') {
    return api.post<{ sent: boolean; expires_in: number; cooldown: number; debug_code?: string }>(
      '/auth/sms-code',
      { phone, purpose },
    )
  },

  async register(input: {
    tenant_name: string
    username: string
    password: string
    phone: string
    code: string
  }) {
    return api.post<{
      tokens: AuthLoginResponse
      user: CommercialUser
      tenant: TenantInfo
    }>('/auth/register', input)
  },

  async loginSms(phone: string, code: string) {
    return api.post<{ tokens: AuthLoginResponse; user: CommercialUser }>('/auth/login-sms', {
      phone,
      code,
    })
  },

  async resetPassword(phone: string, code: string, newPassword: string) {
    return api.post<{ reset: boolean }>('/auth/password/reset', {
      phone,
      code,
      new_password: newPassword,
    })
  },

  persistLogin(tokens: AuthLoginResponse) {
    setAuthTokens(tokens)
    dispatchAuthStateChanged(true)
  },
}

export const billingApi = {
  async getPlans() {
    return api.get<PlansResponse>('/public/plans')
  },

  async getSubscription() {
    return api.get<SubscriptionResponse>('/billing/subscription')
  },

  async getUsage() {
    return api.get<Usage>('/billing/usage')
  },

  async listOrders() {
    return api.get<{ total: number; items: BillingOrder[] }>('/billing/orders')
  },

  async createOrder(planCode: string, provider: string) {
    return api.post<BillingOrder>('/billing/orders', { plan_code: planCode, provider })
  },

  async cancelOrder(orderNo: string) {
    return api.post<BillingOrder>(`/billing/orders/${encodeURIComponent(orderNo)}/cancel`)
  },

  async mockPay(orderNo: string) {
    return api.post<{ ok: boolean; order: BillingOrder }>(
      `/billing/orders/${encodeURIComponent(orderNo)}/mock-pay`,
    )
  },

  async cancelSubscription() {
    return api.post<Subscription>('/billing/subscription/cancel')
  },

  async resumeSubscription() {
    return api.post<Subscription>('/billing/subscription/resume')
  },
}

export const tenantSettingsApi = {
  async getCurrentTenant() {
    return api.get<TenantInfo>('/tenant/me')
  },
  async getProfile() {
    return api.get<TenantInfo>('/admin/tenant-profile')
  },
  async updateProfile(patch: Partial<TenantInfo>) {
    return api.put<TenantInfo>('/admin/tenant-profile', patch)
  },
  async getNotificationConfig() {
    return api.get<{ tenant_id: string; config: TenantNotificationConfig }>(
      '/admin/tenant-notification-config',
    )
  },
  async updateNotificationConfig(payload: Partial<TenantNotificationConfig>) {
    return api.put<{ tenant_id: string; config: TenantNotificationConfig }>(
      '/admin/tenant-notification-config',
      payload,
    )
  },
}

export const rulesApi = {
  async list() {
    const raw = await api.get<{ total: number; items: NotificationRuleRaw[] }>(
      '/notifications/rules',
    )
    return raw.items
  },
  async create(payload: Partial<NotificationRuleRaw>) {
    const raw = await api.post<{ rule: NotificationRuleRaw }>('/notifications/rules', payload)
    return raw.rule
  },
  async update(id: string, payload: Partial<NotificationRuleRaw>) {
    return api.put<NotificationRuleRaw>(`/notifications/rules/${encodeURIComponent(id)}`, payload)
  },
  async remove(id: string) {
    return api.delete<{ deleted: boolean }>(`/notifications/rules/${encodeURIComponent(id)}`)
  },
  async toggle(id: string, enabled: boolean) {
    return api.put<NotificationRuleRaw>(`/notifications/rules/${encodeURIComponent(id)}`, {
      enabled,
    })
  },
}

export const jobsApi = {
  async list(status?: string) {
    const query = status ? `?status=${encodeURIComponent(status)}` : ''
    return api.get<{ total: number; items: NotificationJob[] }>(
      `/admin/notification-jobs${query}`,
    )
  },
  async requeue(jobId: string) {
    return api.post<NotificationJob>(
      `/admin/notification-jobs/${encodeURIComponent(jobId)}/requeue`,
    )
  },
}

export const tenantUsersApi = {
  async list() {
    return api.get<{ total: number; items: TenantUser[] }>('/admin/users')
  },
  async create(payload: {
    username: string
    password: string
    display_name?: string
    email?: string
    phone?: string
    role?: string
  }) {
    return api.post<TenantUser>('/admin/users', payload)
  },
  async update(username: string, payload: Partial<TenantUser>) {
    return api.put<TenantUser>(`/admin/users/${encodeURIComponent(username)}`, payload)
  },
}


export interface TeamTripSummary {
  id: string
  destination: string
  team_id: string
  start_date: string
  end_date: string
  participants: number
  status: string
  assigned_user_ids: string[]
  send_mode?: 'auto' | 'approval'
  webhook_configured: boolean
  wecom_chat_id: string
}

export interface TeamNotificationSummary {
  id: string
  task_id: string
  trip_id: string
  trip_label: string
  channel: string
  status: string
  content: string
  customer_name: string
  operator_id: string
  operator_name: string
  created_at: string
}

export interface TeamMemberOverview {
  id: string
  username: string
  display_name?: string
  role: string
  phone: string
  status: string
  assigned_trips: TeamTripSummary[]
  notification_count: number
  recent_notifications: TeamNotificationSummary[]
}

export interface TeamOverview {
  stats: {
    members: number
    assigned_trips: number
    unassigned_trips: number
    notifications_7d: number
    failed_7d: number
    trips_without_group: number
  }
  members: TeamMemberOverview[]
  unassigned_trips: TeamTripSummary[]
  trips_without_group: TeamTripSummary[]
  recent_notifications: TeamNotificationSummary[]
}

export const teamOverviewApi = {
  async get() {
    return api.get<TeamOverview>('/admin/team-overview')
  },
}
