# MySQL 表设计（行程管理 + 通知中心）

这个文档对应 `docs/mysql_schema_seed.sql`，用于把当前 MVP 的 JSON 持久化模型落到 MySQL。

## 1. 表清单

1. `t_trip`：行程管理主表（支持增删改查）
2. `t_lifecycle_playbook`：行程流程动作表（来自你提供的 Excel 表格）
3. `t_notification_template`：通知模板表（通知中心模板增删改查）
4. `t_notification_rule`：通知规则表（按阶段/时段/场景）
5. `t_notification_rule_channel`：规则渠道表（主渠道 + 兜底渠道）
6. `t_notification_task`：通知发送任务主表
7. `t_notification_attempt`：通知发送尝试明细表（用于统计“已发送/成功率”）
8. `t_collection_store`：通用 JSON 集合表（承载偏好设置、审计、分析快照等扩展集合）

## 2. 关系说明

- `t_notification_rule.template_id -> t_notification_template.id`
- `t_notification_rule_channel.rule_id -> t_notification_rule.id`
- `t_notification_task.trip_id -> t_trip.id`
- `t_notification_attempt.task_id -> t_notification_task.id`

补充说明：
- `t_notification_task.trip_id` 允许为空（支持手工发送/无行程通知场景）
- `t_notification_task.team_id` 冗余存储团号，便于按团队维度查询通知历史
- 多租户上下文统一落库：`t_trip / t_notification_template / t_notification_rule / t_notification_task` 均包含 `tenant_id`

## 3. 你关心的 CRUD 覆盖

### 行程管理

- 新增行程：`INSERT t_trip`
- 查询行程：`SELECT ... FROM t_trip`
- 修改行程：`UPDATE t_trip ... WHERE trip_code = ?`
- 删除行程：`DELETE FROM t_trip WHERE trip_code = ?`

### 通知中心

- 模板 CRUD：`t_notification_template`
- 规则 CRUD：`t_notification_rule + t_notification_rule_channel`
- 发送记录查询：`t_notification_task + t_notification_attempt`

## 4. 初始化方式

```bash
mysql -h <host> -u <user> -p <db_name> < docs/mysql_schema_seed.sql
```

脚本已经包含：
- 建表 DDL
- 示例 trips
- 你提供流程表对应的 10 条 lifecycle 数据
- 默认通知模板、规则、渠道与发送记录样例
