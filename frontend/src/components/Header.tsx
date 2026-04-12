import { useState } from 'react'
import { Bell, User, LogOut } from 'lucide-react'
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
    <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
      <div className="flex items-center justify-between px-8 py-4">
        <h2 className="text-2xl font-bold text-gray-900">欢迎使用行程管家服务</h2>
        <div className="flex items-center gap-6">
          <button className="relative p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition" aria-label="通知">
            <Bell className="w-6 h-6" />
            <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
          </button>
          <div className="flex items-center gap-3">
            <div className="text-right">
              <p className="text-sm font-semibold text-gray-900">张三</p>
              <p className="text-xs text-gray-500">管理员</p>
              {logoutError ? <p className="text-xs text-red-600 mt-1">退出失败: {logoutError}</p> : null}
            </div>
            <button className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition" aria-label="用户信息">
              <User className="w-6 h-6" />
            </button>
            <button
              className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition disabled:opacity-50"
              onClick={handleLogout}
              disabled={isLoggingOut}
              aria-label="退出登录"
            >
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    </header>
  )
}
