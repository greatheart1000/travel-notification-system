import { useState } from 'react'
import { Building2, LogOut, Menu, UserRound } from 'lucide-react'
import { authApi, getErrorMessage } from '../services/api'
import { useSession } from '../context/SessionContext'

const ROLE_LABELS: Record<string, string> = {
  admin: '管理员',
  guide: '导游',
  user: '成员',
  operator: '平台运营',
}

interface HeaderProps {
  onOpenMenu?: () => void
}

export function Header({ onOpenMenu }: HeaderProps) {
  const { user, tenant } = useSession()
  const [isLoggingOut, setIsLoggingOut] = useState(false)
  const [logoutError, setLogoutError] = useState<string | null>(null)

  const handleLogout = async () => {
    setIsLoggingOut(true)
    setLogoutError(null)
    try {
      await authApi.logout()
    } catch (error) {
      setLogoutError(getErrorMessage(error))
    } finally {
      setIsLoggingOut(false)
    }
  }

  return (
    <header className="relative flex h-14 items-center justify-between gap-3 border-b border-paper-200 bg-white/90 px-4 backdrop-blur lg:px-6">
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-px bg-accent-200" />
      <div className="flex min-w-0 items-center gap-2 text-sm">
        <button
          type="button"
          onClick={onOpenMenu}
          className="-ml-1 rounded-control p-2 text-paper-600 transition-colors hover:bg-white/80 hover:text-accent-700 lg:hidden"
          aria-label="打开菜单"
        >
          <Menu className="h-5 w-5" />
        </button>
        <span className="hidden h-7 w-7 shrink-0 items-center justify-center rounded-control bg-paper-100 text-paper-600 sm:flex">
          <Building2 className="h-4 w-4" />
        </span>
        <span className="truncate font-medium text-paper-900">{tenant?.name || '当前企业'}</span>
        {tenant?.tenant_id && tenant.tenant_id !== 'platform' ? (
          <span className="hidden rounded-full bg-paper-100 px-2 py-0.5 text-xs text-paper-500 md:inline">
            {tenant.tenant_id}
          </span>
        ) : null}
      </div>

      <div className="flex shrink-0 items-center gap-2 sm:gap-3">
        <div className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-accent-50 text-accent-700">
            <UserRound className="h-4 w-4" />
          </span>
          <div className="hidden leading-tight sm:block">
            <span className="block text-sm font-medium text-paper-900">{user?.display_name || user?.username || '未登录'}</span>
            <span className="block text-xs text-paper-500">
              {ROLE_LABELS[user?.role ?? ''] ?? user?.role ?? ''}
            </span>
          </div>
        </div>
        {logoutError ? <span className="text-xs text-danger-600">退出失败</span> : null}
        <button
          type="button"
          className="rounded-control p-2 text-paper-500 transition-colors hover:bg-white/80 hover:text-pink-600 disabled:opacity-50"
          onClick={() => void handleLogout()}
          disabled={isLoggingOut}
          aria-label="退出登录"
        >
          <LogOut className="h-4 w-4" />
        </button>
      </div>
    </header>
  )
}
