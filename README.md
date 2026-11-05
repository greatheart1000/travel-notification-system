# 新疆行程管家服务流程数字化

本仓库是“行程通知与管家流程”项目的 MVP 后端与前端联调工程。

## 商用化配置（必须显式设置）

生产环境不会回退到硬编码企微 webhook 或模拟短信：

| 变量 | 说明 |
|---|---|
| `APP_ENV` | `production` / `staging` / `dev` / `test`；非 dev/test 下未配置短信 provider 会失败关闭 |
| `WECHAT_WEBHOOK_URL` | 默认企微群机器人地址；也可在行程上配置 `webhook_url` 覆盖 |
| `SMS_PROVIDER` | `aliyun` 或 `mock`；生产必须显式配置 |
| `ALIYUN_SMS_AK` / `ALIYUN_SMS_SK` | 阿里云短信凭证 |
| `ALIYUN_SMS_TEMPLATE_CODE` | 默认短信模板 ID |
| `QWEATHER_API_HOST` / `QWEATHER_API_KEY` | 和风天气凭证；未配置时天气告警会安全降级 |
| `TRAVEL_NOTIFICATION_PERSISTENCE_BACKEND` | `mysql`（生产默认）或 `json`（本地/FC 演示） |
| `TRAVEL_NOTIFICATION_MYSQL_*` | MySQL 连接信息 |
| `NOTIFICATION_QUEUE_INTERVAL_SECONDS` | 异步发送队列扫描间隔，默认 5 秒 |
| `NOTIFICATION_TIMEZONE` | 定时调度时区，默认 `Asia/Shanghai` |

安全说明：仓库历史中曾出现企微 webhook key，升级后请立即在企微后台轮换该 key，并检查 `WECHAT_WEBHOOK_URL` 是否只配置在环境变量/密钥管理服务中。

可观测性：
- 所有 HTTP 响应带 `X-Trace-Id`；请求可传入同名 header。
- `GET /api/health/metrics` 返回发送尝试、成功、失败、重试、死信计数与延迟直方图。
- `GET /api/health/detail` 返回队列积压、最近失败与组件状态。

测试命令：

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest -q --cov=app --cov-report=term-missing
npm -C frontend test
npm -C frontend run build
```

测试会通过 socket 级 guard 阻止任何真实外呼；如新增外部 provider，必须注入 fake，不能在测试中访问真实网络。

### 分岗位接收人配置

默认情况下，团期负责人/旅行管家/司机三类话术会发送到行程群 webhook。若需要私发到不同接收人，可在行程或项目配置中增加：

```json
{
  "role_recipients": {
    "manager": {"channel": "sms", "address": "13800000001"},
    "concierge": {"channel": "sms", "address": "13800000002"},
    "driver": {"channel": "wechat_work_group", "address": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=..."}
  }
}
```

一旦配置了 `role_recipients`，缺失某个岗位的接收人时该岗位会被跳过并写日志，**不会回退到公共群**，避免把岗位专属内容发给错误的人。

### 租户级 provider 配置

管理员可通过以下接口为当前租户配置独立渠道，不需要改代码或重启：

```bash
GET /api/admin/tenant-notification-config
PUT /api/admin/tenant-notification-config
```

请求字段：`wechat_webhook_url`、`sms_provider`（`mock`/`aliyun`）、`sms_sign_name`、`sms_template_code`、`sms_credential_id`。原始 AK/SK 建议放密钥管理服务，接口只保存凭证引用 ID。

### 异步队列与死信运维

```bash
GET  /api/admin/notification-jobs?status=manual_intervention
POST /api/admin/notification-jobs/{job_id}/requeue
```

- 列表按当前租户过滤，支持 `pending/retrying/sent/failed/manual_intervention`。
- 死信/失败任务可重放，重放会重置 attempt 预算并重新进入队列。
- 所有重放操作写审计日志。

### 可配置通知规则

调度器会读取租户的 `NotificationRuleRepository` 规则：

- 没有规则：保持旧行为；
- 有规则：按 `stage + time_slot + scene + conditions` 匹配；
- 条件支持 `==/!=/>/>=/</<=/in/contains` 运算符；
- 规则存在但条件不匹配：跳过该行程并写审计；
- `all_day` 规则可匹配任意 time_slot。

运营可通过规则管理接口调整“行前几天发、什么条件发”，无需发版。

### 超时与“结果未知”策略

企微群机器人不支持幂等键。对于超时/连接中断这类“请求可能已到达 provider”的情况，系统会：

1. 记录 `delivery_unknown`，不自动重试；
2. 将幂等状态置为 `unknown`；
3. 将任务标记为 `manual_intervention`，由人工核对后处理。

普通 5xx/限流仍会按退避策略重试；配置错误、空内容、非法手机号等属于永久失败，不重试。

### 数据库迁移

商用 MySQL 环境上线前执行：

```bash
mysql -u <user> -p <database> < docs/migrations/2026-11-05-commercial-notification.sql
```

迁移包含 `trace_id`、异步 outbox、持久化幂等状态、角色接收人表和租户唯一索引。

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
