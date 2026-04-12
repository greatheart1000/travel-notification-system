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

## 健康检查

```bash
python dev-server.py health
# 或
curl -fsS http://127.0.0.1:8000/api/health
```

## 统一状态块（2026-04-11）

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
