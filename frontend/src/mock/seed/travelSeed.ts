export type TravelTeamStatus = 'planned' | 'in_progress' | 'completed'

export interface TravelTeam {
  id: string
  name: string
  teamCode: string
  destination: string
  startDate: string
  endDate: string
  status: TravelTeamStatus
  dataCompleteness: number
  importedSchedule: boolean
  importedGuests: boolean
  guestCount: number
  todayTodoCount: number
  nextNotificationAt: string
}

export interface Guest {
  id: string
  teamId: string
  name: string
  phone: string
  idNo: string
  emergencyContact: string
  notes: string
}

export interface ItineraryDay {
  id: string
  teamId: string
  date: string
  dayIndex: number
  title: string
  city: string
  route: string
  transport: string
  hotel: string
  meals: string
  noticeMorning: string
  noticeNoon: string
  noticeEvening: string
}

export interface PickupPlan {
  id: string
  teamId: string
  date: string
  time: string
  location: string
  vehicle: string
  driver: string
  contactPhone: string
  notes: string
}

export type NotificationTaskStatus = 'pending' | 'completed' | 'takeover'
export type NotificationTaskType = 'morning' | 'noon' | 'evening' | 'reminder' | 'weather'

export interface NotificationTask {
  id: string
  teamId: string
  type: NotificationTaskType
  title: string
  content: string
  scheduledAt: string
  status: NotificationTaskStatus
  channel: 'sms' | 'wechat' | 'app'
  targetGroup: string
  relatedDayId: string
}

export interface TeamNotificationConfig {
  teamId: string
  projectName: string
  manualTakeoverTarget: string
  smsSignName: string
  smsProvider: string
  weatherAlertEnabled: boolean
  currentNotificationStatus: string
}

export interface TravelSeedStore {
  teams: TravelTeam[]
  guests: Guest[]
  itineraryDays: ItineraryDay[]
  pickupPlans: PickupPlan[]
  notificationTasks: NotificationTask[]
  notificationConfigs: TeamNotificationConfig[]
}

export const TRAVEL_SEED_DATA: TravelSeedStore = {
  teams: [
    {
      id: 'team-kashgar-20260426',
      name: '新疆-喀什',
      teamCode: 'KASHI-0426',
      destination: '喀什',
      startDate: '2026-04-26',
      endDate: '2026-04-29',
      status: 'in_progress',
      dataCompleteness: 96,
      importedSchedule: true,
      importedGuests: true,
      guestCount: 3,
      todayTodoCount: 3,
      nextNotificationAt: '2026-04-25T20:00:00+08:00',
    },
    {
      id: 'team-yili-20260424',
      name: '新疆-伊犁',
      teamCode: 'YILI-0424',
      destination: '伊犁',
      startDate: '2026-04-24',
      endDate: '2026-04-28',
      status: 'planned',
      dataCompleteness: 92,
      importedSchedule: true,
      importedGuests: true,
      guestCount: 3,
      todayTodoCount: 2,
      nextNotificationAt: '2026-04-24T11:30:00+08:00',
    },
    {
      id: 'team-kanas-20260502',
      name: '新疆-喀纳斯',
      teamCode: 'KANASI-0502',
      destination: '喀纳斯',
      startDate: '2026-05-02',
      endDate: '2026-05-05',
      status: 'planned',
      dataCompleteness: 90,
      importedSchedule: true,
      importedGuests: true,
      guestCount: 3,
      todayTodoCount: 1,
      nextNotificationAt: '2026-05-01T20:00:00+08:00',
    },
  ],
  guests: [
    { id: 'g-k1', teamId: 'team-kashgar-20260426', name: '王蕾', phone: '13800001111', idNo: '650102199001011111', emergencyContact: '王建军 13900001110', notes: '轻微花粉过敏' },
    { id: 'g-k2', teamId: 'team-kashgar-20260426', name: '陈浩', phone: '13800001112', idNo: '650103198812122222', emergencyContact: '陈敏 13900001120', notes: '早餐偏清淡' },
    { id: 'g-k3', teamId: 'team-kashgar-20260426', name: '李晨', phone: '13800001113', idNo: '650104199503033333', emergencyContact: '李辉 13900001130', notes: '需提醒补水' },
    { id: 'g-y1', teamId: 'team-yili-20260424', name: '赵雅', phone: '13800002221', idNo: '650201199104044444', emergencyContact: '赵峰 13900002220', notes: '晕车' },
    { id: 'g-y2', teamId: 'team-yili-20260424', name: '孙婷', phone: '13800002222', idNo: '650202199205055555', emergencyContact: '孙雷 13900002230', notes: '乳糖不耐受' },
    { id: 'g-y3', teamId: 'team-yili-20260424', name: '周伟', phone: '13800002223', idNo: '650203199306066666', emergencyContact: '周晴 13900002240', notes: '带儿童' },
    { id: 'g-n1', teamId: 'team-kanas-20260502', name: '马宁', phone: '13800003331', idNo: '650301199407077777', emergencyContact: '马玉 13900003330', notes: '摄影器材较多' },
    { id: 'g-n2', teamId: 'team-kanas-20260502', name: '郭静', phone: '13800003332', idNo: '650302199508088888', emergencyContact: '郭峰 13900003340', notes: '高海拔提醒' },
    { id: 'g-n3', teamId: 'team-kanas-20260502', name: '何兵', phone: '13800003333', idNo: '650303199609099999', emergencyContact: '何悦 13900003350', notes: '无' },
  ],
  itineraryDays: [
    { id: 'd-k-1', teamId: 'team-kashgar-20260426', date: '2026-04-26', dayIndex: 1, title: '抵达喀什', city: '喀什', route: '喀什机场-古城办理入住', transport: '航班+大巴', hotel: '喀什古城酒店', meals: '晚', noticeMorning: '明早08:00酒店大堂集合，带好证件。', noticeNoon: '午餐后13:30出发参观古城东门。', noticeEvening: '今晚20:00行前说明会，请准时参加。' },
    { id: 'd-k-2', teamId: 'team-kashgar-20260426', date: '2026-04-27', dayIndex: 2, title: '白沙湖-卡拉库里湖', city: '喀什', route: '喀什-白沙湖-卡拉库里湖', transport: '旅游巴士', hotel: '塔县迎宾酒店', meals: '早中晚', noticeMorning: '早晨7:30出发，气温低请备外套。', noticeNoon: '中午高原路段，请注意补水防晒。', noticeEvening: '晚间自由活动勿单独远行。' },
    { id: 'd-k-3', teamId: 'team-kashgar-20260426', date: '2026-04-28', dayIndex: 3, title: '石头城-返程', city: '塔县', route: '石头城-喀什', transport: '旅游巴士', hotel: '喀什古城酒店', meals: '早中', noticeMorning: '08:30退房后出发，随身带好贵重物品。', noticeNoon: '午间路餐，请按导游分组领取。', noticeEvening: '20:00发送返程提醒与次日送机安排。' },

    { id: 'd-y-1', teamId: 'team-yili-20260424', date: '2026-04-24', dayIndex: 1, title: '乌鲁木齐集合', city: '乌鲁木齐', route: '机场接机-入住', transport: '商务车', hotel: '乌市中心酒店', meals: '晚', noticeMorning: '到达后请在2号门集合。', noticeNoon: '12:00统一办理入住与午休。', noticeEvening: '20:30召开破冰会说明行程。' },
    { id: 'd-y-2', teamId: 'team-yili-20260424', date: '2026-04-25', dayIndex: 2, title: '赛里木湖', city: '博州', route: '乌市-赛里木湖', transport: '旅游巴士', hotel: '赛湖营地酒店', meals: '早中晚', noticeMorning: '早上7:00出发，检查保暖衣物。', noticeNoon: '中午湖边风大，注意保暖。', noticeEvening: '晚上星空拍摄，自愿参加。' },
    { id: 'd-y-3', teamId: 'team-yili-20260424', date: '2026-04-26', dayIndex: 3, title: '伊宁河谷', city: '伊宁', route: '赛湖-果子沟-伊宁', transport: '旅游巴士', hotel: '伊宁河谷酒店', meals: '早中', noticeMorning: '08:00集合出发，清点随身物品。', noticeNoon: '午餐后参观薰衣草庄园。', noticeEvening: '20:00发布次日那拉提草原通知。' },

    { id: 'd-n-1', teamId: 'team-kanas-20260502', date: '2026-05-02', dayIndex: 1, title: '布尔津集合', city: '布尔津', route: '接机-五彩滩', transport: '商务车', hotel: '布尔津悦景酒店', meals: '晚', noticeMorning: '抵达后联系接机司机。', noticeNoon: '午后办理入住，16:00出发五彩滩。', noticeEvening: '20:30讲解喀纳斯入园须知。' },
    { id: 'd-n-2', teamId: 'team-kanas-20260502', date: '2026-05-03', dayIndex: 2, title: '喀纳斯湖', city: '喀纳斯', route: '布尔津-喀纳斯', transport: '旅游巴士', hotel: '喀纳斯湖景酒店', meals: '早中晚', noticeMorning: '7:00出发，证件随身携带。', noticeNoon: '中午景区内简餐，注意时间。', noticeEvening: '晚间围炉活动，22:00结束。' },
    { id: 'd-n-3', teamId: 'team-kanas-20260502', date: '2026-05-04', dayIndex: 3, title: '禾木村', city: '禾木', route: '喀纳斯-禾木', transport: '区间车', hotel: '禾木山庄', meals: '早中', noticeMorning: '08:00换乘区间车前往禾木。', noticeNoon: '12:30午餐后自由采风。', noticeEvening: '20:00发布次日返程提醒。' },
  ],
  pickupPlans: [
    { id: 'p-k-1', teamId: 'team-kashgar-20260426', date: '2026-04-26', time: '10:30', location: '喀什机场T2到达层', vehicle: '新A12345', driver: '艾力', contactPhone: '13600001111', notes: '举牌“喀什团”' },
    { id: 'p-y-1', teamId: 'team-yili-20260424', date: '2026-04-24', time: '09:30', location: '乌鲁木齐机场T3', vehicle: '新B22345', driver: '阿迪力', contactPhone: '13600002222', notes: '分两批接机' },
    { id: 'p-n-1', teamId: 'team-kanas-20260502', date: '2026-05-02', time: '11:00', location: '阿勒泰机场', vehicle: '新C32345', driver: '木拉提', contactPhone: '13600003333', notes: '器材优先上车' },
  ],
  notificationTasks: [
    { id: 't-k-1', teamId: 'team-kashgar-20260426', type: 'morning', title: 'D1 早间集合提醒', content: '明早08:00酒店大堂集合，带好证件。', scheduledAt: '2026-04-25T20:00:00+08:00', status: 'pending', channel: 'wechat', targetGroup: '全体游客', relatedDayId: 'd-k-1' },
    { id: 't-k-2', teamId: 'team-kashgar-20260426', type: 'noon', title: 'D2 午间高原提示', content: '中午高原路段，请注意补水防晒。', scheduledAt: '2026-04-27T11:30:00+08:00', status: 'pending', channel: 'sms', targetGroup: '全体游客', relatedDayId: 'd-k-2' },
    { id: 't-k-3', teamId: 'team-kashgar-20260426', type: 'evening', title: 'D3 晚间返程通知', content: '20:00发送返程提醒与次日送机安排。', scheduledAt: '2026-04-28T20:00:00+08:00', status: 'takeover', channel: 'wechat', targetGroup: '全体游客', relatedDayId: 'd-k-3' },

    { id: 't-y-1', teamId: 'team-yili-20260424', type: 'morning', title: 'D1 到达集合提醒', content: '到达后请在2号门集合。', scheduledAt: '2026-04-23T20:00:00+08:00', status: 'completed', channel: 'sms', targetGroup: '全体游客', relatedDayId: 'd-y-1' },
    { id: 't-y-2', teamId: 'team-yili-20260424', type: 'evening', title: 'D2 晚间活动提示', content: '晚上星空拍摄，自愿参加。', scheduledAt: '2026-04-25T20:00:00+08:00', status: 'pending', channel: 'wechat', targetGroup: '全体游客', relatedDayId: 'd-y-2' },
    { id: 't-y-3', teamId: 'team-yili-20260424', type: 'reminder', title: 'D3 物资检查提醒', content: '出发前检查身份证与保暖衣物。', scheduledAt: '2026-04-26T07:30:00+08:00', status: 'pending', channel: 'app', targetGroup: '导游与领队', relatedDayId: 'd-y-3' },

    { id: 't-n-1', teamId: 'team-kanas-20260502', type: 'morning', title: 'D1 接机提示', content: '抵达后联系接机司机。', scheduledAt: '2026-05-01T20:00:00+08:00', status: 'pending', channel: 'sms', targetGroup: '全体游客', relatedDayId: 'd-n-1' },
    { id: 't-n-2', teamId: 'team-kanas-20260502', type: 'noon', title: 'D2 景区午间提示', content: '中午景区内简餐，注意时间。', scheduledAt: '2026-05-03T11:30:00+08:00', status: 'pending', channel: 'wechat', targetGroup: '全体游客', relatedDayId: 'd-n-2' },
    { id: 't-n-3', teamId: 'team-kanas-20260502', type: 'evening', title: 'D3 晚间返程提醒', content: '20:00发布次日返程提醒。', scheduledAt: '2026-05-04T20:00:00+08:00', status: 'pending', channel: 'wechat', targetGroup: '全体游客', relatedDayId: 'd-n-3' },
  ],
  notificationConfigs: [
    { teamId: 'team-kashgar-20260426', projectName: '喀什深度体验团', manualTakeoverTarget: '值班管家A组', smsSignName: 'TravelHub', smsProvider: 'aliyun', weatherAlertEnabled: true, currentNotificationStatus: '执行中' },
    { teamId: 'team-yili-20260424', projectName: '伊犁花海行摄团', manualTakeoverTarget: '值班管家B组', smsSignName: 'TravelHub', smsProvider: 'tencent', weatherAlertEnabled: true, currentNotificationStatus: '待执行' },
    { teamId: 'team-kanas-20260502', projectName: '喀纳斯湖景漫游团', manualTakeoverTarget: '值班管家C组', smsSignName: 'TravelHub', smsProvider: 'aliyun', weatherAlertEnabled: false, currentNotificationStatus: '待执行' },
  ],
}
