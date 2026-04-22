import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import assert from 'node:assert/strict'

const panelSource = readFileSync(
  resolve('frontend/src/components/notifications/TripNotificationConfigPanel.tsx'),
  'utf8',
)
const formSource = readFileSync(
  resolve('frontend/src/components/notifications/TripNotificationRuleForm.tsx'),
  'utf8',
)
const tableSource = readFileSync(
  resolve('frontend/src/components/notifications/TripNotificationStatusTable.tsx'),
  'utf8',
)
const clientSource = readFileSync(
  resolve('frontend/src/features/notifications/tripNotificationClient.ts'),
  'utf8',
)

assert.match(
  panelSource,
  /export function TripNotificationConfigPanel\(\{ tripId, onBackToTrip, tripLabel \}:\s*TripNotificationConfigPanelProps\)/,
  'Trip notification panel must expose the required component contract.',
)

assert.match(
  panelSource,
  /按旅行团配置通知/,
  'Trip notification panel must render Chinese trip-scoped title.',
)

assert.match(
  panelSource,
  /规则名称|时间点|绑定模板|渠道|启用状态/,
  'Trip notification panel must render core Chinese columns for trip rules.',
)

assert.match(
  formSource,
  /新增通知规则|编辑通知规则/,
  'Trip notification rule form must support create/edit flow in Chinese.',
)

assert.match(
  tableSource,
  /发送状态总览|已发送|待发送/,
  'Trip notification status table must display sent/pending status in Chinese.',
)

assert.match(
  clientSource,
  /\/api\/notifications\/rules/,
  'Trip notification client must use notification rules endpoints.',
)
assert.match(
  clientSource,
  /trip_id:\s*tripId/,
  'Trip notification client must persist trip-scoped condition trip_id for rules.',
)
assert.match(
  clientSource,
  /\/api\/notifications\/templates/,
  'Trip notification client must query notification templates endpoint.',
)
assert.match(
  clientSource,
  /\/api\/notifications\/history/,
  'Trip notification client must query history for sent status.',
)
assert.match(
  clientSource,
  /\/api\/notifications\/jobs/,
  'Trip notification client must query jobs for pending status.',
)

console.log('notifications trip config contract ok')
