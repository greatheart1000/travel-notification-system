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
  { icon: SlidersHorizontal, text: '行程通知统一落在企业微信群' },
  { icon: ScrollText, text: '通知内容与发送结果全程留痕' },
]

const PREVIEW_STEPS = [
  { time: '行前 3 天', label: '行程单与出行提醒' },
  { time: '行中每日 7:00', label: '集合与安全提示' },
  { time: '行后当天', label: '欢送词与满意度回访' },
]

export function AuthShell({ title, subtitle, children, footer }: AuthShellProps) {
  return (
    <div className="min-h-screen bg-paper-100 lg:flex">
      <aside className="relative hidden bg-[#0B1B33] px-10 py-12 text-white lg:flex lg:w-5/12 lg:flex-col lg:justify-between">
        <div className="relative">
          <div className="flex items-center gap-2.5">
            <RouteMark className="h-6 w-6 text-accent-300" />
            <div>
              <div className="text-base font-semibold">行程管家</div>
              <div className="mt-0.5 flex items-center gap-1.5 text-xs text-white/50">
                <span className="h-1.5 w-1.5 rounded-full bg-pink-300" />
                行程通知台
              </div>
            </div>
          </div>

          <h1 className="mt-14 max-w-md text-3xl font-semibold leading-snug">
            导游的行程通知台
          </h1>
          <p className="mt-4 max-w-md text-sm leading-relaxed text-white/60">
            按行前、行中、行后发送企业微信群提醒。管理员能看到每位导游负责的团、实际发出的内容和送达结果。
          </p>

          <div className="mt-10 max-w-md rounded-panel border border-white/10 bg-white/5 p-5">
            <p className="text-xs font-medium text-white/50">一次行程的通知节奏</p>
            <ol className="mt-4 space-y-4">
              {PREVIEW_STEPS.map((step, index) => (
                <li key={step.time} className="flex gap-3">
                  <span className="flex flex-col items-center">
                    <span
                      className={`mt-1 h-2 w-2 rounded-full ${
                        index === 1 ? 'bg-pink-300' : 'bg-accent-300'
                      }`}
                    />
                    {index < PREVIEW_STEPS.length - 1 ? (
                      <span className="mt-1 w-px flex-1 bg-white/10" />
                    ) : null}
                  </span>
                  <div>
                    <p className="text-xs tabular-nums text-white/40">{step.time}</p>
                    <p className="mt-0.5 text-sm text-white/80">{step.label}</p>
                  </div>
                </li>
              ))}
            </ol>
          </div>

          <ul className="mt-10 space-y-3">
            {TRUST_POINTS.map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-center gap-2.5 text-sm text-white/55">
                <Icon className="h-4 w-4 shrink-0 text-white/35" />
                {text}
              </li>
            ))}
          </ul>
        </div>

        <div className="relative text-xs text-white/30">© 2026 行程管家</div>
      </aside>

      <main className="flex min-h-screen flex-1 items-center justify-center px-4 py-10 sm:px-6 sm:py-12">
        <div className="w-full max-w-md">
          <div className="mb-6 flex items-center gap-2 lg:hidden">
            <RouteMark className="h-6 w-6 text-accent-300" />
            <span className="text-base font-semibold text-paper-900">行程管家</span>
          </div>

          <div className="rounded-panel border border-paper-200 bg-white p-6 sm:p-8">
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
