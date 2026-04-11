import { useEffect, useState } from 'react'
import { Header } from '../components/Header'
import { Card } from '../components/Card'
import { Button } from '../components/Button'
import { Badge } from '../components/Badge'
import { Modal } from '../components/Modal'
import { Plus, Edit, Trash2, Calendar, Users } from 'lucide-react'
import { tripsApi } from '../services/api'

interface Trip {
  id: string
  destination: string
  team: string
  start_date: string
  end_date: string
  participants: number
  status: string
}

export function Trips() {
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [trips, setTrips] = useState<Trip[]>([])
  const [form, setForm] = useState({ destination: '', team: '', start_date: '', end_date: '' })

  const loadTrips = async () => {
    const res = await tripsApi.list()
    setTrips(res.data.items)
  }

  useEffect(() => {
    loadTrips()
  }, [])

  const createTrip = async () => {
    await tripsApi.create({ ...form, participants: 0, status: '计划中' })
    setIsModalOpen(false)
    setForm({ destination: '', team: '', start_date: '', end_date: '' })
    loadTrips()
  }

  const deleteTrip = async (id: string) => {
    await tripsApi.remove(id)
    loadTrips()
  }

  const markCompleted = async (id: string) => {
    await tripsApi.update(id, { status: '已完成' })
    loadTrips()
  }

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
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-bold text-gray-900">行程管理</h1>
          <Button onClick={() => setIsModalOpen(true)}>
            <Plus className="w-5 h-5 inline mr-2" />
            新建行程
          </Button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {trips.map((trip) => (
            <Card key={trip.id}>
              <div className="mb-4">
                <div className="flex items-start justify-between mb-2">
                  <h3 className="text-lg font-semibold text-gray-900">{trip.destination}</h3>
                  <Badge variant={getStatusColor(trip.status)}>{trip.status}</Badge>
                </div>
                <p className="text-sm text-gray-500">{trip.team}</p>
              </div>

              <div className="space-y-3 mb-6">
                <div className="flex items-center gap-3 text-sm text-gray-600">
                  <Calendar className="w-4 h-4 text-blue-600" />
                  <span>{trip.start_date} 至 {trip.end_date}</span>
                </div>
                <div className="flex items-center gap-3 text-sm text-gray-600">
                  <Users className="w-4 h-4 text-blue-600" />
                  <span>{trip.participants} 人参加</span>
                </div>
              </div>

              <div className="flex gap-2 pt-4 border-t border-gray-200">
                <Button variant="secondary" size="sm" className="flex-1" onClick={() => markCompleted(trip.id)}>
                  <Edit className="w-4 h-4 inline mr-1" />
                  完成
                </Button>
                <Button variant="danger" size="sm" className="flex-1" onClick={() => deleteTrip(trip.id)}>
                  <Trash2 className="w-4 h-4 inline mr-1" />
                  删除
                </Button>
              </div>
            </Card>
          ))}
        </div>

        <Modal
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          title="新建行程"
          footer={
            <div className="flex gap-2 justify-end">
              <Button variant="secondary" onClick={() => setIsModalOpen(false)}>
                取消
              </Button>
              <Button onClick={createTrip}>创建</Button>
            </div>
          }
        >
          <div className="space-y-4">
            <input type="text" placeholder="目的地" value={form.destination} onChange={(e) => setForm({ ...form, destination: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg" />
            <input type="date" value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg" />
            <input type="date" value={form.end_date} onChange={(e) => setForm({ ...form, end_date: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg" />
            <input type="text" placeholder="团队ID" value={form.team} onChange={(e) => setForm({ ...form, team: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg" />
          </div>
        </Modal>
      </div>
    </>
  )
}
