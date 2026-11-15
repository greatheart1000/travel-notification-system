import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import assert from 'node:assert/strict'

const source = readFileSync(resolve('frontend/src/pages/Notifications.tsx'), 'utf8')

assert.match(
  source,
  /notificationsApi\.getEmergencyWeatherSummary/,
  'Notifications page must load the real emergency weather summary API.',
)

assert.match(
  source,
  /notificationsApi\.sendEmergencyWeather/,
  'Notifications page must send through the real emergency weather API.',
)

assert.doesNotMatch(
  source,
  /FigmaWeatherService/,
  'Notifications page must not depend on demo weather data.',
)

console.log('notifications page action wiring ok')
