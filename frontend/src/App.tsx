import { useEffect, useMemo, useState } from 'react'
import { Sidebar } from './components/Sidebar'
import { Button } from './components/Button'
import { Dashboard } from './pages/Dashboard'
import { Trips } from './pages/Trips'
import { Notifications } from './pages/Notifications'
import { Preferences } from './pages/Preferences'
import { Analytics } from './pages/Analytics'
import { Templates } from './pages/Templates'
import { AUTH_STATE_CHANGED_EVENT, hasAccessToken } from './adapters/authAdapter'
import { authApi, getErrorMessage } from './services/api'

type Page = 'dashboard' | 'trips' | 'notifications' | 'preferences' | 'analytics' | 'templates'

export default function App() {
  const [currentPage, setCurrentPage] = useState<Page>('dashboard')

  const [isCheckingAuth, setIsCheckingAuth] = useState(true)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [authError, setAuthError] = useState<string | null>(null)

  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('123456')
  const [isLoginSubmitting, setIsLoginSubmitting] = useState(false)

  useEffect(() => {
    let active = true

    const verifyAuth = async () => {
      if (!hasAccessToken()) {
        if (active) {
          setIsAuthenticated(false)
          setIsCheckingAuth(false)
        }
        return
      }

      try {
        await authApi.me()
        if (active) {
          setIsAuthenticated(true)
          setAuthError(null)
        }
      } catch (error) {
        if (active) {
          setIsAuthenticated(false)
          setAuthError(getErrorMessage(error))
        }
      } finally {
        if (active) {
          setIsCheckingAuth(false)
        }
      }
    }

    const handleAuthStateChanged = (event: Event) => {
      const customEvent = event as CustomEvent<{ authenticated?: boolean }>
      const authenticated = Boolean(customEvent.detail?.authenticated)
      setIsAuthenticated(authenticated)
      if (!authenticated) {
        setCurrentPage('dashboard')
      }
    }

    window.addEventListener(AUTH_STATE_CHANGED_EVENT, handleAuthStateChanged)
    verifyAuth()

    return () => {
      active = false
      window.removeEventListener(AUTH_STATE_CHANGED_EVENT, handleAuthStateChanged)
    }
  }, [])

  const handleLogin = async () => {
    if (!username.trim() || !password.trim()) {
      setAuthError('请输入用户名和密码')
      return
    }

    setIsLoginSubmitting(true)
    setAuthError(null)

    try {
      await authApi.login(username.trim(), password)
      await authApi.me()
      setIsAuthenticated(true)
      setCurrentPage('dashboard')
    } catch (error) {
      setIsAuthenticated(false)
      setAuthError(getErrorMessage(error))
    } finally {
      setIsLoginSubmitting(false)
    }
  }

  const pageNode = useMemo(() => {
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
      case 'templates':
        return <Templates />
      default:
        return <Dashboard />
    }
  }, [currentPage])

  if (isCheckingAuth) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
        <div className="bg-white border border-gray-200 rounded-lg p-8 w-full max-w-md text-center">
          <p className="text-lg font-semibold text-gray-900">正在校验登录态...</p>
          <p className="text-sm text-gray-500 mt-2">请稍候</p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
        <div className="bg-white border border-gray-200 rounded-lg p-8 w-full max-w-md">
          <h1 className="text-2xl font-bold text-gray-900">登录 Travel Hub</h1>
          <p className="text-sm text-gray-500 mt-2">未登录无法访问业务页面</p>

          <div className="space-y-4 mt-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">用户名</label>
              <input
                type="text"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">密码</label>
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                onKeyDown={(event) => {
                  if (event.key === 'Enter') {
                    void handleLogin()
                  }
                }}
              />
            </div>

            {authError ? <p className="text-sm text-red-600">登录失败: {authError}</p> : null}

            <Button onClick={handleLogin} loading={isLoginSubmitting} className="w-full">
              登录
            </Button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar currentPage={currentPage} onPageChange={setCurrentPage} />
      <main className="flex-1 overflow-auto">{pageNode}</main>
    </div>
  )
}
