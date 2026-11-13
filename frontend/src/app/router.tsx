export type AppPage =
  | 'tasks_todo'
  | 'tasks_overdue'
  | 'tasks_takeover'
  | 'tasks_my_workbench'
  | 'task_detail'
  | 'group_high_risk'
  | 'group_detail'
  | 'trips'
  | 'team_execution'
  | 'trip_notifications'
  | 'trip_workflow'
  | 'analytics'
  | 'preferences'
  | 'billing'
  | 'settings_channels'
  | 'settings_rules'
  | 'settings_jobs'
  | 'settings_users'
  | 'operator'
  | 'login'
  | 'register'

export interface AppRoute {
  page: AppPage
  taskId?: string
  groupId?: string
  tripId?: string | null
  tripTab?: string
}

export function parseAppRoute(pathname: string, search: string): AppRoute {
  const parts = pathname.split('/').filter(Boolean)

  if (parts[0] === 'team') return { page: 'team_execution' }

  if (parts.length === 0 || parts[0] === 'trips') {
    if (parts[1] && parts[2] === 'workflow') return { page: 'trip_workflow', tripId: decodeURIComponent(parts[1]) }
    if (parts[1] && parts[2] === 'notifications') return { page: 'trip_notifications', tripId: decodeURIComponent(parts[1]) }
    if (parts[1]) {
      const query = new URLSearchParams(search)
      return {
        page: 'trips',
        tripId: decodeURIComponent(parts[1]),
        tripTab: query.get('tab') ?? undefined,
      }
    }
    return { page: 'trips', tripId: null }
  }

  if (parts[0] === 'tasks' && parts[1] === 'todo') {
    const query = new URLSearchParams(search)
    if (query.get('scope') === 'mine') return { page: 'tasks_my_workbench' }
    return { page: 'tasks_todo' }
  }
  if (parts[0] === 'tasks' && parts[1] === 'overdue') return { page: 'tasks_overdue' }
  if (parts[0] === 'tasks' && parts[1] === 'takeover') return { page: 'tasks_takeover' }
  if (parts[0] === 'tasks' && parts[1] === 'my-workbench') return { page: 'tasks_my_workbench' }
  if (parts[0] === 'tasks' && parts[1]) return { page: 'task_detail', taskId: decodeURIComponent(parts[1]) }

  if (parts[0] === 'groups' && parts[1] === 'high-risk' && parts[2]) {
    return { page: 'group_detail', groupId: decodeURIComponent(parts[2]) }
  }
  if (parts[0] === 'groups' && parts[1] === 'high-risk') return { page: 'group_high_risk' }

  if (parts[0] === 'notifications') {
    if (parts[1] === 'team' && parts[2]) {
      return { page: 'trips', tripId: decodeURIComponent(parts[2]) }
    }
    const query = new URLSearchParams(search)
    const tripId = query.get('trip_id')
    return tripId ? { page: 'trips', tripId } : { page: 'trips', tripId: null }
  }
  if (parts[0] === 'analytics') return { page: 'analytics' }
  if (parts[0] === 'preferences') return { page: 'preferences' }
  if (parts[0] === 'billing') return { page: 'billing' }
  if (parts[0] === 'operator') return { page: 'operator' }
  if (parts[0] === 'login') return { page: 'login' }
  if (parts[0] === 'register') return { page: 'register' }
  if (parts[0] === 'settings') {
    if (parts[1] === 'channels') return { page: 'settings_channels' }
    if (parts[1] === 'rules') return { page: 'settings_rules' }
    if (parts[1] === 'jobs') return { page: 'settings_jobs' }
    if (parts[1] === 'users') return { page: 'settings_users' }
  }

  return { page: 'trips' }
}

export function pageToPath(page: AppPage, params?: { taskId?: string; groupId?: string; tripId?: string | null }): string {
  switch (page) {
    case 'tasks_todo':
      return '/tasks/todo'
    case 'tasks_overdue':
      return '/tasks/overdue'
    case 'tasks_takeover':
      return '/tasks/takeover'
    case 'tasks_my_workbench':
      return '/tasks/my-workbench'
    case 'task_detail':
      return `/tasks/${encodeURIComponent(params?.taskId ?? '')}`
    case 'group_high_risk':
      return '/groups/high-risk'
    case 'group_detail':
      return `/groups/high-risk/${encodeURIComponent(params?.groupId ?? '')}`
    case 'analytics':
      return '/analytics'
    case 'team_execution':
      return '/team'
    case 'trips':
      return params?.tripId ? `/trips/${encodeURIComponent(params.tripId)}` : '/trips'
    case 'trip_notifications':
      return `/trips/${encodeURIComponent(params?.tripId ?? '')}/notifications`
    case 'trip_workflow':
      return `/trips/${encodeURIComponent(params?.tripId ?? '')}/workflow`
    case 'preferences':
      return '/preferences'
    case 'billing':
      return '/billing'
    case 'operator':
      return '/operator'
    case 'settings_channels':
      return '/settings/channels'
    case 'settings_rules':
      return '/settings/rules'
    case 'settings_jobs':
      return '/settings/jobs'
    case 'settings_users':
      return '/settings/users'
    case 'login':
      return '/login'
    case 'register':
      return '/register'
    default:
      return '/trips'
  }
}
