# API 联调 / 上线 Runbook

> Last updated: 2026-04-11 (Asia/Shanghai)
> Scope: `travel-notification-system` 本地联调、回归、问题定位与数据修复建议

## 1. 启动

### 1.1 环境准备

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .

cd frontend
npm install
cd ..
```

### 1.2 一键启动（推荐）

```bash
python dev-server.py up
```

服务地址：
- Backend: `http://127.0.0.1:8000`
- Frontend: `http://127.0.0.1:5173`

### 1.3 分开启动

后端：

```bash
PYTHONPATH=src python -m app.main
```

前端：

```bash
cd frontend
./start.sh dev
```

### 1.4 健康检查

```bash
python dev-server.py health
```

或：

```bash
curl -fsS http://127.0.0.1:8000/api/health
```

## 2. 回归验证

### 2.0 统一状态块（2026-04-11）

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


### 2.1 一键最小回归（推荐先跑）

```bash
python dev-server.py verify
```

包含：
1. smoke：真实 HTTP 调用 `/health`、认证、行程、通知、分析接口

### 2.2 全量回归（主链路通后执行）

```bash
python dev-server.py verify --full-tests
```

包含：
1. smoke
2. 契约测试：`tests/test_http_api.py`
3. 关键链路：`test_bootstrap/test_notification_pipeline/test_trigger_and_audit/test_lifecycle_rule_builder/test_concierge_playbook`

### 2.3 分步回归

契约测试：

```bash
python -m pytest -q tests/test_http_api.py
```

关键链路：

```bash
python -m pytest -q \
  tests/test_bootstrap.py \
  tests/test_notification_pipeline.py \
  tests/test_trigger_and_audit.py \
  tests/test_lifecycle_rule_builder.py \
  tests/test_concierge_playbook.py
```

smoke：

```bash
python dev-server.py smoke --spawn-backend
```

## 3. 常见故障定位

### 3.1 `backend unreachable` / health 失败

排查：
1. 确认 backend 是否启动：`PYTHONPATH=src python -m app.main`
2. 检查端口占用：`8000` 是否被其他进程占用
3. 检查 Python 环境是否安装本项目：`python -m pip install -e .`

### 3.2 前端能打开但 API 全失败

排查：
1. 确认 Vite 代理配置：`frontend/vite.config.ts`
2. 确认 backend 地址为 `http://localhost:8000`
3. 前端执行 `./start.sh health`

### 3.3 `401 Invalid token`

排查：
1. 先调用 `POST /api/auth/login` 获取新 token
2. 确认请求头格式：`Authorization: Bearer <token>`
3. 本地存储残留旧 token 时，清理前端 `localStorage.access_token`

### 3.4 pytest 收集到非项目测试

排查：
1. 确认在仓库根执行 `python -m pytest`
2. 确认 `pyproject.toml` 包含：
   - `testpaths = ["tests"]`
   - `norecursedirs` 含 `everything-claude-code`

## 4. 数据修复建议（当前为内存存储 MVP）

当前后端使用 `InMemoryStore`，重启即重置。联调阶段的数据修复建议：

1. 异常脏数据（如 trip 字段缺失）直接重启服务，回到初始数据。
2. 需要复现实例数据时，使用 API 重新创建：
   - `POST /api/trips`
   - `POST /api/notifications/send`
3. 需要清理登录态异常时，重启 backend 或重新登录获取 token。
4. 若后续接数据库，建议增加：
   - 幂等修复脚本（按业务键 upsert）
   - 数据回滚脚本（按批次/时间窗口）
   - 校验脚本（必填字段和枚举一致性）

## 5. 已知限制

1. 后端是 `http.server` MVP，并非 FastAPI/OpenAPI 形态。
2. `Preferences` 页面未接后端，`/api/preferences` 未实现。
3. Trips 当前使用字段 `team`，尚未迁移为 `team_id`。
4. 状态/渠道存在中文展示值与机器枚举并存问题，需后续统一。
5. 数据为内存态，重启即丢失，不适合生产。

## 6. 联调收尾出口标准（建议）

满足以下条件可判定“本轮联调完成”：
1. `python dev-server.py verify` 全通过
2. 前端关键页面（Dashboard/Trips/Notifications/Analytics）接口可用
3. `docs/api-contract.md` 与实现一致
4. 本 Runbook 与 `docs/api_connectivity_report.md` 已更新到同一日期

## 7. 联调交接执行清单

本清单直接引用本文件 `2.0 统一状态块` 与其中 `恢复步骤（统一）`，不引入第二套口径。

### 7.0 当前交接状态（2026-04-11）

1. Backend：契约基线已稳定，`python -m pytest -q tests/test_http_api.py` 可执行；剩余待收口项为 `/api/preferences`、`team/team_id`、枚举统一。
2. Frontend：可执行 smoke 路径（`python dev-server.py smoke --spawn-backend`）；Preferences 仍等待后端接口落地后切换。
3. Integration：`python dev-server.py verify` 与 `python dev-server.py verify --full-tests` 已验证可跑，当前可进入交接并行推进。

### 7.1 Backend 执行清单

前置条件：
1. 已确认 `docs/api-contract.md` 为契约基线。
2. 已确认当前内容级阻塞项：`/api/preferences`、`team/team_id`、枚举统一。

执行步骤：
1. 完成 `/api/preferences`（GET/PUT）最小可用契约实现并对齐文档。
2. 按 `team/team_id 兼容过渡期说明（统一口径）` 落地兼容策略。
3. 统一状态与渠道枚举返回口径，并同步 `docs/api-contract.md`。
4. 运行 `python -m pytest -q tests/test_http_api.py` 做契约回归。

成功判据：
1. 契约测试通过。
2. `docs/api-contract.md` 已反映最新行为。
3. 阻塞项数量减少且在 `2.0 统一状态块` 中可追踪。

### 7.2 Frontend 执行清单

前置条件：
1. 已读取 `2.0 统一状态块` 与 `team/team_id 兼容过渡期说明（统一口径）`。
2. 本地可执行 `python dev-server.py smoke --spawn-backend`。

执行步骤：
1. 通过适配层兼容 `team`/`team_id` 过渡期读写。
2. 将 `Preferences` 页面由本地状态改为调用后端接口（待 backend 提供后切换）。
3. 运行 frontend smoke：`python dev-server.py smoke --spawn-backend`。
4. 页面联调验证 Dashboard/Trips/Notifications/Analytics 主路径。

成功判据：
1. frontend smoke 通过。
2. 核心页面无因契约字段变更导致的阻断错误。
3. 前端口径与 `docs/api-contract.md` 一致。

### 7.3 Integration 执行清单

前置条件：
1. Backend/Frontend 变更已合并到当前联调分支。
2. 四份联调文档状态矩阵已一致：`README.md`、`API_INTEGRATION.md`、`docs/api_connectivity_report.md`、`docs/api_connectivity_runbook.md`。

执行步骤：
1. 按统一恢复顺序执行：
   1. backend 契约收口完成。
   2. frontend smoke：`python dev-server.py smoke --spawn-backend`
   3. integration verify：`python dev-server.py verify`
   4. integration full verify：`python dev-server.py verify --full-tests`
2. 将验证结果回填到 `docs/api_connectivity_report.md`（仅更新事实，不新增口径）。
3. 对照 `2.0 统一状态块` 更新剩余阻塞项状态。

成功判据：
1. `python dev-server.py verify --full-tests` 通过。
2. 报告、Runbook、README、API_INTEGRATION 的状态矩阵保持一致。
3. 交接方可按同一命令集完成复现与回归。
