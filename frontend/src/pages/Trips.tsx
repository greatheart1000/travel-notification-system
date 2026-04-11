import { useState } from 'react'
import { Header } from '../components/Header'
import { Card } from '../components/Card'
import { Button } from '../components/Button'
import { Badge } from '../components/Badge'
import { Modal } from '../components/Modal'
import { Plus, Edit, Trash2, MapPin, Calendar, Users } from 'lucide-react'

export function Trips() {
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [trips, setTrips] = useState([
    {
      id: 1,
      destination: '乌鲁木齐 - 喀什',
      team: 'TEAM-001',
      startDate: '2026-04-15',
      endDate: '2026-04-20',
      participants: 28,
      status: '进行中',
    },
    {
      id: 2,
      destination: '伊犁 - 塔城',
      team: 'TEAM-002',
      startDate: '2026-04-18',
      endDate: '2026-04-25',
      participants: 35,
      status: '计划中',
    },
    {
      id: 3,
      destination: '阿克苏 - 库尔勒',
      team: 'TEAM-003',
      startDate: '2026-04-20',
      endDate: '2026-04-22',
      participants: 18,
      status: '已完成',
    },
  ])

  const getStatusColor = (status: string) => {
    switch (status) {
      case '进行中':
        return 'success'
      case '计划中':
        return 'info'
      case '已完成':
        return 'default'
      default:
        return 'default'
    }
  }

  return (
    <>
      <Header />
      <div className="p-8">
        {/* Header with Add Button */}
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-bold text-gray-900">行程管理</h1>
          <Button onClick={() => setIsModalOpen(true)}>
            <Plus className="w-5 h-5 inline mr-2" />
            新建行程
          </Button>
        </div>

        {/* Trips Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {trips.map((trip) => (
            <Card key={trip.id}>
              <div className="mb-4">
                <div className="flex items-start justify-between mb-2">
                  <h3 className="text-lg font-semibold text-gray-900">{trip.destination}</h3>
                  <Badge variant={getStatusColor(trip.status)}>
                    {trip.status}
                  </Badge>
                </div>
                <p className="text-sm text-gray-500">{trip.team}</p>
              </div>

              <div className="space-y-3 mb-6">
                <div className="flex items-center gap-3 text-sm text-gray-600">
                  <Calendar className="w-4 h-4 text-blue-600" />
                  <span>{trip.startDate} 至 {trip.endDate}</span>
                </div>
                <div className="flex items-center gap-3 text-sm text-gray-600">
                  <Users className="w-4 h-4 text-blue-600" />
                  <span>{trip.participants} 人参加</span>
                </div>
              </div>

              <div className="flex gap-2 pt-4 border-t border-gray-200">
                <Button variant="secondary" size="sm" className="flex-1">
                  <Edit className="w-4 h-4 inline mr-1" />
                  编辑
                </Button>
                <Button variant="danger" size="sm" className="flex-1">
                  <Trash2 className="w-4 h-4 inline mr-1" />
                  删除
                </Button>
              </div>
            </Card>
          ))}
        </div>

        {/* Add Trip Modal */}
        <Modal
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          title="新建行程"
          footer={
            <div className="flex gap-2 justify-end">
              <Button variant="secondary" onClick={() => setIsModalOpen(false)}>
                取消
              </Button>
              <Button onClick={() => setIsModalOpen(false)}>
                创建
              </Button>
            </div>
          }
        >
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                目的地
              </label>
              <input
                type="text"
                placeholder="例：乌鲁木齐 - 喀什"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                开始日期
              </label>
              <input
                type="date"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                结束日期
              </label>
              <input
                type="date"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                团队ID
              </label>
              <input
                type="text"
                placeholder="例：TEAM-001"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </Modal>
      </div>
    </>
  )
}
