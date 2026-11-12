import { ReactNode } from 'react'

type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'success'
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
  primary: 'bg-sky-500 text-white hover:bg-sky-600',
  secondary: 'bg-gray-200 text-gray-900 hover:bg-gray-300',
  danger: 'bg-red-600 text-white hover:bg-red-700',
  success: 'bg-green-600 text-white hover:bg-green-700',
}

const sizeClasses: Record<ButtonSize, string> = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2 text-base',
  lg: 'px-6 py-3 text-lg',
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
        font-semibold rounded-lg transition-all duration-200
        disabled:opacity-50 disabled:cursor-not-allowed
        ${variantClasses[variant]}
        ${sizeClasses[size]}
        ${className}
      `}
    >
      {loading ? '加载中...' : children}
    </button>
  )
}
