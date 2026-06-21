import { BarChart3, Headphones, MapPin, Plane, Settings } from 'lucide-react'

type Page = 'trips' | 'analytics' | 'preferences'

interface SidebarProps {
  currentPage: Page
  onPageChange: (page: Page) => void
}

export function Sidebar({ currentPage, onPageChange }: SidebarProps) {
  const menuItems = [
    { id: 'trips' as const, label: '行程管理', icon: Plane },
    { id: 'analytics' as const, label: '数据分析', icon: BarChart3 },
    { id: 'preferences' as const, label: '偏好设置', icon: Settings },
  ]

  return (
    <aside className="w-40 bg-gradient-to-b from-cyan-500 to-blue-600 text-white flex flex-col h-screen">
      <div className="p-6">
        <div className="flex items-center gap-2 mb-8">
          <MapPin className="h-6 w-6" />
          <div>
            <div className="font-bold leading-tight">Travel Hub</div>
            <div className="text-xs opacity-80">行程管理平台</div>
          </div>
        </div>
      </div>

      <nav className="flex-1 px-3">
        {menuItems.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => onPageChange(id)}
            className={`flex w-full items-center gap-3 px-4 py-3 rounded-lg mb-2 transition-colors text-left ${
              currentPage === id ? 'bg-white/20 font-medium' : 'hover:bg-white/10'
            }`}
          >
            <Icon className="h-4 w-4" />
            <span className="text-sm">{label}</span>
          </button>
        ))}
      </nav>

      <div className="p-4 border-t border-white/20">
        <button className="flex items-center gap-2 text-sm opacity-80 hover:opacity-100">
          <Headphones className="h-4 w-4" />
          <span>需要帮助?</span>
        </button>
        <div className="text-xs mt-2 opacity-60">联系我们获取技术支持</div>
      </div>
    </aside>
  )
}
