export type AppPage =
  | 'dashboard'
  | 'dashboard_ongoing_trips'
  | 'dashboard_pending_notifications'
  | 'tasks_todo'
  | 'tasks_overdue'
  | 'tasks_takeover'
  | 'tasks_my_workbench'
  | 'task_detail'
  | 'group_high_risk'
  | 'group_detail'
  | 'trips'
  | 'analytics'

export interface AppRoute {
  page: AppPage
  taskId?: string
  groupId?: string
  tripId?: string | null
}

export function parseAppRoute(pathname: string, search: string): AppRoute {
  const parts = pathname.split('/').filter(Boolean)

  if (parts.length === 0 || parts[0] === 'dashboard') {
    if (parts[1] === 'ongoing-trips') return { page: 'dashboard_ongoing_trips' }
    if (parts[1] === 'pending-notifications') return { page: 'dashboard_pending_notifications' }
    return { page: 'dashboard' }
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

  if (parts[0] === 'trips' && parts[1] && parts[2] === 'notifications') {
    return { page: 'trips', tripId: decodeURIComponent(parts[1]) }
  }
  if (parts[0] === 'trips' && parts[1]) return { page: 'trips', tripId: decodeURIComponent(parts[1]) }
  if (parts[0] === 'trips') return { page: 'trips', tripId: null }

  if (parts[0] === 'notifications') {
    if (parts[1] === 'team' && parts[2]) {
      return { page: 'trips', tripId: decodeURIComponent(parts[2]) }
    }
    const query = new URLSearchParams(search)
    const tripId = query.get('trip_id')
    return tripId ? { page: 'trips', tripId } : { page: 'trips', tripId: null }
  }
  if (parts[0] === 'analytics') return { page: 'analytics' }

  return { page: 'dashboard' }
}

export function pageToPath(page: AppPage, params?: { taskId?: string; groupId?: string; tripId?: string | null }): string {
  switch (page) {
    case 'dashboard':
      return '/dashboard'
    case 'dashboard_ongoing_trips':
      return '/dashboard/ongoing-trips'
    case 'dashboard_pending_notifications':
      return '/dashboard/pending-notifications'
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
    case 'trips':
      return params?.tripId ? `/trips/${encodeURIComponent(params.tripId)}` : '/trips'
    default:
      return '/dashboard'
  }
}
