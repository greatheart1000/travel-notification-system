import type { RiskGroup } from '../groups/types'
import type { Task, TaskRiskLevel, TaskStatus } from '../tasks/types'

export interface MockDatabase {
  tasks: Task[]
  groups: RiskGroup[]
}

const STORAGE_KEY = 'travelhub:workbench-db:v2'
const hour = 60 * 60 * 1000

function isBrowser(): boolean {
  return typeof window !== 'undefined'
}

function nowIso(offsetHours = 0): string {
  return new Date(Date.now() + offsetHours * hour).toISOString()
}

function buildSeedTasks(): Task[] {
  return [
    {
      id: 'task-101',
      title: 'T-3 航班确认与集合通知',
      type: 'pre_trip_t3_flight_check',
      status: 'todo',
      priority: 'P0',
      riskLevel: 'medium',
      teamId: 'team-001',
      teamName: '乌鲁木齐-喀纳斯精品线',
      teamCode: 'XJ-KNS-0428',
      destination: '新疆·喀纳斯',
      departureDate: nowIso(32),
      dueAt: nowIso(3),
      assigneeId: 'u-zhangsan',
      assigneeName: '张三',
      source: '规则引擎：行前 T-3 节点',
      relatedDayId: 'day-0',
      relatedNotificationTaskId: 'ntf-101',
      recommendedAction: '去确认航班',
      aiSuggestion: '优先确认去程航班号与值机状态，并同步早晚温差提醒。',
      linkedNotificationNode: '行前提醒（T-3）',
      currentTripDay: 0,
      travelerCount: 24,
      tags: ['行前', '航班'],
      history: [
        { id: 'h-101-1', action: '系统创建任务', operator: '规则引擎', at: nowIso(-8), note: '触发条件：出发前 3 天' },
      ],
    },
    {
      id: 'task-102',
      title: '今日晨间出行提醒执行',
      type: 'daily_morning',
      status: 'overdue',
      priority: 'P0',
      riskLevel: 'high',
      teamId: 'team-002',
      teamName: '伊犁草原深度游',
      teamCode: 'XJ-YL-0426',
      destination: '新疆·伊犁',
      departureDate: nowIso(-24),
      dueAt: nowIso(-2),
      assigneeId: 'u-zhangsan',
      assigneeName: '张三',
      source: '通知编排：行中晨间触达',
      relatedDayId: 'day-2',
      relatedNotificationTaskId: 'ntf-201',
      recommendedAction: '去通知执行',
      aiSuggestion: '请先发送路况与集合时间提醒，再确认老年游客回执。',
      linkedNotificationNode: '行中晨间提醒',
      currentTripDay: 2,
      travelerCount: 18,
      overdueReason: '08:00 前需触达全员，当前仍有 7 位游客未收到晨间通知。',
      remedySuggestion: '先推送短信兜底，再电话补触达领队。',
      tags: ['行中', '晨间'],
      history: [
        { id: 'h-102-1', action: '触达失败重试', operator: '系统', at: nowIso(-3), note: '微信失败，已进入人工处理池' },
      ],
    },
    {
      id: 'task-103',
      title: '午间风险播报执行',
      type: 'daily_noon',
      status: 'todo',
      priority: 'P1',
      riskLevel: 'high',
      teamId: 'team-003',
      teamName: '阿勒泰禾木轻奢团',
      teamCode: 'XJ-ALT-0425',
      destination: '新疆·阿勒泰',
      departureDate: nowIso(-48),
      dueAt: nowIso(5),
      assigneeId: 'u-zhangsan',
      assigneeName: '张三',
      source: '天气风险引擎',
      relatedDayId: 'day-3',
      relatedNotificationTaskId: 'ntf-301',
      recommendedAction: '去通知执行',
      aiSuggestion: '建议在午间通知补充降温与补水提醒。',
      linkedNotificationNode: '行中午间播报',
      currentTripDay: 3,
      travelerCount: 16,
      tags: ['行中', '午间', '天气'],
      history: [],
    },
    {
      id: 'task-104',
      title: '保险与建群核验',
      type: 'insurance_check',
      status: 'blocked',
      priority: 'P0',
      riskLevel: 'high',
      teamId: 'team-004',
      teamName: '喀什古城文化线',
      teamCode: 'XJ-KS-0427',
      destination: '新疆·喀什',
      departureDate: nowIso(9),
      dueAt: nowIso(4),
      assigneeId: 'u-zhangsan',
      assigneeName: '张三',
      source: '风控核验清单',
      relatedDayId: 'day-0',
      relatedNotificationTaskId: 'ntf-401',
      recommendedAction: '去核验保险',
      aiSuggestion: '供应商返回保单较慢，建议并行联系渠道经理确认。',
      linkedNotificationNode: '行前资料核验',
      currentTripDay: 0,
      travelerCount: 29,
      tags: ['行前', '保险', '阻塞'],
      history: [],
    },
    {
      id: 'task-105',
      title: '航变通知人工接管',
      type: 'pending_takeover',
      status: 'pending_takeover',
      priority: 'P0',
      riskLevel: 'high',
      teamId: 'team-001',
      teamName: '乌鲁木齐-喀纳斯精品线',
      teamCode: 'XJ-KNS-0428',
      destination: '新疆·喀纳斯',
      departureDate: nowIso(32),
      dueAt: nowIso(1),
      assigneeId: '',
      assigneeName: '待接管',
      source: '航变监控告警',
      relatedDayId: 'day-0',
      relatedNotificationTaskId: 'ntf-105',
      recommendedAction: '立即接管',
      aiSuggestion: '建议 30 分钟内完成触达并同步改签说明。',
      linkedNotificationNode: '航变告警通知',
      currentTripDay: 0,
      travelerCount: 24,
      tags: ['接管', '航变'],
      history: [],
    },
    {
      id: 'task-106',
      title: '行后回访问卷补录',
      type: 'post_trip_farewell',
      status: 'todo',
      priority: 'P2',
      riskLevel: 'low',
      teamId: 'team-005',
      teamName: '赛里木湖环线团',
      teamCode: 'XJ-SLMH-0422',
      destination: '新疆·博州',
      departureDate: nowIso(-120),
      dueAt: nowIso(20),
      assigneeId: 'u-zhangsan',
      assigneeName: '张三',
      source: '行后回访流程',
      relatedDayId: 'day+1',
      relatedNotificationTaskId: 'ntf-501',
      recommendedAction: '去回访记录',
      aiSuggestion: '优先补录差评旅客的后续关怀结果。',
      linkedNotificationNode: '行后回访问卷',
      currentTripDay: 0,
      travelerCount: 20,
      tags: ['行后', '回访'],
      history: [],
    },
    {
      id: 'task-107',
      title: '晚间安全播报执行',
      type: 'daily_evening',
      status: 'todo',
      priority: 'P1',
      riskLevel: 'medium',
      teamId: 'team-006',
      teamName: '那拉提草原营地团',
      teamCode: 'XJ-NLT-0429',
      destination: '新疆·那拉提',
      departureDate: nowIso(14),
      dueAt: nowIso(22),
      assigneeId: 'u-lisi',
      assigneeName: '李四',
      source: '日常通知编排',
      relatedDayId: 'day-1',
      relatedNotificationTaskId: 'ntf-601',
      recommendedAction: '去通知执行',
      aiSuggestion: '建议提醒游客夜间低温与集合点变更。',
      linkedNotificationNode: '行中晚间播报',
      currentTripDay: 1,
      travelerCount: 14,
      tags: ['行中', '晚间'],
      history: [],
    },
  ]
}

function buildSeedGroups(): RiskGroup[] {
  return [
    {
      id: 'team-001',
      groupName: '乌鲁木齐-喀纳斯精品线',
      routeName: '北疆环线 6 天 5 晚',
      departureDate: nowIso(32),
      riskScore: 84,
      riskLevel: 'high',
      riskTags: ['航变风险', '天气降温'],
      owner: '张三',
      pendingTaskCount: 2,
      blockedTaskCount: 0,
      summary: '航班存在波动，需优先处理航变通知与兜底触达。',
      tasks: ['task-101', 'task-105'],
      collaborators: ['张三', '王客服'],
      timeline: [{ id: 'e1', title: '航司发布延误预警', at: nowIso(-4), level: 'high' }],
    },
    {
      id: 'team-002',
      groupName: '伊犁草原深度游',
      routeName: '伊犁草原 5 天 4 晚',
      departureDate: nowIso(-24),
      riskScore: 90,
      riskLevel: 'high',
      riskTags: ['晨间通知未触达'],
      owner: '张三',
      pendingTaskCount: 1,
      blockedTaskCount: 0,
      summary: '晨间通知逾期，需补触达并确认回执。',
      tasks: ['task-102'],
      collaborators: ['张三', '通知调度'],
      timeline: [{ id: 'e2', title: '晨间通知失败', at: nowIso(-2), level: 'critical' }],
    },
  ]
}

function buildSeedDb(): MockDatabase {
  return {
    tasks: buildSeedTasks(),
    groups: buildSeedGroups(),
  }
}

function loadDbFromStorage(): MockDatabase {
  if (!isBrowser()) {
    return buildSeedDb()
  }

  const raw = window.localStorage.getItem(STORAGE_KEY)
  if (!raw) {
    const seed = buildSeedDb()
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(seed))
    return seed
  }

  try {
    return JSON.parse(raw) as MockDatabase
  } catch {
    const seed = buildSeedDb()
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(seed))
    return seed
  }
}

const db: MockDatabase = loadDbFromStorage()

function persistDb() {
  if (!isBrowser()) return
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(db))
}

function pushHistory(taskId: string, action: string, operator: string, note: string) {
  const task = db.tasks.find((item) => item.id === taskId)
  if (!task) return
  task.history.unshift({
    id: `h-${taskId}-${Date.now()}`,
    action,
    operator,
    note,
    at: new Date().toISOString(),
  })
}

function syncGroupRiskFromTask(task: Task, riskLevel: TaskRiskLevel) {
  const group = db.groups.find((item) => item.id === task.teamId)
  if (!group) return
  if (riskLevel === 'high' || riskLevel === 'critical') {
    group.riskLevel = riskLevel === 'critical' ? 'critical' : 'high'
    group.riskScore = Math.max(group.riskScore, 85)
    if (!group.riskTags.includes('人工标记高风险')) {
      group.riskTags = [...group.riskTags, '人工标记高风险']
    }
  }
}

export function getDb(): MockDatabase {
  return db
}

export function updateTaskStatus(taskId: string, status: TaskStatus, operator = '张三', note = '手动更新状态') {
  const task = db.tasks.find((item) => item.id === taskId)
  if (!task) return null
  task.status = status
  pushHistory(taskId, `状态变更为 ${status}`, operator, note)
  persistDb()
  return task
}

export function completeTask(taskId: string, operator = '张三') {
  return updateTaskStatus(taskId, 'done', operator, '任务处理完成')
}

export function deferTask(taskId: string, operator = '张三') {
  const task = db.tasks.find((item) => item.id === taskId)
  if (!task) return null
  task.dueAt = new Date(new Date(task.dueAt).getTime() + 24 * hour).toISOString()
  if (task.status === 'overdue') {
    task.status = 'todo'
  }
  pushHistory(taskId, '延期处理', operator, '截止时间顺延 24 小时')
  persistDb()
  return task
}

export function takeoverTask(taskId: string, assigneeId = 'u-zhangsan', assigneeName = '张三') {
  const task = db.tasks.find((item) => item.id === taskId)
  if (!task) return null
  task.status = 'todo'
  task.assigneeId = assigneeId
  task.assigneeName = assigneeName
  pushHistory(taskId, '任务接管', assigneeName, '从待接管池接入个人待办')
  persistDb()
  return task
}

export function markTaskRisk(taskId: string, operator = '张三') {
  const task = db.tasks.find((item) => item.id === taskId)
  if (!task) return null
  task.riskLevel = 'high'
  syncGroupRiskFromTask(task, 'high')
  pushHistory(taskId, '标记高风险', operator, '任务提升为高风险，已同步团风险池')
  persistDb()
  return task
}
