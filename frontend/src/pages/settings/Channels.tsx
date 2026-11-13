import { useCallback, useEffect, useState } from 'react'
import { Building2, Eye, EyeOff, FileText, MessageSquare, Send, ShieldCheck } from 'lucide-react'
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

const inputClass =
  'mt-1 w-full rounded-control border border-paper-300 bg-white px-3 py-2 text-sm text-paper-900 transition-colors focus:border-accent-600 focus:outline-none focus:ring-2 focus:ring-accent-100'

const cardClass = 'rounded-card border border-paper-200 bg-white p-5 shadow-card'

function SectionHeading({
  icon: Icon,
  title,
  hint,
  status,
}: {
  icon: typeof Building2
  title: string
  hint: string
  status?: React.ReactNode
}) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div className="flex items-start gap-2.5">
        <Icon className="mt-0.5 h-4 w-4 text-paper-500" />
        <div>
          <h2 className="text-base font-semibold text-paper-900">{title}</h2>
          <p className="mt-0.5 text-xs text-paper-500">{hint}</p>
        </div>
      </div>
      {status}
    </div>
  )
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

  const saveInvoice = async () => {
    setState((prev) => ({ ...prev, invoice: 'saving' }))
    setMessage((prev) => ({ ...prev, invoice: '' }))
    setError(null)
    try {
      const result = await tenantSettingsApi.updateProfile({
        invoice_title: profile.invoice_title ?? '',
        tax_id: profile.tax_id ?? '',
        invoice_address: profile.invoice_address ?? '',
        invoice_phone: profile.invoice_phone ?? '',
        invoice_bank_name: profile.invoice_bank_name ?? '',
        invoice_bank_account: profile.invoice_bank_account ?? '',
        invoice_email: profile.invoice_email ?? '',
      })
      setProfile(result)
      setState((prev) => ({ ...prev, invoice: 'saved' }))
      setMessage((prev) => ({ ...prev, invoice: '开票信息已保存' }))
    } catch (err) {
      setState((prev) => ({ ...prev, invoice: 'error' }))
      setMessage((prev) => ({ ...prev, invoice: getErrorMessage(err) }))
    }
  }

  const statusBadge = (configured: boolean) =>
    configured ? <Badge variant="success">已配置</Badge> : <Badge variant="default">未配置</Badge>

  const feedback = (section: string) => {
    const current = state[section]
    if (current === 'saved') return <p className="mt-3 text-xs text-success-700">{message[section]}</p>
    if (current === 'error') return <p className="mt-3 text-xs text-danger-700">{message[section]}</p>
    return null
  }

  return (
    <PageShell
      title="通知渠道配置"
      description="配置只对当前租户生效，保存后立即用于后续通知。原始 AK/SK 请放在环境变量或密钥管理服务中。"
    >
      {error ? (
        <div role="alert" className="mb-6 rounded-control border border-danger-200 bg-danger-50 px-4 py-3 text-sm text-danger-700">
          {error}
        </div>
      ) : null}

      {loading ? (
        <div className="rounded-card border border-paper-200 bg-white p-8 text-center text-sm text-paper-500">
          正在加载渠道配置
        </div>
      ) : (
        <div className="grid gap-5 lg:grid-cols-2">
          <section className={`${cardClass} lg:col-span-2`}>
            <SectionHeading
              icon={Building2}
              title="企业资料"
              hint="用于账单抬头、支付回执与运营联系，邮箱可接收支付成功通知"
            />

            <div className="mt-5 grid gap-4 sm:grid-cols-2">
              <label className="block text-sm font-medium text-paper-700">
                企业名称
                <input
                  value={profile.name}
                  onChange={(event) => setProfile((prev) => ({ ...prev, name: event.target.value }))}
                  className={inputClass}
                />
              </label>
              <label className="block text-sm font-medium text-paper-700">
                联系人
                <input
                  value={profile.contact_name ?? ''}
                  onChange={(event) =>
                    setProfile((prev) => ({ ...prev, contact_name: event.target.value }))
                  }
                  className={inputClass}
                  placeholder="可选"
                />
              </label>
              <label className="block text-sm font-medium text-paper-700">
                联系电话
                <input
                  value={profile.contact_phone ?? ''}
                  onChange={(event) =>
                    setProfile((prev) => ({ ...prev, contact_phone: event.target.value }))
                  }
                  className={inputClass}
                  placeholder="可选"
                />
              </label>
              <label className="block text-sm font-medium text-paper-700">
                联系邮箱
                <input
                  type="email"
                  value={profile.contact_email ?? ''}
                  onChange={(event) =>
                    setProfile((prev) => ({ ...prev, contact_email: event.target.value }))
                  }
                  className={inputClass}
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

          <section className={`${cardClass} lg:col-span-2`}>
            <SectionHeading
              icon={FileText}
              title="开票信息"
              hint="用于支付成功后开具发票；收票邮箱可接收电子发票"
            />

            <div className="mt-5 grid gap-4 sm:grid-cols-2">
              <label className="block text-sm font-medium text-paper-700">
                发票抬头
                <input
                  value={profile.invoice_title ?? ''}
                  onChange={(event) =>
                    setProfile((prev) => ({ ...prev, invoice_title: event.target.value }))
                  }
                  className={inputClass}
                  placeholder="与企业营业执照一致"
                />
              </label>
              <label className="block text-sm font-medium text-paper-700">
                税号
                <input
                  value={profile.tax_id ?? ''}
                  onChange={(event) =>
                    setProfile((prev) => ({ ...prev, tax_id: event.target.value }))
                  }
                  className={inputClass}
                  placeholder="统一社会信用代码"
                />
              </label>
              <label className="block text-sm font-medium text-paper-700">
                注册地址
                <input
                  value={profile.invoice_address ?? ''}
                  onChange={(event) =>
                    setProfile((prev) => ({ ...prev, invoice_address: event.target.value }))
                  }
                  className={inputClass}
                  placeholder="可选"
                />
              </label>
              <label className="block text-sm font-medium text-paper-700">
                注册电话
                <input
                  value={profile.invoice_phone ?? ''}
                  onChange={(event) =>
                    setProfile((prev) => ({ ...prev, invoice_phone: event.target.value }))
                  }
                  className={inputClass}
                  placeholder="可选"
                />
              </label>
              <label className="block text-sm font-medium text-paper-700">
                开户银行
                <input
                  value={profile.invoice_bank_name ?? ''}
                  onChange={(event) =>
                    setProfile((prev) => ({ ...prev, invoice_bank_name: event.target.value }))
                  }
                  className={inputClass}
                  placeholder="可选"
                />
              </label>
              <label className="block text-sm font-medium text-paper-700">
                银行账号
                <input
                  value={profile.invoice_bank_account ?? ''}
                  onChange={(event) =>
                    setProfile((prev) => ({ ...prev, invoice_bank_account: event.target.value }))
                  }
                  className={inputClass}
                  placeholder="可选"
                />
              </label>
              <label className="block text-sm font-medium text-paper-700 sm:col-span-2">
                收票邮箱
                <input
                  type="email"
                  value={profile.invoice_email ?? ''}
                  onChange={(event) =>
                    setProfile((prev) => ({ ...prev, invoice_email: event.target.value }))
                  }
                  className={inputClass}
                  placeholder="用于接收电子发票"
                />
              </label>
            </div>
            <Button
              className="mt-4"
              size="sm"
              loading={state.invoice === 'saving'}
              onClick={() => void saveInvoice()}
            >
              保存开票信息
            </Button>
            {feedback('invoice')}
          </section>

          <section className={cardClass}>
            <SectionHeading
              icon={MessageSquare}
              title="企业微信群通知"
              hint="用于群发通知与岗位消息"
              status={statusBadge(Boolean(config.wechat_webhook_url))}
            />

            <label className="mt-5 block text-sm font-medium text-paper-700">
              群机器人 Webhook
              <div className="mt-1 flex gap-2">
                <input
                  type={showWebhook ? 'text' : 'password'}
                  value={config.wechat_webhook_url}
                  onChange={(event) =>
                    setConfig((prev) => ({ ...prev, wechat_webhook_url: event.target.value }))
                  }
                  className={`${inputClass} mt-0`}
                  placeholder="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=..."
                />
                <button
                  type="button"
                  onClick={() => setShowWebhook((value) => !value)}
                  className="shrink-0 rounded-control border border-paper-300 px-3 text-paper-500 transition-colors hover:bg-paper-50 hover:text-paper-900"
                  aria-label={showWebhook ? '隐藏 Webhook' : '显示 Webhook'}
                >
                  {showWebhook ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </label>
            <p className="mt-2 text-xs text-paper-500">
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

          <section className={cardClass}>
            <SectionHeading
              icon={Send}
              title="短信服务"
              hint="用于游客与员工短信通知"
              status={statusBadge(Boolean(config.sms_provider || config.sms_template_code))}
            />

            <div className="mt-5 space-y-4">
              <label className="block text-sm font-medium text-paper-700">
                短信服务商
                <select
                  value={config.sms_provider}
                  onChange={(event) =>
                    setConfig((prev) => ({ ...prev, sms_provider: event.target.value }))
                  }
                  className={inputClass}
                >
                  <option value="">未配置（沿用系统设置）</option>
                  <option value="aliyun">阿里云短信</option>
                  <option value="mock">演示通道（不会发送真实短信）</option>
                </select>
              </label>
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="block text-sm font-medium text-paper-700">
                  短信签名
                  <input
                    value={config.sms_sign_name}
                    onChange={(event) =>
                      setConfig((prev) => ({ ...prev, sms_sign_name: event.target.value }))
                    }
                    className={inputClass}
                    placeholder="例如：江西锌鑫"
                  />
                </label>
                <label className="block text-sm font-medium text-paper-700">
                  通知模板 CODE
                  <input
                    value={config.sms_template_code}
                    onChange={(event) =>
                      setConfig((prev) => ({ ...prev, sms_template_code: event.target.value }))
                    }
                    className={inputClass}
                    placeholder="例如：SMS_512540357"
                  />
                </label>
              </div>
            </div>
            <p className="mt-2 text-xs text-paper-500">
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

          <section className={`${cardClass} lg:col-span-2`}>
            <SectionHeading
              icon={ShieldCheck}
              title="凭证与安全"
              hint="系统只保存凭证引用 ID，原始密钥不会落库"
            />

            <div className="mt-5 grid gap-4 sm:grid-cols-2">
              <label className="block text-sm font-medium text-paper-700">
                短信凭证引用 ID
                <input
                  value={config.sms_credential_id}
                  onChange={(event) =>
                    setConfig((prev) => ({ ...prev, sms_credential_id: event.target.value }))
                  }
                  className={inputClass}
                  placeholder="例如：qiankun-aliyun-sms-prod"
                />
              </label>
              <div className="text-sm text-paper-600">
                <span className="block font-medium text-paper-700">最后更新时间</span>
                <span className="mt-1 block tabular-nums">{config.updated_at || '尚未保存'}</span>
              </div>
            </div>
            <p className="mt-2 text-xs text-paper-500">
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
