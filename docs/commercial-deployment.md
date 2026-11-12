# 商业化部署 Runbook

本文档覆盖从一台空服务器到可收费上线的完整步骤。所有示例使用 `https://travel.example.com`，请替换为你的真实域名。

## 1. 前置条件

- Linux 服务器（2 vCPU / 4 GB 起步），已安装 Docker 24+ 与 Docker Compose v2
- 一个已备案域名（中国大陆）与 TLS 证书
- 阿里云短信账号：已审核的签名与模板
- 支付商户：易支付/极速付商户号与 MD5 密钥，或 Stripe 账号
- MySQL 由 Compose 内置；生产也可使用云数据库

## 2. 部署

```bash
git clone <repo-url> travel-notification-system
cd travel-notification-system
cp .env.example .env
```

编辑 `.env`：

```dotenv
APP_ENV=production
APP_BASE_URL=https://travel.example.com
TRAVEL_NOTIFICATION_CORS_ORIGINS=https://travel.example.com
TRAVEL_NOTIFICATION_MYSQL_PASSWORD=<强密码>
MYSQL_ROOT_PASSWORD=<另一个强密码>
AUTH_TOKEN_SECRET=<openssl rand -base64 48>
VERIFICATION_CODE_SECRET=<openssl rand -base64 48>
BOOTSTRAP_ADMIN_USERNAME=admin
BOOTSTRAP_ADMIN_PASSWORD=<首次登录后立即修改>
SMS_PROVIDER=aliyun
ALIYUN_SMS_AK=<AK>
ALIYUN_SMS_SK=<SK>
ALIYUN_SMS_SIGN_NAME=江西锌鑫
ALIYUN_SMS_LOGIN_TEMPLATE_CODE=SMS_512540357
ALIYUN_SMS_REGISTER_TEMPLATE_CODE=SMS_512500353
PAYMENT_PROVIDERS=epay,jisufu
PAYMENT_EPAY_BASE_URL=https://xnoo.cn/
PAYMENT_EPAY_PID=<商户ID>
PAYMENT_EPAY_KEY=<MD5密钥>
PAYMENT_JISUFU_BASE_URL=https://pay.weixiue.com/
PAYMENT_JISUFU_PID=<商户ID>
PAYMENT_JISUFU_KEY=<MD5密钥>
BOOTSTRAP_OPERATOR_USERNAME=ops
BOOTSTRAP_OPERATOR_PASSWORD=<运营账号密码>
METRICS_TOKEN=<可选运维指标令牌>
```

启动：

```bash
docker compose up -d --build
docker compose logs -f app
```

首次启动会自动等待 MySQL、创建基础表、执行 `docs/migrations/*.sql` 并启动 API 与调度器。

## 3. 反向代理与 HTTPS

推荐 Caddy（自动证书）：

```caddyfile
travel.example.com {
    encode gzip
    reverse_proxy 127.0.0.1:8000
}
```

Nginx 示例：

```nginx
server {
    listen 443 ssl http2;
    server_name travel.example.com;

    ssl_certificate     /etc/letsencrypt/live/travel.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/travel.example.com/privkey.pem;

    client_max_body_size 20m;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
}
```

> 应用会读取 `X-Forwarded-For` 做登录/验证码限流，务必由反向代理覆盖该头。

## 4. 首次上线检查清单

1. `curl -fsS https://travel.example.com/api/health` 返回 200。
2. 使用 `BOOTSTRAP_ADMIN_USERNAME` 登录，立即在「团队成员」修改密码或新建管理员后停用初始账号。
3. 使用 `BOOTSTRAP_OPERATOR_USERNAME` 登录 `/operator`，确认能看到租户、收入与订单；运营账号只能访问平台运营后台。
4. 「设置 → 通知渠道」保存企业微信 webhook，点击测试（可在行程页使用 webhook 测试接口）。
5. 「设置 → 通知渠道」保存短信签名与通知模板 CODE。
6. 用真实手机号完成一次注册验证码，确认短信可达；验证码 5 分钟内有效、60 秒冷却、单号每日 10 次上限。
7. 「套餐与账单」创建最小金额订单，完成真实支付，确认订单变为已支付且套餐生效。
8. 在支付商户后台检查回调日志，确认收到 `success`；重复回调不会重复开通。
9. 在「设置 → 通知规则」创建一条规则，触发一次通知，确认渠道与内容。
10. 在「运维 → 发送任务」确认队列正常；人为制造失败后验证重新入队。
11. 配置 `METRICS_TOKEN` 后，确认未带令牌访问 `/api/health/metrics` 返回 403，带令牌返回 200。

## 5. 支付接入

### 易支付 / 极速付（彩虹易支付协议）

- 创建订单：`POST {base_url}/mapi.php`
- 签名：参数按字典序拼接 `k=v&...` 后追加商户密钥，MD5 小写
- 回调：`GET/POST /api/payments/{epay|jisufu}/notify`（两个网关必须使用各自的回调地址）
- 回调校验：签名、`pid`、`trade_status in (TRADE_SUCCESS, TRADE_FINISHED)`、金额与订单一致
- 成功返回纯文本 `success`，失败返回 `fail:<原因>`

### Stripe

- 使用 Checkout Session（`mode=payment`，币种由 `BILLING_CURRENCY` 决定）
- Webhook：`POST /api/payments/stripe/webhook`，校验 `Stripe-Signature`
- 必须在 Stripe Dashboard 配置 `checkout.session.completed` 事件
- 需要设置 `STRIPE_WEBHOOK_SECRET`

### 本地模拟支付

`PAYMENT_PROVIDERS=mock` 且 `APP_ENV != production` 时，账单页可调用「模拟支付」完成订单。生产环境该 provider 不会注册，接口会拒绝。

## 6. 短信接入

认证验证码走平台级阿里云凭证（环境变量），业务通知走租户级配置：

- 平台凭证：`ALIYUN_SMS_AK` / `ALIYUN_SMS_SK`
- 签名：`ALIYUN_SMS_SIGN_NAME`
- 验证码模板：登录/注册/重置
- 业务通知模板：租户渠道配置中的 `sms_template_code`，模板变量由模板渲染结果提供

额度：每个租户按自然月统计短信发送量；试用版/套餐额度用尽后短信 provider 返回 `sms_quota_exceeded`，调度器按永久失败处理并尝试回退企业微信。

## 7. 数据与备份

需要备份的内容：

- MySQL 数据库（租户、用户、订单、订阅、任务、审计）
- `.env`（密钥，建议放密钥管理服务）

示例备份：

```bash
docker compose exec mysql mysqldump \
  -u root -p"$MYSQL_ROOT_PASSWORD" \
  --single-transaction --routines --triggers \
  travel_notification_system | gzip > backup-$(date +%F).sql.gz
```

恢复前先停止 app 容器，恢复后重启。

## 8. 扩容与高可用

当前架构中调度器与异步队列 worker 运行在应用进程内：

- 单实例：`WEB_CONCURRENCY=1`（默认，推荐）
- 多实例：仅主实例 `RUN_SCHEDULER=true`，其余实例 `RUN_SCHEDULER=false`，避免重复调度
- MySQL 已使用 `GET_LOCK` 保护队列 tick、订单结算与用量计数；高吞吐场景仍建议将队列 worker 拆为独立服务

## 9. 监控

- 健康：`/api/health`、`/api/health/detail`
- 指标：`/api/health/metrics`（发送、支付、额度、验证码、登录等计数器与延迟直方图）；生产建议设置 `METRICS_TOKEN`
- 日志：至少收集 `ERROR` 与 `WARNING`；手机号与 webhook 已在日志中脱敏
- 告警建议：队列积压、死信数量、支付回调失败、短信失败率、5xx 比例

## 10. 安全与凭证轮换

- 本文档与仓库不包含任何真实密钥；`.env`、`公共资料.txt` 已被忽略
- 若凭证曾出现在聊天/共享文件/仓库历史中，视为已泄露，上线前轮换：
  - 阿里云 AccessKey
  - 易支付/极速付商户密钥
  - Stripe 密钥与 webhook secret
  - SMTP 授权码
  - 企业微信 webhook
- 生产必须关闭 `mock` 短信与 `mock` 支付
- 建议开启数据库网络隔离、定期备份、最小权限账号与操作审计

## 11. 常见问题

| 现象 | 排查 |
|---|---|
| 启动报 `BOOTSTRAP_ADMIN_PASSWORD is required` | 生产环境首次启动未设置管理员密码 |
| 登录返回 429 | 登录失败次数触发限流，等待 15 分钟或清理 `auth_login_attempts` |
| 短信发送失败 `sms_provider_not_configured` | 检查 `SMS_PROVIDER`、AK/SK 与租户渠道配置 |
| 支付回调返回 `invalid_payment_signature` | 检查商户密钥、签名方式与回调参数是否被网关改写 |
| 支付成功但套餐未生效 | 检查订单金额/商户号是否匹配，查看回调日志与 `billing_orders` 状态 |
| 前端刷新 404 | 确认 `FRONTEND_DIST_DIR` 指向构建产物，且反向代理回源到应用 |
| `/docs` 404 | 生产环境已按设计关闭 OpenAPI 文档 |
| 运营后台 403 | 账号角色不是 `operator`，检查 `BOOTSTRAP_OPERATOR_*` 或用户角色 |
