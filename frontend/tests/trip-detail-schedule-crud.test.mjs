import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import assert from 'node:assert/strict'

const tripsSource = readFileSync(resolve('frontend/src/pages/Trips.tsx'), 'utf8')
const tripDetailSource = readFileSync(resolve('frontend/src/pages/TripDetail.tsx'), 'utf8')
const apiSource = readFileSync(resolve('frontend/src/features/trip-management/tripDetailApi.ts'), 'utf8')
const mapperSource = readFileSync(resolve('frontend/src/features/trip-management/tripDetailMapper.ts'), 'utf8')
const editorSource = readFileSync(resolve('frontend/src/components/trip/TripDayEditor.tsx'), 'utf8')

assert.doesNotMatch(tripsSource, /通知设置/, 'Latest Make design must not render a standalone "通知设置" entry point.')
assert.match(tripsSource, /查看详情/, 'Trips page must open the trip detail page from the list.')
assert.match(tripDetailSource, /详细行程/, 'Trip detail page must render the itinerary table module.')
assert.match(tripDetailSource, /企业微信群通知/, 'Trip detail page must embed the WeCom notification table.')
assert.match(tripDetailSource, /旅行团游客名单/, 'Trip detail page must render the tourist list module.')
assert.match(tripDetailSource, /导入Excel/, 'Tourist list module must support mock Excel import.')
assert.match(tripDetailSource, /handleEditNotification/, 'WeCom notification table must support inline editing.')
assert.match(tripDetailSource, /handleDeleteNotification/, 'WeCom notification table must support deleting notifications.')
assert.match(tripsSource, /发送天气预警到企业微信群/, 'Trips page must render the weather warning group modal.')
assert.match(tripsSource, /editableWarnings/, 'Weather warning modal must support editable warning content.')
assert.match(tripsSource, /选择接收旅行团/, 'Weather warning modal must support selecting recipient trips.')

assert.match(apiSource, /tripsApi\.get\(tripId\)/, 'Trip detail API wrapper must call GET /api/trips/{trip_id}.')
assert.match(apiSource, /tripsApi\.getSchedule\(tripId\)/, 'Trip detail API wrapper must call GET /api/trips/{trip_id}/schedule.')
assert.match(apiSource, /tripsApi\.update\(tripId,\s*\{\s*itinerary:/s, 'Trip detail API wrapper must use PUT /api/trips/{trip_id} for day CRUD persistence.')

assert.match(mapperSource, /buildDayDraft/, 'Mapper must provide add-day draft builder.')
assert.match(mapperSource, /upsertDay/, 'Mapper must provide edit-day updater.')
assert.match(mapperSource, /removeDay/, 'Mapper must provide delete-day updater.')
assert.match(editorSource, /出发时间/, 'Day editor must include departure time field.')
assert.match(editorSource, /到达时间/, 'Day editor must include arrival time field.')
assert.match(editorSource, /景点/, 'Day editor must include sightseeing field.')
assert.match(editorSource, /集合提醒/, 'Day editor must include meeting reminder field.')

console.log('trip detail schedule CRUD contract ok')
