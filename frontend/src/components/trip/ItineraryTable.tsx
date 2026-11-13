import { Trash2, PlusCircle, Car, Map, Building2, CalendarDays } from 'lucide-react'
import { Button } from '../Button'
import { type ItineraryItem } from '../../types/api'

interface ItineraryTableProps {
  items: ItineraryItem[]
  onChange: (items: ItineraryItem[]) => void
}

export function ItineraryTable({ items, onChange }: ItineraryTableProps) {
  const handleAdd = () => {
    onChange([...items, { date: '', transport: '越野车', route: '', hotel: '' }])
  }

  const handleUpdate = (index: number, field: keyof ItineraryItem, value: string) => {
    const newItems = [...items]
    newItems[index] = { ...newItems[index], [field]: value }
    onChange(newItems)
  }

  const handleRemove = (index: number) => {
    onChange(items.filter((_, i) => i !== index))
  }

  return (
    <div className="space-y-6 print:space-y-2">
      <div className="flex justify-between items-center print:hidden">
        <h3 className="text-xl font-semibold text-paper-900 flex items-center gap-2">
          <CalendarDays className="text-accent-600" size={24} />
          每日日程安排
        </h3>
        <Button size="sm" variant="secondary" onClick={handleAdd}>
          <PlusCircle className="w-4 h-4 mr-1" />
          新增一天
        </Button>
      </div>

      <div className="overflow-hidden rounded-panel border border-paper-100 shadow-card bg-white print:border-2 print:border-paper-900 print:rounded-none print:shadow-none">
        <table className="w-full text-sm text-left border-collapse print:text-xs">
          <thead className="bg-paper-50 border-b border-paper-100 print:bg-paper-100 print:border-b-2 print:border-paper-900">
            <tr>
              <th className="px-4 py-4 font-semibold text-paper-500 w-24 print:border-r print:border-paper-900 print:text-paper-900 print:py-2">日期</th>
              <th className="px-4 py-4 font-semibold text-paper-500 w-32 print:border-r print:border-paper-900 print:text-paper-900 print:py-2">交通方式</th>
              <th className="px-4 py-4 font-semibold text-paper-500 print:border-r print:border-paper-900 print:text-paper-900 print:py-2">路线详情</th>
              <th className="px-4 py-4 font-semibold text-paper-500 w-56 print:border-r print:border-paper-900 print:text-paper-900 print:py-2">入住酒店</th>
              <th className="px-4 py-4 font-semibold text-paper-500 w-16 text-center print:hidden">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-paper-50 print:divide-y print:divide-paper-900">
            {items.map((item, idx) => (
              <tr key={idx} className="group hover:bg-accent-50/30 transition-colors align-top print:break-inside-avoid">
                <td className="px-3 py-3 print:px-2 print:py-1 print:border-r print:border-paper-900">
                  <input
                    className="w-full px-2 py-2 bg-transparent border border-transparent hover:border-paper-200 focus:border-accent-600 focus:bg-white rounded-control outline-none transition-colors text-paper-900 font-medium print:p-0 print:border-none print:bg-transparent"
                    placeholder="MM-DD"
                    value={item.date}
                    onChange={(e) => handleUpdate(idx, 'date', e.target.value)}
                  />
                </td>
                <td className="px-3 py-3 print:px-2 print:py-1 print:border-r print:border-paper-900">
                  <div className="relative">
                    <Car className="absolute left-2.5 top-3 text-paper-400 w-3.5 h-3.5 print:hidden" />
                    <select
                      className="w-full pl-8 pr-2 py-2 bg-transparent border border-transparent hover:border-paper-200 focus:border-accent-600 focus:bg-white rounded-control outline-none appearance-none transition-colors text-paper-700 print:p-0 print:border-none print:bg-transparent print:appearance-none print:text-paper-900"
                      value={item.transport}
                      onChange={(e) => handleUpdate(idx, 'transport', e.target.value)}
                    >
                      <option value="越野车">越野车</option>
                      <option value="接机">接机</option>
                      <option value="送机">送机</option>
                      <option value="商务车">商务车</option>
                      <option value="自由活动">自由活动</option>
                    </select>
                  </div>
                </td>
                <td className="px-3 py-3 print:px-2 print:py-1 print:border-r print:border-paper-900">
                  <div className="relative">
                    <Map className="absolute left-2.5 top-3 text-paper-400 w-3.5 h-3.5 print:hidden" />
                    <textarea
                      className="w-full pl-8 pr-2 py-2 bg-transparent border border-transparent hover:border-paper-200 focus:border-accent-600 focus:bg-white rounded-control outline-none transition-colors text-paper-800 resize-y min-h-11 leading-snug print:p-0 print:border-none print:bg-transparent print:text-paper-900 print:resize-none print:min-h-0 print:overflow-hidden"
                      placeholder="例如：喀什古城 - 白沙湖"
                      rows={2}
                      value={item.route}
                      onChange={(e) => handleUpdate(idx, 'route', e.target.value)}
                    />
                  </div>
                </td>
                <td className="px-3 py-3 print:px-2 print:py-1 print:border-r print:border-paper-900">
                  <div className="relative">
                    <Building2 className="absolute left-2.5 top-3 text-paper-400 w-3.5 h-3.5 print:hidden" />
                    <textarea
                      className="w-full pl-8 pr-2 py-2 bg-transparent border border-transparent hover:border-paper-200 focus:border-accent-600 focus:bg-white rounded-control outline-none transition-colors text-paper-800 resize-y min-h-16 leading-snug print:p-0 print:border-none print:bg-transparent print:text-paper-900 print:resize-none print:min-h-0 print:overflow-hidden"
                      placeholder="入住酒店名称"
                      rows={2}
                      value={item.hotel}
                      onChange={(e) => handleUpdate(idx, 'hotel', e.target.value)}
                      onFocus={(e) => {
                        e.currentTarget.style.height = 'auto';
                        e.currentTarget.style.height = e.currentTarget.scrollHeight + 'px';
                      }}
                      onInput={(e) => {
                        e.currentTarget.style.height = 'auto';
                        e.currentTarget.style.height = e.currentTarget.scrollHeight + 'px';
                      }}
                    />
                  </div>
                </td>
                <td className="px-3 py-3 text-center print:hidden">
                  <button
                    className="text-paper-300 hover:text-danger-500 p-2 mt-1 rounded-control hover:bg-danger-50 transition-colors opacity-0 group-hover:opacity-100"
                    onClick={() => handleRemove(idx)}
                  >
                    <Trash2 size={16} />
                  </button>
                </td>
              </tr>
            ))}
            {items.length === 0 && (
              <tr>
                <td colSpan={5} className="py-20 text-center">
                  <div className="flex flex-col items-center gap-2 text-paper-400">
                    <CalendarDays size={48} className="opacity-20" />
                    <p>暂无日程计划，点击右上角开始添加</p>
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
