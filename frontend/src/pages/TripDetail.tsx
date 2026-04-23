import { useEffect, useState } from 'react'
import { ArrowLeft, Bell, FileText, MapPin, Phone, Plus, Save, Users } from 'lucide-react'
import { Header } from '../components/Header'
import { Button } from '../components/Button'
import { Card } from '../components/Card'
import { Modal } from '../components/Modal'
import { GuestTable } from '../components/trip/GuestTable'
import { PageState } from '../components/PageState'
import { TripOverviewCards } from '../components/trip/TripOverviewCards'
import { TripScheduleTimeline } from '../components/trip/TripScheduleTimeline'
import { TripDayEditor } from '../components/trip/TripDayEditor'
import { notificationsApi, tripsApi, getErrorMessage } from '../services/api'
import { type Guest, type NotificationTemplate, type Trip } from '../types/api'
import { loadTripDetail, saveTripDays } from '../features/trip-management/tripDetailApi'
import {
  buildDayDraft,
  mergeTripDetail,
  removeDay,
  type TripDayPlan,
  type TripDetailViewModel,
  upsertDay,
} from '../features/trip-management/tripDetailMapper'

interface TripDetailProps {
  tripId: string | null
  onBack: () => void
  onOpenTripNotifications?: (tripId: string) => void
}

export function TripDetail({ tripId, onBack, onOpenTripNotifications }: TripDetailProps) {
  const statusOptions: Array<{ value: Trip['status']; label: string }> = [
    { value: 'planned', label: '计划中' },
    { value: 'in_progress', label: '进行中' },
    { value: 'completed', label: '已完成' },
    { value: 'cancelled', label: '已取消' },
  ]
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [savingDays, setSavingDays] = useState(false)
  const [error, setError] = useState('')
  const [saveMessage, setSaveMessage] = useState('')

  const [trip, setTrip] = useState<Trip | null>(null)
  const [form, setForm] = useState<Trip | null>(null)
  const [detail, setDetail] = useState<TripDetailViewModel | null>(null)
  const [days, setDays] = useState<TripDayPlan[]>([])
  const [nextHint, setNextHint] = useState('')

  const [sendModalOpen, setSendModalOpen] = useState(false)
  const [targetGuest, setTargetGuest] = useState<Guest | null>(null)
  const [templates, setTemplates] = useState<NotificationTemplate[]>([])
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>('')
  const [sendingMsg, setSendingMsg] = useState(false)
  const [sendResultMsg, setSendResultMsg] = useState('')

  useEffect(() => {
    if (!tripId) {
      const blankTrip: Trip = {
        id: '',
        destination: '',
        teamId: '',
        startDate: '',
        endDate: '',
        participants: 0,
        status: 'planned',
        statusLabel: '计划中',
        itinerary: [],
        guests: [],
      }
      setTrip(blankTrip)
      setForm(blankTrip)
      setDetail(null)
      setDays([])
      setLoading(false)
      return
    }

    let active = true
    const run = async () => {
      setLoading(true)
      setError('')
      try {
        const payload = await loadTripDetail(tripId)
        if (!active) return
        const vm = mergeTripDetail(payload.trip, payload.schedule)
        setTrip(payload.trip)
        setForm(payload.trip)
        setDetail(vm)
        setDays(vm.days)
        setNextHint(payload.schedule.notificationSummary.nextHint)
      } catch (err) {
        if (!active) return
        setError(getErrorMessage(err))
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }
    void run()
    return () => {
      active = false
    }
  }, [tripId])

  const handleOpenSendModal = async (guest: Guest) => {
    setTargetGuest(guest)
    setSendModalOpen(true)
    setSendResultMsg('')
    if (templates.length === 0) {
      try {
        const list = await notificationsApi.listTemplates()
        setTemplates(list)
        if (list.length > 0) {
          setSelectedTemplateId(list[0].id)
        }
      } catch (err) {
        setSendResultMsg(`模板加载失败: ${getErrorMessage(err)}`)
      }
    }
  }

  const executeSend = async () => {
    if (!targetGuest || !selectedTemplateId) return
    setSendingMsg(true)
    setSendResultMsg('')
    try {
      await notificationsApi.send({
        templateId: selectedTemplateId,
        channel: 'sms',
        customerName: targetGuest.name || '游客',
        customerPhone: targetGuest.phone,
        trip: tripId || undefined,
      })
      setSendResultMsg('短信发送成功！')
      setTimeout(() => {
        setSendModalOpen(false)
        setSendResultMsg('')
      }, 2000)
    } catch (err) {
      setSendResultMsg(`发送失败: ${getErrorMessage(err)}`)
    } finally {
      setSendingMsg(false)
    }
  }

  const handleSaveBase = async () => {
    if (!tripId || !form) return
    setSaving(true)
    setSaveMessage('')
    try {
      const updated = await tripsApi.update(tripId, form)
      setTrip(updated)
      setForm(updated)
      setSaveMessage('基础信息已保存')
      setTimeout(() => setSaveMessage(''), 2500)
    } catch (err) {
      setSaveMessage(`保存失败: ${getErrorMessage(err)}`)
    } finally {
      setSaving(false)
    }
  }

  const handleSaveDays = async () => {
    if (!tripId || !form) return
    setSavingDays(true)
    setSaveMessage('')
    try {
      const updated = await saveTripDays(tripId, days)
      const payload = await loadTripDetail(tripId)
      const vm = mergeTripDetail(updated, payload.schedule)
      setTrip(updated)
      setForm(updated)
      setDetail(vm)
      setDays(vm.days)
      setNextHint(payload.schedule.notificationSummary.nextHint)
      setSaveMessage('每日安排已保存')
      setTimeout(() => setSaveMessage(''), 2500)
    } catch (err) {
      setSaveMessage(`保存失败: ${getErrorMessage(err)}`)
    } finally {
      setSavingDays(false)
    }
  }

  if (loading) {
    return (
      <>
        <div className="print:hidden">
          <Header />
        </div>
        <div className="p-8">
          <PageState kind="loading" title="正在加载行程详情..." />
        </div>
      </>
    )
  }

  if (error) {
    return (
      <>
        <div className="print:hidden">
          <Header />
        </div>
        <div className="p-8">
          <PageState kind="error" title="加载失败" description={error} onRetry={() => window.location.reload()} />
        </div>
      </>
    )
  }

  if (!form) return null

  return (
    <>
      <div className="print:hidden">
        <Header />
      </div>
      <div className="min-h-screen bg-gray-50 pb-16">
        <div className="sticky top-0 z-20 border-b bg-white shadow-sm">
          <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
            <div className="flex items-center gap-4">
              <button onClick={onBack} className="rounded-full p-2 text-gray-500 transition hover:bg-gray-100">
                <ArrowLeft size={20} />
              </button>
              <div>
                <h1 className="text-xl font-bold text-gray-900">
                  {tripId ? form.destination : '规划新行程'}
                </h1>
                <p className="mt-0.5 font-mono text-xs uppercase text-gray-500">{form.teamId || 'Draft ID'}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {tripId ? (
                <Button
                  variant="secondary"
                  onClick={() => {
                    if (onOpenTripNotifications) {
                      onOpenTripNotifications(tripId)
                      return
                    }
                    window.history.pushState({}, '', '/notifications')
                    window.dispatchEvent(new PopStateEvent('popstate'))
                  }}
                >
                  <Bell className="mr-2 h-4 w-4" />
                  通知设置
                </Button>
              ) : null}
              {saveMessage ? <span className="text-sm text-blue-700">{saveMessage}</span> : null}
              {tripId ? (
                <Button
                  variant="secondary"
                  onClick={() => void tripsApi.exportPdf(tripId, form.destination || '行程')}
                >
                  <FileText className="mr-2 h-4 w-4" />
                  导出 PDF
                </Button>
              ) : null}
              <Button onClick={handleSaveBase} loading={saving}>
                <Save className="mr-2 h-4 w-4" />
                保存基础信息
              </Button>
            </div>
          </div>
        </div>

        <div className="mx-auto max-w-7xl space-y-6 px-6 py-8">
          {tripId && detail ? (
            <>
              <TripOverviewCards detail={detail} />
              <TripScheduleTimeline days={days} nextHint={nextHint} />
            </>
          ) : null}

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <div className="space-y-6 lg:col-span-2">
              <Card title="每日行程编排">
                <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <p className="text-sm text-slate-500">
                    在此维护每日路线、交通和酒店信息，保存后将用于通知编排与数据分析。
                  </p>
                  <Button
                    variant="secondary"
                    onClick={() => setDays((current) => [...current, buildDayDraft(current)])}
                  >
                    <Plus className="mr-2 h-4 w-4" />
                    新增行程日
                  </Button>
                </div>
                <div className="space-y-4">
                  {days.map((day) => (
                    <TripDayEditor
                      key={day.id}
                      day={day}
                      onChange={(next) => setDays((current) => upsertDay(current, next))}
                      onDelete={(dayId) => setDays((current) => removeDay(current, dayId))}
                    />
                  ))}
                  {days.length === 0 ? (
                    <div className="rounded-xl border border-dashed border-blue-200 bg-blue-50/50 p-4 text-sm text-slate-600">
                      暂无行程日，请点击右上角“新增行程日”开始编辑。
                    </div>
                  ) : null}
                </div>
                <div className="mt-4">
                  <Button onClick={handleSaveDays} loading={savingDays}>
                    <Save className="mr-2 h-4 w-4" />
                    保存每日安排
                  </Button>
                </div>
              </Card>

              <Card title="游客与联系">
                <GuestTable
                  guests={form.guests}
                  onChange={(newGuests) => setForm({ ...form, guests: newGuests })}
                  onSend={handleOpenSendModal}
                />
              </Card>
            </div>

            <div className="space-y-6 lg:sticky lg:top-24 lg:self-start">
              <Card title="团信息">
                <div className="space-y-4">
                  <label className="block text-xs font-bold uppercase text-gray-400">
                    团名称
                    <input
                      type="text"
                      value={form.destination}
                      onChange={(e) => setForm({ ...form, destination: e.target.value })}
                      className="mt-1 w-full rounded-xl border border-gray-200 px-3 py-2"
                    />
                  </label>
                  <label className="block text-xs font-bold uppercase text-gray-400">
                    团号
                    <input
                      type="text"
                      value={form.teamId}
                      onChange={(e) => setForm({ ...form, teamId: e.target.value })}
                      className="mt-1 w-full rounded-xl border border-gray-200 px-3 py-2 font-mono"
                    />
                  </label>
                  <label className="block text-xs font-bold uppercase text-gray-400">
                    状态
                    <select
                      value={form.status}
                      onChange={(e) => setForm({ ...form, status: e.target.value as Trip['status'] })}
                      className="mt-1 w-full rounded-xl border border-gray-200 px-3 py-2"
                    >
                      {statusOptions.map((option) => (
                        <option key={option.value} value={option.value}>{option.label}</option>
                      ))}
                    </select>
                  </label>
                  <div className="grid grid-cols-2 gap-3">
                    <label className="block text-xs font-bold uppercase text-gray-400">
                      出发日期
                      <input
                        type="date"
                        value={form.startDate}
                        onChange={(e) => setForm({ ...form, startDate: e.target.value })}
                        className="mt-1 w-full rounded-xl border border-gray-200 px-3 py-2"
                      />
                    </label>
                    <label className="block text-xs font-bold uppercase text-gray-400">
                      结束日期
                      <input
                        type="date"
                        value={form.endDate}
                        onChange={(e) => setForm({ ...form, endDate: e.target.value })}
                        className="mt-1 w-full rounded-xl border border-gray-200 px-3 py-2"
                      />
                    </label>
                  </div>
                </div>
              </Card>
              <Card className="bg-blue-600 text-white">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-blue-100">游客人数</p>
                    <p className="text-3xl font-bold">{form.guests.length || form.participants} 人</p>
                    <p className="mt-1 text-xs text-blue-100">
                      行程天数：{days.length} 天 · {form.startDate || '未设置'} ~ {form.endDate || '未设置'}
                    </p>
                  </div>
                  <Users className="h-10 w-10 text-blue-300" />
                </div>
              </Card>
              <Card>
                <div className="space-y-3 text-sm text-slate-600">
                  <p className="flex items-center gap-2 text-xs font-bold uppercase text-gray-400">
                    <MapPin className="h-4 w-4 text-blue-600" />
                    领队信息
                  </p>
                  <input
                    type="text"
                    value={form.leaderName || ''}
                    onChange={(e) => setForm({ ...form, leaderName: e.target.value })}
                    placeholder="领队姓名"
                    className="w-full rounded-xl border border-gray-200 px-3 py-2"
                  />
                  <p className="flex items-center gap-2 text-xs font-bold uppercase text-gray-400">
                    <Phone className="h-4 w-4 text-blue-600" />
                    联系方式
                  </p>
                  <input
                    type="text"
                    value={form.contactPhone || ''}
                    onChange={(e) => setForm({ ...form, contactPhone: e.target.value })}
                    placeholder="领队手机号"
                    className="w-full rounded-xl border border-gray-200 px-3 py-2"
                  />
                  <Button size="sm" onClick={handleSaveBase} loading={saving}>
                    保存领队信息
                  </Button>
                </div>
              </Card>
            </div>
          </div>
        </div>
      </div>

      <Modal
        isOpen={sendModalOpen}
        onClose={() => setSendModalOpen(false)}
        title={`发送短信给 ${targetGuest?.name || '未知客人'}`}
        footer={
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setSendModalOpen(false)}>
              取消
            </Button>
            <Button onClick={executeSend} loading={sendingMsg} disabled={!selectedTemplateId || !targetGuest?.phone}>
              确认发送
            </Button>
          </div>
        }
      >
        <div className="space-y-4">
          {sendResultMsg ? (
            <div className={`rounded-lg p-3 text-sm ${sendResultMsg.includes('失败') ? 'bg-red-50 text-red-600' : 'bg-green-50 text-green-600'}`}>
              {sendResultMsg}
            </div>
          ) : null}
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-gray-700">接收号码</label>
            <input
              type="text"
              readOnly
              value={targetGuest?.phone || '无'}
              className="w-full cursor-not-allowed rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-gray-500"
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-gray-700">选择通知模板 (短信渠道)</label>
            <select
              value={selectedTemplateId}
              onChange={(e) => setSelectedTemplateId(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2"
            >
              <option value="">请选择...</option>
              {templates.filter((t) => t.channel === 'sms').map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </Modal>
    </>
  )
}
