# 前后端联调连通性报告

> 更新时间：2026-04-11（Asia/Shanghai）
> 检查范围：`dev-server.py`、`frontend/start.sh`、`src/app/api/http.py`、`tests/`

## 1) 当前结论（最新）

- 当前本地联调主链路可运行。
- 最小联调命令 `python dev-server.py verify` 已通过（smoke 全绿）。
- 全量联调命令 `python dev-server.py verify --full-tests` 已通过（smoke + 契约测试 + 关键链路测试）。
- 仍存在业务层已知限制：`/api/preferences` 未实现、字段/枚举尚未完全统一（见 `docs/api-contract.md`）。

## 2) 本轮已完成的集成落地

1. 新增并统一联调入口：`dev-server.py`
   - `up`：一键启动前后端
   - `health`：健康检查
   - `smoke --spawn-backend`：最小真实 HTTP 校验
   - `verify`：默认最小 smoke
   - `verify --full-tests`：smoke + pytest 全量
2. 强化前端启动脚本：`frontend/start.sh`
   - `dev` / `health` / `smoke` 模式
3. 修复测试边界：`pyproject.toml`
   - 限定 `testpaths = ["tests"]`
   - 排除 `everything-claude-code` 子目录
4. 文档与命令统一：`README.md`、`API_INTEGRATION.md`、`docs/api-contract.md`、`docs/api_connectivity_runbook.md`

## 3) 统一状态块（2026-04-11）

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


## 4) 最小可行本地工作流（MVP）

### A. 只做联调最小闭环（推荐日常）

```bash
python dev-server.py verify
```

### B. 启动并手工联调前端页面

```bash
python dev-server.py up
# 浏览器打开 http://127.0.0.1:5173
```

### C. 联调收尾时做全量验证

```bash
python dev-server.py verify --full-tests
```

## 5) 临时绕行 / 旁路步骤（若后端启动异常再次出现）

若后端在未来改动中再次出现启动失败（例如依赖不兼容或端口冲突），按以下顺序旁路：

1. 先确认端口：检查 `8000` 是否被占用，再重试 `python dev-server.py smoke --spawn-backend`。
2. 仅做前端开发：
   - `cd frontend && ./start.sh dev --skip-api-check`
   - 使用 mock 数据或本地状态继续 UI 开发。
3. 仅做后端开发：
   - 运行 `python -m pytest -q tests/test_http_api.py` 与模块测试，先保证接口行为。
4. 等后端恢复后再执行：`python dev-server.py verify` 重新收敛联调状态。

## 6) 恢复步骤（Recovery）

出现联调失败时，建议按以下固定顺序恢复：

1. backend 契约收口完成（字段/枚举/`/api/preferences` 与 `docs/api-contract.md` 同步）。
2. frontend smoke：`python dev-server.py smoke --spawn-backend`
3. integration verify：`python dev-server.py verify`
4. integration full verify：`python dev-server.py verify --full-tests`（收尾）

## 7) 仍需后续推进（非阻塞）

1. 实现 `GET/PUT /api/preferences`，消除前端 Preferences 本地态孤岛。
2. 统一 `team`/`team_id`、状态与渠道枚举，减少前后端映射成本。

## 8) 交接版状态快照（2026-04-11）

1. Backend：契约测试路径可执行，待收口 `/api/preferences`、`team/team_id`、枚举统一。
2. Frontend：smoke 路径可执行，Preferences 等待后端接口完成后切换。
3. Integration：`verify` 与 `verify --full-tests` 可执行，已具备按统一恢复顺序推进交接条件。
