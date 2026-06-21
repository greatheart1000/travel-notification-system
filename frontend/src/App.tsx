import { Suspense, lazy, useCallback, useEffect, useMemo, useState } from 'react'
import { AUTH_STATE_CHANGED_EVENT, hasAccessToken, setAuthTokens } from './adapters/authAdapter'
import { parseAppRoute, type AppRoute } from './app/router'
import { Button } from './components/Button'
import { Header } from './components/Header'
import { Sidebar } from './components/Sidebar'
import { authApi, getErrorMessage } from './services/api'

const Analytics = lazy(() => import('./pages/Analytics').then((module) => ({ default: module.Analytics })))
const Trips = lazy(() => import('./pages/Trips').then((module) => ({ default: module.Trips })))
const TripNotifications = lazy(() => import('./pages/TripNotifications').then((module) => ({ default: module.TripNotifications })))
const TripWorkflowPage = lazy(() => import('./pages/TripWorkflowPage').then((module) => ({ default: module.TripWorkflowPage })))
const Preferences = lazy(() => import('./pages/Preferences').then((module) => ({ default: module.Preferences })))

function PageLoadingFallback() {
  return (
    <div className="min-h-[240px] rounded-lg border border-gray-200 bg-white p-6 text-center">
      <p className="text-base font-semibold text-gray-900">页面加载中...</p>
      <p className="mt-2 text-sm text-gray-500">正在按需加载当前模块</p>
    </div>
  )
}

function setupMockAuth(): void {
  // Only use mock auth in dev mode, never in production
  if (import.meta.env.DEV) {
    setAuthTokens({
      access_token: 'figma-make-mock-access-token',
      refresh_token: 'figma-make-mock-refresh-token',
      token_type: 'Bearer',
    })
  }
}

export default function App() {
  const [route, setRoute] = useState<AppRoute>(() => parseAppRoute(window.location.pathname, window.location.search))
  const [isCheckingAuth, setIsCheckingAuth] = useState(true)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [authError, setAuthError] = useState<string | null>(null)
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('123456')
  const [isLoginSubmitting, setIsLoginSubmitting] = useState(false)

  const navigate = useCallback((path: string) => {
    window.history.pushState({}, '', path)
    setRoute(parseAppRoute(path, ''))
  }, [])

  useEffect(() => {
    let active = true

    const verifyAuth = async () => {
      if (!hasAccessToken()) {
        setupMockAuth()
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
          setAuthError(null)
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
      setAuthError(null)
      if (!authenticated) {
        navigate('/trips')
      }
    }

    window.addEventListener(AUTH_STATE_CHANGED_EVENT, handleAuthStateChanged)
    void verifyAuth()

    return () => {
      active = false
      window.removeEventListener(AUTH_STATE_CHANGED_EVENT, handleAuthStateChanged)
    }
  }, [navigate])

  const handleLogin = async () => {
    if (!username.trim() || !password.trim()) {
      setAuthError('请输入用户名和密码')
      return
    }

    setIsLoginSubmitting(true)
    setAuthError(null)

    try {
      await authApi.login(username.trim(), password)
      setIsAuthenticated(true)
      navigate('/trips')
    } catch (error) {
      setAuthError(getErrorMessage(error))
    } finally {
      setIsLoginSubmitting(false)
    }
  }

  useEffect(() => {
    const handlePopState = () => setRoute(parseAppRoute(window.location.pathname, window.location.search))
    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [])

  const sidebarPage = useMemo(() => {
    if (route.page === 'analytics' || route.page === 'trips' || route.page === 'trip_notifications' || route.page === 'trip_workflow' || route.page === 'preferences') {
      return route.page === 'trip_notifications' || route.page === 'trip_workflow' ? 'trips' : route.page === 'preferences' ? 'preferences' : route.page
    }
    return 'trips'
  }, [route.page])

  const pageNode = useMemo(() => {
    switch (route.page) {
      case 'trips':
        return (
          <Trips
            tripId={route.tripId ?? null}
            onOpenTrip={(tripId) => navigate(`/trips/${encodeURIComponent(tripId)}`)}
            onBackToList={() => navigate('/trips')}
          />
        )
      case 'trip_notifications':
        return (
          <TripNotifications
            tripId={route.tripId ?? ''}
            onBackToTrip={() => navigate(`/trips/${encodeURIComponent(route.tripId ?? '')}`)}
          />
        )
      case 'trip_workflow':
        return (
          <TripWorkflowPage
            tripId={route.tripId ?? ''}
            onBack={() => navigate(`/trips/${encodeURIComponent(route.tripId ?? '')}`)}
          />
        )
      case 'analytics':
        return <Analytics />
      case 'preferences':
        return <Preferences />
      default:
        return (
          <Trips
            tripId={null}
            onOpenTrip={(tripId) => navigate(`/trips/${encodeURIComponent(tripId)}`)}
            onBackToList={() => navigate('/trips')}
          />
        )
    }
  }, [navigate, route.page, route.tripId])

  if (isCheckingAuth) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
        <div className="bg-white border border-gray-200 rounded-lg p-8 w-full max-w-md text-center">
          <p className="text-lg font-semibold text-gray-900">正在校验登录态...</p>
          <p className="text-sm text-gray-500 mt-2">Figma Mock 模式会自动准备演示登录态</p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
        <div className="bg-white border border-gray-200 rounded-lg p-8 w-full max-w-md">
          <h1 className="text-2xl font-bold text-gray-900">登录 Travel Hub</h1>
          <p className="text-sm text-gray-500 mt-2">默认账号用于 Figma Make 演示 Mock 数据</p>

          <div className="space-y-4 mt-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">用户名</label>
              <input
                type="text"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">密码</label>
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500"
                onKeyDown={(event) => {
                  if (event.key === 'Enter') {
                    void handleLogin()
                  }
                }}
              />
            </div>

            {authError ? <p className="text-sm text-cyan-600">{authError}</p> : null}

            <Button onClick={handleLogin} loading={isLoginSubmitting} className="w-full">
              登录
            </Button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-screen bg-gray-50 print:h-auto print:bg-white print:block">
      <div className="print:hidden">
        <Sidebar
          currentPage={sidebarPage}
          onPageChange={(page) => {
            navigate(`/${page}`)
          }}
        />
      </div>
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto">
          <Suspense fallback={<PageLoadingFallback />}>{pageNode}</Suspense>
        </main>
      </div>
    </div>
  )
}
