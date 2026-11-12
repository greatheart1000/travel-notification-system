import type { ReactNode } from 'react'
import { Plane, ShieldCheck, SlidersHorizontal, ScrollText } from 'lucide-react'

interface AuthShellProps {
  title: string
  subtitle: string
  children: ReactNode
  footer?: ReactNode
}

const TRUST_POINTS = [
  { icon: ShieldCheck, text: '多租户数据隔离，企业之间互不可见' },
  { icon: SlidersHorizontal, text: '短信与企业微信渠道可配置' },
  { icon: ScrollText, text: '发送过程可追溯，失败可重放' },
]

export function AuthShell({ title, subtitle, children, footer }: AuthShellProps) {
  return (
    <div className="min-h-screen bg-slate-50 lg:flex">
      <aside className="relative hidden overflow-hidden bg-gradient-to-br from-slate-950 via-slate-900 to-sky-900 px-12 py-14 text-white lg:flex lg:w-[45%] lg:flex-col lg:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-sky-500/20 ring-1 ring-sky-400/40">
              <Plane className="h-5 w-5 text-sky-300" />
            </span>
            <div>
              <div className="text-xl font-semibold tracking-wide">行程管家</div>
              <div className="text-xs uppercase tracking-[0.25em] text-sky-200/70">Travel Hub</div>
            </div>
          </div>

          <h1 className="mt-16 max-w-md text-3xl font-semibold leading-snug">
            为旅行社提供行前、行中、行后一体化通知与管家协作
          </h1>
          <p className="mt-4 max-w-md text-sm leading-relaxed text-slate-300">
            把重复的提醒交给系统，把时间留给游客。多租户、可配置、可追溯，开箱即用的商业化行程通知平台。
          </p>

          <ul className="mt-12 space-y-4">
            {TRUST_POINTS.map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-center gap-3 text-sm text-slate-200">
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/5 ring-1 ring-white/10">
                  <Icon className="h-4 w-4 text-sky-300" />
                </span>
                {text}
              </li>
            ))}
          </ul>
        </div>

        <div className="text-xs text-slate-400">© 2026 行程管家 · 企业版</div>
      </aside>

      <main className="flex min-h-screen flex-1 items-center justify-center px-6 py-12">
        <div className="w-full max-w-md">
          <div className="mb-6 flex items-center gap-2 lg:hidden">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-sky-600 text-white">
              <Plane className="h-4 w-4" />
            </span>
            <span className="text-lg font-semibold text-slate-900">行程管家</span>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
            <h2 className="text-2xl font-semibold text-slate-900">{title}</h2>
            <p className="mt-2 text-sm text-slate-500">{subtitle}</p>
            <div className="mt-6">{children}</div>
          </div>

          {footer ? <div className="mt-6 text-center text-sm text-slate-500">{footer}</div> : null}
        </div>
      </main>
    </div>
  )
}
