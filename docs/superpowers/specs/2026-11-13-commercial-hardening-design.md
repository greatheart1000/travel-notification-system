# 商业化推进设计（2026-11-13）

## 目标

在已有商业化 SaaS 骨架和外部凭证（公共资料.txt）基础上，优先补齐会阻断真实收费/运营的代码缺口：

1. 行程页天气列表 API + 前端降级
2. 租户开票/税务信息
3. 退款工作流（网关尝试 + 人工兜底）
4. 独立 worker 进程入口
5. Playwright 端到端冒烟脚本

## 非目标

- 不在测试中发起真实短信/支付/天气外呼
- 不做发票 PDF 生成、催收（dunning）完整策略
- 不做 Stripe 退款（当前订单只保存 Checkout Session，缺少 payment_intent 映射）
- 不在本次实现 MySQL `SELECT ... FOR UPDATE SKIP LOCKED`（保留为下一阶段）
- 不追求整体覆盖率从 51% 提到目标值；只覆盖本次新增路径

## 方案与取舍

### 天气列表
- 方案 A：后端新增 `GET /api/weather/{region}`，复用现有 `WeatherProvider`；QWeather 未配置时用 `MockWeatherProvider` 降级。前端保持现有 `/api/weather/xinjiang` 调用。
- 方案 B：前端改接 `GET /api/notifications/emergency-weather`。但该接口返回单个紧急摘要，不是城市列表，不合适。
- 选择 A。前端同时把天气请求改为非阻塞：天气失败不影响行程列表。

### 开票/税务
- 方案 A：扩展 `Tenant` 资料字段（JSON/collection store 直接支持），在渠道配置页增加“开票信息”卡片。
- 方案 B：新建独立开票表。需要迁移和额外仓储，本次不必要。
- 选择 A。字段：`invoice_title`、`tax_id`、`invoice_address`、`invoice_phone`、`invoice_bank_name`、`invoice_bank_account`、`invoice_email`。

### 退款
- 方案 A：直接调用网关退款 API，失败即报错。
- 方案 B：退款工作流。订单增加 `refund_status`（none/processing/refunded/manual/failed）、`refund_error`、`refunded_at`；运营可选择“尝试网关退款”或“仅记账退款”。网关适配器未实现/未配置时明确标记人工处理。
- 选择 B。既避免伪退款，又为后续接真实网关留出接口。

### Worker
- 方案 A：Web 进程内继续跑调度器（现状）。
- 方案 B：新增 `python -m app.worker` 独立入口 + Compose worker 服务；Web 设 `RUN_SCHEDULER=false`。
- 选择 B 的第一步；`SKIP LOCKED` 仍留待下一阶段。

### E2E
- 方案 A：完整 Playwright Test 套件（需要新增 npm 依赖和 CI 配置）。
- 方案 B：Python Playwright 冒烟脚本，读取环境变量登录并检查关键页面。
- 选择 B，先建立可执行的端到端冒烟基线。

## 验收

- 新增后端测试覆盖天气、开票资料、退款工作流。
- `pytest -q` 全绿。
- `npm -C frontend run build` 与前端契约测试通过。
- 不修改 `.env`、不把真实凭证写入仓库。
