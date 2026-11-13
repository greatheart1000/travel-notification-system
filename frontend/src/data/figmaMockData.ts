export type MakeTripStatus = '招募中' | '进行中' | '已结束'

export interface MakeTrip {
  id: string
  teamId: string
  name: string
  code: string
  startDate: string
  endDate: string
  participants: number
  leader: string
  status: MakeTripStatus
  statusColor: string
  assignedUserIds: string[]
  assignedUsers?: { id: string; username: string; displayName?: string; role: string }[]
  sendMode?: 'auto' | 'approval'
}

export interface MakeWeatherInfo {
  city: string
  temp: number
  weather: string
  wind: string
  warning: string | null
  warning_title?: string
  source?: string
}

export interface MakeItineraryDay {
  date: string
  type: string
  activity: string
  breakfast: string
  lunch: string
  dinner: string
  hotel: string
}

export interface MakeTourist {
  name: string
  age: number
  gender: string
  phone: string
  idCard: string
  notes: string
  wechat?: string
}

export type MakeNotificationStatus = '已启用' | '未启用' | '已发送' | '待发送'

export interface MakeNotificationRule {
  id: string
  phase: string
  icon: string
  time: string
  title: string
  content: string
  tag: string
  tagColor: string
  status: MakeNotificationStatus
  coreWork?: string
  lastSent?: string
  recipients?: number
  enabled?: boolean
  ruleId?: string
  templateId?: string
}

export interface MakeTripDetail extends MakeTrip {
  itinerary: MakeItineraryDay[]
  tourists: MakeTourist[]
  notifications: MakeNotificationRule[]
}

export const makeStatusColorMap: Record<MakeTripStatus, string> = {
  招募中: 'bg-accent-50 text-accent-800',
  进行中: 'bg-success-50 text-success-700',
  已结束: 'bg-paper-100 text-paper-600',
}

export const mockTrips: MakeTrip[] = [
  { id: 'trip-001', teamId: 'YL-2026-1120-BJ', name: '北疆雪境 7 日｜乌鲁木齐·喀纳斯·禾木', code: 'YL-2026-1120-BJ', startDate: '2026-11-20', endDate: '2026-11-26', participants: 12, leader: '赵玥', status: '招募中', statusColor: makeStatusColorMap.招募中, assignedUserIds: [] },
  { id: 'trip-002', teamId: 'YL-2026-1125-YL', name: '伊犁冬牧 6 日｜赛里木湖·那拉提', code: 'YL-2026-1125-YL', startDate: '2026-11-25', endDate: '2026-11-30', participants: 8, leader: '吴昊然', status: '招募中', statusColor: makeStatusColorMap.招募中, assignedUserIds: [] },
  { id: 'trip-003', teamId: 'YL-2026-1130-NJ', name: '南疆人文 8 日｜喀什古城·帕米尔', code: 'YL-2026-1130-NJ', startDate: '2026-11-30', endDate: '2026-12-07', participants: 10, leader: '吾麦尔', status: '招募中', statusColor: makeStatusColorMap.招募中, assignedUserIds: [] },
  { id: 'trip-004', teamId: 'YL-2026-1205-TLF', name: '吐鲁番暖冬 4 日｜火焰山·库木塔格', code: 'YL-2026-1205-TLF', startDate: '2026-12-05', endDate: '2026-12-08', participants: 6, leader: '林溪', status: '招募中', statusColor: makeStatusColorMap.招募中, assignedUserIds: [] },
  { id: 'trip-005', teamId: 'YL-2026-1210-ALT', name: '阿勒泰滑雪 5 日｜将军山·禾木', code: 'YL-2026-1210-ALT', startDate: '2026-12-10', endDate: '2026-12-14', participants: 9, leader: '田野', status: '招募中', statusColor: makeStatusColorMap.招募中, assignedUserIds: [] },
  { id: 'trip-006', teamId: 'YL-2026-1215-TC', name: '塔城边境 4 日｜巴克图·小白杨', code: 'YL-2026-1215-TC', startDate: '2026-12-15', endDate: '2026-12-18', participants: 7, leader: '胡静', status: '招募中', statusColor: makeStatusColorMap.招募中, assignedUserIds: [] },
  { id: 'trip-007', teamId: 'YL-2026-1220-KEL', name: '库尔勒胡杨 5 日｜轮台·罗布人村寨', code: 'YL-2026-1220-KEL', startDate: '2026-12-20', endDate: '2026-12-24', participants: 11, leader: '赵玥', status: '招募中', statusColor: makeStatusColorMap.招募中, assignedUserIds: [] },
  { id: 'trip-008', teamId: 'YL-2026-1225-HT', name: '和田人文 6 日｜约特干·达玛沟', code: 'YL-2026-1225-HT', startDate: '2026-12-25', endDate: '2026-12-30', participants: 8, leader: '吴昊然', status: '招募中', statusColor: makeStatusColorMap.招募中, assignedUserIds: [] },
  { id: 'trip-009', teamId: 'YL-2026-1005-KNS', name: '喀纳斯秋色 7 日', code: 'YL-2026-1005-KNS', startDate: '2026-10-05', endDate: '2026-10-11', participants: 14, leader: '古丽娜扎', status: '已结束', statusColor: makeStatusColorMap.已结束, assignedUserIds: [] },
  { id: 'trip-010', teamId: 'YL-2026-0410-YL', name: '伊犁杏花 6 日｜吐尔根·那拉提', code: 'YL-2026-0410-YL', startDate: '2026-04-10', endDate: '2026-04-15', participants: 18, leader: '林溪', status: '已结束', statusColor: makeStatusColorMap.已结束, assignedUserIds: [] },
  { id: 'trip-011', teamId: 'YL-2026-0705-DK', name: '独库公路 8 日｜乔尔玛·巴音布鲁克', code: 'YL-2026-0705-DK', startDate: '2026-07-05', endDate: '2026-07-12', participants: 12, leader: '田野', status: '已结束', statusColor: makeStatusColorMap.已结束, assignedUserIds: [] },
  { id: 'trip-012', teamId: 'YL-2026-0815-TLF', name: '吐鲁番葡萄节 4 日', code: 'YL-2026-0815-TLF', startDate: '2026-08-15', endDate: '2026-08-18', participants: 20, leader: '胡静', status: '已结束', statusColor: makeStatusColorMap.已结束, assignedUserIds: [] },
]

export const mockWeather: MakeWeatherInfo[] = [
  { city: '乌鲁木齐', temp: -8, weather: '多云', wind: '3级', warning: null },
  { city: '喀什', temp: 5, weather: '晴', wind: '2级', warning: null },
  { city: '伊犁', temp: -12, weather: '暴雪', wind: '7级', warning: '暴雪预警' },
  { city: '阿勒泰', temp: -18, weather: '大雪', wind: '6级', warning: '寒潮预警' },
  { city: '吐鲁番', temp: 2, weather: '晴', wind: '3级', warning: null },
  { city: '塔城', temp: -5, weather: '小雪', wind: '4级', warning: null },
  { city: '库尔勒', temp: 8, weather: '多云', wind: '2级', warning: null },
  { city: '和田', temp: 10, weather: '沙尘', wind: '5级', warning: '沙尘预警' },
]

const altayItinerary: MakeItineraryDay[] = [
  { date: '11-20', type: '接机', activity: '乌鲁木齐地窝堡机场接机，入住酒店', breakfast: '×', lunch: '×', dinner: '√', hotel: '乌鲁木齐环球国际酒店' },
  { date: '11-21', type: '商务车', activity: '乌鲁木齐—布尔津，S21 沙漠公路、五彩滩日落', breakfast: '√', lunch: '√', dinner: '×', hotel: '布尔津旅游宾馆' },
  { date: '11-22', type: '商务车', activity: '布尔津—禾木，禾木村徒步、日落观景台', breakfast: '√', lunch: '√', dinner: '√', hotel: '禾木山庄' },
  { date: '11-23', type: '商务车', activity: '禾木—喀纳斯，三湾徒步、喀纳斯湖', breakfast: '√', lunch: '√', dinner: '×', hotel: '喀纳斯阅湖酒店' },
  { date: '11-24', type: '商务车', activity: '喀纳斯—布尔津，白哈巴村、边境公路', breakfast: '√', lunch: '√', dinner: '√', hotel: '布尔津旅游宾馆' },
  { date: '11-25', type: '商务车', activity: '布尔津—乌鲁木齐，国际大巴扎', breakfast: '√', lunch: '√', dinner: '×', hotel: '乌鲁木齐环球国际酒店' },
  { date: '11-26', type: '送机', activity: '乌鲁木齐送机', breakfast: '√', lunch: '×', dinner: '×', hotel: '—' },
]

const fallbackItinerary = (trip: MakeTrip, index: number): MakeItineraryDay[] => [
  { date: trip.startDate.slice(5), type: index % 2 === 0 ? '大巴' : '飞机', activity: `${trip.name} D1 抵达集合与欢迎晚宴`, breakfast: '×', lunch: '×', dinner: '√', hotel: '精选当地酒店' },
  { date: trip.startDate.slice(5, 8) + String(Number(trip.startDate.slice(8)) + 1).padStart(2, '0'), type: '大巴', activity: `${trip.name} 核心景区深度游览`, breakfast: '√', lunch: '√', dinner: '√', hotel: '精选当地酒店' },
  { date: trip.startDate.slice(5, 8) + String(Number(trip.startDate.slice(8)) + 2).padStart(2, '0'), type: '大巴', activity: `${trip.name} 文化体验与自由活动`, breakfast: '√', lunch: '√', dinner: '×', hotel: '精选当地酒店' },
]

const defaultTourists: MakeTourist[] = [
  { name: '张慧', age: 34, gender: '女', phone: '139****2418', wechat: 'zhanghui_88', idCard: '65010219891106****', notes: '' },
  { name: '王磊', age: 41, gender: '男', phone: '138****3651', wechat: 'wanglei_xj', idCard: '65010319840712****', notes: '' },
  { name: '李佳', age: 29, gender: '女', phone: '136****7632', wechat: 'lijia_0912', idCard: '65010419960518****', notes: '素食' },
  { name: '陈思远', age: 37, gender: '男', phone: '189****0614', wechat: 'chensiyuan', idCard: '65010519880124****', notes: '' },
  { name: '刘洋', age: 45, gender: '男', phone: '135****1903', wechat: 'liuyang_trip', idCard: '65010619791030****', notes: '需无烟房' },
  { name: '赵敏', age: 32, gender: '女', phone: '150****4178', wechat: 'zhaomin_33', idCard: '65010719931208****', notes: '带 7 岁儿童' },
  { name: '周建国', age: 58, gender: '男', phone: '139****1846', wechat: 'zhoujianguo', idCard: '65010819670215****', notes: '高血压，避免高强度徒步' },
  { name: '孙悦', age: 27, gender: '女', phone: '186****0827', wechat: 'sunyue_27', idCard: '65010919980221****', notes: '' },
  { name: '马丽', age: 39, gender: '女', phone: '137****1256', wechat: 'mali_xj', idCard: '65011019860509****', notes: '不吃香菜' },
  { name: '吴桐', age: 31, gender: '男', phone: '159****3702', wechat: 'wutong_31', idCard: '65012119940617****', notes: '' },
  { name: '郑凯', age: 36, gender: '男', phone: '181****0317', wechat: 'zhengkai', idCard: '65012219890928****', notes: '' },
  { name: '何雨', age: 24, gender: '女', phone: '136****2840', wechat: 'heyu_24', idCard: '65012320010312****', notes: '' },
]

const excelImportedTourists: MakeTourist[] = [
  { name: '高翔', age: 43, gender: '男', phone: '138****2045', wechat: 'gaoxiang', idCard: '65010419821205****', notes: 'Excel 导入' },
  { name: '许静', age: 35, gender: '女', phone: '186****7429', wechat: 'xujing_35', idCard: '65010519900719****', notes: 'Excel 导入' },
]

const baseNotifications: MakeNotificationRule[] = [
  {
    id: 'pre-3',
    phase: '行程前',
    icon: '',
    time: '出发前3天 09:00',
    title: '行前准备提醒',
    content: '【行前提醒】还有 3 天出发。请准备身份证件、常用药品和保暖衣物，集合信息将在出发前 1 天发送。',
    tag: '自动触发',
    tagColor: 'bg-paper-100 text-paper-600',
    status: '已启用',
    lastSent: '-',
    recipients: 12,
    enabled: true,
  },
  {
    id: 'pre-1',
    phase: '行程前',
    icon: '',
    time: '出发前1天 18:00',
    title: '集合与导游信息',
    content: '【行前确认】明天出发。集合时间 07:30，地点为机场 T3 航站楼 4 号门。领队：{{leader_name}}，电话：138****1234。',
    tag: '自动触发',
    tagColor: 'bg-paper-100 text-paper-600',
    status: '已启用',
    lastSent: '-',
    recipients: 12,
    enabled: true,
  },
  {
    id: 'daily-morning',
    phase: '行程中',
    icon: '',
    time: '每日 07:00',
    title: '当日行程 + 天气',
    content: '【今日行程】{{today_activity}}。天气：{{weather}}，{{temperature}}℃。注意事项：{{safety_tips}}。',
    tag: '每日自动',
    tagColor: 'bg-paper-100 text-paper-600',
    status: '已启用',
    lastSent: '-',
    recipients: 12,
    enabled: true,
  },
  {
    id: 'daily-noon',
    phase: '行程中',
    icon: '',
    time: '每日 12:00',
    title: '餐饮与安全提醒',
    content: '【午间提醒】下午天气{{afternoon_weather}}，请注意防晒或保暖。午餐安排在{{restaurant}}，如有不适请联系领队。',
    tag: '每日自动',
    tagColor: 'bg-paper-100 text-paper-600',
    status: '已启用',
    lastSent: '-',
    recipients: 12,
    enabled: true,
  },
  {
    id: 'daily-night',
    phase: '行程中',
    icon: '',
    time: '每日 20:00',
    title: '次日行程预告',
    content: '【明日安排】{{tomorrow_activity}}。出发时间：{{departure_time}}，请提前准备。',
    tag: '每日自动',
    tagColor: 'bg-paper-100 text-paper-600',
    status: '已启用',
    lastSent: '-',
    recipients: 12,
    enabled: true,
  },
  {
    id: 'horse-safety',
    phase: '特殊场景',
    icon: '',
    time: '系统检测触发',
    title: '骑马活动安全提醒',
    content: '今日有骑马活动。请听从教练指导，穿运动鞋，不要站在马后方；拍照时与马保持距离。如有不适请提前告知领队。',
    tag: '关键词：骑马、马术',
    tagColor: 'bg-paper-100 text-paper-600',
    status: '已启用',
    lastSent: '-',
    recipients: 12,
    enabled: true,
  },
]

function touristsForTrip(trip: MakeTrip, _index: number): MakeTourist[] {
  if (trip.teamId === 'YL-2026-1120-BJ') return defaultTourists
  return defaultTourists.slice(0, Math.min(trip.participants, 8)).map((tourist, touristIndex) => ({
    ...tourist,
    name: `${trip.name.slice(0, 2)}游客${touristIndex + 1}`,
    notes: touristIndex === 1 ? '素食' : '',
  }))
}

function notificationsForTrip(trip: MakeTrip): MakeNotificationRule[] {
  return baseNotifications.map((notification) => ({
    ...notification,
    content: `【${trip.name}】${notification.content}`,
    coreWork: notification.title,
    recipients: trip.participants,
  }))
}

export const mockTripDetails: MakeTripDetail[] = mockTrips.map((trip, index) => ({
  ...trip,
  itinerary: trip.teamId === 'YL-2026-1120-BJ' ? altayItinerary : fallbackItinerary(trip, index),
  tourists: touristsForTrip(trip, index),
  notifications: notificationsForTrip(trip),
}))

export const mockImportedTourists = excelImportedTourists
