import { useState } from 'react'
import { Bell, LogOut, Search, User } from 'lucide-react'
import { authApi, getErrorMessage } from '../services/api'

export function Header() {
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
    <header className="sticky top-0 z-10 border-b border-blue-100 bg-white/85 backdrop-blur-xl">
      <div className="flex items-center justify-between px-8 py-4">
        <div className="relative hidden w-80 lg:block">
          <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            className="w-full rounded-full border border-blue-100 bg-blue-50/70 py-2 pl-10 pr-4 text-sm text-slate-700 outline-none transition focus:border-blue-300 focus:bg-white focus:ring-4 focus:ring-blue-100"
            placeholder="搜索行程、客人或通知..."
            type="search"
          />
        </div>
        <h2 className="text-lg font-black tracking-tight text-slate-900 lg:hidden">Travel Hub</h2>
        <div className="flex items-center gap-6">
          <button className="relative rounded-full p-2 text-slate-500 transition hover:bg-blue-50 hover:text-blue-700" aria-label="通知">
            <Bell className="h-6 w-6" />
            <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-red-500 ring-2 ring-white" />
          </button>
          <div className="flex items-center gap-3">
            <div className="text-right">
              <p className="text-sm font-bold text-slate-900">张三</p>
              <p className="text-xs text-slate-500">管理员</p>
              {logoutError ? <p className="text-xs text-red-600 mt-1">退出失败: {logoutError}</p> : null}
            </div>
            <button className="rounded-full bg-slate-100 p-2 text-slate-600 transition hover:bg-blue-50 hover:text-blue-700" aria-label="用户信息">
              <User className="h-6 w-6" />
            </button>
            <button
              className="rounded-full p-2 text-slate-500 transition hover:bg-blue-50 hover:text-blue-700 disabled:opacity-50"
              onClick={handleLogout}
              disabled={isLoggingOut}
              aria-label="退出登录"
            >
              <LogOut className="h-5 w-5" />
            </button>
          </div>
        </div>
      </div>
    </header>
  )
}
