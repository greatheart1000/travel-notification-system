import { useState } from 'react'
import { Building2, LogOut, UserRound } from 'lucide-react'
import { authApi, getErrorMessage } from '../services/api'
import { useSession } from '../context/SessionContext'

const ROLE_LABELS: Record<string, string> = {
  admin: '管理员',
  user: '成员',
  operator: '平台运营',
}

export function Header() {
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
    <header className="flex h-14 items-center justify-between border-b border-paper-200 bg-white px-6">
      <div className="flex items-center gap-2 text-sm">
        <Building2 className="h-4 w-4 text-paper-500" />
        <span className="font-medium text-paper-800">{tenant?.name || '当前企业'}</span>
        {tenant?.tenant_id && tenant.tenant_id !== 'platform' ? (
          <span className="text-xs text-paper-500">{tenant.tenant_id}</span>
        ) : null}
      </div>

      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <UserRound className="h-4 w-4 text-paper-500" />
          <div className="leading-tight">
            <span className="block text-sm font-medium text-paper-800">{user?.username || '未登录'}</span>
            <span className="block text-xs text-paper-500">
              {ROLE_LABELS[user?.role ?? ''] ?? user?.role ?? ''}
            </span>
          </div>
        </div>
        {logoutError ? <span className="text-xs text-danger-600">退出失败</span> : null}
        <button
          type="button"
          className="rounded-control p-2 text-paper-500 transition-colors hover:bg-paper-100 hover:text-paper-900 disabled:opacity-50"
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
