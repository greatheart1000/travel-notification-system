import { Suspense, lazy, useCallback, useEffect, useMemo, useState } from 'react'
import { AUTH_STATE_CHANGED_EVENT, hasAccessToken } from './adapters/authAdapter'
import { parseAppRoute, type AppRoute } from './app/router'
import { Header } from './components/Header'
import { Sidebar, type SidebarPage } from './components/Sidebar'
import { SessionProvider } from './context/SessionContext'
import { tenantSettingsApi, type TenantInfo } from './services/commercialApi'
import { authApi } from './services/api'
import type { CurrentUser } from './types/api'

const Analytics = lazy(() => import('./pages/Analytics').then((module) => ({ default: module.Analytics })))
const Trips = lazy(() => import('./pages/Trips').then((module) => ({ default: module.Trips })))
const TripNotifications = lazy(() => import('./pages/TripNotifications').then((module) => ({ default: module.TripNotifications })))
const TripWorkflowPage = lazy(() => import('./pages/TripWorkflowPage').then((module) => ({ default: module.TripWorkflowPage })))
const Preferences = lazy(() => import('./pages/Preferences').then((module) => ({ default: module.Preferences })))
const Billing = lazy(() => import('./pages/Billing').then((module) => ({ default: module.Billing })))
const Login = lazy(() => import('./pages/Login').then((module) => ({ default: module.Login })))
const Register = lazy(() => import('./pages/Register').then((module) => ({ default: module.Register })))
const Channels = lazy(() =>
  import('./pages/settings/Channels').then((module) => ({ default: module.Channels })),
)
const Rules = lazy(() => import('./pages/settings/Rules').then((module) => ({ default: module.Rules })))
const Jobs = lazy(() => import('./pages/settings/Jobs').then((module) => ({ default: module.Jobs })))
const Users = lazy(() => import('./pages/settings/Users').then((module) => ({ default: module.Users })))
const Operator = lazy(() => import('./pages/Operator').then((module) => ({ default: module.Operator })))

function PageLoadingFallback() {
  return (
    <div className="min-h-60 rounded-card border border-paper-200 bg-white p-6 text-center">
      <p className="text-base font-medium text-paper-900">加载中</p>
      <p className="mt-2 text-sm text-paper-500">正在加载当前模块</p>
    </div>
  )
}

function SessionLoading() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-paper-100 p-6">
      <div className="w-full max-w-md rounded-panel border border-paper-200 bg-white p-8 text-center shadow-card">
        <p className="text-base font-medium text-paper-900">正在校验登录态</p>
        <p className="mt-2 text-sm text-paper-500">请稍候，正在加载企业工作台</p>
      </div>
    </div>
  )
}

export default function App() {
  const [route, setRoute] = useState<AppRoute>(() =>
    parseAppRoute(window.location.pathname, window.location.search),
  )
  const [isCheckingAuth, setIsCheckingAuth] = useState(true)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [user, setUser] = useState<CurrentUser | null>(null)
  const [tenant, setTenant] = useState<TenantInfo | null>(null)

  const navigate = useCallback((path: string) => {
    window.history.pushState({}, '', path)
    setRoute(parseAppRoute(path, ''))
  }, [])

  const loadSession = useCallback(async () => {
    const profile = await authApi.me()
    setUser(profile)
    try {
      const tenantInfo = await tenantSettingsApi.getCurrentTenant()
      setTenant(tenantInfo)
    } catch {
      setTenant(null)
    }
    setIsAuthenticated(true)
    return profile
  }, [])

  useEffect(() => {
    let active = true

    const verifyAuth = async () => {
      if (!hasAccessToken()) {
        if (active) {
          setIsAuthenticated(false)
          setIsCheckingAuth(false)
          if (!['login', 'register'].includes(route.page)) {
            navigate('/login')
          }
        }
        return
      }
      try {
        const profile = await loadSession()
        if (active && ['login', 'register'].includes(route.page)) {
          navigate(profile.role === 'operator' ? '/operator' : '/trips')
        }
      } catch {
        if (active) {
          setIsAuthenticated(false)
          setUser(null)
          setTenant(null)
        }
      } finally {
        if (active) setCheckingDone()
      }
    }

    const setCheckingDone = () => setIsCheckingAuth(false)

    const handleAuthStateChanged = (event: Event) => {
      const customEvent = event as CustomEvent<{ authenticated?: boolean }>
      const authenticated = Boolean(customEvent.detail?.authenticated)
      setIsAuthenticated(authenticated)
      if (!authenticated) {
        setUser(null)
        setTenant(null)
        navigate('/login')
      }
    }

    window.addEventListener(AUTH_STATE_CHANGED_EVENT, handleAuthStateChanged)
    void verifyAuth()

    return () => {
      active = false
      window.removeEventListener(AUTH_STATE_CHANGED_EVENT, handleAuthStateChanged)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const handlePopState = () =>
      setRoute(parseAppRoute(window.location.pathname, window.location.search))
    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [])

  const handleAuthenticated = useCallback(async () => {
    const profile = await loadSession()
    navigate(profile.role === 'operator' ? '/operator' : '/trips')
  }, [loadSession, navigate])

  const sidebarPage: SidebarPage = useMemo(() => {
    switch (route.page) {
      case 'analytics':
        return 'analytics'
      case 'preferences':
        return 'preferences'
      case 'billing':
        return 'billing'
      case 'settings_channels':
        return 'settings_channels'
      case 'settings_rules':
        return 'settings_rules'
      case 'settings_jobs':
        return 'settings_jobs'
      case 'settings_users':
        return 'settings_users'
      case 'operator':
        return 'operator'
      default:
        return 'trips'
    }
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
      case 'billing':
        return <Billing />
      case 'settings_channels':
        return <Channels />
      case 'settings_rules':
        return <Rules />
      case 'settings_jobs':
        return <Jobs />
      case 'settings_users':
        return <Users />
      case 'operator':
        return <Operator />
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
    return <SessionLoading />
  }

  if (!isAuthenticated) {
    return (
      <Suspense fallback={<SessionLoading />}>
        {route.page === 'register' ? (
          <Register onAuthenticated={handleAuthenticated} onNavigate={navigate} />
        ) : (
          <Login onAuthenticated={handleAuthenticated} onNavigate={navigate} />
        )}
      </Suspense>
    )
  }

  return (
    <SessionProvider
      value={{ user, tenant, refreshSession: async () => { await loadSession() } }}
    >
      <div className="flex h-screen bg-paper-100 print:block print:h-auto print:bg-white">
        <div className="print:hidden">
          <Sidebar
            currentPage={sidebarPage}
            onPageChange={(page) => navigate(pageToPath(page))}
            userRole={user?.role ?? 'user'}
            tenantName={tenant?.name}
            username={user?.username}
          />
        </div>
        <div className="flex flex-1 flex-col overflow-hidden">
          <Header />
          <main className="flex-1 overflow-y-auto">
            <Suspense fallback={<PageLoadingFallback />}>{pageNode}</Suspense>
          </main>
        </div>
      </div>
    </SessionProvider>
  )
}

function pageToPath(page: SidebarPage): string {
  switch (page) {
    case 'analytics':
      return '/analytics'
    case 'preferences':
      return '/preferences'
    case 'billing':
      return '/billing'
    case 'settings_channels':
      return '/settings/channels'
    case 'settings_rules':
      return '/settings/rules'
    case 'settings_jobs':
      return '/settings/jobs'
    case 'settings_users':
      return '/settings/users'
    case 'operator':
      return '/operator'
    default:
      return '/trips'
  }
}
