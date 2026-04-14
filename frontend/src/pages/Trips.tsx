import { useEffect, useRef, useState } from 'react'
import { Header } from '../components/Header'
import { Card } from '../components/Card'
import { Button } from '../components/Button'
import { Badge } from '../components/Badge'
import { Modal } from '../components/Modal'
import { PageState } from '../components/PageState'
import { Plus, Edit, Trash2, Calendar, Users, Upload, CheckCircle } from 'lucide-react'
import { tripsApi, getErrorMessage } from '../services/api'
import { type Trip, type TripStatusCode } from '../types/api'

type LoadState = 'loading' | 'ready' | 'error' | 'empty'

interface TripFormState {
  destination: string
  teamId: string
  startDate: string
  endDate: string
}

const EMPTY_FORM: TripFormState = {
  destination: '',
  teamId: '',
  startDate: '',
  endDate: '',
}

function statusBadgeVariant(status: TripStatusCode): 'success' | 'info' | 'default' | 'warning' {
  if (status === 'in_progress') {
    return 'success'
  }
  if (status === 'planned') {
    return 'info'
  }
  if (status === 'completed') {
    return 'default'
  }
  return 'warning'
}

export function Trips() {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingTripId, setEditingTripId] = useState<string | null>(null)
  const [trips, setTrips] = useState<Trip[]>([])
  const [form, setForm] = useState<TripFormState>(EMPTY_FORM)

  const [loadState, setLoadState] = useState<LoadState>('loading')
  const [errorMessage, setErrorMessage] = useState('')
  const [actionMessage, setActionMessage] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isImporting, setIsImporting] = useState(false)

  const loadTrips = async () => {
    setLoadState('loading')
    setErrorMessage('')

    try {
      const list = await tripsApi.list()
      setTrips(list)
      setLoadState(list.length === 0 ? 'empty' : 'ready')
    } catch (error) {
      setLoadState('error')
      setErrorMessage(getErrorMessage(error))
    }
  }

  useEffect(() => {
    void loadTrips()
  }, [])

  const closeTripModal = () => {
    setIsModalOpen(false)
    setEditingTripId(null)
    setForm(EMPTY_FORM)
  }

  const openCreateModal = () => {
    setEditingTripId(null)
    setForm(EMPTY_FORM)
    setIsModalOpen(true)
  }

  const openEditModal = (trip: Trip) => {
    setEditingTripId(trip.id)
    setForm({
      destination: trip.destination,
      teamId: trip.teamId,
      startDate: trip.startDate,
      endDate: trip.endDate,
    })
    setIsModalOpen(true)
  }



  const submitTrip = async () => {
    if (!form.destination || !form.teamId || !form.startDate || !form.endDate) {
      setActionMessage('保存失败: 请完整填写目的地、团队和日期')
      return
    }

    setIsSubmitting(true)
    setActionMessage(null)

    try {
      if (editingTripId) {
        await tripsApi.update(editingTripId, {
          destination: form.destination,
          teamId: form.teamId,
          startDate: form.startDate,
          endDate: form.endDate,
        })
        setActionMessage('行程修改成功')
      } else {
        await tripsApi.create({
          destination: form.destination,
          teamId: form.teamId,
          startDate: form.startDate,
          endDate: form.endDate,
          participants: 0,
          status: 'planned',
        })
        setActionMessage('行程创建成功')
      }
      closeTripModal()
      await loadTrips()
    } catch (error) {
      setActionMessage(`保存失败: ${getErrorMessage(error)}`)
    } finally {
      setIsSubmitting(false)
    }
  }

  const deleteTrip = async (id: string) => {
    setActionMessage(null)

    try {
      await tripsApi.remove(id)
      setActionMessage('行程已删除')
      await loadTrips()
    } catch (error) {
      setActionMessage(`删除失败: ${getErrorMessage(error)}`)
    }
  }

  const markCompleted = async (id: string) => {
    setActionMessage(null)

    try {
      await tripsApi.update(id, { status: 'completed' })
      setActionMessage('行程已标记为完成')
      await loadTrips()
    } catch (error) {
      setActionMessage(`更新失败: ${getErrorMessage(error)}`)
    }
  }

  const importTrips = async (file: File) => {
    setIsImporting(true)
    setActionMessage(null)

    try {
      const result = await tripsApi.importFile(file)
      await loadTrips()
      setActionMessage(`Excel 导入完成: 成功创建 ${result.createdCount} 条，跳过 ${result.skippedCount} 条`)
    } catch (error) {
      setActionMessage(`导入失败: ${getErrorMessage(error)}`)
    } finally {
      setIsImporting(false)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  const pageHeader = (
    <div className="flex items-center justify-between mb-8">
      <h1 className="text-3xl font-bold text-gray-900">行程管理</h1>
      <div className="flex items-center gap-3">
        <input
          ref={fileInputRef}
          type="file"
          accept=".xlsx,.csv"
          className="hidden"
          onChange={(event) => {
            const file = event.target.files?.[0]
            if (file) {
              void importTrips(file)
            }
          }}
        />
        <Button variant="secondary" onClick={() => fileInputRef.current?.click()} loading={isImporting}>
          <Upload className="w-5 h-5 inline mr-2" />
          Excel导入
        </Button>
        <Button onClick={openCreateModal}>
          <Plus className="w-5 h-5 inline mr-2" />
          新建行程
        </Button>
      </div>
    </div>
  )

  return (
    <>
      <Header />
      <div className="p-8">
        {pageHeader}

        {actionMessage ? (
          <p className={`text-sm mb-4 ${actionMessage.includes('失败') ? 'text-red-600' : 'text-green-600'}`}>
            {actionMessage}
          </p>
        ) : null}

        {loadState === 'loading' ? (
          <PageState kind="loading" title="正在加载行程" />
        ) : null}

        {loadState === 'error' ? (
          <PageState
            kind="error"
            title="行程加载失败"
            description={errorMessage}
            onRetry={() => {
              void loadTrips()
            }}
          />
        ) : null}

        {loadState === 'empty' ? (
          <PageState
            kind="empty"
            title="暂无行程数据"
            description="可以先创建一条行程"
            onRetry={() => {
              void loadTrips()
            }}
          />
        ) : null}

        {loadState === 'ready' ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {trips.map((trip) => (
              <Card key={trip.id}>
                <div className="mb-4">
                  <div className="flex items-start justify-between mb-2">
                    <h3 className="text-lg font-semibold text-gray-900">{trip.destination}</h3>
                    <Badge variant={statusBadgeVariant(trip.status)}>{trip.statusLabel}</Badge>
                  </div>
                  <p className="text-sm text-gray-500">{trip.teamId}</p>
                </div>

                <div className="space-y-3 mb-6">
                  <div className="flex items-center gap-3 text-sm text-gray-600">
                    <Calendar className="w-4 h-4 text-blue-600" />
                    <span>
                      {trip.startDate} 至 {trip.endDate}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-sm text-gray-600">
                    <Users className="w-4 h-4 text-blue-600" />
                    <span>{trip.participants} 人参加</span>
                  </div>
                </div>

                <div className="flex gap-2 pt-4 border-t border-gray-200">
                  <Button variant="secondary" size="sm" className="flex-1" onClick={() => openEditModal(trip)}>
                    <Edit className="w-4 h-4 inline mr-1" />
                    修改
                  </Button>
                  <Button variant="secondary" size="sm" className="flex-1" onClick={() => void markCompleted(trip.id)}>
                    <Edit className="w-4 h-4 inline mr-1" />
                    完成
                  </Button>
                  <Button variant="danger" size="sm" className="flex-1" onClick={() => void deleteTrip(trip.id)}>
                    <Trash2 className="w-4 h-4 inline mr-1" />
                    删除
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        ) : null}

        <Modal
          isOpen={isModalOpen}
          onClose={closeTripModal}
          title={editingTripId ? '修改行程' : '新建行程'}
          footer={
            <div className="flex gap-2 justify-end">
              <Button variant="secondary" onClick={closeTripModal}>
                取消
              </Button>
              <Button onClick={() => void submitTrip()} loading={isSubmitting}>
                {editingTripId ? '保存' : '创建'}
              </Button>
            </div>
          }
        >
          <div className="space-y-4">
            <input
              type="text"
              placeholder="目的地"
              value={form.destination}
              onChange={(event) => setForm((prev) => ({ ...prev, destination: event.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            />
            <input
              type="date"
              value={form.startDate}
              onChange={(event) => setForm((prev) => ({ ...prev, startDate: event.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            />
            <input
              type="date"
              value={form.endDate}
              onChange={(event) => setForm((prev) => ({ ...prev, endDate: event.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            />
            <input
              type="text"
              placeholder="团队ID"
              value={form.teamId}
              onChange={(event) => setForm((prev) => ({ ...prev, teamId: event.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            />
          </div>
        </Modal>
      </div>
    </>
  )
}
