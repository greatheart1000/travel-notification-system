# API Integration Guide

> Last updated: 2026-04-11 (Asia/Shanghai)
> Source of truth: `docs/api-contract.md` + `src/app/api/http.py`

## 1. 前后端启动方式

### 1.1 一键启动（推荐）

在仓库根目录执行：

```bash
python dev-server.py up
```

该命令会：
- 启动后端：`python -m app.main`（监听 `127.0.0.1:8000`）
- 启动前端：`frontend/start.sh dev --skip-api-check`（Vite 默认 `127.0.0.1:5173`）

### 1.2 分开启动

后端（根目录）：

```bash
PYTHONPATH=src python -m app.main
```

前端（`frontend/` 目录）：

```bash
./start.sh dev
```

## 2. 健康检查

### 后端健康检查

```bash
python dev-server.py health
# 或
curl -fsS http://127.0.0.1:8000/api/health
```

预期：HTTP `200`，JSON 中 `code=200` 且 `data.status=ok`。

### 前端脚本内健康检查

```bash
cd frontend
./start.sh health
```

## 3. 推荐测试命令

### 3.0 统一状态块（2026-04-11）

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
- 最小联调命令（可直接复制执行）：
```bash
python dev-server.py health
python dev-server.py smoke --spawn-backend
python dev-server.py verify
```

### team/team_id 兼容过渡期说明（统一口径）

- 现状：接口字段仍存在 `team` 与 `team_id` 并存。
- 过渡期写入：前端/联调请求优先使用 `team_id`，并在兼容阶段同时携带 `team`。
- 过渡期读取：若响应仅返回 `team`，客户端在适配层映射为 `team_id` 后再进入业务逻辑。
- 退出条件：后端完成 `team_id` 统一并发布后，移除 `team` 兼容写入与映射逻辑。


### 3.1 最小联调校验（优先）

```bash
python dev-server.py verify
```

该命令默认只做最小 smoke 校验，确保主链路可运行。

### 3.2 契约测试（HTTP API）

```bash
python -m pytest -q tests/test_http_api.py
```

### 3.3 关键链路验证（领域流程）

```bash
python -m pytest -q \
  tests/test_bootstrap.py \
  tests/test_notification_pipeline.py \
  tests/test_trigger_and_audit.py \
  tests/test_lifecycle_rule_builder.py \
  tests/test_concierge_playbook.py
```

### 3.4 Smoke 测试（真实 HTTP）

```bash
python dev-server.py smoke --spawn-backend
```

### 3.5 一键验证（含全量测试）

```bash
python dev-server.py verify --full-tests
```

该命令执行顺序：
1. smoke 校验（自动拉起 backend，如需）
2. 契约测试 `tests/test_http_api.py`
3. 关键链路测试（5 个核心测试文件）

## 4. 前端 API 接入说明

- 前端 API 客户端：`frontend/src/services/api.ts`
- 基础地址：`/api`
- Vite 代理：`frontend/vite.config.ts` 将 `/api` 转发到 `http://localhost:8000/api`
- Token 存储：`localStorage.access_token`

当前已接入的页面/模块调用：
- 认证：`/auth/login`, `/auth/logout`, `/auth/refresh`, `/users/me`
- 仪表盘：`/dashboard/stats`, `/notifications/recent`
- 行程：`/trips`, `/trips/{id}`
- 通知：`/notifications/templates`, `/notifications/send`
- 分析：`/analytics/metrics`

未接入后端：
- Preferences 页面（本地状态，未调用 `/api/preferences`）

## 5. 接口契约对齐原则

- 真实行为以 `src/app/api/http.py` 为准。
- 文档基线以 `docs/api-contract.md` 为准。
- 任何接口变更必须同时更新：
  1. `src/app/api/http.py`
  2. `tests/test_http_api.py`
  3. `docs/api-contract.md`

## 6. 测试边界（防子目录污染）

`pyproject.toml` 中已固定：
- `testpaths = ["tests"]`
- `norecursedirs` 包含 `everything-claude-code`

因此在仓库根目录执行 `python -m pytest` 时，仅收集仓库业务测试，不扫描 `everything-claude-code` 子目录。
