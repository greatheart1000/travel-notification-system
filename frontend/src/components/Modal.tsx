import { ReactNode } from 'react'
import { X } from 'lucide-react'

interface ModalProps {
  isOpen: boolean
  onClose: () => void
  title: string
  children: ReactNode
  footer?: ReactNode
  panelClassName?: string
}

export function Modal({ isOpen, onClose, title, children, footer, panelClassName }: ModalProps) {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="fixed inset-0 bg-paper-950/40" onClick={onClose} aria-hidden="true"></div>
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={`relative mx-4 w-full rounded-panel border border-paper-200 bg-white shadow-raised ${panelClassName ?? 'max-w-md'}`}
      >
        <div className="flex items-center justify-between border-b border-paper-200 px-5 py-4">
          <h2 className="text-lg font-semibold text-paper-900">{title}</h2>
          <button
            onClick={onClose}
            className="rounded-control p-1 text-paper-500 transition-colors hover:bg-paper-100 hover:text-paper-900"
            aria-label="关闭"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="max-h-[70vh] overflow-y-auto p-5">{children}</div>
        {footer && (
          <div className="rounded-b-panel border-t border-paper-200 bg-paper-50 px-5 py-4">
            {footer}
          </div>
        )}
      </div>
    </div>
  )
}
