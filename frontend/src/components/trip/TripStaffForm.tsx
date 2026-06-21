import { useEffect, useState } from 'react'
import { Save, User, Phone } from 'lucide-react'
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
  { value: 'manager', label: '团期负责人', icon: '👔' },
  { value: 'concierge', label: '旅行管家', icon: '🎒' },
  { value: 'driver', label: '司机', icon: '🚗' },
]

export function TripStaffForm({ tripId }: Props) {
  const [staff, setStaff] = useState<StaffMember[]>(DEFAULT_STAFF)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  useEffect(() => {
    (async () => {
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
      setMessage(`保存失败: ${e?.message || '未知错误'}`)
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div className="p-4 text-sm text-gray-500">加载人员配置...</div>

  return (
    <div className="space-y-4">
      {message && (
        <div className={`text-sm p-2 rounded ${message.includes('失败') ? 'bg-red-50 text-red-700' : 'bg-green-50 text-green-700'}`}>
          {message}
        </div>
      )}

      {ROLE_OPTIONS.map(({ value, label, icon }) => {
        const s = staff.find((x) => x.role === value) || { role: value, name: '', phone: '' }
        return (
          <div key={value} className="border rounded-lg p-3 space-y-2">
            <div className="text-sm font-medium text-gray-700">
              {icon} {label}
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-xs text-gray-400 flex items-center gap-1">
                  <User className="h-3 w-3" /> 姓名
                </label>
                <input
                  type="text"
                  value={s.name}
                  onChange={(e) => updateField(value, 'name', e.target.value)}
                  placeholder="输入姓名"
                  className="w-full mt-1 px-2 py-1.5 text-sm border rounded focus:outline-none focus:ring-2 focus:ring-cyan-300"
                />
              </div>
              <div>
                <label className="text-xs text-gray-400 flex items-center gap-1">
                  <Phone className="h-3 w-3" /> 电话
                </label>
                <input
                  type="text"
                  value={s.phone}
                  onChange={(e) => updateField(value, 'phone', e.target.value)}
                  placeholder="输入电话"
                  className="w-full mt-1 px-2 py-1.5 text-sm border rounded focus:outline-none focus:ring-2 focus:ring-cyan-300"
                />
              </div>
            </div>
          </div>
        )
      })}

      <button
        onClick={handleSave}
        disabled={saving}
        className="w-full flex items-center justify-center gap-2 px-4 py-2 text-sm text-white bg-cyan-600 hover:bg-cyan-700 rounded disabled:opacity-50"
      >
        <Save className="h-4 w-4" />
        {saving ? '保存中...' : '保存人员配置'}
      </button>
    </div>
  )
}
