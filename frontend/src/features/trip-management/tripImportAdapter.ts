import { type Trip, type TripExecutionRow } from '../../types/api'

export interface ImportFlowSnapshot {
  completeness: number
  hasItinerary: boolean
  hasGuests: boolean
  todayTodo: number
  nextNode: string
  recognizedFields: Array<{ key: string; label: string; value: string }>
  pendingFields: Array<{ key: string; label: string; value: string }>
  missingFields: Array<{ key: string; label: string }>
  itineraryDigest: Array<{ date: string; transport: string; route: string; hotel: string; meal: string }>
  guestDigest: Array<{ name: string; phone: string; status: string }>
  pickupDigest: Array<{ type: '接' | '送'; date: string; location: string; shift: string; note: string }>
}

const recognizedLabelMap: Record<string, string> = {
  teamId: '团号',
  destination: '线路',
  startDate: '出团日期',
  participants: '人数',
  itinerary: '每日行程',
  hotel: '酒店',
  guests: '客人名单',
}

export function buildImportFlowSnapshot(trip: Trip, execution?: TripExecutionRow): ImportFlowSnapshot {
  const hasItinerary = trip.itinerary.length > 0
  const hasGuests = trip.guests.length > 0
  const hasGuestPhone = trip.guests.some((guest) => Boolean(guest.phone))
  const hasLeaderContact = Boolean(trip.contactPhone)

  const recognizedFields: ImportFlowSnapshot['recognizedFields'] = [
    { key: 'teamId', label: recognizedLabelMap.teamId, value: trip.teamId || '未识别' },
    { key: 'destination', label: recognizedLabelMap.destination, value: trip.destination || '未识别' },
    { key: 'startDate', label: recognizedLabelMap.startDate, value: trip.startDate || '未识别' },
    { key: 'participants', label: recognizedLabelMap.participants, value: String(trip.participants || 0) },
    {
      key: 'itinerary',
      label: recognizedLabelMap.itinerary,
      value: hasItinerary ? `${trip.itinerary.length} 天` : '未识别',
    },
    {
      key: 'guests',
      label: recognizedLabelMap.guests,
      value: hasGuests ? `${trip.guests.length} 人` : '未识别',
    },
  ]

  const pendingFields: ImportFlowSnapshot['pendingFields'] = [
    {
      key: 'transportMapping',
      label: '交通工具映射',
      value: hasItinerary ? '待确认（越野车/大巴/火车）' : '待导入行程',
    },
    {
      key: 'mealSymbols',
      label: '早午晚符号解析',
      value: hasItinerary ? '待确认（√/×）' : '待导入行程',
    },
  ]

  const missingFields: ImportFlowSnapshot['missingFields'] = []
  if (!hasGuestPhone) {
    missingFields.push({ key: 'guestPhone', label: '游客联系方式' })
  }
  if (!hasLeaderContact) {
    missingFields.push({ key: 'leaderPhone', label: '领队电话' })
  }

  const importReadyCount = recognizedFields.filter((field) => field.value !== '未识别').length
  const importAllCount = recognizedFields.length + pendingFields.length + missingFields.length
  const completeness = Math.round((importReadyCount / Math.max(importAllCount, 1)) * 100)

  return {
    completeness,
    hasItinerary,
    hasGuests,
    todayTodo: execution?.todoCount ?? 0,
    nextNode: execution?.nextNodeDueAt || execution?.dispatchStatus || '待生成通知节点',
    recognizedFields,
    pendingFields,
    missingFields,
    itineraryDigest: trip.itinerary.map((item) => ({
      date: item.date,
      transport: item.transport || '待补全',
      route: item.route || '待补全',
      hotel: item.hotel || '待补全',
      meal: '早:待确认 午:待确认 晚:待确认',
    })),
    guestDigest: trip.guests.map((guest) => ({
      name: guest.name || '未命名游客',
      phone: guest.phone || '待补录电话',
      status: guest.phone ? '可通知' : '待补全',
    })),
    pickupDigest: trip.itinerary.slice(0, 2).flatMap((item, index) => [
      {
        type: '接' as const,
        date: item.date,
        location: `${item.route.split('→')[0]?.trim() || '机场'}接站口`,
        shift: `航班待补录-${index + 1}`,
        note: '来源于导入行程，需人工确认班次',
      },
      {
        type: '送' as const,
        date: item.date,
        location: `${item.route.split('→').at(-1)?.trim() || '酒店'}送站点`,
        shift: `返程待补录-${index + 1}`,
        note: '来源于导入行程，需人工确认班次',
      },
    ]),
  }
}
