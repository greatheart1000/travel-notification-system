import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import assert from 'node:assert/strict'

const notificationsSource = readFileSync(resolve('frontend/src/pages/Notifications.tsx'), 'utf8')
const apiSource = readFileSync(resolve('frontend/src/services/api.ts'), 'utf8')

assert.match(
  notificationsSource,
  /紧急天气通知|天气风险通知/,
  'Notifications page must render a Chinese emergency weather module title.',
)

assert.match(
  notificationsSource,
  /天气摘要/,
  'Notifications page must display a weather summary section.',
)

assert.match(
  notificationsSource,
  /风险分析/,
  'Notifications page must display a risk analysis section.',
)

assert.match(
  notificationsSource,
  /通知文案/,
  'Notifications page must display a notification preview section.',
)

assert.match(
  notificationsSource,
  /编辑后发送|确认发送/,
  'Notifications page must provide edit/send actions for the emergency weather module.',
)

assert.doesNotMatch(
  notificationsSource,
  /Global Emergency Alert & Trigger Management Center|Send Alert|Notification Templates|Trip-Specific SMS Timeline Management|Morning SMS|Noon SMS|Evening SMS|Actions/,
  'Notifications page should not keep old English headings or action labels.',
)

assert.match(
  apiSource,
  /emergency-weather/,
  'Frontend API client must expose emergency weather endpoints.',
)

console.log('notifications page Chinese emergency module contract ok')
