import { ReactNode } from 'react'
import { Header } from './Header'

interface PageShellProps {
  title: string
  eyebrow?: string
  description?: string
  actions?: ReactNode
  children: ReactNode
}

export function PageShell({ title, eyebrow, description, actions, children }: PageShellProps) {
  return (
    <>
      <Header />
      <div className="min-h-full bg-[radial-gradient(circle_at_top_left,#dbeafe_0,#f8fafc_32%,#f8fafc_100%)]">
        <div className="mx-auto max-w-[1500px] px-6 py-8 lg:px-10">
          <div className="mb-8 flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
            <div>
              {eyebrow ? (
                <p className="mb-3 text-xs font-black uppercase tracking-[0.28em] text-blue-700">
                  {eyebrow}
                </p>
              ) : null}
              <h1 className="text-3xl font-black tracking-tight text-slate-950 lg:text-4xl">
                {title}
              </h1>
              {description ? <p className="mt-3 max-w-3xl text-base text-slate-600">{description}</p> : null}
            </div>
            {actions ? <div className="flex flex-wrap items-center gap-3">{actions}</div> : null}
          </div>
          {children}
        </div>
      </div>
    </>
  )
}
