# 今日工作台 / 行程执行 / 通知作业台 API 契约草案（联调版）

> Last updated: 2026-04-23 (UTC)
> Status: Draft for frontend-backend integration
> Base path: `/api`

## 1. 通用响应

### 1.1 成功

```json
{
  "code": 200,
  "data": {}
}
```

### 1.2 失败

```json
{
  "code": 400,
  "error": "message"
}
```

## 2. 今日工作台

## 2.1 获取今日总览

- `GET /api/workbench/today/overview`
- Query:
  - `date` (optional, `YYYY-MM-DD`)
  - `owner_scope` (optional, `mine|all`)

### Response `200`

```json
{
  "code": 200,
  "data": {
    "date": "2026-04-23",
    "timezone": "Asia/Shanghai",
    "pending_tasks": 24,
    "overdue_tasks": 5,
    "risky_trips": 3,
    "pending_takeovers": 2
  }
}
```

## 2.2 获取待我处理清单

- `GET /api/workbench/today/action-items`
- Query:
  - `limit` (optional, default `20`)
  - `owner_scope` (optional, `mine|all`)

### Response `200`

```json
{
  "code": 200,
  "data": {
    "items": [
      {
        "id": "task_123",
        "trip_id": "trip_a",
        "trip_name": "乌鲁木齐-喀纳斯精品线",
        "team_id": "TEAM-DEMO-PRE",
        "stage": "pre_trip_t1",
        "node_key": "pre_trip_t1_insurance_check",
        "title": "出发前1天保险核查",
        "due_at": "2026-04-23T09:30:00Z",
        "owner_role": "concierge",
        "owner_name": "张三",
        "priority": "p0",
        "risk_level": "high",
        "status": "overdue"
      }
    ]
  }
}
```

## 3. 行程执行列表与详情

## 3.1 获取行程执行列表

- `GET /api/trips/execution`
- Query:
  - `owner_scope` (`mine|all`)
  - `stage` (optional)
  - `risk_level` (optional)
  - `date` (optional)

### Response `200`

```json
{
  "code": 200,
  "data": {
    "items": [
      {
        "trip_id": "trip_a",
        "team_id": "TEAM-DEMO-PRE",
        "trip_name": "乌鲁木齐-喀纳斯精品线",
        "current_stage": "pre_trip_t1",
        "todo_count": 2,
        "total_count": 5,
        "next_node_due_at": "2026-04-23T10:00:00Z",
        "risk_level": "high",
        "dispatch_status": "pending",
        "owner_name": "张三",
        "overdue_minutes": 30
      }
    ]
  }
}
```

## 3.2 获取团执行详情

- `GET /api/trips/{trip_id}/execution`

### Response `200`

```json
{
  "code": 200,
  "data": {
    "trip_id": "trip_a",
    "team_id": "TEAM-DEMO-PRE",
    "trip_name": "乌鲁木齐-喀纳斯精品线",
    "current_stage": "pre_trip_t1",
    "today_total": 5,
    "today_done": 2,
    "risk_level": "high",
    "next_dispatch_at": "2026-04-23T10:00:00Z",
    "tasks": [
      {
        "task_id": "task_123",
        "title": "监督司导发送出发前1天提醒",
        "stage": "pre_trip_t1",
        "node_key": "pre_trip_t1_driver_briefing",
        "due_at": "2026-04-23T09:00:00Z",
        "status": "overdue",
        "owner_role": "concierge",
        "owner_name": "张三",
        "evidence_required": true,
        "dispatch_id": "dispatch_001"
      }
    ]
  }
}
```

## 4. 通知作业台（发送、重试、接管）

## 4.1 发送前预览

- `POST /api/notifications/dispatch/preview`

### Request

```json
{
  "trip_id": "trip_a",
  "node_key": "daily_morning",
  "channel": "sms",
  "channel_code": "sms",
  "template_id": "tpl_001"
}
```

### Response `200`

```json
{
  "code": 200,
  "data": {
    "trip_id": "trip_a",
    "node_key": "daily_morning",
    "channel": "sms",
    "template_id": "tpl_001",
    "content": "亲爱的游客朋友们早上好...",
    "variable_check": {
      "ok": true,
      "missing_fields": []
    }
  }
}
```

## 4.2 立即发送

- `POST /api/notifications/dispatch`

### Request

```json
{
  "trip_id": "trip_a",
  "node_key": "daily_morning",
  "channel": "sms",
  "channel_code": "sms",
  "template_id": "tpl_001",
  "content": "..."
}
```

### Response `200`

```json
{
  "code": 200,
  "data": {
    "ok": true,
    "status": "sent",
    "message": "dispatch sent",
    "task_id": "task_123",
    "dispatch_id": "dispatch_001"
  }
}
```

## 4.3 失败重试

- `POST /api/notifications/dispatch/{dispatch_id}/retry`

### Request

```json
{
  "reason": "manual retry from workbench"
}
```

### Response `200`

```json
{
  "code": 200,
  "data": {
    "ok": true,
    "status": "retrying",
    "message": "dispatch retry accepted",
    "task_id": "task_123",
    "dispatch_id": "dispatch_001"
  }
}
```

## 4.4 人工接管分配

- `POST /api/workbench/takeovers`

### Request

```json
{
  "task_id": "task_123",
  "assignee_user_id": "u_2001",
  "assignee_name": "李四",
  "deadline_at": "2026-04-23T11:30:00Z",
  "note": "渠道连续失败，人工接管"
}
```

### Response `200`

```json
{
  "code": 200,
  "data": {
    "ok": true,
    "status": "handover_in_progress",
    "message": "takeover assigned",
    "task_id": "task_123",
    "dispatch_id": "dispatch_001"
  }
}
```

## 4.5 完成并留痕

- `POST /api/workbench/tasks/{task_id}/complete`

### Request

```json
{
  "result_note": "已电话确认司导执行",
  "evidence_type": "receipt",
  "evidence_ref": "receipt_789"
}
```

### Response `200`

```json
{
  "code": 200,
  "data": {
    "ok": true,
    "status": "done",
    "message": "task completed",
    "task_id": "task_123",
    "dispatch_id": "dispatch_001"
  }
}
```

## 4.6 催办

- `POST /api/workbench/tasks/{task_id}/nudge`

### Request

```json
{
  "target_role": "guide",
  "message": "请在10分钟内完成发送并回执"
}
```

### Response `200`

```json
{
  "code": 200,
  "data": {
    "ok": true,
    "status": "nudged",
    "message": "nudge sent",
    "task_id": "task_123",
    "dispatch_id": "dispatch_001"
  }
}
```

## 5. 状态枚举（联调）

- `risk_level`: `low|medium|high|critical|unknown`
- `priority`: `p0|p1|p2|unknown`
- `task.status`: `todo|in_progress|blocked|overdue|done|handover_in_progress|unknown`
- `dispatch.status`: `pending|sending|sent|failed|retrying|manual_intervention|unknown`

## 6. 按钮到接口映射（前端执行清单）

- `开始执行` -> `GET /api/trips/{trip_id}/execution`
- `一键发送当前节点` -> `POST /api/notifications/dispatch/preview` -> `POST /api/notifications/dispatch`
- `一键补发` -> `POST /api/notifications/dispatch/{dispatch_id}/retry`
- `人工接管` -> `POST /api/workbench/takeovers`
- `完成并留痕` -> `POST /api/workbench/tasks/{task_id}/complete`
- `催办` -> `POST /api/workbench/tasks/{task_id}/nudge`
