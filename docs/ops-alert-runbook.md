# Ops Alert Runbook（MVP）

## 1. 告警目标

本手册覆盖 Batch 2 Week 2 的三类核心告警：

1. **5 分钟通知失败率超阈值**
2. **异步队列堆积超阈值**
3. **人工接管率异常上升**

## 2. 指标与阈值建议

| 告警名 | 指标 | 建议阈值 | 观察窗口 |
|---|---|---:|---|
| notification_failure_burst_5m | `error_burst_5m` | `>= 20` | 5m |
| notification_queue_backlog_high | `queue_backlog` | `>= 100` | 10m |
| manual_takeover_rate_spike | `notification_manual_takeover_rate` | `>= 5%` | 15m |

## 3. 统一排障流程

1. 访问 `/api/health/detail`，确认 `queue_backlog / oldest_pending_job_age / error_burst_5m`。
2. 访问 `/api/notifications/jobs`，按租户筛选 `retrying/manual_intervention` 任务。
3. 访问 `/api/notifications/history`，定位高失败渠道与错误码。
4. 若失败集中于单渠道：切换 fallback（SMS ↔ 企业微信）并降频。
5. 若失败跨渠道且持续：升级值班负责人，转人工接管。

## 4. 告警剧本

### 4.1 5 分钟失败率超阈值

- **可能原因**：外部通道故障、模板参数缺失、限流。
- **立即动作**：
  - 暂停非必发通知。
  - 触发重试任务（`/api/notifications/jobs/run`）。
  - 检查最新错误集中在 `task_not_found` 还是 `send_failed`。
- **升级条件**：持续 15 分钟未恢复。

### 4.2 队列堆积超阈值

- **可能原因**：消费者未执行、下游响应慢、重试风暴。
- **立即动作**：
  - 确认运行器是否存活。
  - 根据 `oldest_pending_job_age` 判断是否出现饿死任务。
  - 临时降低新入队速率，优先清理历史积压。

### 4.3 人工接管率异常上升

- **可能原因**：重试上限过低、模板或规则发布异常、渠道持续抖动。
- **立即动作**：
  - 拉取 `manual_intervention` 任务清单并按租户分桶。
  - 让客服/管家按高优先级租户先行手动发送。
  - 回看最近规则发布记录，必要时回滚到上一个稳定版本。

## 5. 复盘要求

每次告警关闭后 24 小时内输出复盘，至少包含：

- 事件时间线（开始/发现/缓解/恢复）。
- 影响范围（租户、任务量、漏发量）。
- 根因与证据。
- 永久修复项（代码、阈值、值班流程）。
