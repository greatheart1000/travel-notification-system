# 新疆行程管家服务 API 文档

> 部署域名: `http://toyspace.tech`  
> 更新时间: 2026-06-02

---

## 认证与用户

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/login` | 登录 |
| POST | `/api/auth/logout` | 登出 |
| POST | `/api/auth/refresh` | 刷新 token |
| GET | `/api/users/me` | 当前用户信息 |

---

## 系统健康

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/health/detail` | 详细健康状态 |

---

## 用户偏好

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/preferences/me` | 获取当前用户偏好 |
| PUT | `/api/preferences/me` | 更新当前用户偏好 |
| GET | `/api/preferences` | 获取偏好（旧版兼容） |
| PUT | `/api/preferences` | 更新偏好（旧版兼容） |

---

## 通知模板

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/templates` | 模板列表 |
| GET | `/api/templates/{id}` | 模板详情 |
| POST | `/api/templates` | 创建模板 |
| PUT | `/api/templates/{id}` | 更新模板 |
| DELETE | `/api/templates/{id}` | 删除模板 |
| GET | `/api/notifications/templates` | 通知模板列表 |
| POST | `/api/notifications/templates` | 创建通知模板 |
| PUT | `/api/notifications/templates/{id}` | 更新通知模板 |
| DELETE | `/api/notifications/templates/{id}` | 删除通知模板 |
| POST | `/api/notifications/templates/agent-drafts` | AI 草稿生成 |

---

## 通知规则

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/notifications/rules` | 规则列表（支持 `enabled`/`stage`/`time_slot`/`scene` 过滤） |
| POST | `/api/notifications/rules` | 创建规则 |
| GET | `/api/notifications/rules/{id}` | 规则详情 |
| PUT | `/api/notifications/rules/{id}` | 更新规则 |
| DELETE | `/api/notifications/rules/{id}` | 删除规则 |

请求体示例 (POST/PUT):
```json
{
  "name": "行前3天提醒",
  "stage": "pre_trip",
  "time_slot": "morning",
  "scene": "normal",
  "channels": ["sms", "wechat_work_group"],
  "template_id": "tpl-xxx",
  "enabled": true,
  "priority": 10
}
```

---

## 通知发送

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/notifications/dispatch/preview` | 预览发送内容 |
| POST | `/api/notifications/dispatch` | 执行发送 |
| POST | `/api/notifications/dispatch/{id}/retry` | 重试发送 |
| POST | `/api/notifications/send` | 直接发送通知 |
| POST | `/api/notifications/generate-daily` | 生成每日通知 |
| GET | `/api/notifications/recent` | 近期通知记录 |
| GET | `/api/notifications/emergency-weather` | 紧急天气摘要 |
| POST | `/api/notifications/emergency-weather/send` | 发送紧急天气通知 |

---

## 行程管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/trips` | 行程列表 |
| POST | `/api/trips` | 创建行程 |
| POST | `/api/trips/import` | 导入行程 |
| GET | `/api/trips/{id}` | 行程详情 |
| PUT | `/api/trips/{id}` | 更新行程 |
| DELETE | `/api/trips/{id}` | 删除行程 |
| GET | `/api/trips/{id}/schedule` | 行程日程 |
| GET | `/api/trips/{id}/timeline` | 行程时间线 |
| GET | `/api/trips/execution` | 行程执行状态列表 |
| GET | `/api/trips/{id}/execution` | 单个行程执行详情 |
| GET | `/api/trips/{id}/import-snapshot` | 导入快照 |
| PUT | `/api/trips/{id}/import-validation` | 导入校验 |

注意：`{id}` 为后端生成的 `trip-{uuid}` 格式主键，非业务团号 `team_id`。

---

## 项目配置

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/project-configs` | 项目配置列表 |
| GET | `/api/project-configs/{id}` | 项目配置详情 |
| PUT | `/api/project-configs/{id}` | 更新项目配置 |

---

## 工作台

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/workbench/today/overview` | 今日概览 |
| GET | `/api/workbench/today/action-items` | 今日待办 |
| POST | `/api/workbench/takeovers` | 任务接管 |
| POST | `/api/workbench/tasks/{id}/complete` | 完成任务 |
| POST | `/api/workbench/tasks/{id}/nudge` | 催办任务 |

---

## 仪表盘与分析

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/dashboard/stats` | 仪表盘统计 |
| GET | `/api/dashboard/smart-suggestions` | 智能建议 |
| GET | `/api/analytics/metrics` | 数据分析指标 |

---

## 管理后台

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/admin/run-automation-scan` | 运行自动扫描 |
| POST | `/api/admin/trigger-weather-check` | 触发天气检查 |

---

## 天气（FC 专有）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/weather/xinjiang` | 新疆 8 城市实时天气（和风天气） |

> 需要环境变量: `QWEATHER_API_KEY`, `QWEATHER_API_HOST`
