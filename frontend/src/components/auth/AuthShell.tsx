import type { ReactNode } from 'react'
import { ScrollText, ShieldCheck, SlidersHorizontal } from 'lucide-react'
import { RouteMark } from '../RouteMark'

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

const PREVIEW_STEPS = [
  { time: '行前 3 天', label: '行程单与出行提醒' },
  { time: '行中每日', label: '集合与安全提示' },
  { time: '行后 1 天', label: '满意度回访' },
]

export function AuthShell({ title, subtitle, children, footer }: AuthShellProps) {
  return (
    <div className="min-h-screen bg-paper-100 lg:flex">
      <aside className="hidden overflow-hidden bg-paper-950 px-10 py-12 text-paper-50 lg:flex lg:w-5/12 lg:flex-col lg:justify-between">
        <div>
          <div className="flex items-center gap-2.5">
            <RouteMark className="h-6 w-6 text-accent-300" />
            <div>
              <div className="text-base font-semibold">行程管家</div>
              <div className="text-xs text-paper-500">行程通知台</div>
            </div>
          </div>

          <h1 className="mt-14 max-w-md text-2xl font-semibold leading-snug">
            行前、行中、行后的通知，按规则发到
            <span className="whitespace-nowrap">短信和企业微信</span>
          </h1>
          <p className="mt-4 max-w-md text-sm leading-relaxed text-paper-400">
            管理旅行团、排期和通知规则；发送结果可追踪，失败任务可重新入队。
          </p>

          <div className="mt-10 max-w-md rounded-card border border-paper-800 bg-paper-900 p-5">
            <p className="text-xs font-medium text-paper-400">一次行程的通知节奏</p>
            <ol className="mt-4 space-y-4">
              {PREVIEW_STEPS.map((step, index) => (
                <li key={step.time} className="flex gap-3">
                  <span className="flex flex-col items-center">
                    <span className="mt-1 h-2 w-2 rounded-full bg-accent-300" />
                    {index < PREVIEW_STEPS.length - 1 ? (
                      <span className="mt-1 w-px flex-1 bg-paper-700" />
                    ) : null}
                  </span>
                  <div>
                    <p className="text-xs tabular-nums text-paper-400">{step.time}</p>
                    <p className="mt-0.5 text-sm text-paper-100">{step.label}</p>
                  </div>
                </li>
              ))}
            </ol>
          </div>

          <ul className="mt-10 space-y-3">
            {TRUST_POINTS.map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-center gap-2.5 text-sm text-paper-300">
                <Icon className="h-4 w-4 shrink-0 text-paper-500" />
                {text}
              </li>
            ))}
          </ul>
        </div>

        <div className="text-xs text-paper-500">© 2026 行程管家</div>
      </aside>

      <main className="flex min-h-screen flex-1 items-center justify-center px-6 py-12">
        <div className="w-full max-w-md">
          <div className="mb-6 flex items-center gap-2 lg:hidden">
            <RouteMark className="h-6 w-6 text-accent-700" />
            <span className="text-base font-semibold text-paper-900">行程管家</span>
          </div>

          <div className="rounded-panel border border-paper-200 bg-white p-8 shadow-card">
            <h2 className="text-xl font-semibold text-paper-900">{title}</h2>
            <p className="mt-2 text-sm text-paper-500">{subtitle}</p>
            <div className="mt-6">{children}</div>
          </div>

          {footer ? <div className="mt-6 text-center text-sm text-paper-500">{footer}</div> : null}
        </div>
      </main>
    </div>
  )
}
