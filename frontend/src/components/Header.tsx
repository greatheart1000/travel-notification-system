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
    <header className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-6">
      <div className="flex-1">
        <div className="relative max-w-md">
          <input
            type="text"
            placeholder="搜索行程、客人或通知..."
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500"
          />
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
        </div>
      </div>

      <div className="flex items-center gap-4">
        <button className="relative p-2 hover:bg-gray-100 rounded-lg" aria-label="通知">
          <Bell className="h-5 w-5 text-gray-700" />
          <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
        </button>
        <div className="flex items-center gap-2 hover:bg-gray-100 rounded-lg px-3 py-2">
          <User className="h-5 w-5 text-gray-700" />
          <div className="leading-tight">
            <span className="block text-sm text-gray-800">管理员</span>
            {logoutError ? <span className="block text-xs text-red-600">退出失败</span> : null}
          </div>
        </div>
        <button
          className="p-2 text-gray-500 hover:text-gray-900 hover:bg-gray-100 rounded-lg disabled:opacity-50"
          onClick={handleLogout}
          disabled={isLoggingOut}
          aria-label="退出登录"
        >
          <LogOut className="h-4 w-4" />
        </button>
      </div>
    </header>
  )
}
