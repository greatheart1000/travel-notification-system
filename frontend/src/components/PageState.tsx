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
    iconClass: 'text-blue-600 animate-spin',
  },
  error: {
    icon: AlertCircle,
    defaultTitle: '加载失败',
    iconClass: 'text-red-600',
  },
  empty: {
    icon: Inbox,
    defaultTitle: '暂无数据',
    iconClass: 'text-gray-500',
  },
}

export function PageState({ kind, title, description, onRetry, className = '' }: PageStateProps) {
  const config = stateConfig[kind]
  const Icon = config.icon

  return (
    <div className={`bg-white border border-gray-200 rounded-lg p-8 text-center ${className}`}>
      <Icon className={`w-8 h-8 mx-auto mb-3 ${config.iconClass}`} />
      <p className="text-lg font-semibold text-gray-900">{title ?? config.defaultTitle}</p>
      {description ? <p className="text-sm text-gray-500 mt-2">{description}</p> : null}
      {onRetry ? (
        <div className="mt-5">
          <Button variant="secondary" onClick={onRetry}>
            <RefreshCw className="w-4 h-4 inline mr-2" />
            重试
          </Button>
        </div>
      ) : null}
    </div>
  )
}
