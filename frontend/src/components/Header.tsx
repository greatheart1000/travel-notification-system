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
    <header className="flex h-14 items-center justify-between border-b border-slate-200 bg-white px-6">
      <div className="flex items-center gap-2 text-sm text-slate-500">
        <Building2 className="h-4 w-4" />
        <span className="font-medium text-slate-800">{tenant?.name || '当前企业'}</span>
        {tenant?.tenant_id && tenant.tenant_id !== 'platform' ? (
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-500">
            {tenant.tenant_id}
          </span>
        ) : null}
      </div>

      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 rounded-lg px-2 py-1.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-sky-50 text-sky-600">
            <UserRound className="h-4 w-4" />
          </span>
          <div className="leading-tight">
            <span className="block text-sm font-medium text-slate-800">
              {user?.username || '未登录'}
            </span>
            <span className="block text-xs text-slate-500">
              {ROLE_LABELS[user?.role ?? ''] ?? user?.role ?? ''}
            </span>
          </div>
        </div>
        {logoutError ? <span className="text-xs text-red-600">退出失败</span> : null}
        <button
          type="button"
          className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-900 disabled:opacity-50"
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
