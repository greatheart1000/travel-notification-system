interface RouteMarkProps {
  className?: string
}

// 品牌记号：一条路线，前两个节点取当前文字色，终点固定为粉色。
export function RouteMark({ className = 'h-5 w-5' }: RouteMarkProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden="true">
      <path
        d="M4 17c3-.8 4-4 7-5s4 1 7-3"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
      <circle cx="4" cy="17" r="1.9" fill="currentColor" />
      <circle cx="11" cy="12" r="1.9" fill="currentColor" />
      <circle cx="18" cy="9" r="1.9" fill="#F472B6" />
    </svg>
  )
}
