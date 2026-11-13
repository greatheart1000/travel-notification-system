import { useEffect, useState } from 'react'
import { Phone, Save, User } from 'lucide-react'
import { Button } from '../Button'
import { staffApi, type StaffMember } from '../../services/api'

interface Props {
  tripId: string
}

const DEFAULT_STAFF: StaffMember[] = [
  { role: 'manager', name: '', phone: '' },
  { role: 'concierge', name: '', phone: '' },
  { role: 'driver', name: '', phone: '' },
]

const ROLE_OPTIONS = [
  { value: 'manager', label: '团期负责人' },
  { value: 'concierge', label: '旅行管家' },
  { value: 'driver', label: '司机' },
]

export function TripStaffForm({ tripId }: Props) {
  const [staff, setStaff] = useState<StaffMember[]>(DEFAULT_STAFF)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  useEffect(() => {
    ;(async () => {
      setLoading(true)
      try {
        const list = await staffApi.getByTrip(tripId)
        if (list.length > 0) {
          setStaff(list)
        }
      } catch { /* use defaults */ }
      finally { setLoading(false) }
    })()
  }, [tripId])

  const updateField = (role: string, field: 'name' | 'phone', value: string) => {
    setStaff((prev) => prev.map((s) => (s.role === role ? { ...s, [field]: value } : s)))
  }

  const handleSave = async () => {
    setSaving(true)
    setMessage(null)
    try {
      await staffApi.updateTripStaff(tripId, staff)
      setMessage('人员配置已保存')
      setTimeout(() => setMessage(null), 3000)
    } catch (e: any) {
      setMessage(`保存失败：${e?.message || '未知错误'}`)
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div className="p-4 text-sm text-paper-500">加载人员配置</div>

  return (
    <div className="space-y-4">
      {message && (
        <div className={`rounded-control border p-3 text-sm ${message.includes('失败') ? 'border-danger-200 bg-danger-50 text-danger-700' : 'border-success-200 bg-success-50 text-success-700'}`}>
          {message}
        </div>
      )}

      {ROLE_OPTIONS.map(({ value, label }) => {
        const s = staff.find((x) => x.role === value) || { role: value, name: '', phone: '' }
        return (
          <div key={value} className="space-y-2 rounded-control border border-paper-200 p-3">
            <div className="text-sm font-medium text-paper-700">{label}</div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <label className="flex items-center gap-1 text-xs text-paper-500">
                  <User className="h-3 w-3" /> 姓名
                </label>
                <input
                  type="text"
                  value={s.name}
                  onChange={(e) => updateField(value, 'name', e.target.value)}
                  placeholder="输入姓名"
                  className="mt-1 w-full rounded-control border border-paper-300 px-2.5 py-2 text-sm focus:border-accent-600 focus:outline-none focus:ring-2 focus:ring-accent-100"
                />
              </div>
              <div>
                <label className="flex items-center gap-1 text-xs text-paper-500">
                  <Phone className="h-3 w-3" /> 电话
                </label>
                <input
                  type="text"
                  value={s.phone}
                  onChange={(e) => updateField(value, 'phone', e.target.value)}
                  placeholder="输入电话"
                  className="mt-1 w-full rounded-control border border-paper-300 px-2.5 py-2 text-sm focus:border-accent-600 focus:outline-none focus:ring-2 focus:ring-accent-100"
                />
              </div>
            </div>
          </div>
        )
      })}

      <Button className="w-full" onClick={() => void handleSave()} loading={saving}>
        <Save className="h-4 w-4" />
        保存人员配置
      </Button>
    </div>
  )
}
