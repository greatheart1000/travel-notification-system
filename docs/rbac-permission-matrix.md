# RBAC 权限与数据域矩阵（Batch2 Week1）

## 角色-资源-动作

| 角色 | trip | notification | rule | template | audit | ops |
| --- | --- | --- | --- | --- | --- | --- |
| admin | read/write | read/write | read/write/approve | read/write | read | read |
| ops | read | read/write | read | read | read | read |
| concierge | read | read/write | - | read | - | - |
| cs | read | read | - | - | read | - |
| sales | read | read | - | - | - | - |
| user | read/write | read/write | - | - | - | - |

## 数据域约束

- **tenant 域（强约束）**：所有接口默认按 `tenant_id` 过滤，跨租户访问统一返回 `403`。
- **team 域（可选约束）**：当用户绑定 `team_id` 时，默认仅允许访问同团队资源；`admin` 可跨团队。
- **user 域（最小权限）**：普通用户只能读取/修改自己创建的行程与通知记录。

## 统一错误语义

- 缺少权限：`403 missing_permission`
- 跨租户：`403 cross_tenant_forbidden`
- 跨团队：`403 cross_team_forbidden`

## 本次落地范围

1. 新增 `require_permission()`、`assert_tenant_scope()`、`assert_team_scope()` 基础能力。
2. 在 `templates/rules/trips/notifications` 关键 API 增加权限闸门。
3. 健康检查扩展异步队列指标，为 Week1 Day4/Day5 的异步任务能力提供观测基线。
