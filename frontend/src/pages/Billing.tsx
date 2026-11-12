import { useCallback, useEffect, useMemo, useState } from 'react'
import { CheckCircle2, CreditCard, Crown, Sparkles } from 'lucide-react'
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

function UsageMeter({ used, quota }: { used: number; quota: number }) {
  const ratio = quota > 0 ? Math.min(used / quota, 1) : 0
  const percent = Math.round(ratio * 100)
  const tone = percent >= 90 ? 'bg-red-500' : percent >= 70 ? 'bg-amber-500' : 'bg-sky-500'
  return (
    <div>
      <div className="flex items-center justify-between text-sm text-slate-600">
        <span>本月短信用量</span>
        <span className="font-medium text-slate-900">
          {used} / {quota}
        </span>
      </div>
      <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-slate-100">
        <div className={`h-full rounded-full ${tone}`} style={{ width: `${percent}%` }} />
      </div>
      <p className="mt-1 text-xs text-slate-500">剩余 {Math.max(quota - used, 0)} 条，额度按自然月重置</p>
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
      eyebrow="BILLING"
      title="套餐与账单"
      description="按需购买短信额度与团队席位。支付成功后立即生效，额度按自然月重置。"
      actions={
        canPurchase && catalog?.payment_methods.length ? (
          <label className="flex items-center gap-2 text-sm text-slate-600">
            支付方式
            <select
              value={provider}
              onChange={(event) => setProvider(event.target.value)}
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:border-sky-500 focus:outline-none"
            >
              {catalog.payment_methods.map((method) => (
                <option key={method.code} value={method.code}>
                  {method.name}
                </option>
              ))}
            </select>
          </label>
        ) : (
          <span className="text-sm text-slate-500">如需升级套餐，请联系企业管理员</span>
        )
      }
    >
      {error ? (
        <div role="alert" className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}
      {notice ? (
        <div className="mb-6 rounded-lg border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-800">
          {notice}
        </div>
      ) : null}

      {loading && !subscription ? (
        <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-slate-500">
          正在加载套餐信息...
        </div>
      ) : null}

      {subscription ? (
        <div className="mb-8 grid gap-5 lg:grid-cols-[1.4fr_1fr]">
          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-600">当前套餐</p>
                <div className="mt-2 flex items-center gap-2">
                  <Crown className="h-5 w-5 text-amber-500" />
                  <h2 className="text-2xl font-semibold text-slate-900">{subscription.plan.name}</h2>
                  <Badge variant={subscription.subscription.status === 'active' ? 'success' : 'info'}>
                    {STATUS_LABELS[subscription.subscription.status] ?? subscription.subscription.status}
                  </Badge>
                </div>
                <p className="mt-2 text-sm text-slate-500">
                  到期时间：{formatDate(subscription.subscription.current_period_end)}
                </p>
              </div>
              <div className="text-right">
                <div className="text-3xl font-semibold text-slate-900">
                  ¥{subscription.plan.price_yuan}
                </div>
                <div className="text-xs text-slate-500">/ {subscription.plan.period_days} 天</div>
              </div>
            </div>

            <div className="mt-6">
              <UsageMeter used={subscription.usage.sms_used} quota={subscription.usage.sms_quota} />
            </div>

            <ul className="mt-6 grid gap-2 text-sm text-slate-600 sm:grid-cols-2">
              {subscription.plan.features.map((feature) => (
                <li key={feature} className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                  {feature}
                </li>
              ))}
            </ul>

            {!subscription.plan.is_free && canPurchase ? (
              <div className="mt-6 flex items-center justify-between rounded-lg bg-slate-50 px-4 py-3">
                <span className="text-sm text-slate-600">
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

          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="flex items-center gap-2 text-lg font-semibold text-slate-900">
              <CreditCard className="h-5 w-5 text-sky-600" />
              购买说明
            </h3>
            <ul className="mt-4 space-y-3 text-sm text-slate-600">
              <li>• 支付成功后套餐立即生效，同一套餐续费将顺延到期时间。</li>
              <li>• 升级套餐立即生效，剩余额度不跨套餐保留。</li>
              <li>• 试用期结束后自动回落到免费版额度，不会中断通知链路。</li>
              <li>• 企业微信渠道不消耗短信额度。</li>
            </ul>
            {mockOrder && canPurchase ? (
              <div className="mt-5 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
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
        <div className="mb-4 flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-sky-600" />
          <h2 className="text-xl font-semibold text-slate-900">选择套餐</h2>
        </div>
        <div className="grid gap-5 md:grid-cols-3">
          {paidPlans.map((plan) => {
            const isCurrent = plan.code === currentPlanCode
            return (
              <article
                key={plan.code}
                className={`relative flex flex-col rounded-2xl border bg-white p-6 shadow-sm transition ${
                  isCurrent ? 'border-sky-400 ring-2 ring-sky-100' : 'border-slate-200'
                }`}
              >
                {isCurrent ? (
                  <span className="absolute -top-3 left-6 rounded-full bg-sky-600 px-3 py-1 text-xs font-medium text-white">
                    当前套餐
                  </span>
                ) : null}
                <h3 className="text-lg font-semibold text-slate-900">{plan.name}</h3>
                <div className="mt-3 flex items-baseline gap-1">
                  <span className="text-3xl font-bold text-slate-900">¥{plan.price_yuan}</span>
                  <span className="text-sm text-slate-500">/ {plan.period_days} 天</span>
                </div>
                <p className="mt-1 text-sm text-slate-500">{plan.sms_quota.toLocaleString()} 条短信</p>
                <ul className="mt-4 flex-1 space-y-2 text-sm text-slate-600">
                  {plan.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-2">
                      <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" />
                      {feature}
                    </li>
                  ))}
                </ul>
                {canPurchase ? (
                  <Button
                    className="mt-6 w-full"
                    variant={isCurrent ? 'secondary' : 'primary'}
                    loading={busyPlan === plan.code}
                    onClick={() => void startPurchase(plan)}
                  >
                    {isCurrent ? '续费当前套餐' : '立即订阅'}
                  </Button>
                ) : (
                  <p className="mt-6 rounded-lg bg-slate-50 px-3 py-2 text-center text-xs text-slate-500">
                    联系管理员升级
                  </p>
                )}
              </article>
            )
          })}
        </div>
      </section>

      <section className="mt-10">
        <h2 className="mb-4 text-xl font-semibold text-slate-900">订单记录</h2>
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">订单号</th>
                <th className="px-4 py-3">套餐</th>
                <th className="px-4 py-3">金额</th>
                <th className="px-4 py-3">支付方式</th>
                <th className="px-4 py-3">状态</th>
                <th className="px-4 py-3">创建时间</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {orders.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-slate-500">
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
                    <tr key={order.order_no}>
                      <td className="px-4 py-3 font-mono text-xs text-slate-600">{order.order_no}</td>
                      <td className="px-4 py-3">{order.plan_code}</td>
                      <td className="px-4 py-3">¥{(order.amount_cents / 100).toFixed(2)}</td>
                      <td className="px-4 py-3">{order.provider}</td>
                      <td className="px-4 py-3">
                        <Badge variant={status.variant}>{status.label}</Badge>
                      </td>
                      <td className="px-4 py-3 text-slate-500">{formatDate(order.created_at)}</td>
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
