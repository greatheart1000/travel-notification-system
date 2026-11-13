import { useCallback, useEffect, useState } from 'react'
import { UserPlus } from 'lucide-react'
import { PageShell } from '../../components/PageShell'
import { Button } from '../../components/Button'
import { Badge } from '../../components/Badge'
import { Modal } from '../../components/Modal'
import { getErrorMessage } from '../../services/api'
import { tenantUsersApi, type TenantUser } from '../../services/commercialApi'

const ROLE_LABELS: Record<string, string> = { admin: '管理员', guide: '导游', user: '普通成员', operator: '平台运营' }
const STATUS_LABELS: Record<string, string> = { active: '启用', disabled: '停用' }

const inputClass =
  'mt-1 w-full rounded-control border border-paper-300 bg-white px-3 py-2 text-sm text-paper-900 transition-colors focus:border-accent-600 focus:outline-none focus:ring-2 focus:ring-accent-100'

export function Users() {
  const [users, setUsers] = useState<TenantUser[]>([])
  const [isOpen, setIsOpen] = useState(false)
  const [form, setForm] = useState({ username: '', display_name: '', password: '', email: '', phone: '', role: 'user' })
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const result = await tenantUsersApi.list()
      setUsers(result.items)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const activeAdmins = users.filter(
    (item) => item.role === 'admin' && (item.status ?? 'active') === 'active',
  ).length
  const isLastAdmin = (user: TenantUser) =>
    user.role === 'admin' &&
    (user.status ?? 'active') === 'active' &&
    activeAdmins <= 1

  const submit = async () => {
    if (!form.username.trim() || !form.password) {
      setError('请填写用户名和初始密码')
      return
    }
    setSaving(true)
    setError(null)
    try {
      await tenantUsersApi.create({
        username: form.username.trim(),
        display_name: form.display_name.trim(),
        password: form.password,
        email: form.email.trim(),
        phone: form.phone.trim(),
        role: form.role,
      })
      setIsOpen(false)
      setForm({ username: '', display_name: '', password: '', email: '', phone: '', role: 'user' })
      setNotice('成员已创建')
      await load()
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  const update = async (user: TenantUser, patch: Partial<TenantUser>) => {
    try {
      await tenantUsersApi.update(user.username, patch)
      await load()
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  return (
    <PageShell
      title="团队成员"
      description="管理当前企业的登录账号与角色。管理员可配置渠道、规则与发送任务。"
      actions={
        <Button size="sm" onClick={() => setIsOpen(true)}>
          <UserPlus className="h-4 w-4" /> 添加成员
        </Button>
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

      <div className="overflow-hidden rounded-card border border-paper-200 bg-white shadow-card">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-paper-200 text-xs font-medium text-paper-500">
              <th className="px-5 py-3">成员</th>
              <th className="px-5 py-3">邮箱 / 手机</th>
              <th className="px-5 py-3">角色</th>
              <th className="px-5 py-3">状态</th>
              <th className="px-5 py-3 text-right">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-paper-100">
            {loading ? (
              <tr>
                <td colSpan={5} className="px-5 py-8 text-center text-sm text-paper-500">
                  正在加载成员
                </td>
              </tr>
            ) : users.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-5 py-8 text-center text-sm text-paper-500">
                  暂无成员
                </td>
              </tr>
            ) : (
              users.map((user) => (
                <tr key={user.id || user.username} className="transition-colors hover:bg-paper-50">
                  <td className="px-5 py-3">
                    <span className="block font-medium text-paper-900">{user.display_name || user.username}</span>
                    <span className="block text-xs text-paper-400">@{user.username}</span>
                  </td>
                  <td className="px-5 py-3 text-paper-600">
                    <span className="block">{user.email || '-'}</span>
                    <span className="block text-xs text-paper-400">{user.phone || ''}</span>
                  </td>
                  <td className="px-5 py-3">
                    <select
                      value={user.role}
                      disabled={isLastAdmin(user)}
                      title={isLastAdmin(user) ? '企业至少需要保留一名启用状态的管理员' : undefined}
                      onChange={(event) => void update(user, { role: event.target.value })}
                      className="rounded-control border border-paper-300 px-2 py-1 text-sm disabled:opacity-60"
                    >
                      <option value="admin">管理员</option>
                      <option value="guide">导游</option>
                      <option value="user">普通成员</option>
                    </select>
                  </td>
                  <td className="px-5 py-3">
                    <Badge variant={(user.status ?? 'active') === 'active' ? 'success' : 'default'}>
                      {STATUS_LABELS[user.status ?? 'active'] ?? user.status}
                    </Badge>
                  </td>
                  <td className="px-5 py-3 text-right">
                    <Button
                      size="sm"
                      variant={(user.status ?? 'active') === 'active' ? 'secondary' : 'success'}
                      disabled={isLastAdmin(user)}
                      title={isLastAdmin(user) ? '企业至少需要保留一名启用状态的管理员' : undefined}
                      onClick={() =>
                        void update(user, {
                          status: (user.status ?? 'active') === 'active' ? 'disabled' : 'active',
                        })
                      }
                    >
                      {(user.status ?? 'active') === 'active' ? '停用' : '启用'}
                    </Button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <Modal
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        title="添加团队成员"
        footer={
          <div className="flex justify-end gap-3">
            <Button variant="secondary" size="sm" onClick={() => setIsOpen(false)}>
              取消
            </Button>
            <Button size="sm" loading={saving} onClick={() => void submit()}>
              创建成员
            </Button>
          </div>
        }
      >
        <div className="space-y-4">
          <label className="block text-sm font-medium text-paper-700">
            用户名
            <input
              value={form.username}
              onChange={(event) => setForm((prev) => ({ ...prev, username: event.target.value }))}
              className={inputClass}
              placeholder="3-32 位字母、数字或下划线"
            />
          </label>
          <label className="block text-sm font-medium text-paper-700">
            初始密码
            <input
              type="password"
              value={form.password}
              onChange={(event) => setForm((prev) => ({ ...prev, password: event.target.value }))}
              className={inputClass}
              placeholder="至少 8 位"
            />
          </label>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block text-sm font-medium text-paper-700">
              邮箱
              <input
                value={form.email}
                onChange={(event) => setForm((prev) => ({ ...prev, email: event.target.value }))}
                className={inputClass}
                placeholder="可选"
              />
            </label>
            <label className="block text-sm font-medium text-paper-700">
              手机号
              <input
                value={form.phone}
                onChange={(event) => setForm((prev) => ({ ...prev, phone: event.target.value }))}
                className={inputClass}
                placeholder="可选，用于短信登录"
              />
            </label>
          </div>
          <label className="block text-sm font-medium text-paper-700">
            角色
            <select
              value={form.role}
              onChange={(event) => setForm((prev) => ({ ...prev, role: event.target.value }))}
              className={inputClass}
            >
              <option value="guide">导游</option>
              <option value="user">普通成员</option>
              <option value="admin">管理员</option>
            </select>
          </label>
          <p className="text-xs text-paper-500">
            角色说明：{Object.entries(ROLE_LABELS).map(([key, label]) => `${label}（${key}）`).join('、')}
          </p>
        </div>
      </Modal>
    </PageShell>
  )
}
