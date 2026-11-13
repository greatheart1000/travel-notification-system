import { useCallback, useEffect, useMemo, useState } from 'react'
import { Mail, RefreshCw } from 'lucide-react'
import { PageShell } from '../components/PageShell'
import { Button } from '../components/Button'
import { Badge } from '../components/Badge'
import { Modal } from '../components/Modal'
import { getErrorMessage } from '../services/api'
import { useSession } from '../context/SessionContext'
import {
  billingApi,
  operatorApi,
  type BillingOrder,
  type OperatorOverview,
  type OperatorTenant,
  type Plan,
} from '../services/commercialApi'

const ORDER_STATUS: Record<string, { label: string; variant: 'success' | 'warning' | 'danger' | 'default' }> = {
  paid: { label: '已支付', variant: 'success' },
  pending: { label: '待支付', variant: 'warning' },
  closed: { label: '已关闭', variant: 'default' },
  refunded: { label: '已退款', variant: 'default' },
  failed: { label: '失败', variant: 'danger' },
}

function money(cents: number): string {
  return `¥${(cents / 100).toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`
}

function formatDate(raw: string): string {
  if (!raw) return '-'
  const date = new Date(raw)
  return Number.isNaN(date.getTime()) ? raw : date.toLocaleString('zh-CN', { hour12: false })
}

function StatCard({
  label,
  value,
  hint,
  wide = false,
}: {
  label: string
  value: string
  hint: string
  wide?: boolean
}) {
  return (
    <div
      className={`rounded-card border border-paper-200 bg-white p-5 shadow-card ${
        wide ? 'sm:col-span-2 xl:col-span-2' : ''
      }`}
    >
      <p className="text-sm text-paper-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold tabular-nums text-paper-900">{value}</p>
      <p className="mt-1 text-xs text-paper-500">{hint}</p>
    </div>
  )
}

export function Operator() {
  const { user } = useSession()
  const [overview, setOverview] = useState<OperatorOverview | null>(null)
  const [tenants, setTenants] = useState<OperatorTenant[]>([])
  const [plans, setPlans] = useState<Plan[]>([])
  const [editing, setEditing] = useState<{ tenant: OperatorTenant; planCode: string; days: string } | null>(null)
  const [refundTarget, setRefundTarget] = useState<BillingOrder | null>(null)
  const [refundMode, setRefundMode] = useState<'manual' | 'gateway'>('manual')
  const [refundReason, setRefundReason] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState('')

  const isOperator = user?.role === 'operator'

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [overviewData, tenantData, planData] = await Promise.all([
        operatorApi.overview(),
        operatorApi.listTenants(),
        billingApi.getPlans(),
      ])
      setOverview(overviewData)
      setTenants(tenantData.items)
      setPlans(planData.plans)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (isOperator) void load()
    else setLoading(false)
  }, [isOperator, load])

  const recentOrders = useMemo(
    () => (overview?.orders ?? []).slice(0, 20),
    [overview],
  )

  const activate = async () => {
    if (!editing) return
    setBusy(`activate:${editing.tenant.tenant_id}`)
    try {
      await operatorApi.activatePlan(
        editing.tenant.tenant_id,
        editing.planCode,
        editing.days ? Number(editing.days) : undefined,
      )
      setNotice(`已为 ${editing.tenant.name} 开通 ${editing.planCode}`)
      setEditing(null)
      await load()
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setBusy('')
    }
  }

  const runDunning = async () => {
    setBusy('dunning')
    setError(null)
    try {
      const summary = await operatorApi.runDunning()
      setNotice(
        `到期提醒已处理：发送 ${summary.sent} 封，跳过 ${summary.skipped} 个，失败 ${summary.failed} 个`,
      )
      await load()
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setBusy('')
    }
  }

  const refund = async () => {
    if (!refundTarget) return
    const orderNo = refundTarget.order_no
    setBusy(`refund:${orderNo}`)
    setError(null)
    try {
      await operatorApi.refundOrder(orderNo, {
        mode: refundMode,
        reason: refundReason.trim(),
      })
      setNotice(
        refundMode === 'gateway'
          ? `订单 ${orderNo} 网关退款成功`
          : `订单 ${orderNo} 已记账退款，请在支付商户后台完成资金退回`,
      )
      setRefundTarget(null)
      setRefundReason('')
      await load()
    } catch (err) {
      setError(getErrorMessage(err))
      await load()
    } finally {
      setBusy('')
    }
  }

  if (!isOperator) {
    return (
      <PageShell title="平台运营">
        <div className="rounded-card border border-warning-200 bg-warning-50 p-5 text-sm text-warning-800">
          当前账号不是平台运营角色，无法访问运营后台。
        </div>
      </PageShell>
    )
  }

  return (
    <PageShell
      title="平台运营"
      description="查看全平台租户、订阅与收入，处理手动开通与退款。退款标记仅做账务记录，实际资金退还请在支付商户后台操作。"
      actions={
        <div className="flex items-center gap-2">
          <Button size="sm" variant="secondary" onClick={() => void runDunning()} loading={busy === 'dunning'}>
            <Mail className="h-4 w-4" /> 运行到期提醒
          </Button>
          <Button size="sm" variant="secondary" onClick={() => void load()}>
            <RefreshCw className="h-4 w-4" /> 刷新
          </Button>
        </div>
      }
    >
      {error ? (
        <div role="alert" className="mb-4 rounded-control border border-danger-200 bg-danger-50 px-4 py-3 text-sm text-danger-700">
          {error}
        </div>
      ) : null}
      {notice ? (
        <div className="mb-4 rounded-control border border-success-200 bg-success-50 px-4 py-3 text-sm text-success-700">
          {notice}
        </div>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <StatCard
          label="租户总数"
          value={String(overview?.tenants ?? '-')}
          hint={`活跃订阅 ${overview?.active_subscriptions ?? 0}`}
        />
        <StatCard
          label="本月收入"
          value={money(overview?.revenue_cents_this_period ?? 0)}
          hint={`累计 ${money(overview?.revenue_cents_total ?? 0)}`}
          wide
        />
        <StatCard
          label="已支付订单"
          value={String(overview?.paid_orders ?? '-')}
          hint={`统计周期 ${overview?.period ?? '-'}`}
        />
        <StatCard
          label="本月短信量"
          value={String(overview?.sms_used_this_period ?? '-')}
          hint="所有租户合计"
        />
      </div>

      <section className="mt-8">
        <h2 className="mb-3 text-lg font-semibold text-paper-900">租户</h2>
        <div className="overflow-hidden rounded-card border border-paper-200 bg-white shadow-card">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-paper-200 text-xs font-medium text-paper-500">
                <th className="px-5 py-3">企业</th>
                <th className="px-5 py-3">租户 ID</th>
                <th className="px-5 py-3">状态</th>
                <th className="px-5 py-3">套餐</th>
                <th className="px-5 py-3">本月短信</th>
                <th className="px-5 py-3 text-right">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-paper-100">
              {loading ? (
                <tr>
                  <td colSpan={6} className="px-5 py-8 text-center text-sm text-paper-500">
                    正在加载租户
                  </td>
                </tr>
              ) : tenants.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-5 py-8 text-center text-sm text-paper-500">
                    暂无租户
                  </td>
                </tr>
              ) : (
                tenants.map((tenant) => (
                  <tr key={tenant.tenant_id} className="transition-colors hover:bg-paper-50">
                    <td className="px-5 py-3 font-medium text-paper-900">{tenant.name}</td>
                    <td className="px-5 py-3 font-mono text-xs text-paper-500">{tenant.tenant_id}</td>
                    <td className="px-5 py-3">
                      <Badge variant={tenant.status === 'active' ? 'success' : 'danger'}>
                        {tenant.status === 'active' ? '正常' : '停用'}
                      </Badge>
                    </td>
                    <td className="px-5 py-3 text-paper-600">
                      {tenant.plan_name ?? '-'}
                      {tenant.subscription_status ? (
                        <span className="ml-1 text-xs text-paper-400">({tenant.subscription_status})</span>
                      ) : null}
                    </td>
                    <td className="px-5 py-3 tabular-nums text-paper-600">
                      {tenant.sms_used ?? 0} / {tenant.sms_quota ?? 0}
                    </td>
                    <td className="px-5 py-3 text-right">
                      <Button
                        size="sm"
                        variant="secondary"
                        loading={busy === `activate:${tenant.tenant_id}`}
                        onClick={() =>
                          setEditing({
                            tenant,
                            planCode: plans.find((plan) => !plan.is_free)?.code ?? plans[0]?.code ?? 'starter',
                            days: '',
                          })
                        }
                      >
                        调整套餐
                      </Button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mt-8">
        <h2 className="mb-3 text-lg font-semibold text-paper-900">最近订单</h2>
        <div className="overflow-hidden rounded-card border border-paper-200 bg-white shadow-card">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-paper-200 text-xs font-medium text-paper-500">
                <th className="px-5 py-3">订单号</th>
                <th className="px-5 py-3">租户</th>
                <th className="px-5 py-3">金额</th>
                <th className="px-5 py-3">状态</th>
                <th className="px-5 py-3">时间</th>
                <th className="px-5 py-3 text-right">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-paper-100">
              {recentOrders.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-5 py-8 text-center text-sm text-paper-500">
                    暂无订单
                  </td>
                </tr>
              ) : (
                recentOrders.map((order) => {
                  const status = ORDER_STATUS[order.status] ?? {
                    label: order.status,
                    variant: 'default' as const,
                  }
                  return (
                    <tr key={order.order_no} className="transition-colors hover:bg-paper-50">
                      <td className="px-5 py-3 font-mono text-xs text-paper-600">{order.order_no}</td>
                      <td className="px-5 py-3 text-paper-600">{order.tenant_id}</td>
                      <td className="px-5 py-3 tabular-nums text-paper-700">{money(order.amount_cents)}</td>
                      <td className="px-5 py-3">
                        <Badge variant={status.variant}>{status.label}</Badge>
                        {order.refund_status === 'failed' && order.refund_error ? (
                          <p className="mt-1 max-w-52 truncate text-xs text-danger-700" title={order.refund_error}>
                            退款失败：{order.refund_error}
                          </p>
                        ) : null}
                        {order.refund_status === 'refunded' ? (
                          <p className="mt-1 text-xs text-success-700">
                            退款：{order.refund_mode === 'gateway' ? '网关' : '人工记账'}
                          </p>
                        ) : null}
                      </td>
                      <td className="px-5 py-3 tabular-nums text-paper-500">{formatDate(order.created_at)}</td>
                      <td className="px-5 py-3 text-right">
                        {order.status === 'paid' ? (
                          <Button
                            size="sm"
                            variant="secondary"
                            loading={busy === `refund:${order.order_no}`}
                            onClick={() => {
                              setRefundTarget(order)
                              setRefundMode('manual')
                              setRefundReason('')
                            }}
                          >
                            处理退款
                          </Button>
                        ) : (
                          <span className="text-xs text-paper-400">-</span>
                        )}
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </section>

      <Modal
        isOpen={Boolean(editing)}
        onClose={() => setEditing(null)}
        title={editing ? `调整套餐 · ${editing.tenant.name}` : '调整套餐'}
        footer={
          <div className="flex justify-end gap-3">
            <Button variant="secondary" size="sm" onClick={() => setEditing(null)}>
              取消
            </Button>
            <Button size="sm" loading={Boolean(busy)} onClick={() => void activate()}>
              确认开通
            </Button>
          </div>
        }
      >
        {editing ? (
          <div className="space-y-4">
            <p className="text-sm text-paper-500">
              当前租户：<span className="font-medium text-paper-800">{editing.tenant.tenant_id}</span>
            </p>
            <label className="block text-sm font-medium text-paper-700">
              目标套餐
              <select
                value={editing.planCode}
                onChange={(event) =>
                  setEditing((prev) => (prev ? { ...prev, planCode: event.target.value } : prev))
                }
                className="mt-1 w-full rounded-control border border-paper-300 px-3 py-2 text-sm"
              >
                {plans.map((plan) => (
                  <option key={plan.code} value={plan.code}>
                    {plan.name}（{plan.sms_quota.toLocaleString('zh-CN')} 条短信）
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm font-medium text-paper-700">
              自定义天数（留空使用套餐默认周期）
              <input
                type="number"
                min={1}
                max={3650}
                value={editing.days}
                onChange={(event) =>
                  setEditing((prev) => (prev ? { ...prev, days: event.target.value } : prev))
                }
                className="mt-1 w-full rounded-control border border-paper-300 px-3 py-2 text-sm"
                placeholder="例如 30"
              />
            </label>
            <p className="text-xs text-paper-500">
              手动开通不会生成支付订单；如需账务记录，请创建并完成支付订单。
            </p>
          </div>
        ) : null}
      </Modal>

      <Modal
        isOpen={Boolean(refundTarget)}
        onClose={() => setRefundTarget(null)}
        title={refundTarget ? `退款 · ${refundTarget.order_no}` : '退款'}
        footer={
          <div className="flex justify-end gap-3">
            <Button variant="secondary" size="sm" onClick={() => setRefundTarget(null)}>
              取消
            </Button>
            <Button
              size="sm"
              loading={busy === `refund:${refundTarget?.order_no ?? ''}`}
              onClick={() => void refund()}
            >
              确认退款
            </Button>
          </div>
        }
      >
        {refundTarget ? (
          <div className="space-y-4">
            <p className="text-sm text-paper-600">
              订单金额：<span className="font-medium tabular-nums text-paper-900">{money(refundTarget.amount_cents)}</span>
            </p>
            <label className="block text-sm font-medium text-paper-700">
              退款方式
              <select
                value={refundMode}
                onChange={(event) => setRefundMode(event.target.value as 'manual' | 'gateway')}
                className="mt-1 w-full rounded-control border border-paper-300 px-3 py-2 text-sm"
              >
                <option value="manual">仅记账（在支付商户后台手动退款）</option>
                <option value="gateway">尝试网关退款</option>
              </select>
            </label>
            <label className="block text-sm font-medium text-paper-700">
              退款原因
              <input
                value={refundReason}
                onChange={(event) => setRefundReason(event.target.value)}
                className="mt-1 w-full rounded-control border border-paper-300 px-3 py-2 text-sm"
                placeholder="可选，最多 200 字"
                maxLength={200}
              />
            </label>
            <p className="text-xs text-paper-500">
              {refundMode === 'gateway'
                ? '将调用支付网关退款接口；网关不支持或失败时订单保持已支付并记录失败原因。'
                : '仅记录退款状态，不会自动把资金退回；请在支付商户后台完成退款。'}
            </p>
          </div>
        ) : null}
      </Modal>
    </PageShell>
  )
}
