import { useEffect, useState } from 'react'
import { ArrowLeft } from 'lucide-react'
import { PageShell } from '../components/PageShell'
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
    ;(async () => {
      try {
        const trip = await FigmaTripService.getTripById(tripId)
        setTripName(trip?.name || tripId)
      } catch {
        setTripName(tripId)
      } finally {
        setLoading(false)
      }
    })()
  }, [tripId])

  return (
    <PageShell
      title="消息发送预览"
      description={loading ? '加载行程信息' : `行程：${tripName}`}
      actions={
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-1.5 text-sm text-paper-500 transition-colors hover:text-paper-900"
        >
          <ArrowLeft className="h-4 w-4" /> 返回行程
        </button>
      }
    >
      <p className="mb-4 text-sm text-paper-600">
        展开每个步骤可查看将发送到企业微信群的完整消息内容，点击「执行」按钮推送。
      </p>
      <TripWorkflowPanel tripId={tripId} />
    </PageShell>
  )
}
