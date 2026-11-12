import { useCallback, useEffect, useMemo, useState } from 'react'
import { Building2, Crown, RefreshCw, Wallet } from 'lucide-react'
import { PageShell } from '../components/PageShell'
import { Button } from '../components/Button'
import { Badge } from '../components/Badge'
import { Modal } from '../components/Modal'
import { getErrorMessage } from '../services/api'
import { useSession } from '../context/SessionContext'
import {
  billingApi,
  operatorApi,
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
  return `¥${(cents / 100).toFixed(2)}`
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
  icon: Icon,
}: {
  label: string
  value: string
  hint: string
  icon: typeof Crown
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <span className="text-sm text-slate-500">{label}</span>
        <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-sky-50 text-sky-600">
          <Icon className="h-4 w-4" />
        </span>
      </div>
      <div className="mt-3 text-2xl font-semibold text-slate-900">{value}</div>
      <div className="mt-1 text-xs text-slate-500">{hint}</div>
    </div>
  )
}

export function Operator() {
  const { user } = useSession()
  const [overview, setOverview] = useState<OperatorOverview | null>(null)
  const [tenants, setTenants] = useState<OperatorTenant[]>([])
  const [plans, setPlans] = useState<Plan[]>([])
  const [editing, setEditing] = useState<{ tenant: OperatorTenant; planCode: string; days: string } | null>(null)
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

  const refund = async (orderNo: string) => {
    if (!window.confirm(`确认将订单 ${orderNo} 标记为已退款？实际退款需在支付商户后台完成。`)) return
    setBusy(`refund:${orderNo}`)
    try {
      await operatorApi.refundOrder(orderNo, false)
      setNotice(`订单 ${orderNo} 已标记为退款`)
      await load()
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setBusy('')
    }
  }

  if (!isOperator) {
    return (
      <PageShell title="平台运营" eyebrow="OPERATOR">
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-6 text-sm text-amber-800">
          当前账号不是平台运营角色，无法访问运营后台。
        </div>
      </PageShell>
    )
  }

  return (
    <PageShell
      eyebrow="OPERATOR"
      title="平台运营"
      description="查看全平台租户、订阅与收入，处理手动开通与退款。退款标记仅做账务记录，实际资金退还请在支付商户后台操作。"
      actions={
        <Button size="sm" variant="secondary" onClick={() => void load()}>
          <span className="flex items-center gap-1">
            <RefreshCw className="h-4 w-4" /> 刷新
          </span>
        </Button>
      }
    >
      {error ? (
        <div role="alert" className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}
      {notice ? (
        <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
          {notice}
        </div>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="租户总数"
          value={String(overview?.tenants ?? '-')}
          hint={`活跃订阅 ${overview?.active_subscriptions ?? 0}`}
          icon={Building2}
        />
        <StatCard
          label="本月收入"
          value={money(overview?.revenue_cents_this_period ?? 0)}
          hint={`累计 ${money(overview?.revenue_cents_total ?? 0)}`}
          icon={Wallet}
        />
        <StatCard
          label="已支付订单"
          value={String(overview?.paid_orders ?? '-')}
          hint={`统计周期 ${overview?.period ?? '-'}`}
          icon={Crown}
        />
        <StatCard
          label="本月短信量"
          value={String(overview?.sms_used_this_period ?? '-')}
          hint="所有租户合计"
          icon={Crown}
        />
      </div>

      <section className="mt-8">
        <h2 className="mb-3 text-xl font-semibold text-slate-900">租户</h2>
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">企业</th>
                <th className="px-4 py-3">租户 ID</th>
                <th className="px-4 py-3">状态</th>
                <th className="px-4 py-3">套餐</th>
                <th className="px-4 py-3">本月短信</th>
                <th className="px-4 py-3 text-right">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-slate-500">
                    正在加载租户...
                  </td>
                </tr>
              ) : tenants.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-slate-500">
                    暂无租户
                  </td>
                </tr>
              ) : (
                tenants.map((tenant) => (
                  <tr key={tenant.tenant_id}>
                    <td className="px-4 py-3 font-medium text-slate-900">{tenant.name}</td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-500">{tenant.tenant_id}</td>
                    <td className="px-4 py-3">
                      <Badge variant={tenant.status === 'active' ? 'success' : 'danger'}>
                        {tenant.status === 'active' ? '正常' : '停用'}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-slate-600">
                      {tenant.plan_name ?? '-'}
                      {tenant.subscription_status ? (
                        <span className="ml-1 text-xs text-slate-400">({tenant.subscription_status})</span>
                      ) : null}
                    </td>
                    <td className="px-4 py-3 text-slate-600">
                      {tenant.sms_used ?? 0} / {tenant.sms_quota ?? 0}
                    </td>
                    <td className="px-4 py-3 text-right">
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
        <h2 className="mb-3 text-xl font-semibold text-slate-900">最近订单</h2>
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">订单号</th>
                <th className="px-4 py-3">租户</th>
                <th className="px-4 py-3">金额</th>
                <th className="px-4 py-3">状态</th>
                <th className="px-4 py-3">时间</th>
                <th className="px-4 py-3 text-right">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {recentOrders.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-slate-500">
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
                    <tr key={order.order_no}>
                      <td className="px-4 py-3 font-mono text-xs text-slate-600">{order.order_no}</td>
                      <td className="px-4 py-3 text-slate-600">{order.tenant_id}</td>
                      <td className="px-4 py-3">{money(order.amount_cents)}</td>
                      <td className="px-4 py-3">
                        <Badge variant={status.variant}>{status.label}</Badge>
                      </td>
                      <td className="px-4 py-3 text-slate-500">{formatDate(order.created_at)}</td>
                      <td className="px-4 py-3 text-right">
                        {order.status === 'paid' ? (
                          <Button
                            size="sm"
                            variant="secondary"
                            loading={busy === `refund:${order.order_no}`}
                            onClick={() => void refund(order.order_no)}
                          >
                            标记退款
                          </Button>
                        ) : (
                          <span className="text-xs text-slate-400">-</span>
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
            <p className="text-sm text-slate-500">
              当前租户：<span className="font-medium text-slate-800">{editing.tenant.tenant_id}</span>
            </p>
            <label className="block text-sm font-medium text-slate-700">
              目标套餐
              <select
                value={editing.planCode}
                onChange={(event) =>
                  setEditing((prev) => (prev ? { ...prev, planCode: event.target.value } : prev))
                }
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              >
                {plans.map((plan) => (
                  <option key={plan.code} value={plan.code}>
                    {plan.name}（{plan.sms_quota} 条短信）
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm font-medium text-slate-700">
              自定义天数（留空使用套餐默认周期）
              <input
                type="number"
                min={1}
                max={3650}
                value={editing.days}
                onChange={(event) =>
                  setEditing((prev) => (prev ? { ...prev, days: event.target.value } : prev))
                }
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                placeholder="例如 30"
              />
            </label>
            <p className="text-xs text-slate-500">
              手动开通不会生成支付订单；如需账务记录，请创建并完成支付订单。
            </p>
          </div>
        ) : null}
      </Modal>
    </PageShell>
  )
}
