import type { RiskGroup } from '../groups/types'
import type { Task, TaskStatus } from '../tasks/types'

export interface MockDatabase {
  tasks: Task[]
  groups: RiskGroup[]
}

const now = Date.now()
const hour = 60 * 60 * 1000

const seedTasks: Task[] = [
  {
    id: 'task-101',
    title: '出发前3天航班确认与温馨提示',
    type: 'pre_departure_notice',
    status: 'todo',
    priority: 'P0',
    riskLevel: 'medium',
    dueAt: new Date(now + hour * 3).toISOString(),
    departureDate: new Date(now + hour * 36).toISOString(),
    assignee: '张三',
    groupId: 'grp-1',
    groupName: '乌鲁木齐-喀纳斯精品线',
    customerName: '王先生家庭团',
    destination: '新疆·喀纳斯',
    tags: ['行前', '航班', '提醒'],
    aiSuggestion: '建议叠加天气提醒，强调昼夜温差与保暖准备。',
    history: [
      { id: 'h-101-1', action: '系统创建任务', operator: '规则引擎', at: new Date(now - hour * 2).toISOString(), note: '触发：出发前3天' },
    ],
  },
  {
    id: 'task-102',
    title: '行程中导游中途关怀回访',
    type: 'in_trip_followup',
    status: 'in_progress',
    priority: 'P1',
    riskLevel: 'medium',
    dueAt: new Date(now + hour * 8).toISOString(),
    departureDate: new Date(now - hour * 24).toISOString(),
    assignee: '张三',
    groupId: 'grp-2',
    groupName: '伊犁草原深度游',
    customerName: '陈女士闺蜜团',
    destination: '新疆·伊犁',
    tags: ['行中', '回访'],
    aiSuggestion: '建议优先联系今日有高海拔行程客人，询问体感与补给。',
    history: [
      { id: 'h-102-1', action: '开始处理', operator: '张三', at: new Date(now - hour).toISOString(), note: '已联系领队收集反馈' },
    ],
  },
  {
    id: 'task-103',
    title: '下团欢迎与满意度回访',
    type: 'post_trip_feedback',
    status: 'todo',
    priority: 'P1',
    riskLevel: 'low',
    dueAt: new Date(now + hour * 12).toISOString(),
    departureDate: new Date(now - hour * 96).toISOString(),
    assignee: '张三',
    groupId: 'grp-3',
    groupName: '阿勒泰禾木轻奢团',
    customerName: '刘先生企业团',
    destination: '新疆·阿勒泰',
    tags: ['行后', '回访', 'NPS'],
    aiSuggestion: '建议按客诉标签分层回访，优先处理体验波动人群。',
    history: [],
  },
  {
    id: 'task-104',
    title: '出发前1天保险核查与建群检查',
    type: 'risk_control',
    status: 'overdue',
    priority: 'P0',
    riskLevel: 'high',
    dueAt: new Date(now - hour * 5).toISOString(),
    departureDate: new Date(now + hour * 10).toISOString(),
    assignee: '张三',
    groupId: 'grp-4',
    groupName: '喀什古城文化线',
    customerName: '马女士亲子团',
    destination: '新疆·喀什',
    tags: ['行前', '保险', '建群'],
    aiSuggestion: '该任务影响发团节点，建议立刻升级并补齐保单校验。',
    history: [],
  },
  {
    id: 'task-105',
    title: '航变通知二次确认',
    type: 'flight_change',
    status: 'pending_takeover',
    priority: 'P0',
    riskLevel: 'high',
    dueAt: new Date(now + hour * 2).toISOString(),
    departureDate: new Date(now + hour * 30).toISOString(),
    assignee: '',
    groupId: 'grp-1',
    groupName: '乌鲁木齐-喀纳斯精品线',
    customerName: '王先生家庭团',
    destination: '新疆·喀纳斯',
    tags: ['接管', '航变'],
    aiSuggestion: '建议30分钟内完成触达并确认改签方案。',
    history: [],
  },
  {
    id: 'task-106',
    title: '酒店满房应急替换确认',
    type: 'supplier_issue',
    status: 'pending_takeover',
    priority: 'P0',
    riskLevel: 'critical',
    dueAt: new Date(now + hour).toISOString(),
    departureDate: new Date(now + hour * 20).toISOString(),
    assignee: '',
    groupId: 'grp-5',
    groupName: '赛里木湖环线团',
    customerName: '赵先生摄影团',
    destination: '新疆·博州',
    tags: ['接管', '供应商'],
    aiSuggestion: '建议同时准备A/B酒店备选并发送补偿说明模板。',
    history: [],
  },
]

const seedGroups: RiskGroup[] = [
  {
    id: 'grp-1',
    groupName: '乌鲁木齐-喀纳斯精品线',
    routeName: '北疆环线 6 天 5 晚',
    departureDate: new Date(now + hour * 36).toISOString(),
    riskScore: 82,
    riskLevel: 'high',
    riskTags: ['航班延误', '天气降温'],
    owner: '李值守',
    pendingTaskCount: 3,
    blockedTaskCount: 0,
    summary: '航班延误概率提升，需提前完成提醒触达与备选接驳。',
    tasks: ['task-101', 'task-105'],
    collaborators: ['张三', '王客服'],
    timeline: [
      { id: 'e1', title: '航司发布延误预警', at: new Date(now - hour * 3).toISOString(), level: 'high' },
      { id: 'e2', title: '系统生成航变通知任务', at: new Date(now - hour * 2).toISOString(), level: 'medium' },
    ],
  },
  {
    id: 'grp-4',
    groupName: '喀什古城文化线',
    routeName: '南疆人文 5 天 4 晚',
    departureDate: new Date(now + hour * 10).toISOString(),
    riskScore: 92,
    riskLevel: 'critical',
    riskTags: ['保险未核查', '供应商波动'],
    owner: '周主管',
    pendingTaskCount: 2,
    blockedTaskCount: 1,
    summary: '出发前关键资料尚未闭环，存在发团阻断风险。',
    tasks: ['task-104'],
    collaborators: ['张三', '陈调度'],
    timeline: [
      { id: 'e3', title: '保险凭证缺失告警', at: new Date(now - hour * 6).toISOString(), level: 'critical' },
    ],
  },
  {
    id: 'grp-5',
    groupName: '赛里木湖环线团',
    routeName: '伊犁+赛湖 4 天 3 晚',
    departureDate: new Date(now + hour * 20).toISOString(),
    riskScore: 88,
    riskLevel: 'high',
    riskTags: ['酒店满房', '节假日拥堵'],
    owner: '待分配',
    pendingTaskCount: 2,
    blockedTaskCount: 1,
    summary: '酒店容量不足，需紧急替换与补偿策略。',
    tasks: ['task-106'],
    collaborators: ['资源采购组'],
    timeline: [
      { id: 'e4', title: '酒店方通知满房', at: new Date(now - hour * 4).toISOString(), level: 'high' },
    ],
  },
]

const db: MockDatabase = {
  tasks: seedTasks,
  groups: seedGroups,
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

export function getDb(): MockDatabase {
  return db
}

export function updateTaskStatus(taskId: string, status: TaskStatus, operator = '张三', note = '手动更新状态') {
  const task = db.tasks.find((item) => item.id === taskId)
  if (!task) return null
  task.status = status
  pushHistory(taskId, `状态变更为 ${status}`, operator, note)
  return task
}

export function takeoverTask(taskId: string, operator = '张三') {
  const task = db.tasks.find((item) => item.id === taskId)
  if (!task) return null
  task.status = 'todo'
  task.assignee = operator
  pushHistory(taskId, '任务接管', operator, '从待接管池接入个人待办')
  return task
}
