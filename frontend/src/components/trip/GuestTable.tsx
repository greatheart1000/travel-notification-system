import { Trash2, PlusCircle, User, Phone, StickyNote, Users2, Send } from 'lucide-react'
import { Button } from '../Button'
import { type Guest } from '../../types/api'

interface GuestTableProps {
  guests: Guest[]
  onChange: (guests: Guest[]) => void
  onSend?: (guest: Guest) => void
}

export function GuestTable({ guests, onChange, onSend }: GuestTableProps) {
  const handleAdd = () => {
    onChange([...guests, { name: '', phone: '', notes: '' }])
  }

  const handleUpdate = (index: number, field: keyof Guest, value: string) => {
    const newGuests = [...guests]
    newGuests[index] = { ...newGuests[index], [field]: value }
    onChange(newGuests)
  }

  const handleRemove = (index: number) => {
    onChange(guests.filter((_, i) => i !== index))
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center print:hidden">
        <h3 className="text-xl font-semibold text-paper-900 flex items-center gap-2">
          <Users2 className="text-accent-600" size={24} />
          客人名单及备注
        </h3>
        <Button size="sm" variant="secondary" onClick={handleAdd}>
          <PlusCircle className="w-4 h-4 mr-1" />
          新增客人
        </Button>
      </div>

      <div className="overflow-hidden rounded-panel border border-paper-100 shadow-card bg-white">
        <table className="w-full text-sm text-left border-collapse">
          <thead className="bg-paper-50 border-b border-paper-100">
            <tr>
              <th className="px-6 py-4 font-semibold text-paper-500 w-48">姓名</th>
              <th className="px-6 py-4 font-semibold text-paper-500 w-48">联系电话</th>
              <th className="px-6 py-4 font-semibold text-paper-500">备注 / 特别需求</th>
              <th className="px-6 py-4 font-semibold text-paper-500 w-16 text-center">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-paper-50">
            {guests.map((guest, idx) => (
              <tr key={idx} className="group hover:bg-accent-50/30 transition-colors align-top">
                <td className="px-3 py-3">
                  <div className="relative">
                    <User className="absolute left-2.5 top-3 text-paper-400 w-3.5 h-3.5" />
                    <input
                      className="w-full pl-8 pr-2 py-2 bg-transparent border border-transparent hover:border-paper-200 focus:border-accent-600 focus:bg-white rounded-control outline-none transition-colors text-paper-900 font-medium"
                      placeholder="客人姓名"
                      value={guest.name}
                      onChange={(e) => handleUpdate(idx, 'name', e.target.value)}
                    />
                  </div>
                </td>
                <td className="px-3 py-3">
                  <div className="relative">
                    <Phone className="absolute left-2.5 top-3 text-paper-400 w-3.5 h-3.5" />
                    <input
                      className="w-full pl-8 pr-2 py-2 bg-transparent border border-transparent hover:border-paper-200 focus:border-accent-600 focus:bg-white rounded-control outline-none transition-colors text-paper-800"
                      placeholder="13x xxxx xxxx"
                      value={guest.phone}
                      onChange={(e) => handleUpdate(idx, 'phone', e.target.value)}
                    />
                  </div>
                </td>
                <td className="px-3 py-3">
                  <div className="relative">
                    <StickyNote className="absolute left-2.5 top-3 text-paper-400 w-3.5 h-3.5" />
                    <textarea
                      className="w-full pl-8 pr-2 py-2 bg-transparent border border-transparent hover:border-paper-200 focus:border-accent-600 focus:bg-white rounded-control outline-none transition-colors text-paper-800 resize-y min-h-11 leading-snug"
                      placeholder="例如：接机安排、酒店偏好..."
                      rows={2}
                      value={guest.notes}
                      onChange={(e) => handleUpdate(idx, 'notes', e.target.value)}
                    />
                  </div>
                </td>
                <td className="px-3 py-3 text-center">
                  <div className="flex items-center justify-center gap-1">
                    {onSend && (
                      <button
                        className="text-paper-300 hover:text-accent-600 p-2 mt-1 rounded-control hover:bg-accent-50 transition-colors opacity-0 group-hover:opacity-100"
                        onClick={() => onSend(guest)}
                        title="发送短信"
                      >
                        <Send size={16} />
                      </button>
                    )}
                    <button
                      className="text-paper-300 hover:text-danger-500 p-2 mt-1 rounded-control hover:bg-danger-50 transition-colors opacity-0 group-hover:opacity-100"
                      onClick={() => handleRemove(idx)}
                      title="删除客人"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {guests.length === 0 && (
              <tr>
                <td colSpan={4} className="py-20 text-center">
                  <div className="flex flex-col items-center gap-2 text-paper-400">
                    <Users2 size={48} className="opacity-20" />
                    <p>暂无客人名单，点击右上角开始添加</p>
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
