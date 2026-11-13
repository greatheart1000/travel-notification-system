import {
  BarChart3,
  BellRing,
  CreditCard,
  LayoutDashboard,
  ListChecks,
  MessageSquare,
  Plane,
  Settings,
  Users,
} from 'lucide-react'
import { RouteMark } from './RouteMark'

export type SidebarPage =
  | 'trips'
  | 'analytics'
  | 'preferences'
  | 'billing'
  | 'settings_channels'
  | 'settings_rules'
  | 'settings_jobs'
  | 'settings_users'
  | 'operator'

interface SidebarProps {
  currentPage: SidebarPage
  onPageChange: (page: SidebarPage) => void
  userRole?: string
  tenantName?: string
  username?: string
}

const ROLE_LABELS: Record<string, string> = {
  admin: '管理员',
  user: '成员',
  operator: '平台运营',
}

export function Sidebar({
  currentPage,
  onPageChange,
  userRole = 'user',
  tenantName,
  username,
}: SidebarProps) {
  const isAdmin = userRole === 'admin'
  const isOperator = userRole === 'operator'
  const operatorGroups: { title: string; items: { id: SidebarPage; label: string; icon: typeof Plane }[] }[] = [
    {
      title: '平台运营',
      items: [{ id: 'operator', label: '运营概览', icon: LayoutDashboard }],
    },
  ]
  const groups: { title: string; items: { id: SidebarPage; label: string; icon: typeof Plane }[] }[] = isOperator
    ? operatorGroups
    : [
    {
      title: '业务',
      items: [
        { id: 'trips', label: '行程管理', icon: Plane },
        { id: 'analytics', label: '数据分析', icon: BarChart3 },
      ],
    },
    {
      title: '设置',
      items: [
        ...(isAdmin ? [{ id: 'settings_channels' as const, label: '通知渠道', icon: MessageSquare }] : []),
        { id: 'settings_rules' as const, label: '通知规则', icon: BellRing },
        ...(isAdmin ? [{ id: 'settings_users' as const, label: '团队成员', icon: Users }] : []),
        { id: 'preferences' as const, label: '偏好设置', icon: Settings },
        { id: 'billing' as const, label: '套餐与账单', icon: CreditCard },
      ],
    },
    ...(isAdmin
      ? [
          {
            title: '运维',
            items: [{ id: 'settings_jobs' as const, label: '发送任务', icon: ListChecks }],
          },
        ]
      : []),
  ]

  return (
    <aside className="flex h-screen w-60 flex-col border-r border-paper-200 bg-white">
      <div className="px-4 py-5">
        <div className="flex items-center gap-2.5">
          <RouteMark className="h-6 w-6 text-accent-700" />
          <div>
            <div className="text-sm font-semibold leading-tight text-paper-900">行程管家</div>
            <div className="text-xs text-paper-500">行程通知台</div>
          </div>
        </div>
      </div>

      <nav className="flex-1 space-y-5 overflow-y-auto px-2 pb-4">
        {groups.map((group) => (
          <div key={group.title}>
            <p className="px-3 pb-2 text-xs font-medium text-paper-500">{group.title}</p>
            <div className="space-y-1">
              {group.items.map(({ id, label, icon: Icon }) => {
                const active = currentPage === id
                return (
                  <button
                    key={id}
                    type="button"
                    aria-current={active ? 'page' : undefined}
                    onClick={() => onPageChange(id)}
                    className={`flex w-full items-center gap-2.5 rounded-control px-3 py-2 text-left text-sm transition-colors ${
                      active
                        ? 'bg-paper-200 font-medium text-paper-900'
                        : 'text-paper-600 hover:bg-paper-100 hover:text-paper-900'
                    }`}
                  >
                    <Icon className={`h-4 w-4 shrink-0 ${active ? 'text-accent-700' : 'text-paper-500'}`} />
                    {label}
                  </button>
                )
              })}
            </div>
          </div>
        ))}
      </nav>

      <div className="border-t border-paper-200 p-3">
        <div className="px-2 py-1.5">
          <div className="truncate text-sm font-medium text-paper-900">{tenantName || '当前企业'}</div>
          <div className="mt-0.5 truncate text-xs text-paper-500">
            {username || '未登录'} · {ROLE_LABELS[userRole] ?? userRole}
          </div>
          <div className="mt-1 text-xs text-paper-400">v0.3.0</div>
        </div>
      </div>
    </aside>
  )
}
