# 新疆行程管家服务流程数字化

本仓库是“行程通知与管家流程”项目的 MVP 后端与前端联调工程。

## 模块概览

- `notification`：通知编排与发送任务（短信主渠道、企业微信群兜底）
- `trigger`：必发节点与条件触发规则引擎
- `complaint`：投诉/负面情绪识别与升级
- `integration`：外部系统接口抽象（易途、天气）
- `audit`：关键操作审计日志
- `survey`：满意度回收与低分自动跟进
- `services/lifecycle_rule_builder.py`：生命周期规则草案生成

## 目录结构

```text
src/app/
  core/
  api/
  modules/
  services/
frontend/
tests/
docs/
```

## 本地环境准备

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

> 说明：`python-multipart` 已纳入项目依赖，无需额外手工安装，可直接用于 `/api/trips/import` 等上传接口。

前端依赖（首次）：

```bash
cd frontend
npm install
cd ..
```

## 启动方式

后端：

```bash
TRAVEL_NOTIFICATION_CORS_ORIGINS=http://127.0.0.1:4180 \
PYTHONPATH=src python -m uvicorn app.api.http:app --host 127.0.0.1 --port 18000
```

前端：

```bash
cd frontend
npm run build
cd ..
python scripts/frontend_proxy_server.py \
  --host 127.0.0.1 \
  --port 4180 \
  --backend http://127.0.0.1:18000 \
  --static-dir frontend/dist
```

## 部署命令（前后端）

当前推荐部署端口：
- backend: `18000`
- frontend: `4180`（通过本地代理转发 `/api/*` 到 backend）

### 生产构建前端

```bash
npm -C frontend run build
```

### 启动后端（端口 18000）

```bash
TRAVEL_NOTIFICATION_CORS_ORIGINS=http://127.0.0.1:4180 \
PYTHONPATH=src python -m uvicorn app.api.http:app --host 127.0.0.1 --port 18000
```

> `TRAVEL_NOTIFICATION_CORS_ORIGINS` 支持逗号分隔多个来源（例如 `http://127.0.0.1:4180,http://localhost:5173`）。

### 启动前端代理（端口 4180）

```bash
python scripts/frontend_proxy_server.py \
  --host 127.0.0.1 \
  --port 4180 \
  --backend http://127.0.0.1:18000 \
  --static-dir frontend/dist
```

### 部署后检查

```bash
curl -fsS http://127.0.0.1:18000/api/health
curl -fsS -X POST http://127.0.0.1:4180/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"123456"}'
```

访问地址：
- 前端登录页：`http://127.0.0.1:4180`

## 健康检查

```bash
curl -fsS http://127.0.0.1:18000/api/health
```

## 统一状态块（2026-04-12）

- `/api/health` 运行时验证：以直接 HTTP 健康检查为准
- `/api/notifications/rules*` 端点现状：已实现并可鉴权访问（见 `docs/api-contract.md`）
- 当前 blocker（命令级）：无
- 本地执行观察（2026-05-10）：后端 `uvicorn` 启动与 `python -m pytest -q` 为当前主验证方式。
- 当前剩余阻塞（rules 联调内容级）：
  1. `rules` 端点已纳入 `tests/test_http_api.py`（`test_notification_rules_contract_smoke`）。
  2. 前端规则阶段枚举与后端规范值仍有收敛空间（后端规范：`pre_trip|in_trip|post_trip`）。
  3. `stage/time_slot/scene` 的别名输入策略尚未冻结为团队统一规范。
- 临时绕行（仅当 backend 再次启动失败时）：
  1. `python -m pytest -q tests/test_http_api.py`
  2. 单独启动 backend 后执行 `curl -fsS http://127.0.0.1:18000/api/health`
- 当前可运行命令（已验证）：
  - `python -m pytest -q`
  - `python -m pytest -q tests/test_http_api.py`
  - `curl -fsS http://127.0.0.1:18000/api/health`
  - `npm -C frontend run build`
- 恢复步骤（统一）：
  1. backend rules 契约收口完成（以 `docs/api-contract.md` 为准）。
  2. frontend rules smoke：执行下方 `rules 最小 smoke 命令链`。
  3. integration verify：`python -m pytest -q tests/test_http_api.py`
  4. integration full verify：`python -m pytest -q`（收尾）
- 阶段边界：实现优先 + 最小验证，综合回归 deferred（待 rules 用例纳入最小默认回归后执行）。
- 最小联调命令（可直接复制执行）：
```bash
curl -fsS http://127.0.0.1:18000/api/health
python -m pytest -q tests/test_http_api.py
```

- rules 最小 smoke 命令链（可直接复制执行）：
```bash
TOKEN=$(curl -fsS -X POST http://127.0.0.1:18000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"123456"}' \
  | python -c 'import sys,json;print(json.load(sys.stdin)["data"]["access_token"])')

curl -fsS "http://127.0.0.1:18000/api/notifications/rules?stage=pre_trip&time_slot=morning&scene=normal" \
  -H "Authorization: Bearer ${TOKEN}"

curl -sS -w '\nHTTP_STATUS:%{http_code}\n' -X POST http://127.0.0.1:18000/api/notifications/rules \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer ${TOKEN}" \
  -d '{"name":"smoke-rule","stage":"pre_trip","time_slot":"morning","scene":"normal","channels":["sms"],"enabled":true,"priority":100}'
```

### team/team_id 兼容过渡期说明（统一口径）

- 现状：接口字段仍存在 `team` 与 `team_id` 并存。
- 过渡期写入：前端/联调请求优先使用 `team_id`，并在兼容阶段同时携带 `team`。
- 过渡期读取：若响应仅返回 `team`，客户端在适配层映射为 `team_id` 后再进入业务逻辑。
- 退出条件：后端完成 `team_id` 统一并发布后，移除 `team` 兼容写入与映射逻辑。


## 推荐测试命令

### 最小联调校验（推荐先跑）

```bash
python -m pytest -q tests/test_http_api.py
```

### 契约测试（可选，主链路通后再跑）

```bash
python -m pytest -q tests/test_http_api.py
```

### 关键链路验证（可选，主链路通后再跑）

```bash
python -m pytest -q \
  tests/test_bootstrap.py \
  tests/test_notification_pipeline.py \
  tests/test_trigger_and_audit.py \
  tests/test_lifecycle_rule_builder.py \
  tests/test_concierge_playbook.py
```

### Smoke 测试（真实 HTTP）

```bash
curl -fsS http://127.0.0.1:18000/api/health
```

### 联调收尾（含全量测试）

```bash
python -m pytest -q
```

## API 与联调文档

- 契约文档：`docs/api-contract.md`
- 联调指南：`API_INTEGRATION.md`
- 连通性报告：`docs/api_connectivity_report.md`
- 上线/联调 Runbook：`docs/api_connectivity_runbook.md`
- 联调交接执行清单：`docs/api_connectivity_runbook.md`（章节：`7. 联调交接执行清单`）
- Batch 2 两周迭代任务单（RBAC/异步重试/可观测/审批流）：`docs/batch2-two-week-iteration-plan.md`
- MySQL 表结构与种子数据：`docs/mysql_schema_seed.sql`
- MySQL 设计说明：`docs/mysql-table-design.md`

## 测试边界说明

`pyproject.toml` 已设置 `testpaths = ["tests"]`，并排除 `everything-claude-code` 子目录，避免非本项目测试被误收集。
