import { notificationsApi, tripsApi } from '../services/api'
import type { NotificationTask } from '../mock/seed/travelSeed'
import { travelRepository } from './travelRepository'

function toTaskStatus(status: string): NotificationTask['status'] {
  if (status === 'done') return 'completed'
  if (status === 'pending_takeover') return 'takeover'
  return 'pending'
}

export async function generateNotificationTasksFromItinerary(teamId: string): Promise<NotificationTask[]> {
  const trip = await travelRepository.resolveTripByTeamId(teamId)
  if (!trip) return []
  const detail = await tripsApi.get(trip.tripId)

  const generated: NotificationTask[] = []
  for (const [index, day] of detail.itinerary.entries()) {
    await notificationsApi.generateDaily({
      groupId: detail.teamId || detail.id,
      date: day.date,
      weather: '晴',
      coreWork: '每日固定时段提醒',
    }).catch(() => null)

    generated.push(
      {
        id: `gen-${detail.id}-d${index + 1}-morning`,
        teamId: detail.id,
        type: 'morning',
        title: `D${index + 1} 早间通知`,
        content: `早安提醒：${day.route}`,
        scheduledAt: new Date(`${day.date}T08:00:00+08:00`).toISOString(),
        status: 'pending',
        channel: 'sms',
        targetGroup: '全体游客',
        relatedDayId: `${detail.id}-day-${index + 1}`,
      },
      {
        id: `gen-${detail.id}-d${index + 1}-noon`,
        teamId: detail.id,
        type: 'noon',
        title: `D${index + 1} 中午通知`,
        content: `中午提醒：${day.transport}`,
        scheduledAt: new Date(`${day.date}T11:30:00+08:00`).toISOString(),
        status: 'pending',
        channel: 'sms',
        targetGroup: '全体游客',
        relatedDayId: `${detail.id}-day-${index + 1}`,
      },
      {
        id: `gen-${detail.id}-d${index + 1}-evening`,
        teamId: detail.id,
        type: 'evening',
        title: `D${index + 1} 晚间通知`,
        content: `晚间提醒：入住${day.hotel}`,
        scheduledAt: new Date(`${day.date}T20:00:00+08:00`).toISOString(),
        status: 'pending',
        channel: 'wechat',
        targetGroup: '全体游客',
        relatedDayId: `${detail.id}-day-${index + 1}`,
      },
    )
  }
  return generated
}

export const notificationRepository = {
  async getTasksByTeamId(teamId: string): Promise<NotificationTask[]> {
    const trip = await travelRepository.resolveTripByTeamId(teamId)
    if (!trip) return []
    const detail = await tripsApi.getExecutionDetail(trip.tripId).catch(() => null)
    if (!detail) return []

    return detail.tasks.map((task) => ({
      id: task.taskId,
      teamId: detail.tripId,
      type: task.nodeKey.includes('morning') ? 'morning' : task.nodeKey.includes('noon') ? 'noon' : 'evening',
      title: task.title,
      content: task.nodeKey,
      scheduledAt: task.dueAt,
      status: toTaskStatus(task.status),
      channel: 'sms',
      targetGroup: '全体游客',
      relatedDayId: task.nodeKey,
    }))
  },

  async generateTasksForTeam(teamId: string): Promise<NotificationTask[]> {
    return generateNotificationTasksFromItinerary(teamId)
  },
}
