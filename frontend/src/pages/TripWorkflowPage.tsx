import { useEffect, useState } from 'react'
import { ArrowLeft } from 'lucide-react'
import { TripWorkflowPanel } from '../components/trip/TripWorkflowPanel'
import { FigmaTripService } from '../services/figmaTripService'

interface Props {
  tripId: string
  onBack: () => void
}

export function TripWorkflowPage({ tripId, onBack }: Props) {
  const [tripName, setTripName] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    (async () => {
      try {
        const trip = await FigmaTripService.getTripById(tripId)
        setTripName(trip?.name || tripId)
      } catch { setTripName(tripId) }
      finally { setLoading(false) }
    })()
  }, [tripId])

  return (
    <div className="p-6 max-w-4xl">
      <button onClick={onBack} className="mb-4 flex items-center gap-2 text-sm text-cyan-600 hover:text-cyan-700">
        <ArrowLeft className="h-4 w-4" /> 返回行程
      </button>

      <div className="mb-6">
        <h1 className="text-xl font-bold text-gray-900">📋 消息发送预览</h1>
        {!loading && <p className="text-sm text-gray-500 mt-1">行程：{tripName}</p>}
        <p className="text-xs text-gray-400 mt-2">
          展开每个步骤可查看将发送到企业微信群的完整消息内容，点击「发送」按钮执行推送。
        </p>
      </div>

      <TripWorkflowPanel tripId={tripId} />
    </div>
  )
}
