# FRONTEND_HANDOFF

Updated: 2026-04-11 (Asia/Shanghai)

## 1. 页面就绪度

| 页面 | 状态 | 备注 |
|---|---|---|
| Dashboard | ready | 已接入 typed API + adapter；支持 loading/error/empty/retry。 |
| Trips | ready | 已接入 team/team_id 兼容映射；支持 loading/error/empty/retry。 |
| Notifications | ready | 模板列表/创建/发送均已接通；若后端未开放创建接口会显示明确错误态，不会崩溃。 |
| Analytics | ready | 指标与排行映射已接入；支持 loading/error/empty/retry。 |
| Preferences | ready | 已改真实接口读写（`/preferences/me` 优先，404 回退 `/preferences`）。 |

## 2. 后端依赖接口矩阵

| 领域 | 方法 | 接口 | 说明 |
|---|---|---|---|
| Auth | POST | `/api/auth/login` | 登录获取 token |
| Auth | POST | `/api/auth/logout` | 退出并清理登录态 |
| Auth | GET | `/api/users/me` | 登录态校验 |
| Dashboard | GET | `/api/dashboard/stats` | 统计卡片 |
| Dashboard | GET | `/api/notifications/recent?limit=10` | 最近通知 |
| Trips | GET | `/api/trips` | 行程列表 |
| Trips | POST | `/api/trips` | 创建行程 |
| Trips | PUT | `/api/trips/{id}` | 更新行程 |
| Trips | DELETE | `/api/trips/{id}` | 删除行程 |
| Notifications | GET | `/api/notifications/templates` | 模板列表 |
| Notifications | POST | `/api/notifications/templates` | 模板创建主路径 |
| Notifications | POST | `/api/templates` | 模板创建兼容回退路径（主路径 404 时） |
| Notifications | POST | `/api/notifications/send` | 手工发送 |
| Analytics | GET | `/api/analytics/metrics` | 分析数据 |
| Preferences | GET/PUT | `/api/preferences/me` | 偏好设置主路径 |
| Preferences | GET/PUT | `/api/preferences` | 偏好设置兼容回退路径 |

## 3. 已知限制与用户影响

1. 通知模板创建是否成功取决于后端是否开放创建接口。
   - 用户影响：若后端未开放 `/api/notifications/templates` 与 `/api/templates`，页面会明确提示“后端未开放模板创建接口”，但不会崩溃。
2. 契约处于兼容期（字段/枚举混用）。
   - 用户影响：目前无直接影响；前端通过 adapter 吸收 `team/team_id`、channel/status 多值风格。
3. 401 统一处理为清理登录态并回到登录守卫。
   - 用户影响：token 失效时会要求重新登录。

## 4. 最小回归路径

1. 打开应用，确认未登录时显示登录守卫。
2. 使用有效账户登录，进入 Dashboard。
3. Dashboard 验证统计与最近通知可加载。
4. 进入 Trips，验证列表可加载。
5. 切到 Notifications，验证模板列表可加载、创建动作有明确成功/失败反馈、发送可触发。
6. 切到 Analytics，验证指标区可加载。
7. 进入 Preferences，修改后保存并刷新确认回读。
8. 点击退出，确认回到登录守卫。

## 5. 联动注意事项

1. 后端若收敛为单一字段（仅 `team_id`）或单一枚举值，前端可逐步删除兼容分支。
2. 兼容期内通知模板创建采用“双路径”：先 `/api/notifications/templates`，404 回退 `/api/templates`；后端收敛后可删回退。
3. 如果后端把更多接口改为强鉴权，保持当前 401 统一拦截策略并补充页面提示文案。
