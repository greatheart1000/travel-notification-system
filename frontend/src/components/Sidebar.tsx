import { MapPin, Bell, Settings, BarChart3, Home, Plane } from 'lucide-react'

type Page = 'dashboard' | 'trips' | 'notifications' | 'preferences' | 'analytics' | 'templates'

interface SidebarProps {
  currentPage: Page
  onPageChange: (page: Page) => void
}

export function Sidebar({ currentPage, onPageChange }: SidebarProps) {
  const menuItems = [
    { id: 'dashboard' as const, label: '仪表盘', icon: Home },
    { id: 'trips' as const, label: '行程管理', icon: Plane },
    { id: 'notifications' as const, label: '通知中心', icon: Bell },
    { id: 'templates' as const, label: '消息模板', icon: Bell },
    { id: 'analytics' as const, label: '数据分析', icon: BarChart3 },
    { id: 'preferences' as const, label: '偏好设置', icon: Settings },
  ]

  return (
    <aside className="w-64 bg-gradient-to-b from-blue-600 to-blue-700 text-white shadow-xl">
      {/* Logo */}
      <div className="flex items-center gap-3 p-6 border-b border-blue-500">
        <MapPin className="w-8 h-8" />
        <div>
          <h1 className="text-xl font-bold">Travel Hub</h1>
          <p className="text-xs text-blue-200">行程管家服务</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="p-4 flex-1">
        <p className="text-xs font-semibold text-blue-200 uppercase tracking-wider mb-4">
          菜单
        </p>
        <ul className="space-y-2">
          {menuItems.map(({ id, label, icon: Icon }) => (
            <li key={id}>
              <button
                onClick={() => onPageChange(id)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
                  currentPage === id
                    ? 'bg-blue-500 text-white'
                    : 'text-blue-100 hover:bg-blue-500/50'
                }`}
              >
                <Icon className="w-5 h-5" />
                <span className="font-medium">{label}</span>
              </button>
            </li>
          ))}
        </ul>
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-blue-500">
        <div className="bg-blue-500/30 rounded-lg p-3 text-sm">
          <p className="font-semibold mb-1">需要帮助？</p>
          <p className="text-blue-200 text-xs">联系我们的客服团队获取支持</p>
        </div>
      </div>
    </aside>
  )
}
