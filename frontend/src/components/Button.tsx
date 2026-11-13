import { ReactNode } from 'react'

type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'danger-outline' | 'success' | 'ghost'
type ButtonSize = 'sm' | 'md' | 'lg'

interface ButtonProps {
  children: ReactNode
  onClick?: () => void
  variant?: ButtonVariant
  size?: ButtonSize
  disabled?: boolean
  loading?: boolean
  className?: string
  title?: string
}

const variantClasses: Record<ButtonVariant, string> = {
  primary: 'bg-accent-600 text-white hover:bg-accent-700',
  secondary: 'border border-paper-300 bg-white text-paper-800 hover:bg-paper-50',
  danger: 'bg-danger-600 text-white hover:bg-danger-700',
  'danger-outline': 'border border-danger-200 bg-white text-danger-700 hover:bg-danger-50',
  success: 'bg-success-600 text-white hover:bg-success-700',
  ghost: 'text-paper-600 hover:bg-paper-100 hover:text-paper-900',
}

const sizeClasses: Record<ButtonSize, string> = {
  sm: 'h-8 px-3 text-sm',
  md: 'h-9 px-4 text-sm',
  lg: 'h-10 px-5 text-base',
}

export function Button({
  children,
  onClick,
  variant = 'primary',
  size = 'md',
  disabled = false,
  loading = false,
  className = '',
  title,
}: ButtonProps) {
  return (
    <button
      onClick={onClick}
      title={title}
      disabled={disabled || loading}
      className={`
        inline-flex items-center justify-center gap-1.5 whitespace-nowrap rounded-control font-medium
        transition-colors disabled:cursor-not-allowed disabled:opacity-50
        ${variantClasses[variant]}
        ${sizeClasses[size]}
        ${className}
      `}
    >
      {loading ? '加载中…' : children}
    </button>
  )
}
