import { useCallback, useEffect, useMemo, useState } from 'react'
import { CheckCircle2 } from 'lucide-react'
import { PageShell } from '../components/PageShell'
import { Button } from '../components/Button'
import { Badge } from '../components/Badge'
import { getErrorMessage } from '../services/api'
import { useSession } from '../context/SessionContext'
import {
  billingApi,
  type BillingOrder,
  type Plan,
  type PlansResponse,
  type SubscriptionResponse,
} from '../services/commercialApi'

const STATUS_LABELS: Record<string, string> = {
  trialing: '试用中',
  active: '生效中',
  expired: '已到期',
  cancelled: '已取消',
}

const ORDER_STATUS_LABELS: Record<string, { label: string; variant: 'success' | 'warning' | 'danger' | 'default' }> = {
  pending: { label: '待支付', variant: 'warning' },
  paid: { label: '已支付', variant: 'success' },
  closed: { label: '已关闭', variant: 'default' },
  failed: { label: '支付失败', variant: 'danger' },
  refunded: { label: '已退款', variant: 'default' },
}

function formatDate(raw: string): string {
  if (!raw) return '-'
  const date = new Date(raw)
  if (Number.isNaN(date.getTime())) return raw
  return date.toLocaleString('zh-CN', { hour12: false })
}

function formatMoney(cents: number): string {
  return `¥${(cents / 100).toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`
}

function formatYuan(raw: string): string {
  const value = Number(raw)
  if (!Number.isFinite(value)) return `¥${raw}`
  return `¥${value.toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`
}

function formatCount(value: number): string {
  return value.toLocaleString('zh-CN')
}

function UsageMeter({ used, quota }: { used: number; quota: number }) {
  const ratio = quota > 0 ? Math.min(used / quota, 1) : 0
  const percent = Math.round(ratio * 100)
  const tone = percent >= 90 ? 'bg-danger-600' : percent >= 70 ? 'bg-warning-500' : 'bg-accent-600'
  return (
    <div>
      <div className="flex items-center justify-between text-sm text-paper-600">
        <span>本月短信用量</span>
        <span className="font-medium tabular-nums text-paper-900">
          {formatCount(used)} / {formatCount(quota)}
        </span>
      </div>
      <div className="mt-2 h-1.5 w-full overflow-hidden rounded-sm bg-paper-100">
        <div className={`h-full ${tone}`} style={{ width: `${percent}%` }} />
      </div>
      <p className="mt-1 text-xs text-paper-500">
        剩余 {formatCount(Math.max(quota - used, 0))} 条，额度按自然月重置
      </p>
    </div>
  )
}

export function Billing() {
  const { user } = useSession()
  const canPurchase = user?.role === 'admin' || user?.role === 'operator'
  const [catalog, setCatalog] = useState<PlansResponse | null>(null)
  const [subscription, setSubscription] = useState<SubscriptionResponse | null>(null)
  const [orders, setOrders] = useState<BillingOrder[]>([])
  const [provider, setProvider] = useState('')
  const [busyPlan, setBusyPlan] = useState('')
  const [mockOrder, setMockOrder] = useState<BillingOrder | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [plans, current, orderList] = await Promise.all([
        billingApi.getPlans(),
        billingApi.getSubscription(),
        billingApi.listOrders(),
      ])
      setCatalog(plans)
      setSubscription(current)
      setOrders(orderList.items)
      setProvider((existing) => existing || plans.payment_methods[0]?.code || '')
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    if (params.get('paid') === '1') {
      setNotice('支付已提交，正在确认到账状态。')
    }
  }, [])

  const currentPlanCode = subscription?.plan.code ?? ''
  const paidPlans = useMemo(
    () => (catalog?.plans ?? []).filter((plan) => !plan.is_free),
    [catalog],
  )

  const startPurchase = async (plan: Plan) => {
    if (!provider) {
      setError('请先选择支付方式')
      return
    }
    setBusyPlan(plan.code)
    setError(null)
    setNotice(null)
    try {
      const order = await billingApi.createOrder(plan.code, provider)
      if (/^https?:\/\//i.test(order.pay_url)) {
        window.location.assign(order.pay_url)
        return
      }
      setMockOrder(order)
      setNotice('订单已创建，开发环境可使用“模拟支付”完成到账。')
      await load()
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setBusyPlan('')
    }
  }

  const completeMockPayment = async () => {
    if (!mockOrder) return
    setBusyPlan(mockOrder.plan_code)
    try {
      await billingApi.mockPay(mockOrder.order_no)
      setMockOrder(null)
      setNotice('模拟支付成功，套餐已生效。')
      await load()
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setBusyPlan('')
    }
  }

  const toggleRenewal = async () => {
    if (!subscription) return
    setBusyPlan('renewal')
    try {
      if (subscription.subscription.cancel_at_period_end) {
        await billingApi.resumeSubscription()
        setNotice('已恢复自动续费。')
      } else {
        await billingApi.cancelSubscription()
        setNotice('已设置到期后取消，当前周期内仍可正常使用。')
      }
      await load()
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setBusyPlan('')
    }
  }

  return (
    <PageShell
      title="套餐与账单"
      description="按需购买短信额度与团队席位。支付成功后立即生效，额度按自然月重置。"
      actions={
        canPurchase && catalog?.payment_methods.length ? (
          <label className="flex items-center gap-2 text-sm text-paper-600">
            支付方式
            <select
              value={provider}
              onChange={(event) => setProvider(event.target.value)}
              className="rounded-control border border-paper-300 bg-white px-3 py-2 text-sm text-paper-900 focus:border-accent-600 focus:outline-none"
            >
              {catalog.payment_methods.map((method) => (
                <option key={method.code} value={method.code}>
                  {method.name}
                </option>
              ))}
            </select>
          </label>
        ) : (
          <span className="text-sm text-paper-500">如需升级套餐，请联系企业管理员</span>
        )
      }
    >
      {error ? (
        <div role="alert" className="mb-6 rounded-control border border-danger-200 bg-danger-50 px-4 py-3 text-sm text-danger-700">
          {error}
        </div>
      ) : null}
      {notice ? (
        <div className="mb-6 rounded-control border border-accent-200 bg-accent-50 px-4 py-3 text-sm text-accent-800">
          {notice}
        </div>
      ) : null}

      {loading && !subscription ? (
        <div className="rounded-card border border-paper-200 bg-white p-8 text-center text-sm text-paper-500">
          正在加载套餐信息
        </div>
      ) : null}

      {subscription ? (
        <div className="mb-8 grid gap-5 lg:grid-cols-[1.4fr_1fr]">
          <section className="rounded-card border border-paper-200 bg-white p-5 shadow-card">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm text-paper-500">当前套餐</p>
                <div className="mt-2 flex items-center gap-2">
                  <h2 className="text-lg font-semibold text-paper-900">{subscription.plan.name}</h2>
                  <Badge variant={subscription.subscription.status === 'active' ? 'success' : 'info'}>
                    {STATUS_LABELS[subscription.subscription.status] ?? subscription.subscription.status}
                  </Badge>
                </div>
                <p className="mt-2 text-sm text-paper-500">
                  到期时间：{formatDate(subscription.subscription.current_period_end)}
                </p>
              </div>
              <div className="text-right">
                <div className="text-2xl font-semibold tabular-nums text-paper-900">
                  {formatYuan(subscription.plan.price_yuan)}
                </div>
                <div className="text-xs text-paper-500">/ {subscription.plan.period_days} 天</div>
              </div>
            </div>

            <div className="mt-5">
              <UsageMeter used={subscription.usage.sms_used} quota={subscription.usage.sms_quota} />
            </div>

            <ul className="mt-5 grid gap-2 text-sm text-paper-600 sm:grid-cols-2">
              {subscription.plan.features.map((feature) => (
                <li key={feature} className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-success-600" />
                  {feature}
                </li>
              ))}
            </ul>

            {!subscription.plan.is_free && canPurchase ? (
              <div className="mt-5 flex items-center justify-between gap-4 rounded-control bg-paper-50 px-4 py-3">
                <span className="text-sm text-paper-600">
                  {subscription.subscription.cancel_at_period_end
                    ? '已设置到期后取消，当前周期内仍可使用全部能力'
                    : '套餐将自动续费，可在到期前随时取消'}
                </span>
                <Button
                  size="sm"
                  variant="secondary"
                  loading={busyPlan === 'renewal'}
                  onClick={() => void toggleRenewal()}
                >
                  {subscription.subscription.cancel_at_period_end ? '恢复续费' : '到期后取消'}
                </Button>
              </div>
            ) : null}
          </section>

          <section className="rounded-card border border-paper-200 bg-white p-5 shadow-card">
            <h3 className="text-base font-semibold text-paper-900">购买说明</h3>
            <ul className="mt-4 list-disc space-y-2 pl-4 text-sm text-paper-600">
              <li>支付成功后套餐立即生效，同一套餐续费将顺延到期时间。</li>
              <li>升级套餐立即生效，剩余额度不跨套餐保留。</li>
              <li>试用期结束后自动回落到免费版额度，不会中断通知链路。</li>
              <li>企业微信渠道不消耗短信额度。</li>
              <li>发票信息由企业管理员在「通知渠道 → 开票信息」维护。</li>
            </ul>
            {mockOrder && canPurchase ? (
              <div className="mt-5 rounded-control border border-warning-200 bg-warning-50 p-4 text-sm text-warning-800">
                <p>订单 {mockOrder.order_no} 已创建（开发环境）。</p>
                <Button
                  className="mt-3 w-full"
                  variant="success"
                  size="sm"
                  loading={busyPlan === mockOrder.plan_code}
                  onClick={() => void completeMockPayment()}
                >
                  模拟支付并激活
                </Button>
              </div>
            ) : null}
          </section>
        </div>
      ) : null}

      <section>
        <h2 className="mb-4 text-lg font-semibold text-paper-900">选择套餐</h2>
        <div className="grid gap-5 md:grid-cols-3">
          {paidPlans.map((plan) => {
            const isCurrent = plan.code === currentPlanCode
            return (
              <article
                key={plan.code}
                className={`flex flex-col rounded-card border bg-white p-5 shadow-card ${
                  isCurrent ? 'border-accent-600' : 'border-paper-200'
                }`}
              >
                {isCurrent ? <p className="text-xs font-medium text-accent-700">当前套餐</p> : null}
                <h3 className="mt-1 text-base font-semibold text-paper-900">{plan.name}</h3>
                <div className="mt-3 flex items-baseline gap-1">
                  <span className="text-2xl font-semibold tabular-nums text-paper-900">
                    {formatYuan(plan.price_yuan)}
                  </span>
                  <span className="text-sm text-paper-500">/ {plan.period_days} 天</span>
                </div>
                <p className="mt-1 text-sm text-paper-500">{formatCount(plan.sms_quota)} 条短信</p>
                <ul className="mt-4 flex-1 space-y-2 text-sm text-paper-600">
                  {plan.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-2">
                      <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-success-600" />
                      {feature}
                    </li>
                  ))}
                </ul>
                {canPurchase ? (
                  <Button
                    className="mt-5 w-full"
                    variant={isCurrent ? 'secondary' : 'primary'}
                    loading={busyPlan === plan.code}
                    onClick={() => void startPurchase(plan)}
                  >
                    {isCurrent ? '续费当前套餐' : '订阅'}
                  </Button>
                ) : (
                  <p className="mt-5 rounded-control bg-paper-50 px-3 py-2 text-center text-xs text-paper-500">
                    联系管理员升级
                  </p>
                )}
              </article>
            )
          })}
        </div>
      </section>

      <section className="mt-8">
        <h2 className="mb-4 text-lg font-semibold text-paper-900">订单记录</h2>
        <div className="overflow-hidden rounded-card border border-paper-200 bg-white shadow-card">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-paper-200 text-xs font-medium text-paper-500">
                <th className="px-5 py-3">订单号</th>
                <th className="px-5 py-3">套餐</th>
                <th className="px-5 py-3">金额</th>
                <th className="px-5 py-3">支付方式</th>
                <th className="px-5 py-3">状态</th>
                <th className="px-5 py-3">创建时间</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-paper-100">
              {orders.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-5 py-8 text-center text-sm text-paper-500">
                    暂无订单
                  </td>
                </tr>
              ) : (
                orders.map((order) => {
                  const status = ORDER_STATUS_LABELS[order.status] ?? {
                    label: order.status,
                    variant: 'default' as const,
                  }
                  return (
                    <tr key={order.order_no} className="transition-colors hover:bg-paper-50">
                      <td className="px-5 py-3 font-mono text-xs text-paper-600">{order.order_no}</td>
                      <td className="px-5 py-3 text-paper-700">{order.plan_code}</td>
                      <td className="px-5 py-3 tabular-nums text-paper-700">
                        {formatMoney(order.amount_cents)}
                      </td>
                      <td className="px-5 py-3 text-paper-600">{order.provider}</td>
                      <td className="px-5 py-3">
                        <Badge variant={status.variant}>{status.label}</Badge>
                      </td>
                      <td className="px-5 py-3 tabular-nums text-paper-500">{formatDate(order.created_at)}</td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </section>
    </PageShell>
  )
}
