import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import assert from 'node:assert/strict'

const tripDetail = readFileSync(resolve('frontend/src/pages/TripDetail.tsx'), 'utf8')
const toggle = readFileSync(resolve('frontend/src/components/trip/TripSendModeToggle.tsx'), 'utf8')
const staffPanel = readFileSync(resolve('frontend/src/components/trip/TripStaffMessagesPanel.tsx'), 'utf8')
const api = readFileSync(resolve('frontend/src/services/api.ts'), 'utf8')
const workspace = readFileSync(resolve('frontend/src/pages/GuideWorkspace.tsx'), 'utf8')

assert.match(tripDetail, /TripSendModeToggle/, 'Trip detail must render the per-trip send mode toggle.')
assert.match(tripDetail, /TripStaffMessagesPanel/, 'Trip detail must render role-specific staff messages.')
assert.match(toggle, /自动发送/, 'Send mode toggle must offer automatic sending.')
assert.match(toggle, /需我确认/, 'Send mode toggle must offer approval mode.')
assert.match(toggle, /updateSendMode/, 'Send mode toggle must persist through the API.')
assert.match(api, /\/trips\/\$\{encodeURIComponent\(tripId\)\}\/send-mode/, 'API must expose the send-mode endpoint.')
assert.match(api, /\/staff-messages/, 'API must expose staff messages.')
assert.match(api, /sendStaffMessage/, 'API must allow sending one role message independently.')
assert.match(staffPanel, /团期负责人/, 'Staff panel must show the trip manager role.')
assert.match(staffPanel, /旅行管家/, 'Staff panel must show the concierge role.')
assert.match(staffPanel, /司机/, 'Staff panel must show the driver role.')
assert.match(staffPanel, /润色/, 'Staff messages must be polishable.')
assert.match(staffPanel, /单独发送/, 'Staff messages must be sendable independently.')
assert.match(workspace, /send_mode/, 'Guide workspace must show each trip send mode.')

console.log('send mode and staff messages contract ok')
