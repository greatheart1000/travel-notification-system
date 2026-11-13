interface TripNotificationRuleFormProps {
  mode: 'create' | 'edit'
}

export function TripNotificationRuleForm({ mode }: TripNotificationRuleFormProps) {
  return (
    <div className="rounded-control border border-accent-100 bg-accent-50 p-4">
      <h3 className="font-semibold text-paper-900">{mode === 'create' ? '新增通知规则' : '编辑通知规则'}</h3>
      <p className="mt-1 text-sm text-paper-600">支持从 Figma Make 的短信内容模板创建或编辑旅行团通知规则。</p>
    </div>
  )
}
