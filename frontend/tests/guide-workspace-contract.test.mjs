import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import assert from 'node:assert/strict'

const pageSource = readFileSync(resolve('frontend/src/pages/GuideWorkspace.tsx'), 'utf8')
const apiSource = readFileSync(resolve('frontend/src/services/api.ts'), 'utf8')
const appSource = readFileSync(resolve('frontend/src/App.tsx'), 'utf8')

assert.match(pageSource, /我的工作台/, 'Guide workspace must render its heading.')
assert.match(pageSource, /今天要跟进/, 'Guide workspace must show today\'s trips.')
assert.match(pageSource, /group_missing/, 'Guide workspace must surface trips missing a WeCom group.')
assert.match(pageSource, /recent_notifications/, 'Guide workspace must show recent sent content.')
assert.match(pageSource, /onOpenTrip/, 'Guide trip cards must open trip detail.')
assert.match(apiSource, /\/guide\/workspace/, 'Guide workspace must use the guide workspace endpoint.')
assert.match(appSource, /GuideWorkspace/, 'App must render the guide workspace for non-admin users.')

console.log('guide workspace contract ok')
