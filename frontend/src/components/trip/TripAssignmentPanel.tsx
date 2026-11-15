import { useEffect, useState } from 'react'
import { Check, UsersRound } from 'lucide-react'
import { Button } from '../Button'
import { tripAssignmentsApi, type TripAssignee } from '../../services/api'
import { tenantUsersApi, type TenantUser } from '../../services/commercialApi'
import { useSession } from '../../context/SessionContext'

interface Props {
  tripId: string
  onAssigned?: (userIds: string[]) => void
}

const ROLE_LABELS: Record<string, string> = {
  admin: '管理员',
  guide: '导游',
  user: '成员',
  concierge: '管家',
  ops: '运营',
  cs: '客服',
  sales: '销售',
}

function roleLabel(role: string): string {
  return ROLE_LABELS[role] ?? role
}

export function TripAssignmentPanel({ tripId, onAssigned }: Props) {
  const { user } = useSession()
  const isAdmin = user?.role === 'admin'
  const [assignees, setAssignees] = useState<TripAssignee[]>([])
  const [members, setMembers] = useState<TenantUser[]>([])
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ kind: 'ok' | 'error'; text: string } | null>(null)

  useEffect(() => {
    let active = true
    const load = async () => {
      setLoading(true)
      setMessage(null)
      try {
        const [assignment, tenantUsers] = await Promise.all([
          tripAssignmentsApi.get(tripId),
          isAdmin ? tenantUsersApi.list() : Promise.resolve(null),
        ])
        if (!active) return
        setAssignees(assignment.users)
        setSelected(new Set(assignment.assigned_user_ids))
        if (tenantUsers) {
          setMembers(
            tenantUsers.items.filter(
              (member) => member.status !== 'disabled' && member.role !== 'admin',
            ),
          )
        }
      } catch (error) {
        if (active) {
          setMessage({
            kind: 'error',
            text: error instanceof Error ? error.message : '导游分配加载失败',
          })
        }
      } finally {
        if (active) setLoading(false)
      }
    }
    void load()
    return () => {
      active = false
    }
  }, [tripId, isAdmin])

  const toggle = (userId: string) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(userId)) next.delete(userId)
      else next.add(userId)
      return next
    })
  }

  const handleSave = async () => {
    setSaving(true)
    setMessage(null)
    try {
      const assignment = await tripAssignmentsApi.update(tripId, Array.from(selected))
      setAssignees(assignment.users)
      setSelected(new Set(assignment.assigned_user_ids))
      onAssigned?.(assignment.assigned_user_ids)
      setMessage({ kind: 'ok', text: '导游分配已保存，成员登录后即可看到该行程' })
    } catch (error) {
      setMessage({
        kind: 'error',
        text: error instanceof Error ? error.message : '导游分配保存失败',
      })
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return <div className="p-4 text-sm text-paper-500">加载导游分配</div>
  }

  return (
    <div className="space-y-4">
      <div className="flex items-start gap-2.5">
        <UsersRound className="mt-0.5 h-4 w-4 text-paper-500" />
        <div>
          <h3 className="text-sm font-medium text-paper-900">导游与执行人</h3>
          <p className="mt-1 text-xs text-paper-500">
            被分配的成员可在自己的行程列表中看到并执行该团；管理员始终可见全部行程
          </p>
        </div>
      </div>

      {message ? (
        <div
          className={`rounded-control border px-3 py-2 text-sm ${
            message.kind === 'ok'
              ? 'border-success-200 bg-success-50 text-success-700'
              : 'border-danger-200 bg-danger-50 text-danger-700'
          }`}
        >
          {message.text}
        </div>
      ) : null}

      {isAdmin ? (
        <>
          {members.length === 0 ? (
            <p className="rounded-control border border-dashed border-paper-300 px-4 py-6 text-center text-sm text-paper-500">
              还没有可分配的成员，请先在“成员管理”中添加账号
            </p>
          ) : (
            <div className="grid gap-2 sm:grid-cols-2">
              {members.map((member) => {
                const checked = selected.has(member.id)
                return (
                  <label
                    key={member.id}
                    className={`flex cursor-pointer items-center gap-3 rounded-control border px-3 py-2.5 transition-colors ${
                      checked
                        ? 'border-accent-300 bg-accent-50'
                        : 'border-paper-200 bg-white hover:bg-paper-50'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggle(member.id)}
                      className="h-4 w-4 accent-accent-600"
                    />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-medium text-paper-900">
                        {member.display_name || member.username}
                      </span>
                      <span className="block text-xs text-paper-500">
                        {roleLabel(member.role)}
                        {member.phone ? ` · ${member.phone}` : ''}
                      </span>
                    </span>
                    {checked ? <Check className="h-4 w-4 text-accent-600" /> : null}
                  </label>
                )
              })}
            </div>
          )}
          <div className="flex items-center justify-between gap-3">
            <span className="text-xs text-paper-500">已选 {selected.size} 人</span>
            <Button size="sm" onClick={() => void handleSave()} loading={saving}>
              保存分配
            </Button>
          </div>
        </>
      ) : assignees.length > 0 ? (
        <ul className="divide-y divide-paper-100 rounded-control border border-paper-200">
          {assignees.map((assignee) => (
            <li key={assignee.id} className="flex items-center justify-between px-3 py-2.5 text-sm">
              <span className="font-medium text-paper-900">{assignee.display_name || assignee.username}</span>
              <span className="text-xs text-paper-500">{roleLabel(assignee.role)}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="rounded-control border border-dashed border-paper-300 px-4 py-6 text-center text-sm text-paper-500">
          暂未分配导游，请联系管理员
        </p>
      )}
    </div>
  )
}
