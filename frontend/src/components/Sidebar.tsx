import { BarChart3, Bell, Headphones, Home, MapPin, Plane, Settings } from 'lucide-react'

type Page = 'dashboard' | 'trips' | 'notifications' | 'preferences' | 'analytics'

interface SidebarProps {
  currentPage: Page
  onPageChange: (page: Page) => void
}

export function Sidebar({ currentPage, onPageChange }: SidebarProps) {
  const menuItems = [
    { id: 'dashboard' as const, label: '仪表盘', icon: Home },
    { id: 'trips' as const, label: '行程管理', icon: Plane },
    { id: 'notifications' as const, label: '通知中心', icon: Bell },
    { id: 'analytics' as const, label: '数据分析', icon: BarChart3 },
    { id: 'preferences' as const, label: '偏好设置', icon: Settings },
  ]

  return (
    <aside className="flex h-screen w-64 flex-col bg-gradient-to-b from-sky-400 via-sky-500 to-blue-600 text-white shadow-2xl shadow-sky-900/20">
      <div className="flex items-center gap-3 border-b border-white/10 p-6">
        <div className="rounded-2xl bg-white/10 p-2 ring-1 ring-white/15">
          <MapPin className="h-7 w-7" />
        </div>
        <div>
          <h1 className="text-xl font-bold">Travel Hub</h1>
          <p className="text-xs text-sky-100">行程管家服务</p>
        </div>
      </div>

      <nav className="flex-1 p-4">
        <p className="mb-4 px-2 text-xs font-black uppercase tracking-[0.22em] text-sky-100">
          菜单
        </p>
        <ul className="space-y-2">
          {menuItems.map(({ id, label, icon: Icon }) => (
            <li key={id}>
              <button
                onClick={() => onPageChange(id)}
                className={`w-full rounded-xl px-4 py-3 text-left transition-all ${
                  currentPage === id
                    ? 'bg-white/95 text-sky-700 shadow-lg shadow-sky-900/20'
                    : 'text-sky-50 hover:bg-white/20 hover:text-white'
                }`}
              >
                <span className="flex items-center gap-3">
                  <Icon className="h-5 w-5" />
                  <span className="font-semibold">{label}</span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      </nav>

      <div className="border-t border-white/10 p-4">
        <div className="rounded-2xl bg-white/10 p-4 text-sm ring-1 ring-white/10">
          <div className="mb-2 flex items-center gap-2 font-bold">
            <Headphones className="h-4 w-4" />
            需要帮助？
          </div>
          <p className="text-xs leading-5 text-sky-50">联系值班管家团队获取运营支持</p>
        </div>
      </div>
    </aside>
  )
}
