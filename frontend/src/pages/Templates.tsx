import { useState, useEffect } from 'react'
import { Card } from '../components/Card'
import { Button } from '../components/Button'
import { api } from '../services/api'
import { MessageSquare, Plus, Save, Trash2, Variable } from 'lucide-react'

export function Templates() {
  const [templates, setTemplates] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [editingId, setEditingId] = useState<string | null>(null)

  const fetchTemplates = async () => {
    try {
      const data = await api.get('/templates')
      setTemplates(data.items || [])
    } catch (error) {
      console.error('Failed to fetch templates', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchTemplates()
  }, [])

  const handleSave = async (tpl: any) => {
    try {
      await api.put(`/templates/${tpl.id}`, tpl)
      setEditingId(null)
      fetchTemplates()
    } catch (error) {
      alert('保存失败')
    }
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">消息模板管理</h1>
          <p className="text-sm text-gray-500 mt-1">配置自动发送的短信与企微文案</p>
        </div>
        <Button icon={<Plus size={18} />}>新建模板</Button>
      </div>

      <div className="grid grid-cols-1 gap-6">
        {templates.map(tpl => (
          <Card key={tpl.id} className="p-0 overflow-hidden">
            <div className="p-4 border-b border-gray-100 bg-gray-50 flex justify-between items-center">
              <div className="flex items-center gap-2">
                <MessageSquare size={18} className="text-blue-500" />
                <span className="font-semibold text-gray-800">{tpl.name}</span>
                <span className="text-xs px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full">{tpl.channel}</span>
              </div>
              <div className="flex gap-2">
                {editingId === tpl.id ? (
                  <Button size="sm" icon={<Save size={16} />} onClick={() => handleSave(tpl)}>保存</Button>
                ) : (
                  <Button size="sm" variant="secondary" onClick={() => setEditingId(tpl.id)}>编辑</Button>
                )}
                <Button size="sm" variant="secondary" className="text-red-600"><Trash2 size={16} /></Button>
              </div>
            </div>
            <div className="p-4">
              <textarea
                className="w-full p-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-sm font-mono h-24"
                value={tpl.content}
                disabled={editingId !== tpl.id}
                onChange={(e) => {
                  const newTpls = templates.map(t => t.id === tpl.id ? {...t, content: e.target.value} : t)
                  setTemplates(newTpls)
                }}
              />
              <div className="mt-3 flex items-center gap-4 text-xs text-gray-500">
                <span className="flex items-center gap-1"><Variable size={12} />可用变量:</span>
                <code className="bg-gray-100 px-1 rounded">{{customer_name}}</code>
                <code className="bg-gray-100 px-1 rounded">{{destination}}</code>
                <code className="bg-gray-100 px-1 rounded">{{weather}}</code>
                <code className="bg-gray-100 px-1 rounded">{{trip_date}}</code>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  )
}
