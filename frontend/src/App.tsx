import { useState } from 'react'
import { Sidebar } from './components/Sidebar'
import { Dashboard } from './pages/Dashboard'
import { Trips } from './pages/Trips'
import { Notifications } from './pages/Notifications'
import { Preferences } from './pages/Preferences'
import { Analytics } from './pages/Analytics'

type Page = 'dashboard' | 'trips' | 'notifications' | 'preferences' | 'analytics'

export default function App() {
  const [currentPage, setCurrentPage] = useState<Page>('dashboard')

  const renderPage = () => {
    switch (currentPage) {
      case 'dashboard':
        return <Dashboard />
      case 'trips':
        return <Trips />
      case 'notifications':
        return <Notifications />
      case 'preferences':
        return <Preferences />
      case 'analytics':
        return <Analytics />
      default:
        return <Dashboard />
    }
  }

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar currentPage={currentPage} onPageChange={setCurrentPage} />
      <main className="flex-1 overflow-auto">
        {renderPage()}
      </main>
    </div>
  )
}
