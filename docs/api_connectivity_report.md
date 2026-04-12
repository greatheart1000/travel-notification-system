# 前后端联调连通性报告

> 更新时间：2026-04-12（Asia/Shanghai）
> 检查范围：`dev-server.py`、`frontend/start.sh`、`src/app/api/http.py`、`tests/`

## 1) 当前结论（最新）

- 当前本地联调主链路可运行。
- 最小联调命令 `python dev-server.py verify` 已通过（smoke 全绿）。
- 全量联调命令 `python dev-server.py verify --full-tests` 已通过（smoke + 契约测试 + 关键链路测试）。
- `/api/notifications/rules*` 已落地第一批实现（含鉴权、枚举归一、CRUD），当前进入“实现优先 + 最小验证”阶段。

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

## 3) 统一状态块（2026-04-12）

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

1. backend rules 契约收口完成（以 `docs/api-contract.md` 为准）。
2. frontend rules smoke：执行 `rules 最小 smoke 命令链`。
3. integration verify：`python dev-server.py verify`
4. integration full verify：`python dev-server.py verify --full-tests`（收尾）

## 7) 仍需后续推进（非阻塞）

1. 将已新增的 `test_notification_rules_contract_smoke` 接入 `dev-server.py verify` 默认 smoke 链。
2. 冻结并发布 `stage/time_slot/scene` 输入别名规范，减少前后端枚举歧义。

## 8) 交接版状态快照（2026-04-12）

1. Backend：rules 第一批端点已实现，且已新增 `test_notification_rules_contract_smoke`；待接入 `dev-server.py verify` 默认 smoke 链。
2. Frontend：rules smoke 路径可执行；规则阶段枚举与后端规范仍在收敛。
3. Integration：`verify` 与 `verify --full-tests` 可执行，按统一恢复顺序推进交接。
