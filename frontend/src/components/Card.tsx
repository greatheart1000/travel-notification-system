import { ReactNode } from 'react'

interface CardProps {
  title?: string
  children: ReactNode
  className?: string
  footer?: ReactNode
}

export function Card({ title, children, className = '', footer }: CardProps) {
  return (
    <div className={`rounded-card border border-paper-200 bg-white shadow-card ${className}`}>
      {title && (
        <div className="border-b border-paper-200 px-5 py-4">
          <h3 className="text-base font-semibold text-paper-900">{title}</h3>
        </div>
      )}
      <div className="p-5">{children}</div>
      {footer && (
        <div className="rounded-b-card border-t border-paper-200 bg-paper-50 px-5 py-4">
          {footer}
        </div>
      )}
    </div>
  )
}
