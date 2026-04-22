import { readFileSync, existsSync } from 'node:fs'
import { resolve } from 'node:path'
import assert from 'node:assert/strict'

const appSource = readFileSync(resolve('frontend/src/App.tsx'), 'utf8')
const sidebarSource = readFileSync(resolve('frontend/src/components/Sidebar.tsx'), 'utf8')

assert.doesNotMatch(
  appSource,
  /pages\/Templates|templates-\$\{pageKey\}|['"]templates['"]/,
  'App must not expose a standalone templates route.',
)

assert.doesNotMatch(
  sidebarSource,
  /消息模板|['"]templates['"]/,
  'Sidebar must not render a standalone templates menu item.',
)

assert.equal(
  existsSync(resolve('frontend/src/pages/Templates.tsx')),
  false,
  'Standalone templates page file must be removed.',
)

console.log('standalone templates module removed')
