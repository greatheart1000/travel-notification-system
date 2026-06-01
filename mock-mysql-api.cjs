#!/usr/bin/env node
const http = require('node:http')
const { spawnSync } = require('node:child_process')
const { readFileSync } = require('node:fs')
const { resolve } = require('node:path')
const { createHash } = require('node:crypto')
const vm = require('node:vm')

const PORT = Number(process.env.PORT || 3001)
const MYSQL_USER = process.env.MYSQL_USER || 'root'
const MYSQL_PASSWORD = process.env.MYSQL_PASSWORD || 'testpass123'
const MYSQL_DATABASE = process.env.MYSQL_DATABASE || 'travel_hub'
const MOCK_FILE = resolve(process.env.MOCK_FILE || 'frontend/src/data/figmaMockData.ts')

function runMysql(sql, options = {}) {
  const args = [
    `-u${MYSQL_USER}`,
    `-p${MYSQL_PASSWORD}`,
    '--default-character-set=utf8mb4',
    '--batch',
    '--raw',
    '--skip-column-names',
  ]
  if (options.database !== false) args.push(MYSQL_DATABASE)

  const result = spawnSync('mysql', args, {
    input: sql,
    encoding: 'utf8',
    maxBuffer: 1024 * 1024 * 64,
  })

  if (result.status !== 0) {
    throw new Error(result.stderr || result.stdout || `mysql exited with ${result.status}`)
  }

  return result.stdout.replace(/\n$/, '')
}

function sqlString(value) {
  return `'${String(value).replace(/\\/g, '\\\\').replace(/'/g, "''")}'`
}

function sourceHash() {
  return createHash('sha256').update(readFileSync(MOCK_FILE, 'utf8')).digest('hex')
}

function loadMockExports() {
  const source = readFileSync(MOCK_FILE, 'utf8')
  const ts = require(resolve('frontend/node_modules/typescript'))
  const compiled = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
      esModuleInterop: true,
      removeComments: false,
    },
    fileName: MOCK_FILE,
  }).outputText

  const module = { exports: {} }
  const sandbox = {
    module,
    exports: module.exports,
    require,
    console,
  }
  vm.runInNewContext(compiled, sandbox, { filename: MOCK_FILE })
  return module.exports
}

function withoutDetailFields(detail) {
  const { itinerary, tourists, notifications, ...trip } = detail
  return trip
}

function buildDocuments() {
  const exports = loadMockExports()
  const documents = {
    makeStatusColorMap: exports.makeStatusColorMap,
    mockTrips: exports.mockTrips,
    mockWeather: exports.mockWeather,
    mockTripDetails: exports.mockTripDetails,
    mockImportedTourists: exports.mockImportedTourists,
    mockAnalyticsData: exports.mockAnalyticsData,
    all: {
      makeStatusColorMap: exports.makeStatusColorMap,
      mockTrips: exports.mockTrips,
      mockWeather: exports.mockWeather,
      mockTripDetails: exports.mockTripDetails,
      mockImportedTourists: exports.mockImportedTourists,
      mockAnalyticsData: exports.mockAnalyticsData,
    },
  }

  documents.tripList = exports.mockTripDetails.map(withoutDetailFields)
  documents.warningWeather = exports.mockWeather.filter((weather) => weather.warning !== null)

  return documents
}

function writeDocument(key, value, hash = sourceHash()) {
  const payload = JSON.stringify(value)
  const payloadBase64 = Buffer.from(payload, 'utf8').toString('base64')
  runMysql(`
INSERT INTO mock_documents (mock_key, payload, source_path, source_hash)
VALUES (${sqlString(key)}, CONVERT(FROM_BASE64(${sqlString(payloadBase64)}) USING utf8mb4), ${sqlString(MOCK_FILE)}, ${sqlString(hash)})
ON DUPLICATE KEY UPDATE
  payload = VALUES(payload),
  source_path = VALUES(source_path),
  source_hash = VALUES(source_hash),
  loaded_at = CURRENT_TIMESTAMP;
`)
}

function initializeDatabase() {
  const hash = sourceHash()
  const documents = buildDocuments()

  runMysql(`CREATE DATABASE IF NOT EXISTS \`${MYSQL_DATABASE}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;`, { database: false })
  runMysql(`
CREATE TABLE IF NOT EXISTS mock_documents (
  mock_key VARCHAR(128) PRIMARY KEY,
  payload LONGTEXT NOT NULL,
  source_path VARCHAR(512) NOT NULL,
  source_hash CHAR(64) NOT NULL,
  loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CHECK (JSON_VALID(payload))
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
`)

  for (const [key, value] of Object.entries(documents)) {
    writeDocument(key, value, hash)
  }

  return { sourceHash: hash, keys: Object.keys(documents) }
}

function readDocument(key) {
  const result = runMysql(`SELECT payload FROM mock_documents WHERE mock_key = ${sqlString(key)} LIMIT 1;`)
  if (!result) return null
  return result
}

function readJsonDocument(key) {
  const payload = readDocument(key)
  return payload ? JSON.parse(payload) : null
}

function persistTripDetails(details) {
  writeDocument('mockTripDetails', details)
  writeDocument('tripList', details.map(withoutDetailFields))

  const all = readJsonDocument('all') || {}
  writeDocument('all', {
    ...all,
    mockTripDetails: details,
  })
}

function findTripIndex(details, id) {
  return details.findIndex((trip) => trip.id === id || trip.teamId === id || trip.code === id)
}

function findTripDetail(id) {
  const details = readJsonDocument('mockTripDetails')
  if (!details) return null
  const detail = details.find((trip) => trip.id === id || trip.teamId === id || trip.code === id)
  return detail ? JSON.stringify(detail) : null
}

function detailSubdocument(id, field) {
  const detailPayload = findTripDetail(id)
  if (!detailPayload) return null
  const detail = JSON.parse(detailPayload)
  return JSON.stringify(detail[field])
}

function corsHeaders(extra = {}) {
  return {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type,Accept,Authorization,X-Client-Version',
    ...extra,
  }
}

function sendJson(response, status, payloadText) {
  response.writeHead(status, corsHeaders({
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'no-store',
  }))
  response.end(payloadText)
}

function sendNoContent(response) {
  response.writeHead(204, corsHeaders())
  response.end()
}

function sendNotFound(response) {
  sendJson(response, 404, JSON.stringify({ error: 'not_found' }))
}

async function readJsonBody(request) {
  let body = ''
  for await (const chunk of request) {
    body += chunk
  }
  if (!body.trim()) return null
  return JSON.parse(body)
}

async function routeRequest(request, response) {
  if (request.method === 'OPTIONS') {
    sendNoContent(response)
    return
  }

  const url = new URL(request.url, `http://${request.headers.host || 'localhost'}`)
  const pathname = decodeURIComponent(url.pathname)
  const parts = pathname.split('/').filter(Boolean)

  try {
    if (request.method === 'GET') {
      if (pathname === '/health') {
        sendJson(response, 200, JSON.stringify({ ok: true, source: MOCK_FILE }))
        return
      }

      if (pathname === '/api/mock-data') {
        const payload = readDocument('all')
        return payload ? sendJson(response, 200, payload) : sendNotFound(response)
      }

      if (parts[0] === 'api' && parts[1] === 'mock-data' && parts[2]) {
        const payload = readDocument(parts[2])
        return payload ? sendJson(response, 200, payload) : sendNotFound(response)
      }

      if (pathname === '/api/trips') {
        const payload = readDocument('tripList')
        return payload ? sendJson(response, 200, payload) : sendNotFound(response)
      }

      if (parts[0] === 'api' && parts[1] === 'trips' && parts[2] && parts.length === 3) {
        const payload = findTripDetail(parts[2])
        return payload ? sendJson(response, 200, payload) : sendNotFound(response)
      }

      if (parts[0] === 'api' && parts[1] === 'trips' && parts[2] && parts[3] === 'schedule' && parts.length === 4) {
        const payload = detailSubdocument(parts[2], 'itinerary')
        return payload ? sendJson(response, 200, payload) : sendNotFound(response)
      }

      if (parts[0] === 'api' && parts[1] === 'trips' && parts[2] && parts[3] === 'tourists' && parts.length === 4) {
        const payload = detailSubdocument(parts[2], 'tourists')
        return payload ? sendJson(response, 200, payload) : sendNotFound(response)
      }

      if (parts[0] === 'api' && parts[1] === 'trips' && parts[2] && parts[3] === 'notifications' && parts.length === 4) {
        const payload = detailSubdocument(parts[2], 'notifications')
        return payload ? sendJson(response, 200, payload) : sendNotFound(response)
      }

      if (pathname === '/api/weather') {
        const payload = readDocument('mockWeather')
        return payload ? sendJson(response, 200, payload) : sendNotFound(response)
      }

      if (pathname === '/api/weather/warnings') {
        const payload = readDocument('warningWeather')
        return payload ? sendJson(response, 200, payload) : sendNotFound(response)
      }

      if (pathname === '/api/analytics') {
        const payload = readDocument('mockAnalyticsData')
        return payload ? sendJson(response, 200, payload) : sendNotFound(response)
      }

      if (pathname === '/api/imported-tourists') {
        const payload = readDocument('mockImportedTourists')
        return payload ? sendJson(response, 200, payload) : sendNotFound(response)
      }

      sendNotFound(response)
      return
    }

    if (request.method === 'POST' && pathname === '/api/mock-data/reset') {
      const result = initializeDatabase()
      sendJson(response, 200, JSON.stringify({ ok: true, ...result }))
      return
    }

    if (parts[0] === 'api' && parts[1] === 'trips' && parts[2]) {
      const details = readJsonDocument('mockTripDetails')
      if (!details) return sendNotFound(response)

      const tripIndex = findTripIndex(details, parts[2])
      if (tripIndex < 0) return sendNotFound(response)

      if (request.method === 'PUT' && parts.length === 3) {
        const tripUpdate = await readJsonBody(request)
        details[tripIndex] = {
          ...details[tripIndex],
          ...tripUpdate,
          participants: Number(tripUpdate?.participants) || details[tripIndex].participants,
        }
        persistTripDetails(details)
        sendJson(response, 200, JSON.stringify(withoutDetailFields(details[tripIndex])))
        return
      }

      if (request.method === 'DELETE' && parts.length === 3) {
        persistTripDetails(details.filter((trip) => trip.id !== parts[2] && trip.teamId !== parts[2] && trip.code !== parts[2]))
        sendJson(response, 200, JSON.stringify({ ok: true }))
        return
      }

      if (request.method === 'PUT' && parts[3] === 'notifications' && parts[4] && parts.length === 5) {
        const index = Number(parts[4])
        const notification = await readJsonBody(request)
        if (!Number.isInteger(index) || index < 0 || index >= details[tripIndex].notifications.length) return sendNotFound(response)
        details[tripIndex] = {
          ...details[tripIndex],
          notifications: details[tripIndex].notifications.map((item, itemIndex) => (itemIndex === index ? notification : item)),
        }
        persistTripDetails(details)
        sendJson(response, 200, JSON.stringify(details[tripIndex]))
        return
      }

      if (request.method === 'DELETE' && parts[3] === 'notifications' && parts[4] && parts.length === 5) {
        const index = Number(parts[4])
        if (!Number.isInteger(index) || index < 0 || index >= details[tripIndex].notifications.length) return sendNotFound(response)
        details[tripIndex] = {
          ...details[tripIndex],
          notifications: details[tripIndex].notifications.filter((_, itemIndex) => itemIndex !== index),
        }
        persistTripDetails(details)
        sendJson(response, 200, JSON.stringify(details[tripIndex]))
        return
      }

      if (request.method === 'POST' && parts[3] === 'tourists' && parts.length === 4) {
        const tourist = await readJsonBody(request)
        details[tripIndex] = {
          ...details[tripIndex],
          participants: details[tripIndex].participants + 1,
          tourists: [...details[tripIndex].tourists, tourist],
        }
        persistTripDetails(details)
        sendJson(response, 200, JSON.stringify(details[tripIndex]))
        return
      }

      if (request.method === 'PUT' && parts[3] === 'tourists' && parts[4] && parts.length === 5) {
        const index = Number(parts[4])
        const tourist = await readJsonBody(request)
        if (!Number.isInteger(index) || index < 0 || index >= details[tripIndex].tourists.length) return sendNotFound(response)
        details[tripIndex] = {
          ...details[tripIndex],
          tourists: details[tripIndex].tourists.map((item, itemIndex) => (itemIndex === index ? tourist : item)),
        }
        persistTripDetails(details)
        sendJson(response, 200, JSON.stringify(details[tripIndex]))
        return
      }

      if (request.method === 'DELETE' && parts[3] === 'tourists' && parts[4] && parts.length === 5) {
        const index = Number(parts[4])
        if (!Number.isInteger(index) || index < 0 || index >= details[tripIndex].tourists.length) return sendNotFound(response)
        const tourists = details[tripIndex].tourists.filter((_, itemIndex) => itemIndex !== index)
        details[tripIndex] = {
          ...details[tripIndex],
          participants: tourists.length,
          tourists,
        }
        persistTripDetails(details)
        sendJson(response, 200, JSON.stringify(details[tripIndex]))
        return
      }

      if (request.method === 'POST' && parts[3] === 'imported-tourists' && parts.length === 4) {
        const imported = readJsonDocument('mockImportedTourists') || []
        details[tripIndex] = {
          ...details[tripIndex],
          participants: details[tripIndex].tourists.length + imported.length,
          tourists: [...details[tripIndex].tourists, ...imported],
        }
        persistTripDetails(details)
        sendJson(response, 200, JSON.stringify(details[tripIndex]))
        return
      }
    }

    response.writeHead(405, corsHeaders({ Allow: 'GET,POST,PUT,DELETE,OPTIONS' }))
    response.end()
  } catch (error) {
    sendJson(response, 500, JSON.stringify({ error: 'internal_error', message: error.message }))
  }
}

if (process.argv.includes('--print-documents')) {
  process.stdout.write(JSON.stringify(buildDocuments()))
  process.exit(0)
}

if (process.argv.includes('--init-only')) {
  const result = initializeDatabase()
  console.log(JSON.stringify({ ok: true, ...result }))
  process.exit(0)
}

const initResult = initializeDatabase()
console.log(`Loaded ${initResult.keys.length} mock documents from ${MOCK_FILE}`)
console.log(`MySQL database: ${MYSQL_DATABASE}`)

http.createServer((request, response) => {
  void routeRequest(request, response)
}).listen(PORT, () => {
  console.log(`Mock MySQL API listening on http://127.0.0.1:${PORT}`)
})
