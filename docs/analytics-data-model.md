# 数据分析表结构设计（MVP）

> 适用于当前 `JsonFileStore` 持久化方案，按“逻辑数据表”进行建模。

## 1) 通知事实表 `analytics_notification_facts`

| 字段 | 类型 | 说明 |
|---|---|---|
| `event_id` | string | 事件主键 |
| `event_date` | date | 发送日期（用于趋势统计） |
| `trip_id` | string | 关联行程 |
| `team_id` | string | 关联团队 |
| `channel` | string | 渠道：`sms` / `wechat_work_group` / `email` |
| `success` | boolean | 是否成功 |
| `latency_ms` | int | 响应延迟（毫秒） |

## 2) 行程维度表 `analytics_trip_dimensions`

| 字段 | 类型 | 说明 |
|---|---|---|
| `trip_id` | string | 行程主键 |
| `trip_name` | string | 展示名称 |
| `destination` | string | 目的地 |

## 3) 满意度事实表 `analytics_trip_feedbacks`

| 字段 | 类型 | 说明 |
|---|---|---|
| `feedback_id` | string | 反馈主键 |
| `trip_id` | string | 关联行程 |
| `score` | float | 满意度评分（0~5） |
| `submitted_on` | date | 提交日期 |

## 派生分析指标

后端 `AnalyticsService` 基于以上三张逻辑表输出：

- `metrics`
  - `notification_success_rate`
  - `avg_response_time`
  - `wow_growth`
  - `user_satisfaction`
- `channel_performance`
- `top_trips`

## 种子数据策略

当 `analytics_notification_facts` 为空时：

1. 先尝试从 `notification_attempts` 自动抽取事实数据；
2. 如果仍为空，自动写入最小可分析样本数据（3个行程、3个渠道、3条满意度记录）。

这样可确保“数据分析”页面不再长期显示空状态，支持快速联调和演示。
