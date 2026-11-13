import { ReactNode } from 'react'
import { useSession } from '../context/SessionContext'

interface PageShellProps {
  title: string
  description?: string
  actions?: ReactNode
  children: ReactNode
}

export function PageShell({ title, description, actions, children }: PageShellProps) {
  const { tenant } = useSession()

  return (
    <div className="min-h-full">
      <div className="mx-auto w-full max-w-page px-4 py-5 sm:px-6 sm:py-6 lg:px-8">
        <section className="mb-5 rounded-panel border border-accent-100 bg-accent-50/55 px-5 py-5 sm:mb-6 sm:px-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div className="min-w-0">
              <p className="flex items-center gap-2 text-xs font-medium text-accent-800">
                <span className="h-1.5 w-1.5 rounded-full bg-pink-400" />
                {tenant?.name || '月亮旅行'} · 行程通知台
              </p>
              <h1 className="mt-2 text-2xl font-semibold text-paper-900 sm:text-3xl">{title}</h1>
              {description ? (
                <p className="mt-2 max-w-2xl text-sm leading-6 text-paper-600">{description}</p>
              ) : null}
            </div>
            {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
          </div>
        </section>
        {children}
      </div>
    </div>
  )
}
