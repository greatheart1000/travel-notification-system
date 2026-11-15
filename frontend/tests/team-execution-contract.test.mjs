import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import assert from 'node:assert/strict'

const teamSource = readFileSync(resolve('frontend/src/pages/TeamExecution.tsx'), 'utf8')
const rulesSource = readFileSync(resolve('frontend/src/pages/settings/Rules.tsx'), 'utf8')
const tripDetailSource = readFileSync(resolve('frontend/src/pages/TripDetail.tsx'), 'utf8')
const commercialApi = readFileSync(resolve('frontend/src/services/commercialApi.ts'), 'utf8')

assert.match(teamSource, /团队执行/, 'Team execution page must render its heading.')
assert.match(teamSource, /assigned_trips/, 'Team execution page must show trips assigned to each guide.')
assert.match(teamSource, /recent_notifications/, 'Team execution page must show notification content per guide.')
assert.match(teamSource, /trips_without_group/, 'Team execution page must surface trips missing a WeCom group.')
assert.match(teamSource, /onOpenTrip/, 'Trip cards must be able to open trip detail.')
assert.match(commercialApi, /\/admin\/team-overview/, 'Team overview must use the admin overview endpoint.')

assert.match(rulesSource, /发送到群里的具体内容/, 'Rules page must expose the actual notification content.')
assert.match(rulesSource, /润色模板/, 'Rules page must support template polishing.')

assert.match(tripDetailSource, /TripGroupReminderModal/, 'Trip detail must include the group reminder modal.')
assert.match(tripDetailSource, /润色/, 'Trip detail notification editor must support polishing.')

console.log('team execution and AI contract ok')
