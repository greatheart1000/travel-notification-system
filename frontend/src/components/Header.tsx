import { Bell, User, LogOut } from 'lucide-react'

export function Header() {
  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
      <div className="flex items-center justify-between px-8 py-4">
        <h2 className="text-2xl font-bold text-gray-900">
          欢迎使用行程管家服务
        </h2>
        <div className="flex items-center gap-6">
          <button className="relative p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition">
            <Bell className="w-6 h-6" />
            <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
          </button>
          <div className="flex items-center gap-3">
            <div className="text-right">
              <p className="text-sm font-semibold text-gray-900">张三</p>
              <p className="text-xs text-gray-500">管理员</p>
            </div>
            <button className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition">
              <User className="w-6 h-6" />
            </button>
            <button className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition">
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    </header>
  )
}
