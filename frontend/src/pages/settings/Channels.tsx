import { useCallback, useEffect, useState } from 'react'
import { Building2, Eye, EyeOff, MessageSquare, Send, ShieldCheck } from 'lucide-react'
import { PageShell } from '../../components/PageShell'
import { Button } from '../../components/Button'
import { Badge } from '../../components/Badge'
import { getErrorMessage } from '../../services/api'
import {
  tenantSettingsApi,
  type TenantInfo,
  type TenantNotificationConfig,
} from '../../services/commercialApi'

type SaveState = 'idle' | 'saving' | 'saved' | 'error'

const EMPTY_CONFIG: TenantNotificationConfig = {
  tenant_id: '',
  wechat_webhook_url: '',
  sms_provider: '',
  sms_sign_name: '',
  sms_template_code: '',
  sms_credential_id: '',
}

export function Channels() {
  const [config, setConfig] = useState<TenantNotificationConfig>(EMPTY_CONFIG)
  const [profile, setProfile] = useState<TenantInfo>({
    tenant_id: '',
    name: '',
    status: 'active',
    contact_name: '',
    contact_phone: '',
    contact_email: '',
  })
  const [showWebhook, setShowWebhook] = useState(false)
  const [state, setState] = useState<Record<string, SaveState>>({})
  const [message, setMessage] = useState<Record<string, string>>({})
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [configResult, profileResult] = await Promise.all([
        tenantSettingsApi.getNotificationConfig(),
        tenantSettingsApi.getProfile(),
      ])
      setConfig({ ...EMPTY_CONFIG, ...configResult.config, tenant_id: configResult.tenant_id })
      setProfile(profileResult)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const save = async (section: string, patch: Partial<TenantNotificationConfig>) => {
    const next = { ...config, ...patch }
    if (next.wechat_webhook_url && !next.wechat_webhook_url.startsWith('https://qyapi.weixin.qq.com/')) {
      setState((prev) => ({ ...prev, [section]: 'error' }))
      setMessage((prev) => ({ ...prev, [section]: '请输入企业微信官方群机器人地址（https://qyapi.weixin.qq.com/...）' }))
      return
    }
    setState((prev) => ({ ...prev, [section]: 'saving' }))
    setMessage((prev) => ({ ...prev, [section]: '' }))
    setError(null)
    try {
      const result = await tenantSettingsApi.updateNotificationConfig(next)
      setConfig({ ...EMPTY_CONFIG, ...result.config, tenant_id: result.tenant_id })
      setState((prev) => ({ ...prev, [section]: 'saved' }))
      setMessage((prev) => ({ ...prev, [section]: '已保存，后续通知将使用新配置' }))
    } catch (err) {
      setState((prev) => ({ ...prev, [section]: 'error' }))
      setMessage((prev) => ({ ...prev, [section]: getErrorMessage(err) }))
    }
  }

  const saveProfile = async () => {
    setState((prev) => ({ ...prev, profile: 'saving' }))
    setMessage((prev) => ({ ...prev, profile: '' }))
    setError(null)
    try {
      const result = await tenantSettingsApi.updateProfile({
        name: profile.name,
        contact_name: profile.contact_name,
        contact_phone: profile.contact_phone,
        contact_email: profile.contact_email,
      })
      setProfile(result)
      setState((prev) => ({ ...prev, profile: 'saved' }))
      setMessage((prev) => ({ ...prev, profile: '企业资料已保存' }))
    } catch (err) {
      setState((prev) => ({ ...prev, profile: 'error' }))
      setMessage((prev) => ({ ...prev, profile: getErrorMessage(err) }))
    }
  }

  const statusBadge = (configured: boolean) =>
    configured ? <Badge variant="success">已配置</Badge> : <Badge variant="default">未配置</Badge>

  const feedback = (section: string) => {
    const current = state[section]
    if (current === 'saved') return <p className="mt-3 text-xs text-emerald-600">{message[section]}</p>
    if (current === 'error') return <p className="mt-3 text-xs text-red-600">{message[section]}</p>
    return null
  }

  return (
    <PageShell
      eyebrow="SETTINGS"
      title="通知渠道配置"
      description="配置只对当前租户生效，保存后立即用于后续通知。原始 AK/SK 请放在环境变量或密钥管理服务中。"
    >
      {error ? (
        <div role="alert" className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      {loading ? (
        <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-slate-500">
          正在加载渠道配置...
        </div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-2">
          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm lg:col-span-2">
            <div className="flex items-center gap-3">
              <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
                <Building2 className="h-5 w-5" />
              </span>
              <div>
                <h2 className="text-lg font-semibold text-slate-900">企业资料</h2>
                <p className="text-xs text-slate-500">
                  用于账单抬头、支付回执与运营联系，邮箱可接收支付成功通知
                </p>
              </div>
            </div>

            <div className="mt-5 grid gap-4 sm:grid-cols-2">
              <label className="block text-sm font-medium text-slate-700">
                企业名称
                <input
                  value={profile.name}
                  onChange={(event) => setProfile((prev) => ({ ...prev, name: event.target.value }))}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none"
                />
              </label>
              <label className="block text-sm font-medium text-slate-700">
                联系人
                <input
                  value={profile.contact_name ?? ''}
                  onChange={(event) =>
                    setProfile((prev) => ({ ...prev, contact_name: event.target.value }))
                  }
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none"
                  placeholder="可选"
                />
              </label>
              <label className="block text-sm font-medium text-slate-700">
                联系电话
                <input
                  value={profile.contact_phone ?? ''}
                  onChange={(event) =>
                    setProfile((prev) => ({ ...prev, contact_phone: event.target.value }))
                  }
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none"
                  placeholder="可选"
                />
              </label>
              <label className="block text-sm font-medium text-slate-700">
                联系邮箱
                <input
                  type="email"
                  value={profile.contact_email ?? ''}
                  onChange={(event) =>
                    setProfile((prev) => ({ ...prev, contact_email: event.target.value }))
                  }
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none"
                  placeholder="用于接收支付回执"
                />
              </label>
            </div>
            <Button
              className="mt-4"
              size="sm"
              loading={state.profile === 'saving'}
              onClick={() => void saveProfile()}
            >
              保存企业资料
            </Button>
            {feedback('profile')}
          </section>
          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-50 text-emerald-600">
                  <MessageSquare className="h-5 w-5" />
                </span>
                <div>
                  <h2 className="text-lg font-semibold text-slate-900">企业微信群通知</h2>
                  <p className="text-xs text-slate-500">用于群发通知与岗位消息</p>
                </div>
              </div>
              {statusBadge(Boolean(config.wechat_webhook_url))}
            </div>

            <label className="mt-5 block text-sm font-medium text-slate-700">
              群机器人 Webhook
              <div className="mt-1 flex gap-2">
                <input
                  type={showWebhook ? 'text' : 'password'}
                  value={config.wechat_webhook_url}
                  onChange={(event) =>
                    setConfig((prev) => ({ ...prev, wechat_webhook_url: event.target.value }))
                  }
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none"
                  placeholder="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=..."
                />
                <button
                  type="button"
                  onClick={() => setShowWebhook((value) => !value)}
                  className="shrink-0 rounded-lg border border-slate-300 px-3 text-slate-600 hover:bg-slate-50"
                  aria-label={showWebhook ? '隐藏 Webhook' : '显示 Webhook'}
                >
                  {showWebhook ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </label>
            <p className="mt-2 text-xs text-slate-500">
              未配置时该渠道会失败关闭，不会回退到硬编码地址。仅接受企业微信官方群机器人地址。
            </p>
            <Button
              className="mt-4"
              size="sm"
              loading={state.wechat === 'saving'}
              onClick={() => void save('wechat', { wechat_webhook_url: config.wechat_webhook_url.trim() })}
            >
              保存企业微信配置
            </Button>
            {feedback('wechat')}
          </section>

          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-sky-50 text-sky-600">
                  <Send className="h-5 w-5" />
                </span>
                <div>
                  <h2 className="text-lg font-semibold text-slate-900">短信服务</h2>
                  <p className="text-xs text-slate-500">用于游客与员工短信通知</p>
                </div>
              </div>
              {statusBadge(Boolean(config.sms_provider || config.sms_template_code))}
            </div>

            <div className="mt-5 space-y-4">
              <label className="block text-sm font-medium text-slate-700">
                短信服务商
                <select
                  value={config.sms_provider}
                  onChange={(event) =>
                    setConfig((prev) => ({ ...prev, sms_provider: event.target.value }))
                  }
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none"
                >
                  <option value="">未配置（沿用系统设置）</option>
                  <option value="aliyun">阿里云短信</option>
                  <option value="mock">演示通道（不会发送真实短信）</option>
                </select>
              </label>
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="block text-sm font-medium text-slate-700">
                  短信签名
                  <input
                    value={config.sms_sign_name}
                    onChange={(event) =>
                      setConfig((prev) => ({ ...prev, sms_sign_name: event.target.value }))
                    }
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none"
                    placeholder="例如：江西锌鑫"
                  />
                </label>
                <label className="block text-sm font-medium text-slate-700">
                  通知模板 CODE
                  <input
                    value={config.sms_template_code}
                    onChange={(event) =>
                      setConfig((prev) => ({ ...prev, sms_template_code: event.target.value }))
                    }
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none"
                    placeholder="例如：SMS_512540357"
                  />
                </label>
              </div>
            </div>
            <p className="mt-2 text-xs text-slate-500">
              签名与模板需先在短信服务商控制台完成审核；未配置时发送链路将沿用系统级设置。
            </p>
            <Button
              className="mt-4"
              size="sm"
              loading={state.sms === 'saving'}
              onClick={() =>
                void save('sms', {
                  sms_provider: config.sms_provider,
                  sms_sign_name: config.sms_sign_name.trim(),
                  sms_template_code: config.sms_template_code.trim(),
                })
              }
            >
              保存短信配置
            </Button>
            {feedback('sms')}
          </section>

          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm lg:col-span-2">
            <div className="flex items-center gap-3">
              <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-100 text-slate-600">
                <ShieldCheck className="h-5 w-5" />
              </span>
              <div>
                <h2 className="text-lg font-semibold text-slate-900">凭证与安全</h2>
                <p className="text-xs text-slate-500">系统只保存凭证引用 ID，原始密钥不会落库</p>
              </div>
            </div>

            <div className="mt-5 grid gap-4 sm:grid-cols-2">
              <label className="block text-sm font-medium text-slate-700">
                短信凭证引用 ID
                <input
                  value={config.sms_credential_id}
                  onChange={(event) =>
                    setConfig((prev) => ({ ...prev, sms_credential_id: event.target.value }))
                  }
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none"
                  placeholder="例如：qiankun-aliyun-sms-prod"
                />
              </label>
              <div className="text-sm text-slate-600">
                <span className="block font-medium text-slate-700">最后更新时间</span>
                <span className="mt-1 block">{config.updated_at || '尚未保存'}</span>
              </div>
            </div>
            <p className="mt-2 text-xs text-slate-500">
              原始 AK/SK 请放在环境变量或密钥管理服务中，不要写入本页面。
            </p>
            <Button
              className="mt-4"
              size="sm"
              loading={state.credential === 'saving'}
              onClick={() => void save('credential', { sms_credential_id: config.sms_credential_id.trim() })}
            >
              保存凭证引用
            </Button>
            {feedback('credential')}
          </section>
        </div>
      )}
    </PageShell>
  )
}
