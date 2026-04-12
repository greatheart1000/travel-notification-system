# API Contract (Source of Truth)

> Last updated: 2026-04-11 (Asia/Shanghai)
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

### Error envelope

```json
{
  "code": 400,
  "error": "message"
}
```

### Auth

- Header: `Authorization: Bearer <access_token>`
- 当前严格鉴权接口：`GET /api/users/me`
- 其他接口在 MVP 阶段默认开放

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
  - `400`: `refresh_token is required`
- `GET /api/users/me`
  - 需有效 Bearer token
  - `200`: 用户信息
  - `401`: `Invalid token`

### Dashboard

- `GET /api/dashboard/stats`
- `200`: `today_notifications`, `active_trips`, `total_users`, `pending_complaints`, `notification_success_rate`

### Trips

- `GET /api/trips`
  - `200`: `data.total`, `data.items[]`
- `POST /api/trips`
  - required: `destination`, `team`, `start_date`, `end_date`
  - optional: `participants`, `status`
  - `200`: 创建后的 trip
  - `400`: 缺少必填字段
- `PUT /api/trips/{trip_id}`
  - partial update（当前实现为 merge）
  - `200`: 更新后的 trip
  - `404`: `Trip not found`
- `DELETE /api/trips/{trip_id}`
  - `200`: `{ "code": 200 }`
  - `404`: `Trip not found`

### Notifications

- `GET /api/notifications/templates`
  - `200`: 模板列表
- `POST /api/notifications/send`
  - 可传：`template_id`, `customer_name`, `trip`, `channel`
  - `200`: `ok=true`, `notification_id`
  - `404`: 模板不存在时 `Template not found`
- `GET /api/notifications/recent?limit=10`
  - `limit` 可选，不合法时回退到 `10`
  - `200`: 最近通知列表

### Analytics

- `GET /api/analytics/metrics`
- `200`: `metrics`, `channel_performance`, `top_trips`

## Known Gap (Frontend vs Backend)

- Preferences 页面仍为本地状态，后端尚未实现：
  - `GET /api/preferences`
  - `PUT /api/preferences`

## Verification Matrix

### 统一状态矩阵引用（2026-04-11）

> 本节与 `docs/api_connectivity_report.md`、`docs/api_connectivity_runbook.md`、`README.md`、`API_INTEGRATION.md` 保持同口径。

- `/api/health` 运行时验证：已通过（`python dev-server.py verify` smoke 链路）
- 当前 blocker（命令级）：无
- 当前剩余阻塞（联调内容级）：
  1. `/api/preferences`（GET/PUT）尚未实现，Preferences 页面仍是本地状态。
  2. `team` / `team_id` 字段未统一。
  3. 状态与渠道枚举（中英文/代码值）未统一。
- 临时绕行（仅当 backend 再次启动失败时）：
  1. `python dev-server.py smoke --spawn-backend`
  2. `cd frontend && ./start.sh dev --skip-api-check`（前端继续开发）
  3. `python -m pytest -q tests/test_http_api.py`（后端先保契约）
- 当前可运行命令（已验证）：
  - `python dev-server.py --help`
  - `python dev-server.py health`（backend 运行时返回 OK；未启动时返回 unreachable 属预期）
  - `python dev-server.py smoke --spawn-backend`（含 `/api/health`）
  - `python dev-server.py verify`（含 `/api/health` 运行时校验）
  - `python dev-server.py verify --full-tests`
  - `bash frontend/start.sh --help`
  - `bash frontend/start.sh health`
- 恢复步骤（统一）：
  1. backend 契约收口完成（字段/枚举/`/api/preferences` 与 `docs/api-contract.md` 同步）。
  2. frontend smoke：`python dev-server.py smoke --spawn-backend`
  3. integration verify：`python dev-server.py verify`
  4. integration full verify：`python dev-server.py verify --full-tests`（收尾）

### Minimal unblock verification

```bash
python dev-server.py verify
```

默认执行 smoke，优先验证联调主链路可用。

### Contract tests

```bash
python -m pytest -q tests/test_http_api.py
```

覆盖：
- 认证流程（login -> users/me）
- trips CRUD
- dashboard/notifications/analytics 基础行为

### Smoke tests

```bash
python dev-server.py smoke --spawn-backend
```

覆盖：
- `/health`
- `/auth/login`
- `/users/me`
- `/trips`
- `/notifications/send`
- `/analytics/metrics`

### Key-path validation

```bash
python -m pytest -q \
  tests/test_bootstrap.py \
  tests/test_notification_pipeline.py \
  tests/test_trigger_and_audit.py \
  tests/test_lifecycle_rule_builder.py \
  tests/test_concierge_playbook.py
```

## Test Boundary Rule

为避免 `everything-claude-code` 子目录污染测试收集，仓库根 `pyproject.toml` 已固定：
- `testpaths = ["tests"]`
- `norecursedirs` 包含 `everything-claude-code`

后续统一在仓库根目录执行：

```bash
python -m pytest
```
