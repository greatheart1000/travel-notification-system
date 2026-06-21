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
}

export interface MakeWeatherInfo {
  city: string
  temp: number
  weather: string
  wind: string
  warning: string | null
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
}

export interface MakeTripDetail extends MakeTrip {
  itinerary: MakeItineraryDay[]
  tourists: MakeTourist[]
  notifications: MakeNotificationRule[]
}

export const makeStatusColorMap: Record<MakeTripStatus, string> = {
  招募中: 'bg-blue-100 text-blue-700',
  进行中: 'bg-green-100 text-green-700',
  已结束: 'bg-gray-100 text-gray-600',
}

export const mockTrips: MakeTrip[] = [
  { id: 'trip-001', teamId: 'TEAM-DEMO-POST', name: '阿勒泰本地冬营团', code: 'TEAM-DEMO-POST', startDate: '2026-03-10', endDate: '2026-03-16', participants: 12, leader: '王美丽', status: '已结束', statusColor: makeStatusColorMap.已结束 },
  { id: 'trip-002', teamId: 'TEAM-ETHIO-001', name: '埃塞俄比亚古文明探索团', code: 'TEAM-ETHIO-001', startDate: '2026-04-15', endDate: '2026-04-25', participants: 8, leader: '李强', status: '已结束', statusColor: makeStatusColorMap.已结束 },
  { id: 'trip-003', teamId: 'TEAM-MY-FOOD', name: '马来半岛美食文化之旅', code: 'TEAM-MY-FOOD', startDate: '2026-05-01', endDate: '2026-05-08', participants: 15, leader: '张敏', status: '已结束', statusColor: makeStatusColorMap.已结束 },
  { id: 'trip-004', teamId: 'TEAM-JP-SPRING', name: '北海道春季赏樱团', code: 'TEAM-JP-SPRING', startDate: '2026-04-20', endDate: '2026-04-27', participants: 20, leader: '赵刚', status: '已结束', statusColor: makeStatusColorMap.已结束 },
  { id: 'trip-005', teamId: 'TEAM-TH-BEACH', name: '泰国海岛度假之旅', code: 'TEAM-TH-BEACH', startDate: '2026-05-10', endDate: '2026-05-17', participants: 18, leader: '陈晨', status: '已结束', statusColor: makeStatusColorMap.已结束 },
  { id: 'trip-006', teamId: 'TEAM-EU-CLASSIC', name: '欧洲经典五国游', code: 'TEAM-EU-CLASSIC', startDate: '2026-06-01', endDate: '2026-06-15', participants: 25, leader: '刘洋', status: '进行中', statusColor: makeStatusColorMap.进行中 },
  { id: 'trip-007', teamId: 'TEAM-NZ-NATURE', name: '新西兰南岛自然探索', code: 'TEAM-NZ-NATURE', startDate: '2026-05-20', endDate: '2026-05-30', participants: 10, leader: '周琳', status: '已结束', statusColor: makeStatusColorMap.已结束 },
  { id: 'trip-008', teamId: 'TEAM-TIBET-HOLY', name: '西藏朝圣之旅', code: 'TEAM-TIBET-HOLY', startDate: '2026-07-05', endDate: '2026-07-12', participants: 16, leader: '孙伟', status: '招募中', statusColor: makeStatusColorMap.招募中 },
  { id: 'trip-009', teamId: 'TEAM-DUBAI-LUXURY', name: '迪拜奢华购物团', code: 'TEAM-DUBAI-LUXURY', startDate: '2026-06-10', endDate: '2026-06-16', participants: 14, leader: '吴静', status: '进行中', statusColor: makeStatusColorMap.进行中 },
  { id: 'trip-010', teamId: 'TEAM-YUNNAN-PHOTO', name: '云南摄影采风团', code: 'TEAM-YUNNAN-PHOTO', startDate: '2026-03-25', endDate: '2026-04-03', participants: 9, leader: '郑涛', status: '已结束', statusColor: makeStatusColorMap.已结束 },
  { id: 'trip-011', teamId: 'TEAM-USA-WEST', name: '美国西海岸自驾游', code: 'TEAM-USA-WEST', startDate: '2026-07-15', endDate: '2026-07-28', participants: 12, leader: '许明', status: '招募中', statusColor: makeStatusColorMap.招募中 },
  { id: 'trip-012', teamId: 'TEAM-MALDIVES', name: '马尔代夫蜜月之旅', code: 'TEAM-MALDIVES', startDate: '2026-08-01', endDate: '2026-08-08', participants: 6, leader: '何静', status: '招募中', statusColor: makeStatusColorMap.招募中 },
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
  { date: '03-10', type: '越野车', activity: '客人自行抵达喀什接机（4月20日=酒店接）', breakfast: '×', lunch: '×', dinner: '×', hotel: '喀什古城喜来登酒店' },
  { date: '03-11', type: '越野车', activity: '喀什 → 木垒大山 → 白沙湖', breakfast: '×', lunch: '×', dinner: '×', hotel: '白沙湖度假山庄' },
  { date: '03-12', type: '越野车', activity: '白沙湖 → 塔合曼湿地=卡拉库里湖=托格拉塔村', breakfast: '√', lunch: '×', dinner: '×', hotel: '道在·托格拉草原营地' },
  { date: '03-13', type: '越野车', activity: '塔什库尔干=红其拉甫 → 慕士塔格峰 → 班迪尔蓝湖 → 塔县', breakfast: '√', lunch: '×', dinner: '×', hotel: '塔县美巴酒店' },
  { date: '03-14', type: '越野车', activity: '塔县=慕士塔格峰深度游X沙漠观星', breakfast: '√', lunch: '×', dinner: '×', hotel: '喀什方圆国际酒店' },
  { date: '03-15', type: '越野车', activity: '喀什 → 香妃园=大巴扎 → 阿克苏', breakfast: '√', lunch: '×', dinner: '×', hotel: '阿克拉玛依酒店' },
  { date: '03-16', type: '越野车', activity: '阿克苏 → 乌市送机', breakfast: '√', lunch: '×', dinner: '×', hotel: '伊宁美家酒店' },
]

const fallbackItinerary = (trip: MakeTrip, index: number): MakeItineraryDay[] => [
  { date: trip.startDate.slice(5), type: index % 2 === 0 ? '大巴' : '飞机', activity: `${trip.name} D1 抵达集合与欢迎晚宴`, breakfast: '×', lunch: '×', dinner: '√', hotel: '精选当地酒店' },
  { date: trip.startDate.slice(5, 8) + String(Number(trip.startDate.slice(8)) + 1).padStart(2, '0'), type: '大巴', activity: `${trip.name} 核心景区深度游览`, breakfast: '√', lunch: '√', dinner: '√', hotel: '精选当地酒店' },
  { date: trip.startDate.slice(5, 8) + String(Number(trip.startDate.slice(8)) + 2).padStart(2, '0'), type: '大巴', activity: `${trip.name} 文化体验与自由活动`, breakfast: '√', lunch: '√', dinner: '×', hotel: '精选当地酒店' },
]

const defaultTourists: MakeTourist[] = [
  { name: '张三', age: 28, gender: '男', phone: '138****1234', wechat: 'zhangsan_wx', idCard: '11010119960101****', notes: '' },
  { name: '李四', age: 32, gender: '女', phone: '139****5678', wechat: 'lisi_2024', idCard: '31011019920315****', notes: '素食' },
  { name: '王五', age: 45, gender: '男', phone: '136****9012', wechat: 'wangwu666', idCard: '44010119790520****', notes: '' },
  { name: '赵六', age: 26, gender: '女', phone: '137****3456', wechat: 'zhao_liu', idCard: '51010119980825****', notes: '' },
  { name: '钱七', age: 38, gender: '男', phone: '135****7890', wechat: 'qianqi_77', idCard: '61010119860410****', notes: '需轮椅' },
  { name: '孙八', age: 29, gender: '女', phone: '188****2345', wechat: 'sunba_travel', idCard: '21010119950705****', notes: '' },
  { name: '周九', age: 55, gender: '男', phone: '186****6789', wechat: 'zhoujiu_1969', idCard: '12010119690912****', notes: '高血压' },
  { name: '吴十', age: 24, gender: '女', phone: '183****0123', wechat: 'wushi_00', idCard: '13010120000228****', notes: '' },
  { name: '郑十一', age: 41, gender: '男', phone: '189****4567', wechat: 'zheng11_wx', idCard: '14010119831118****', notes: '' },
  { name: '王十二', age: 33, gender: '女', phone: '185****8901', wechat: 'wang_12', idCard: '15010119911203****', notes: '对海鲜过敏' },
  { name: '陈十三', age: 37, gender: '男', phone: '182****2468', wechat: 'chen13_travel', idCard: '22010119871015****', notes: '' },
  { name: '刘十四', age: 30, gender: '女', phone: '181****1357', wechat: 'liu14_wx', idCard: '23010119941122****', notes: '' },
]

const excelImportedTourists: MakeTourist[] = [
  { name: '导入游客A', age: 34, gender: '女', phone: '180****0001', wechat: 'import_a', idCard: '33010119900101****', notes: 'Excel导入' },
  { name: '导入游客B', age: 42, gender: '男', phone: '180****0002', wechat: 'import_b', idCard: '33010119820202****', notes: 'Excel导入' },
]

const baseNotifications: MakeNotificationRule[] = [
  {
    id: 'pre-3',
    phase: '行程前',
    icon: '📋',
    time: '出发前3天 09:00',
    title: '行前准备提醒',
    content: '亲爱的游客，您好！还有3天即将出发。请准备：①身份证/护照 ②行李箱 ③个人药品 ④防晒/保暖用品。集合信息将提前1天发送。祝您旅途愉快！',
    tag: '自动触发',
    tagColor: 'bg-blue-500',
    status: '已启用',
    lastSent: '-',
    recipients: 12,
    enabled: true,
  },
  {
    id: 'pre-1',
    phase: '行程前',
    icon: '🚌',
    time: '出发前1天 18:00',
    title: '集合与导游信息',
    content: '明日出发！集合时间：07:30，集合地点：机场T3航站楼4号门。导游：{{leader_name}}，电话：138****1234。请提前到达，祝旅途愉快！',
    tag: '自动触发',
    tagColor: 'bg-blue-500',
    status: '已启用',
    lastSent: '-',
    recipients: 12,
    enabled: true,
  },
  {
    id: 'daily-morning',
    phase: '行程中',
    icon: '☀️',
    time: '每日 07:00',
    title: '当日行程 + 天气',
    content: '早安！今日行程：{{today_activity}}。天气：{{weather}}，{{temperature}}℃。注意事项：{{safety_tips}}。祝您玩得开心！',
    tag: '每日自动',
    tagColor: 'bg-green-500',
    status: '已启用',
    lastSent: '-',
    recipients: 12,
    enabled: true,
  },
  {
    id: 'daily-noon',
    phase: '行程中',
    icon: '🌤️',
    time: '每日 12:00',
    title: '餐饮与安全提醒',
    content: '午间提醒：下午天气{{afternoon_weather}}，请注意防晒/保暖。午餐已安排在{{restaurant}}。如有不适请及时联系导游。',
    tag: '每日自动',
    tagColor: 'bg-yellow-500',
    status: '已启用',
    lastSent: '-',
    recipients: 12,
    enabled: true,
  },
  {
    id: 'daily-night',
    phase: '行程中',
    icon: '🌙',
    time: '每日 20:00',
    title: '次日行程预告',
    content: '晚安！今日辛苦了。明日行程：{{tomorrow_activity}}。出发时间：{{departure_time}}，请提前准备。晚安！',
    tag: '每日自动',
    tagColor: 'bg-indigo-500',
    status: '已启用',
    lastSent: '-',
    recipients: 12,
    enabled: true,
  },
  {
    id: 'horse-safety',
    phase: '特殊场景',
    icon: '🐎',
    time: '智能检测触发',
    title: '骑马活动安全提醒',
    content: '今日有骑马活动。请注意：①听从教练指导 ②穿运动鞋 ③不要站在马后方 ④拍照时保持距离。如有恐惧请提前告知。',
    tag: '关键词：骑马、马术',
    tagColor: 'bg-orange-500',
    status: '已启用',
    lastSent: '-',
    recipients: 12,
    enabled: true,
  },
]

function touristsForTrip(trip: MakeTrip, index: number): MakeTourist[] {
  if (trip.teamId === 'TEAM-DEMO-POST') return defaultTourists
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
  itinerary: trip.teamId === 'TEAM-DEMO-POST' ? altayItinerary : fallbackItinerary(trip, index),
  tourists: touristsForTrip(trip, index),
  notifications: notificationsForTrip(trip),
}))

export const mockImportedTourists = excelImportedTourists

export const mockAnalyticsData = {
  overview: [
    { label: '总旅行团数', value: '24', trend: '+3', trendType: 'up' },
    { label: '总游客数', value: '286', trend: '+45', trendType: 'up' },
    { label: '平均满意度', value: '4.8/5.0', trend: '+0.2', trendType: 'up' },
    { label: '通知发送总数', value: '1,234', trend: '+156', trendType: 'up' },
  ],
  tripStats: [
    { status: '进行中', count: 3, percentage: 12.5, color: 'bg-green-500' },
    { status: '即将出发', count: 5, percentage: 20.8, color: 'bg-blue-500' },
    { status: '招募中', count: 8, percentage: 33.3, color: 'bg-yellow-500' },
    { status: '已完成', count: 8, percentage: 33.3, color: 'bg-gray-500' },
  ],
  notificationStats: [
    { type: '早安问候', sent: 245, success: 242, rate: 98.8 },
    { type: '午间提醒', sent: 120, success: 118, rate: 98.3 },
    { type: '晚安问候', sent: 238, success: 235, rate: 98.7 },
    { type: '出发提醒', sent: 24, success: 24, rate: 100 },
    { type: '行程更新', sent: 56, success: 55, rate: 98.2 },
    { type: '天气预警', sent: 18, success: 18, rate: 100 },
  ],
  recentTrips: [
    { name: '阿勒泰本地冬营团', participants: 12, revenue: 38000, satisfaction: 4.9 },
    { name: '埃塞俄比亚古文明探索团', participants: 8, revenue: 52000, satisfaction: 4.7 },
    { name: '马来半岛美食文化之旅', participants: 15, revenue: 28000, satisfaction: 4.8 },
    { name: '北海道春季赏樱团', participants: 20, revenue: 65000, satisfaction: 5.0 },
  ],
}
