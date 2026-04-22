import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import assert from 'node:assert/strict'

const tripsSource = readFileSync(resolve('frontend/src/pages/Trips.tsx'), 'utf8')
const tripDetailSource = readFileSync(resolve('frontend/src/pages/TripDetail.tsx'), 'utf8')
const apiSource = readFileSync(resolve('frontend/src/features/trip-management/tripDetailApi.ts'), 'utf8')
const mapperSource = readFileSync(resolve('frontend/src/features/trip-management/tripDetailMapper.ts'), 'utf8')
const editorSource = readFileSync(resolve('frontend/src/components/trip/TripDayEditor.tsx'), 'utf8')

assert.match(tripsSource, /onOpenTripNotifications\?: \(tripId: string\) => void/, 'Trips props must expose onOpenTripNotifications contract.')
assert.match(tripsSource, /通知设置/, 'Trips page must render "通知设置" entry point.')
assert.match(tripDetailSource, /onOpenTripNotifications\?: \(tripId: string\) => void/, 'TripDetail props must expose onOpenTripNotifications contract.')
assert.match(tripDetailSource, /通知设置/, 'TripDetail page must render "通知设置" button.')

assert.match(apiSource, /tripsApi\.get\(tripId\)/, 'Trip detail API wrapper must call GET /api/trips/{trip_id}.')
assert.match(apiSource, /tripsApi\.getSchedule\(tripId\)/, 'Trip detail API wrapper must call GET /api/trips/{trip_id}\/schedule.')
assert.match(apiSource, /tripsApi\.update\(tripId,\s*\{\s*itinerary:/s, 'Trip detail API wrapper must use PUT /api/trips/{trip_id} for day CRUD persistence.')

assert.match(mapperSource, /buildDayDraft/, 'Mapper must provide add-day draft builder.')
assert.match(mapperSource, /upsertDay/, 'Mapper must provide edit-day updater.')
assert.match(mapperSource, /removeDay/, 'Mapper must provide delete-day updater.')
assert.match(editorSource, /出发时间/, 'Day editor must include departure time field.')
assert.match(editorSource, /到达时间/, 'Day editor must include arrival time field.')
assert.match(editorSource, /景点/, 'Day editor must include sightseeing field.')
assert.match(editorSource, /集合提醒/, 'Day editor must include meeting reminder field.')

console.log('trip detail schedule CRUD contract ok')
