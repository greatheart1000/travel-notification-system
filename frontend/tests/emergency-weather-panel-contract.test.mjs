import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import assert from 'node:assert/strict'

const panelSource = readFileSync(
  resolve('frontend/src/components/notifications/EmergencyWeatherPanel.tsx'),
  'utf8',
)

assert.match(
  panelSource,
  /EmergencyWeatherPanel\(\{[\s\S]*summary[\s\S]*draftContent[\s\S]*onEdit[\s\S]*onSend[\s\S]*onDefer[\s\S]*onViewDetail/,
  'EmergencyWeatherPanel must expose stable props contract: summary, draftContent, onEdit, onSend, onDefer, onViewDetail.',
)

assert.match(panelSource, /紧急天气预警/, 'Panel must render Chinese module title.')
assert.match(panelSource, /今日天气摘要/, 'Panel must render weather summary field.')
assert.match(panelSource, /风险等级/, 'Panel must render risk level field.')
assert.match(panelSource, /影响区域/, 'Panel must render affected region field.')
assert.match(panelSource, /受影响旅行团数量/, 'Panel must render affected trip count field.')
assert.match(panelSource, /受影响旅行团摘要/, 'Panel must render affected trips summary section.')
assert.match(panelSource, /AI 风险分析/, 'Panel must render AI risk analysis section.')
assert.match(panelSource, /游客通知文案/, 'Panel must render tourist notification copy section.')
assert.match(panelSource, /领队\/内部通知文案/, 'Panel must render internal notification copy section.')
assert.match(panelSource, /查看详情/, 'Panel must provide view detail action.')
assert.match(panelSource, /编辑文案/, 'Panel must provide edit action.')
assert.match(panelSource, /发送通知/, 'Panel must provide send action.')
assert.match(panelSource, /暂不发送/, 'Panel must provide defer action.')

console.log('emergency weather panel contract ok')
