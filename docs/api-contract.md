# API Contract (Source of Truth)

> Last updated: 2026-04-12 (Asia/Shanghai)
> Runtime source: `src/app/api/http.py`
> Contract test source: `tests/test_http_api.py`

## Scope

- Protocol: HTTP + JSON
- Base path: `/api`
- Runtime entry: `PYTHONPATH=src python -m app.main`

## Global Contract

### Success envelope

```json
{
  "code": 200,
  "data": {}
}
```

### Success envelope with message

```json
{
  "code": 200,
  "message": "rule created",
  "data": {}
}
```

### Error envelope

```json
{
  "code": 400,
  "error": "message"
}
```

### Auth

- Header: `Authorization: Bearer <access_token>`
- 登录/刷新无需 token：`POST /api/auth/login`, `POST /api/auth/refresh`
- `rules` 读接口需登录：`GET /api/notifications/rules*`
- `rules` 写接口需 admin：`POST|PUT|DELETE /api/notifications/rules*`

## Endpoint List

### Health

- `GET /api/health`
- `200`: `data.status = "ok"`

### Auth

- `POST /api/auth/login`
  - body: `username`, `password`
  - `200`: `access_token`, `refresh_token`, `token_type`, `expires_in`
  - `401`: `Invalid credentials`
- `POST /api/auth/logout`
  - `200`: `{ "code": 200 }`
- `POST /api/auth/refresh`
  - body: `refresh_token`
  - `200`: `access_token`, `expires_in`
  - `401`: `Invalid refresh token`
- `GET /api/users/me`
  - `200`: 用户信息
  - `401`: `Invalid token`

### Dashboard

- `GET /api/dashboard/stats`
- `200`: `today_notifications`, `active_trips`, `total_users`, `pending_complaints`, `notification_success_rate`

### Trips

- `GET /api/trips`
  - `200`: `data.total`, `data.items[]`
- `POST /api/trips`
  - required: `destination`, `team` or `team_id`, `start_date`, `end_date`
  - optional: `participants`, `status`
  - HTTP `201`: 返回创建结果（body 仍为 `code=200`）
  - `400`: 缺少必填字段
- `PUT /api/trips/{trip_id}`
  - partial update
  - `200`: 更新后的 trip
  - `404`: `Trip not found`
- `DELETE /api/trips/{trip_id}`
  - `200`: `{ "code": 200 }`
  - `404`: `Trip not found`

### Notifications

- `GET /api/notifications/templates`
  - `200`: 模板列表
- `POST /api/notifications/send`
  - 可传：`template_id`, `customer_name`, `trip`, `trip_id`, `channel`, `team`, `team_id`
  - `200`: `ok=true`, `notification_id`
  - `404`: 模板不存在时 `Template not found`
- `GET /api/notifications/recent?limit=10`
  - `limit` 可选，不合法时回退到 `10`
  - `200`: 最近通知列表

### Project Configs

- `GET /api/project-configs`
  - Auth: admin
  - `200`: `data.total`, `data.items[]`
- `GET /api/project-configs/{project_id}`
  - Auth: admin
  - `200`: 项目级天气/短信配置
  - `404`: `Project config not found`
- `PUT /api/project-configs/{project_id}`
  - Auth: admin
  - `200`: upsert 后的项目配置
  - 请求体支持：
    - `project_name`
    - `weather_enabled`
    - `qweather_credential_id`
    - `qweather_location_id`
    - `qweather_lat`
    - `qweather_lon`
    - `weather_alert_thresholds`
    - `sms_provider`
    - `sms_sign_name`
    - `sms_template_code_normal`
    - `sms_template_code_weather_alert`
    - `manual_takeover_target`

#### Rules V2 第一批（`/api/notifications/rules*`）

#### `GET /api/notifications/rules`

- Auth: 登录用户
- Query params:
  - `enabled`: `true|false`
  - `stage`: 见下方 `stage` 规范（支持别名）
  - `time_slot`: 见下方 `time_slot` 规范（支持别名）
  - `scene`: 见下方 `scene` 规范（支持别名）
- `200`:

```json
{
  "code": 200,
  "message": "rules listed",
  "data": {
    "total": 1,
    "items": [
      {
        "id": "rule-abc123",
        "name": "晨间常规提醒",
        "stage": "pre_trip",
        "time_slot": "morning",
        "scene": "normal",
        "channels": ["sms"],
        "template_id": null,
        "enabled": true,
        "priority": 100,
        "conditions": {},
        "created_at": "2026-04-12T01:00:00+00:00",
        "updated_at": "2026-04-12T01:00:00+00:00"
      }
    ]
  }
}
```

- `400`: 枚举值非法（例如 `Invalid stage: xxx`）
- `401`: `Invalid token`

#### `GET /api/notifications/rules/{rule_id}`

- Auth: 登录用户
- `200`: `message = "rule found"`
- `401`: `Invalid token`
- `404`: `Rule not found`

#### `POST /api/notifications/rules`

- Auth: admin
- HTTP status: `201`
- Request body:

```json
{
  "name": "晨间常规提醒",
  "stage": "pre_trip",
  "time_slot": "morning",
  "scene": "normal",
  "channels": ["sms"],
  "template_id": null,
  "enabled": true,
  "priority": 100,
  "conditions": {}
}
```

- `201`（body 仍为 `code=200`，`message="rule created"`）
- `400`: 业务校验失败（如枚举非法、channel 非法）
- `401`: `Invalid token`
- `403`: `Admin role required`
- `422`: 请求体缺失必填字段或类型错误

#### `PUT /api/notifications/rules/{rule_id}`

- Auth: admin
- HTTP status: `200`
- Request body: partial update（可传 `name/stage/time_slot/scene/channels/template_id/enabled/priority/conditions`）
- `200`: `message="rule updated"`
- `400`: 业务校验失败
- `401`: `Invalid token`
- `403`: `Admin role required`
- `404`: `Rule not found`
- `422`: 请求体类型错误

#### `DELETE /api/notifications/rules/{rule_id}`

- Auth: admin
- `200`: `message="rule deleted"`, `data.deleted=true`
- `401`: `Invalid token`
- `403`: `Admin role required`
- `404`: `Rule not found`

### Rules 枚举规范（canonical + alias）

别名兼容输入规则：
- 请求可传 canonical 或 alias（英文/中文），后端统一归一化为 canonical 并写入/返回 canonical。
- 归一化失败返回 `400`，错误形态：`{"code":400,"error":"Invalid <field>: <value>"}`。

#### `stage`

- Canonical: `pre_trip`, `in_trip`, `post_trip`
- Alias:
  - `pre_trip`: `before_departure`, `before`, `行前`
  - `in_trip`: `on_trip`, `during`, `行中`
  - `post_trip`: `after_trip`, `after`, `行后`

#### `time_slot`

- Canonical: `morning`, `afternoon`, `evening`, `night`, `all_day`
- Alias:
  - `morning`: `am`, `早间`
  - `afternoon`: `pm`, `午间`
  - `night`: `晚间`
  - `all_day`: `any`, `anytime`, `全天`

#### `scene`

- Canonical: `normal`, `weather_alert`, `delay`, `complaint`, `manual`
- Alias:
  - `normal`: `default`, `常规`
  - `weather_alert`: `weather`, `天气`
  - `delay`: `flight_delay`, `延误`
  - `complaint`: `投诉`
  - `manual`: `人工`

#### `channels`（rules payload）

- Canonical: `sms`, `wechat_work_group`, `email`
- Alias:
  - `sms`: `短信`
  - `wechat_work_group`: `wechat`, `企业微信`
  - `email`: `邮件`

### Analytics

- `GET /api/analytics/metrics`
- `200`: `metrics`, `channel_performance`, `top_trips`

## Known Gap (Rules Scope)

1. `rules` 端点已纳入 `tests/test_http_api.py`（`test_notification_rules_contract_smoke`），并在 `python dev-server.py verify --full-tests` 中执行；默认 `python dev-server.py verify`（最小 smoke）仍不覆盖 rules 契约。
2. 前端规则阶段枚举与后端规范值仍有收敛空间（后端规范：`pre_trip|in_trip|post_trip`）。
3. `stage/time_slot/scene` 的别名输入策略尚未冻结为团队统一规范。

## Verification Matrix

### 阶段边界

- 当前阶段：实现优先+最小验证
- 综合回归 deferred（待 rules 用例接入 `dev-server.py verify` 后执行）
- 本地执行观察（2026-04-12）：`python dev-server.py verify` 与 `python dev-server.py verify --full-tests` 均可完成，未出现超时/卡住。

### Minimal unblock verification

```bash
python dev-server.py verify
```

### Rules minimal smoke chain (copy-ready)

```bash
TOKEN=$(curl -fsS -X POST http://127.0.0.1:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"123456"}' \
  | python -c 'import sys,json;print(json.load(sys.stdin)["data"]["access_token"])')

curl -fsS "http://127.0.0.1:8000/api/notifications/rules?stage=pre_trip&time_slot=morning&scene=normal" \
  -H "Authorization: Bearer ${TOKEN}"

RULE_ID=$(curl -fsS -X POST http://127.0.0.1:8000/api/notifications/rules \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer ${TOKEN}" \
  -d '{"name":"smoke-rule","stage":"pre_trip","time_slot":"morning","scene":"normal","channels":["sms"],"enabled":true,"priority":100}' \
  | python -c 'import sys,json;print(json.load(sys.stdin)["data"]["id"])')

curl -fsS -X PUT "http://127.0.0.1:8000/api/notifications/rules/${RULE_ID}" \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer ${TOKEN}" \
  -d '{"enabled":false,"priority":120}'

curl -fsS -X DELETE "http://127.0.0.1:8000/api/notifications/rules/${RULE_ID}" \
  -H "Authorization: Bearer ${TOKEN}"
```

### Contract tests

```bash
python -m pytest -q tests/test_http_api.py
```

### Test Boundary Rule

为避免 `everything-claude-code` 子目录污染测试收集，仓库根 `pyproject.toml` 已固定：
- `testpaths = ["tests"]`
- `norecursedirs` 包含 `everything-claude-code`
