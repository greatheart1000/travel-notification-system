#!/usr/bin/env node
const assert = require('node:assert/strict')
const { execFileSync } = require('node:child_process')

const baseUrl = process.env.API_BASE_URL || 'http://127.0.0.1:3001'

async function main() {
  const docs = JSON.parse(execFileSync('node', ['mock-mysql-api.cjs', '--print-documents'], {
    encoding: 'utf8',
    maxBuffer: 1024 * 1024 * 64,
  }))

  async function get(path) {
    const response = await fetch(`${baseUrl}${path}`)
    if (!response.ok) throw new Error(`${path} returned ${response.status}`)
    return response.json()
  }

  const checks = [
    ['/api/mock-data', docs.all],
    ['/api/mock-data/mockTripDetails', docs.mockTripDetails],
    ['/api/mock-data/mockTrips', docs.mockTrips],
    ['/api/mock-data/mockWeather', docs.mockWeather],
    ['/api/mock-data/mockImportedTourists', docs.mockImportedTourists],
    ['/api/mock-data/mockAnalyticsData', docs.mockAnalyticsData],
    ['/api/trips', docs.tripList],
    ['/api/weather', docs.mockWeather],
    ['/api/weather/warnings', docs.warningWeather],
    ['/api/analytics', docs.mockAnalyticsData],
    ['/api/imported-tourists', docs.mockImportedTourists],
  ]

  for (const detail of docs.mockTripDetails) {
    checks.push([`/api/trips/${encodeURIComponent(detail.teamId)}`, detail])
    checks.push([`/api/trips/${encodeURIComponent(detail.id)}`, detail])
    checks.push([`/api/trips/${encodeURIComponent(detail.teamId)}/schedule`, detail.itinerary])
    checks.push([`/api/trips/${encodeURIComponent(detail.teamId)}/tourists`, detail.tourists])
    checks.push([`/api/trips/${encodeURIComponent(detail.teamId)}/notifications`, detail.notifications])
  }

  for (const [path, expected] of checks) {
    const actual = await get(path)
    assert.deepStrictEqual(actual, expected, path)
  }

  console.log(`strict JSON equality ok: ${checks.length} endpoints`)
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})
