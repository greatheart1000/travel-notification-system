import { AlertCircle, Inbox, Loader2, RefreshCw } from 'lucide-react'
import { Button } from './Button'

type PageStateKind = 'loading' | 'error' | 'empty'

interface PageStateProps {
  kind: PageStateKind
  title?: string
  description?: string
  onRetry?: () => void
  className?: string
}

const stateConfig: Record<PageStateKind, { icon: typeof Loader2; defaultTitle: string; iconClass: string }> = {
  loading: {
    icon: Loader2,
    defaultTitle: '加载中',
    iconClass: 'text-accent-600 animate-spin',
  },
  error: {
    icon: AlertCircle,
    defaultTitle: '加载失败',
    iconClass: 'text-danger-600',
  },
  empty: {
    icon: Inbox,
    defaultTitle: '暂无数据',
    iconClass: 'text-paper-400',
  },
}

export function PageState({ kind, title, description, onRetry, className = '' }: PageStateProps) {
  const config = stateConfig[kind]
  const Icon = config.icon

  return (
    <div className={`rounded-card border border-paper-200 bg-white p-8 text-center ${className}`}>
      <Icon className={`mx-auto mb-3 h-6 w-6 ${config.iconClass}`} />
      <p className="text-base font-medium text-paper-900">{title ?? config.defaultTitle}</p>
      {description ? <p className="mt-2 text-sm text-paper-500">{description}</p> : null}
      {onRetry ? (
        <div className="mt-4">
          <Button variant="secondary" size="sm" onClick={onRetry}>
            <RefreshCw className="h-4 w-4" />
            重试
          </Button>
        </div>
      ) : null}
    </div>
  )
}
