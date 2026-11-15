interface StatusPillProps {
  tone: 'neutral' | 'warning' | 'danger' | 'success' | 'info'
  label: string
}

const toneClassMap: Record<StatusPillProps['tone'], string> = {
  neutral: 'bg-paper-100 text-paper-700',
  warning: 'bg-warning-50 text-warning-700',
  danger: 'bg-danger-50 text-danger-700',
  success: 'bg-success-50 text-success-700',
  info: 'bg-accent-50 text-accent-800',
}

export function StatusPill({ tone, label }: StatusPillProps) {
  return (
    <span className={`inline-flex items-center rounded-control px-2 py-0.5 text-xs font-medium ${toneClassMap[tone]}`}>
      {label}
    </span>
  )
}
