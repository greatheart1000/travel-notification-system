import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import assert from 'node:assert/strict'

const serviceSource = readFileSync(resolve('frontend/src/services/figmaTripService.ts'), 'utf8')
const packageJson = readFileSync(resolve('frontend/package.json'), 'utf8')

assert.match(
  serviceSource,
  /VITE_DEMO_MODE/,
  'Production builds must gate mock fallbacks behind VITE_DEMO_MODE.',
)

assert.doesNotMatch(
  serviceSource,
  /mockAnalyticsData|FigmaAnalyticsService/,
  'Deprecated dashboard/analytics mock service must not remain in the frontend.',
)

assert.doesNotMatch(
  packageJson,
  /recharts/,
  'Unused recharts dependency must be removed.',
)

console.log('frontend production mock-fallback guard ok')
