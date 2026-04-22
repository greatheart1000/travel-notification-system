import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import assert from 'node:assert/strict'

const appSource = readFileSync(resolve('frontend/src/App.tsx'), 'utf8')

assert.match(
  appSource,
  /AUTH_STATE_CHANGED_EVENT|hasAccessToken/,
  'App must wire the auth adapter so protected pages are not rendered anonymously.',
)

assert.match(
  appSource,
  /authApi\.login/,
  'App must provide a login flow that stores backend-issued access tokens.',
)

assert.match(
  appSource,
  /!isAuthenticated/,
  'App must render a non-authenticated state instead of protected pages when no token exists.',
)

assert.doesNotMatch(
  appSource,
  /彻底移除登录逻辑|强制进入状态/,
  'App must not bypass authentication by force-rendering protected pages.',
)

console.log('app auth guard contract ok')
