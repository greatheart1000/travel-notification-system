import { Suspense, lazy, useCallback, useEffect, useMemo, useState } from 'react'
import { AUTH_STATE_CHANGED_EVENT, hasAccessToken } from './adapters/authAdapter'
import { parseAppRoute, pageToPath, type AppRoute } from './app/router'
import { Button } from './components/Button'
import { Sidebar } from './components/Sidebar'
import { HighRiskGroupDetailPage } from './pages/groups/HighRiskGroupDetailPage'
import { HighRiskGroupListPage } from './pages/groups/HighRiskGroupListPage'
import { WorkflowDashboardPage } from './pages/dashboard/WorkflowDashboardPage'
import { TaskBucketPage } from './pages/tasks/TaskBucketPage'
import { TaskDetailPage } from './pages/tasks/TaskDetailPage'
import { authApi, getErrorMessage } from './services/api'
import { travelDemoService } from './services/travel/travelDemoService'

const Analytics = lazy(() => import('./pages/Analytics').then((module) => ({ default: module.Analytics })))
const Notifications = lazy(() => import('./pages/Notifications').then((module) => ({ default: module.Notifications })))
const Preferences = lazy(() => import('./pages/Preferences').then((module) => ({ default: module.Preferences })))
const Trips = lazy(() => import('./pages/Trips').then((module) => ({ default: module.Trips })))

function PageLoadingFallback() {
  return (
    <div className="min-h-[240px] rounded-2xl border border-slate-200 bg-white p-6 text-center">
      <p className="text-base font-semibold text-slate-900">页面加载中...</p>
      <p className="mt-2 text-sm text-slate-500">正在按需加载当前模块</p>
    </div>
  )
}

export default function App() {
  const [route, setRoute] = useState<AppRoute>(() => parseAppRoute(window.location.pathname, window.location.search))

  useEffect(() => {
    travelDemoService.bootstrap()
  }, [])

  const [isCheckingAuth, setIsCheckingAuth] = useState(true)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [authError, setAuthError] = useState<string | null>(null)

  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('123456')
  const [isLoginSubmitting, setIsLoginSubmitting] = useState(false)

  const navigate = useCallback((path: string) => {
    window.history.pushState({}, '', path)
    setRoute(parseAppRoute(window.location.pathname, window.location.search))
  }, [])

  const openTask = useCallback((taskId: string) => navigate(pageToPath('task_detail', { taskId })), [navigate])
  const openGroup = useCallback((groupId: string) => navigate(pageToPath('group_detail', { groupId })), [navigate])

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
        navigate('/dashboard')
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
      await authApi.me()
      setIsAuthenticated(true)
      navigate('/dashboard')
    } catch (error) {
      setIsAuthenticated(false)
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
    if (
      route.page === 'dashboard' ||
      route.page === 'tasks_todo' ||
      route.page === 'tasks_overdue' ||
      route.page === 'tasks_takeover' ||
      route.page === 'tasks_my_workbench' ||
      route.page === 'task_detail' ||
      route.page === 'group_high_risk' ||
      route.page === 'group_detail'
    ) {
      return 'dashboard'
    }
    return route.page
  }, [route.page])

  const pageNode = useMemo(() => {
    switch (route.page) {
      case 'dashboard':
        return <WorkflowDashboardPage onNavigate={navigate} />
      case 'tasks_todo':
        return <TaskBucketPage bucket="todo" onOpenTask={openTask} />
      case 'tasks_overdue':
        return <TaskBucketPage bucket="overdue" onOpenTask={openTask} />
      case 'tasks_takeover':
        return <TaskBucketPage bucket="takeover" onOpenTask={openTask} />
      case 'tasks_my_workbench':
        return <TaskBucketPage bucket="my" onOpenTask={openTask} />
      case 'task_detail':
        return route.taskId ? (
          <TaskDetailPage taskId={route.taskId} onOpenGroup={openGroup} onNavigate={navigate} />
        ) : (
          <WorkflowDashboardPage onNavigate={navigate} />
        )
      case 'group_high_risk':
        return <HighRiskGroupListPage onOpenGroup={openGroup} />
      case 'group_detail':
        return route.groupId ? <HighRiskGroupDetailPage groupId={route.groupId} onOpenTask={openTask} /> : <HighRiskGroupListPage onOpenGroup={openGroup} />
      case 'trips':
        return (
          <Trips
            tripId={route.tripId ?? null}
            onOpenTrip={(tripId) => navigate(`/trips/${encodeURIComponent(tripId)}`)}
            onBackToList={() => navigate('/trips')}
            onOpenTripNotifications={(tripId) => navigate(pageToPath('notifications', { tripId }))}
          />
        )
      case 'notifications':
        return <Notifications tripId={route.tripId ?? null} onBackToTrip={(tripId) => navigate(`/trips/${encodeURIComponent(tripId)}`)} />
      case 'preferences':
        return <Preferences />
      case 'analytics':
        return <Analytics />
      default:
        return <WorkflowDashboardPage onNavigate={navigate} />
    }
  }, [navigate, openGroup, openTask, route.groupId, route.page, route.taskId, route.tripId])

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
        <Sidebar
          currentPage={sidebarPage}
          onPageChange={(page) => {
            if (page === 'dashboard') navigate('/dashboard')
            else navigate(`/${page}`)
          }}
        />
      </div>
      <main className="flex-1 overflow-auto print:overflow-visible print:w-full">
        <Suspense fallback={<PageLoadingFallback />}>{pageNode}</Suspense>
      </main>
    </div>
  )
}
