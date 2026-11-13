import { ReactNode } from 'react'

interface PageShellProps {
  title: string
  description?: string
  actions?: ReactNode
  children: ReactNode
}

export function PageShell({ title, description, actions, children }: PageShellProps) {
  return (
    <div className="min-h-full bg-paper-100">
      <div className="mx-auto w-full max-w-page px-6 py-6 lg:px-8">
        <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-paper-900">{title}</h1>
            {description ? <p className="mt-2 max-w-2xl text-sm text-paper-600">{description}</p> : null}
          </div>
          {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
        </div>
        {children}
      </div>
    </div>
  )
}
