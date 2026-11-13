# 行程管家 · Travel Hub

面向旅行社的商业化行程通知 SaaS：多租户隔离、短信/企业微信双渠道、可配置通知规则、异步队列与死信重放、套餐订阅与在线支付。

- 后端：FastAPI + MySQL（JSON 文件存储仅用于本地/演示）
- 前端：React 18 + TypeScript + Vite + Tailwind CSS
- 短信：阿里云 Dysmsapi（登录/注册验证码 + 业务通知）
- 支付：易支付 / 极速付（彩虹易支付协议）、Stripe Checkout、本地模拟支付
- 部署：单镜像 + Docker Compose，一条命令启动

## 快速部署

```bash
cp .env.example .env
# 编辑 .env：数据库密码、域名、短信 AK/SK、支付商户信息、管理员初始密码
docker compose up -d --build
```

启动后访问 `http://<服务器地址>:8000`：

1. 使用 `BOOTSTRAP_ADMIN_USERNAME` / `BOOTSTRAP_ADMIN_PASSWORD` 登录；
2. 在「设置 → 通知渠道」配置企业微信 webhook 与短信签名/模板；
3. 在「套餐与账单」查看试用额度并购买套餐；
4. 在「设置 → 通知规则」配置发送策略；
5. 在「运维 → 发送任务」查看队列与死信。

> 生产环境不会创建演示账号，也不会回退到 mock 短信。首次启动必须显式设置管理员密码。

健康检查：

```bash
curl -fsS http://127.0.0.1:8000/api/health
curl -fsS http://127.0.0.1:8000/api/health/detail
```

## 环境变量

完整清单见 [.env.example](.env.example)。关键变量：

| 变量 | 说明 |
|---|---|
| `APP_ENV` | `production` / `staging` / `dev` / `test` |
| `SEED_DEMO_DATA` | 可选。仅 `dev`/`test`/`local` 默认写入演示行程、规则与模板；其他环境需显式设为 `true` |
| `SEED_DEMO_USERS` | 可选。默认 `true`；设为 `false` 时不创建内置 admin/user/partner 演示账号，只保留引导管理员 |
| `APP_BASE_URL` | 对外访问地址，用于支付回调与邮件链接 |
| `TRAVEL_NOTIFICATION_PERSISTENCE_BACKEND` | `mysql`（生产）或 `json`（本地） |
| `TRAVEL_NOTIFICATION_MYSQL_*` | MySQL 连接信息 |
| `AUTH_TOKEN_SECRET` / `VERIFICATION_CODE_SECRET` | 会话与验证码签名密钥，务必使用随机长字符串 |
| `BOOTSTRAP_ADMIN_USERNAME` / `BOOTSTRAP_ADMIN_PASSWORD` | 首个平台管理员 |
| `SMS_PROVIDER` | `aliyun`（生产）；`mock` 仅限本地 |
| `GLM_API_KEY` / `GLM_MODEL` | 可选。配置后使用智谱 GLM 润色通知文案（待润色文本会发送到 GLM API）；未配置时使用本地安全润色 |
| `ALIYUN_SMS_AK` / `ALIYUN_SMS_SK` | 阿里云短信凭证（只放环境变量/密钥管理） |
| `ALIYUN_SMS_SIGN_NAME` | 短信签名，例如 `江西锌鑫` |
| `ALIYUN_SMS_LOGIN_TEMPLATE_CODE` | 登录验证码模板 CODE |
| `ALIYUN_SMS_REGISTER_TEMPLATE_CODE` | 注册验证码模板 CODE |
| `PAYMENT_PROVIDERS` | 逗号分隔：`epay,jisufu,stripe,mock` |
| `PAYMENT_EPAY_*` / `PAYMENT_JISUFU_*` | 易支付 / 极速付商户信息 |
| `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET` | Stripe Checkout 与 webhook 密钥 |
| `BILLING_TRIAL_DAYS` / `BILLING_TRIAL_SMS_QUOTA` | 新租户试用期与试用短信额度 |
| `BOOTSTRAP_OPERATOR_USERNAME` / `BOOTSTRAP_OPERATOR_PASSWORD` | 可选：平台运营账号（跨租户运营后台） |
| `METRICS_TOKEN` | 可选：保护 `/api/health/detail` 与 `/api/health/metrics` |
| `RUN_SCHEDULER` | 多实例部署时仅在主实例设为 `true` |
| `BILLING_PLANS_JSON` | 可选：覆盖内置套餐目录 |
| `SMTP_*` | 可选：支付成功回执邮件 |
| `NOTIFICATION_QUEUE_INTERVAL_SECONDS` | 异步队列扫描间隔，默认 5 秒 |

### 支付回调地址

在支付商户后台配置：

```text
易支付：https://<域名>/api/payments/epay/notify
极速付：https://<域名>/api/payments/jisufu/notify
Stripe：https://<域名>/api/payments/stripe/webhook
```

也可只配置 `PAYMENT_NOTIFY_URL=https://<域名>/api/payments/{provider}/notify`，系统会按 provider 替换。不要把一个固定网关地址复用给另一个网关，否则签名校验会失败。

支付成功后用户回到 `https://<域名>/billing`。回调会校验签名、商户号、金额与订单状态，并做幂等处理；重复回调不会重复开通。

### 短信模板

认证验证码使用阿里云模板参数 `{"code": "123456"}`：

| 用途 | 环境变量 | 当前资料中的模板 |
|---|---|---|
| 登录 | `ALIYUN_SMS_LOGIN_TEMPLATE_CODE` | `SMS_512540357` |
| 注册 | `ALIYUN_SMS_REGISTER_TEMPLATE_CODE` | `SMS_512500353` |
| 重置密码 | `ALIYUN_SMS_RESET_TEMPLATE_CODE` | 复用登录模板 |

业务通知短信需在阿里云控制台审核单独的模板，并通过租户渠道配置的「通知模板 CODE」使用。

## 商业化能力

- **自助注册与登录**：企业注册、短信验证码登录、密码登录、短信重置密码、登录失败限流。
- **多租户与团队**：租户级数据隔离，管理员 / 导游 / 普通成员角色；管理员建团并把成员分配到行程，导游只看到并执行被分配的团。
- **套餐与计费**：免费版/标准版/成长版/企业版，试用期，短信额度按自然月统计与拦截。
- **在线支付**：易支付、极速付、Stripe、本地模拟支付；订单状态机与幂等回调。
- **通知渠道**：租户级企业微信 webhook、短信服务商/签名/模板配置，失败关闭（fail-closed）。
- **通知规则**：阶段/时段/场景/条件组匹配，通道与优先级可配置；规则内容可直接展开查看。
- **企业微信群触达**：行前/行中/行后定时发送到对应行程群，群消息按次去重；天气预警可多团群发。
- **团队执行**：管理员查看每位导游负责的行程、实际发送的通知内容、发送人和失败状态。
- **每团发送模式**：每个团可独立设置「自动发送」或「需我确认」；确认模式下调度器只生成计划，由导游检查后发送。
- **分岗位消息**：团期负责人（司导）、旅行管家、司机早间/午间话术独立成稿、独立发送；每个岗位可跟随本团群、使用单独企业微信群或短信手机号。
- **AI 文案润色**：通知模板、群提醒和分岗位消息支持 GLM 润色；未配置密钥时使用保留事实的本地安全润色。
- **可靠性**：异步 outbox、跨进程锁、重试与死信、人工重放、超时人工复核。
- **可观测性**：`X-Trace-Id`、指标端点、健康详情、手机号/webhook 脱敏。
- **支付回执**：配置 SMTP 后自动发送支付成功邮件。
- **平台运营后台**：`/operator` 查看全平台租户、收入、套餐与订单，支持手动开通套餐与退款标记。
- **生产安全开关**：生产环境关闭 OpenAPI 文档，可用 `METRICS_TOKEN` 保护运维指标。

## 宣传视频

面向抖音、小红书、视频号等渠道的竖屏宣传片：

- `promo/xingcheng-guanjia-promo-vertical.mp4`：1080 × 1920，41 秒，中文旁白
- `promo/xingcheng-guanjia-cover.jpg`：封面
- `promo/xingcheng-guanjia-promo.srt`：字幕
- `promo/README.md`：分镜、发布文案和重新生成说明

## 本地开发

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 本地使用 JSON 存储与 mock 短信，避免真实外呼
export APP_ENV=dev
export TRAVEL_NOTIFICATION_PERSISTENCE_BACKEND=json
export SMS_PROVIDER=mock
export PAYMENT_PROVIDERS=mock
export FRONTEND_DIST_DIR=frontend/dist

npm -C frontend install
npm -C frontend run build
PYTHONPATH=src python -m uvicorn app.api.http:app --host 127.0.0.1 --port 8000
```

前端热更新：

```bash
npm -C frontend run dev
```

## 测试

```bash
.venv/bin/python -m pytest -q
npm -C frontend test
npm -C frontend run build
```

测试通过 socket 级 guard 阻止真实外呼；新增外部 provider 必须注入 fake，不能在测试中访问真实网络。

## 运维

- **数据库迁移**：容器启动时自动执行 `scripts/apply_migrations.py`，已执行文件记录在 `t_schema_migrations`。
- **备份**：备份 MySQL 数据卷/实例；订单、租户与用户数据都在 MySQL 中。
- **扩容**：Compose 已拆出独立 `worker` 服务（`WORKER_MODE=true`）负责调度器与异步队列；Web 进程默认 `RUN_SCHEDULER=false`。Web 可多实例，但只保留一个 worker；每个实例都必须能访问同一 MySQL。高吞吐的 `SKIP LOCKED` 队列领取仍待下一阶段。
- **死信处理**：管理员在「发送任务」按状态筛选并重新入队，操作写审计日志。
- **额度告警**：账单页展示本月用量；额度耗尽时短信发送失败关闭并回退企业微信（若配置）。

## 安全须知

- `.env`、`公共资料.txt` 等包含真实凭证的文件已在 `.gitignore` 中，禁止提交。
- 仓库历史中曾出现企微 webhook key；升级后请立即在企微后台轮换。
- 本次接入使用的阿里云 AK/SK、支付商户密钥、SMTP 授权码均只应配置在环境变量或密钥管理服务中。
- 生产环境必须设置强随机 `AUTH_TOKEN_SECRET`、`VERIFICATION_CODE_SECRET` 与管理员密码。
- 建议在反向代理层启用 HTTPS、HSTS、请求体大小限制与访问日志脱敏。

## 目录结构

```text
src/app/
  api/http.py                 HTTP API 与 SPA 托管
  core/                       配置、可观测性、环境变量加载
  modules/
    identity/                 租户、用户、验证码、登录限流
    billing/                  套餐、订阅、订单、支付 provider、额度
    notification/             通知服务、规则、provider registry、幂等
    integration/              持久化、短信、企微、邮件、天气、认证
  services/                   调度、异步队列、工作流
frontend/src/
  pages/                      业务页、登录/注册、账单、设置
  services/commercialApi.ts   商业化 API 客户端
docs/
  migrations/                 MySQL 迁移
  commercial-deployment.md    部署与上线 runbook
```

## API 速览

```text
POST /api/auth/sms-code             发送验证码
POST /api/auth/register             企业注册
POST /api/auth/login                密码登录
POST /api/auth/login-sms            验证码登录
POST /api/auth/password/reset       重置密码
GET  /api/public/plans              套餐目录（公开）
GET  /api/billing/subscription      当前订阅与用量
POST /api/billing/orders            创建支付订单
GET  /api/billing/orders            订单列表
POST /api/payments/{provider}/notify 支付回调（公开）
GET  /api/admin/tenant-notification-config 租户渠道配置
GET  /api/admin/notification-jobs   死信/队列任务
POST /api/admin/users               团队成员管理
GET  /api/trips/{trip_id}/assignments   查看行程导游分配
PUT  /api/trips/{trip_id}/assignments   管理员分配行程执行人
POST /api/trips/{trip_id}/group-reminder 手动/AI 群提醒
POST /api/notifications/ai-polish       AI 润色通知文案
GET  /api/admin/team-overview           导游负责行程与通知内容总览
GET  /api/operator/tenants          平台运营：租户列表
GET  /api/operator/billing/overview 平台运营：收入与订单
POST /api/operator/tenants/{id}/activate-plan 平台运营：手动开通
POST /api/operator/orders/{no}/refund         平台运营：退款标记
```
