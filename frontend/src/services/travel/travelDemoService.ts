import { notificationsApi } from '../../services/api'

export const travelDemoService = {
  bootstrap(): void {
    // real backend mode: no local mock bootstrap
  },

  async getNotificationConfig(teamId: string) {
    const context = await notificationsApi.getTripConfigContextByTripId(teamId)
    return {
      teamId,
      projectName: context.projectConfig.projectName,
      manualTakeoverTarget: context.projectConfig.manualTakeoverTarget,
      smsSignName: context.projectConfig.smsSignName,
      smsProvider: context.projectConfig.smsProvider,
      weatherAlertEnabled: context.projectConfig.weatherEnabled,
      currentNotificationStatus: '执行中',
    }
  },

  async completeTask(taskId: string) {
    await notificationsApi.completeTask({ taskId, resultNote: '前端手动完成' })
  },

  async takeoverTask(taskId: string) {
    await notificationsApi.assignTakeover({
      taskId,
      assigneeUserId: 'frontend-manual',
      assigneeName: '值班管家',
      note: '前端人工接管',
    })
  },
}
