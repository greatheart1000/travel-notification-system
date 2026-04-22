import { useCallback, useEffect, useMemo, useState } from 'react'
import { AUTH_STATE_CHANGED_EVENT, hasAccessToken } from './adapters/authAdapter'
import { Button } from './components/Button'
import { Sidebar } from './components/Sidebar'
import { Analytics } from './pages/Analytics'
import { Dashboard } from './pages/Dashboard'
import { Notifications } from './pages/Notifications'
import { Preferences } from './pages/Preferences'
import { Trips } from './pages/Trips'
import { authApi, getErrorMessage } from './services/api'

type Page = 'dashboard' | 'trips' | 'notifications' | 'preferences' | 'analytics'

interface AppRoute {
  page: Page
  tripId: string | null
}

function pickTripIdFromSearch(search: string): string | null {
  const query = new URLSearchParams(search)
  const value = query.get('trip_id')
  if (!value) {
    return null
  }
  return decodeURIComponent(value)
}

function parseRoute(pathname: string): AppRoute {
  return parseRouteWithSearch(pathname, window.location.search)
}

function parseRouteWithSearch(pathname: string, search: string): AppRoute {
  const parts = pathname.split('/').filter(Boolean)
  if (parts[0] === 'trips' && parts[1]) {
    return { page: 'trips', tripId: decodeURIComponent(parts[1]) }
  }
  if (parts[0] === 'trips') {
    return { page: 'trips', tripId: null }
  }
  if (parts[0] === 'notifications') {
    return { page: 'notifications', tripId: pickTripIdFromSearch(search) }
  }
  if (parts[0] === 'notifications' || parts[0] === 'preferences' || parts[0] === 'analytics') {
    return { page: parts[0], tripId: null }
  }
  return { page: 'dashboard', tripId: null }
}

function pagePath(page: Page, tripId?: string | null): string {
  if (page === 'notifications' && tripId) {
    return `/notifications?trip_id=${encodeURIComponent(tripId)}`
  }
  return page === 'dashboard' ? '/' : `/${page}`
}

export default function App() {
  const [route, setRoute] = useState<AppRoute>(() => parseRoute(window.location.pathname))
  const [pageKey, setPageKey] = useState(0)

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
      setAuthError(null)
      if (!authenticated) {
        window.history.replaceState({}, '', '/')
        setRoute({ page: 'dashboard', tripId: null })
        setPageKey(0)
      }
    }

    window.addEventListener(AUTH_STATE_CHANGED_EVENT, handleAuthStateChanged)
    void verifyAuth()

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
      window.history.pushState({}, '', '/')
      setRoute({ page: 'dashboard', tripId: null })
      setPageKey((prev) => prev + 1)
    } catch (error) {
      setIsAuthenticated(false)
      setAuthError(getErrorMessage(error))
    } finally {
      setIsLoginSubmitting(false)
    }
  }

  const handlePageChange = useCallback(
    (newPage: Page) => {
      if (newPage === route.page && route.tripId === null) {
        setPageKey((prev) => prev + 1)
        return
      }
      window.history.pushState({}, '', pagePath(newPage, null))
      setRoute({ page: newPage, tripId: null })
    },
    [route.page, route.tripId],
  )

  useEffect(() => {
    const handlePopState = () => setRoute(parseRouteWithSearch(window.location.pathname, window.location.search))
    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [])

  const openTripDetail = useCallback((tripId: string) => {
    window.history.pushState({}, '', `/trips/${encodeURIComponent(tripId)}`)
    setRoute({ page: 'trips', tripId })
  }, [])

  const backToTrips = useCallback(() => {
    window.history.pushState({}, '', '/trips')
    setRoute({ page: 'trips', tripId: null })
    setPageKey((prev) => prev + 1)
  }, [])

  const openTripNotifications = useCallback((tripId: string) => {
    window.history.pushState({}, '', pagePath('notifications', tripId))
    setRoute({ page: 'notifications', tripId })
  }, [])

  const backToTripDetail = useCallback((tripId: string) => {
    window.history.pushState({}, '', `/trips/${encodeURIComponent(tripId)}`)
    setRoute({ page: 'trips', tripId })
  }, [])

  const pageNode = useMemo(() => {
    switch (route.page) {
      case 'dashboard':
        return <Dashboard key={`dashboard-${pageKey}`} />
      case 'trips':
        return (
          <Trips
            key={`trips-${pageKey}-${route.tripId ?? 'list'}`}
            tripId={route.tripId}
            onOpenTrip={openTripDetail}
            onBackToList={backToTrips}
            onOpenTripNotifications={openTripNotifications}
          />
        )
      case 'notifications':
        return (
          <Notifications
            key={`notifications-${pageKey}-${route.tripId ?? 'global'}`}
            tripId={route.tripId}
            onBackToTrip={backToTripDetail}
          />
        )
      case 'preferences':
        return <Preferences key={`preferences-${pageKey}`} />
      case 'analytics':
        return <Analytics key={`analytics-${pageKey}`} />
      default:
        return <Dashboard key={`dashboard-${pageKey}`} />
    }
  }, [backToTripDetail, backToTrips, openTripDetail, openTripNotifications, pageKey, route.page, route.tripId])

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
    <div className="flex h-screen bg-gray-50 print:h-auto print:bg-white print:block">
      <div className="print:hidden">
        <Sidebar currentPage={route.page} onPageChange={handlePageChange} />
      </div>
      <main className="flex-1 overflow-auto print:overflow-visible print:w-full">{pageNode}</main>
    </div>
  )
}
