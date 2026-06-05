import { useEffect, useState } from 'react'
import { notificationsApi } from '../../services/api'
import type { NotificationRule } from '../../types/api'

interface PendingNotificationsPageProps {
  onNavigate: (path: string) => void
}

function stageClass(stage: string): string {
  if (stage === '出行前') return 'bg-blue-100 text-blue-700'
  if (stage === '出行中') return 'bg-green-100 text-green-700'
  if (stage === '出行后') return 'bg-purple-100 text-purple-700'
  return 'bg-gray-100 text-gray-700'
}

export function PendingNotificationsPage({ onNavigate }: PendingNotificationsPageProps) {
  const [rules, setRules] = useState<NotificationRule[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 5

  useEffect(() => {
    let active = true
    const load = async () => {
      setLoading(true)
      try {
        const data = await notificationsApi.listRules()
        if (active) setRules(data)
      } catch (e) {
        if (active) setError(e instanceof Error ? e.message : '加载失败')
      } finally {
        if (active) setLoading(false)
      }
    }
    void load()
    return () => { active = false }
  }, [])

  const totalPages = Math.max(1, Math.ceil(rules.length / itemsPerPage))
  const currentRules = rules.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage)

  if (loading) return <div className="p-6 text-center text-gray-500">加载中...</div>
  if (error) return <div className="p-6 text-center text-red-500">{error}</div>

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <button onClick={() => onNavigate('/dashboard')} className="text-gray-600 hover:text-gray-900">← 返回仪表盘</button>
            <h1 className="text-2xl font-bold text-gray-900">通知规则</h1>
          </div>
          <p className="text-gray-600">管理所有旅行团的通知发送规则</p>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-gray-900">通知规则列表 ({rules.length} 条)</h2>
          </div>
        </div>

        {currentRules.length === 0 ? (
          <div className="p-12 text-center text-gray-400">暂无通知规则</div>
        ) : (
          <div className="divide-y divide-gray-200">
            {currentRules.map((rule) => (
              <div key={rule.id} className="p-6 hover:bg-gray-50">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="font-semibold text-gray-900">{rule.name}</h3>
                      <span className={`px-2 py-1 rounded-full text-xs ${stageClass(rule.stageLabel)}`}>{rule.stageLabel}</span>
                      <span className="px-2 py-1 rounded-full text-xs bg-cyan-100 text-cyan-700">{rule.timeSlotLabel}</span>
                      {rule.enabled ? (
                        <span className="px-2 py-1 rounded-full text-xs bg-green-100 text-green-700">已启用</span>
                      ) : (
                        <span className="px-2 py-1 rounded-full text-xs bg-gray-100 text-gray-500">已停用</span>
                      )}
                    </div>
                    <div className="text-sm text-gray-600 mb-2">{rule.scene}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm text-gray-600 mb-1">优先级</div>
                    <div className="text-sm font-medium text-gray-900">{rule.priority}</div>
                  </div>
                </div>

                <div className="bg-gray-50 rounded-lg p-4 mb-3">
                  <div className="text-xs text-gray-600 mb-1">绑定模板</div>
                  <div className="text-sm text-gray-700">{rule.templateLabel}</div>
                </div>

                <div className="flex items-center justify-between">
                  <div className="text-sm text-gray-600">
                    模板ID: <span className="font-medium text-gray-900">{rule.templateId || '未绑定'}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {rules.length > itemsPerPage && (
          <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex items-center justify-between">
            <div className="text-sm text-gray-600">共 {rules.length} 条记录，当前第 {currentPage} / {totalPages} 页</div>
            <div className="flex gap-2">
              <button onClick={() => setCurrentPage(1)} disabled={currentPage === 1} className="px-3 py-1 text-sm rounded bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:bg-gray-200 disabled:text-gray-400">第一页</button>
              <button onClick={() => setCurrentPage(currentPage - 1)} disabled={currentPage === 1} className="px-3 py-1 text-sm rounded bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:bg-gray-200 disabled:text-gray-400">上一页</button>
              {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                <button key={page} onClick={() => setCurrentPage(page)} className={`px-3 py-1 text-sm rounded ${currentPage === page ? 'bg-cyan-500 text-white' : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'}`}>{page}</button>
              ))}
              <button onClick={() => setCurrentPage(currentPage + 1)} disabled={currentPage === totalPages} className="px-3 py-1 text-sm rounded bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:bg-gray-200 disabled:text-gray-400">下一页</button>
              <button onClick={() => setCurrentPage(totalPages)} disabled={currentPage === totalPages} className="px-3 py-1 text-sm rounded bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:bg-gray-200 disabled:text-gray-400">最后一页</button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
