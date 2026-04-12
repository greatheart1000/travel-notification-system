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

前端依赖（首次）：

```bash
cd frontend
npm install
cd ..
```

## 启动方式

### 方式 A：一键联调启动（推荐）

```bash
python dev-server.py up
```

### 方式 B：分开启动

后端：

```bash
PYTHONPATH=src python -m app.main
```

前端：

```bash
cd frontend
./start.sh dev
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
PYTHONPATH=src python -m uvicorn app.api.http:app --host 127.0.0.1 --port 18000
```

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
python dev-server.py health
# 或
curl -fsS http://127.0.0.1:8000/api/health
```

## 统一状态块（2026-04-12）

- `/api/health` 运行时验证：已通过（`python dev-server.py verify` smoke 链路）
- `/api/notifications/rules*` 端点现状：已实现并可鉴权访问（见 `docs/api-contract.md`）
- 当前 blocker（命令级）：无
- 本地执行观察（2026-04-12）：`python dev-server.py verify` 与 `python dev-server.py verify --full-tests` 均可完成，未出现超时/卡住。
- 当前剩余阻塞（rules 联调内容级）：
  1. `rules` 端点已纳入 `tests/test_http_api.py`（`test_notification_rules_contract_smoke`），并在 `python dev-server.py verify --full-tests` 中执行；默认 `python dev-server.py verify`（最小 smoke）仍不覆盖 rules 契约。
  2. 前端规则阶段枚举与后端规范值仍有收敛空间（后端规范：`pre_trip|in_trip|post_trip`）。
  3. `stage/time_slot/scene` 的别名输入策略尚未冻结为团队统一规范。
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
  1. backend rules 契约收口完成（以 `docs/api-contract.md` 为准）。
  2. frontend rules smoke：执行下方 `rules 最小 smoke 命令链`。
  3. integration verify：`python dev-server.py verify`
  4. integration full verify：`python dev-server.py verify --full-tests`（收尾）
- 阶段边界：实现优先 + 最小验证，综合回归 deferred（待 rules 用例接入 `dev-server.py verify` 后执行）。
- 最小联调命令（可直接复制执行）：
```bash
python dev-server.py health
python dev-server.py smoke --spawn-backend
python dev-server.py verify
```

- rules 最小 smoke 命令链（可直接复制执行）：
```bash
TOKEN=$(curl -fsS -X POST http://127.0.0.1:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"123456"}' \
  | python -c 'import sys,json;print(json.load(sys.stdin)["data"]["access_token"])')

curl -fsS "http://127.0.0.1:8000/api/notifications/rules?stage=pre_trip&time_slot=morning&scene=normal" \
  -H "Authorization: Bearer ${TOKEN}"

curl -sS -w '\nHTTP_STATUS:%{http_code}\n' -X POST http://127.0.0.1:8000/api/notifications/rules \
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
python dev-server.py verify
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
python dev-server.py smoke --spawn-backend
```

### 联调收尾（含全量测试）

```bash
python dev-server.py verify --full-tests
```

## API 与联调文档

- 契约文档：`docs/api-contract.md`
- 联调指南：`API_INTEGRATION.md`
- 连通性报告：`docs/api_connectivity_report.md`
- 上线/联调 Runbook：`docs/api_connectivity_runbook.md`
- 联调交接执行清单：`docs/api_connectivity_runbook.md`（章节：`7. 联调交接执行清单`）

## 测试边界说明

`pyproject.toml` 已设置 `testpaths = ["tests"]`，并排除 `everything-claude-code` 子目录，避免非本项目测试被误收集。
