interface StatusPillProps {
  tone: 'neutral' | 'warning' | 'danger' | 'success' | 'info'
  label: string
}

const toneClassMap: Record<StatusPillProps['tone'], string> = {
  neutral: 'bg-slate-100 text-slate-700',
  warning: 'bg-amber-100 text-amber-700',
  danger: 'bg-rose-100 text-rose-700',
  success: 'bg-emerald-100 text-emerald-700',
  info: 'bg-sky-100 text-sky-700',
}

export function StatusPill({ tone, label }: StatusPillProps) {
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${toneClassMap[tone]}`}>{label}</span>
}
