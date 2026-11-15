import { readFileSync, existsSync } from 'node:fs'
import { resolve } from 'node:path'
import assert from 'node:assert/strict'

const authShellSource = readFileSync(resolve('frontend/src/components/auth/AuthShell.tsx'), 'utf8')
const loginSource = readFileSync(resolve('frontend/src/pages/Login.tsx'), 'utf8')
const registerSource = readFileSync(resolve('frontend/src/pages/Register.tsx'), 'utf8')
const billingSource = readFileSync(resolve('frontend/src/pages/Billing.tsx'), 'utf8')
const channelsSource = readFileSync(resolve('frontend/src/pages/settings/Channels.tsx'), 'utf8')
const rulesSource = readFileSync(resolve('frontend/src/pages/settings/Rules.tsx'), 'utf8')
const jobsSource = readFileSync(resolve('frontend/src/pages/settings/Jobs.tsx'), 'utf8')
const sidebarSource = readFileSync(resolve('frontend/src/components/Sidebar.tsx'), 'utf8')

assert.match(authShellSource, /行程管家|Travel Hub/, 'Auth shell must carry commercial branding.')
assert.match(loginSource, /验证码/, 'Login page must offer SMS verification-code login.')
assert.match(loginSource, /忘记密码/, 'Login page must offer password reset.')
assert.doesNotMatch(loginSource, /123456|演示账号|默认账号/, 'Login page must not prefill demo credentials.')
assert.match(registerSource, /注册企业/, 'Register page must expose tenant registration.')
assert.match(registerSource, /sms-code|sendSmsCode/, 'Register page must request an SMS verification code.')

assert.match(billingSource, /billingApi\.getSubscription/, 'Billing page must load the real subscription API.')
assert.match(billingSource, /billingApi\.createOrder/, 'Billing page must create real payment orders.')
assert.match(billingSource, /短信/, 'Billing page must show SMS quota usage.')
assert.match(billingSource, /订单记录/, 'Billing page must show order history.')

assert.match(channelsSource, /tenantSettingsApi\.getNotificationConfig/, 'Channels page must load tenant config.')
assert.match(channelsSource, /qyapi\.weixin\.qq\.com/, 'Channels page must validate official WeCom webhooks.')
assert.match(rulesSource, /rulesApi\.list/, 'Rules page must load notification rules.')
assert.match(rulesSource, /rulesApi\.create/, 'Rules page must create notification rules.')
assert.match(jobsSource, /jobsApi\.requeue/, 'Jobs page must requeue dead-letter jobs.')

for (const page of ['Billing', 'Login', 'Register']) {
  assert.equal(existsSync(resolve(`frontend/src/pages/${page}.tsx`)), true, `${page} page must exist.`)
}
assert.match(sidebarSource, /通知渠道/, 'Sidebar must expose channel configuration.')
assert.match(sidebarSource, /套餐与账单/, 'Sidebar must expose billing.')
assert.match(sidebarSource, /发送任务/, 'Sidebar must expose dead-letter operations.')

console.log('commercial pages contract ok')

const operatorSource = readFileSync(resolve('frontend/src/pages/Operator.tsx'), 'utf8')
assert.match(operatorSource, /operatorApi\.overview/, 'Operator page must load platform overview.')
assert.match(operatorSource, /operatorApi\.activatePlan/, 'Operator page must support manual plan activation.')
assert.match(operatorSource, /operatorApi\.refundOrder/, 'Operator page must support refund recording.')
assert.match(sidebarSource, /运营概览/, 'Sidebar must expose the operator console for platform operators.')

console.log('operator console contract ok')
