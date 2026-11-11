# 商业化前端改造设计稿

- 日期：2026-11-09
- 分支：`refactor/commercial-notification`
- 状态：待确认
- 范围：登录门面、租户渠道配置、通知规则管理、演示态清理；死信运维为二级页面

## 1. 意图与原因

后端已经具备多租户隔离、租户级 provider 配置、可配置通知规则、异步队列与死信重放能力，但前端仍停留在演示态：登录页预填演示账号、dev 环境自动注入 mock token、顶栏写死“管理员”、渠道配置和规则管理没有入口、规则类型和 adapter 丢掉了 `channels`/`conditions` 字段。客户不会读 README，只会看界面，因此当前最大的商业化障碍不是功能缺失，而是“登录页像 demo、后台能力像半成品”的割裂感。

本次改造把演示主路径收敛为一个客户能看懂、能操作的最小闭环：

**登录 → 当前租户的渠道配置 → 通知规则管理**

死信队列与重放作为二级「运维」页面保留，不占演示主路径。

## 2. 目标与非目标

### 目标

1. 登录页达到可给付费客户演示的门面标准：品牌、定位、无演示账号、无 mock 文案。
2. 登录后明确展示当前租户、用户与角色。
3. 管理员能在界面上完成租户级企微/短信渠道配置，无需读 README 或改环境变量。
4. 管理员能在界面上完成通知规则的增删改查、启停、条件组配置。
5. 死信任务可查看、可重新入队。
6. 演示主路径不出现 raw JSON、`trace_id`、`manual_intervention` 等工程态信息。
7. 保持现有前端构建、契约测试、后端测试通过。

### 非目标

- 不做自助注册、套餐、账单、计费。
- 不做登录前租户编码校验（需要改登录模型与用户查找逻辑）。
- 不做规则锁定/审批流（需要后端增加锁字段与角色语义）。
- 不做规则“命中行程”预览接口（P2，后续单独做）。
- 不做完整模板管理页（本切片只做规则绑定模板的下拉选择）。
- 不引入新的 UI 组件库或图表库。

### 反目标

- 为了“看起来高级”而堆动画、渐变、无意义图表。
- 在登录页伪造租户输入框或假的“测试连通性”按钮。
- 把内部状态词直接翻译成英文缩写或原样展示。
- 为了演示而隐藏真实错误；错误要可读，但不泄露 trace_id。

## 3. 约束

- 前端：React 18 + TypeScript + Vite + Tailwind CSS 3 + lucide-react；不新增运行时依赖。
- 后端：FastAPI 单文件路由 `src/app/api/http.py`；已有接口为主，仅做一处时间戳修正。
- 认证：`POST /api/auth/login` 只接收 `username/password`；`GET /api/users/me` 返回 `tenant_id`、`role`。
- 权限：租户渠道配置与死信运维仅 `role === "admin"`；规则读取所有登录用户可用，写操作本切片仅管理员开放。
- 租户：`tenant-a` 展示为「沙笛旅行」，`tenant-b` 展示为「合作旅行社」，未知租户回退显示租户 ID。
- 现有测试：`frontend/tests/*.mjs` 会读取源码做契约断言，改造不得破坏；必要的语义变化同步更新测试。

## 4. 页面与交互设计

### 4.1 登录页

**布局**：桌面端左右分栏。左侧品牌区占 45%，深色 slate/sky 渐变，右侧为白色登录卡；移动端品牌区折叠为顶部横幅。

**左侧品牌区**
- Logo 标记（`Plane` 图标 + 圆角底）。
- 产品名：**行程管家**；英文副标：Travel Hub。
- 一句话定位：**为旅行社提供行前、行中、行后一体化通知与管家协作**。
- 三条信任信息（图标 + 短句）：多租户数据隔离 / 通知渠道可配置 / 发送过程可追溯。
- 底部：`© 2026 行程管家 · 企业版`。

**右侧登录卡**
- 标题：登录企业工作台。
- 副标题：使用管理员分配的账号登录。
- 用户名、密码（密码可见性切换）。
- 错误提示用红色 `role="alert"`。
- 登录按钮全宽，loading 状态“正在登录…”。
- 底部提示：忘记密码请联系企业管理员。
- 不预填任何账号；不展示 Figma/Mock/演示环境文案。

**登录后**
- 调 `GET /api/users/me`，把 `id/username/email/role/tenant_id` 写入会话上下文。
- 登录失败展示后端可读错误；401 统一为“账号或密码不正确”。

### 4.2 应用外壳

**侧边栏**
- 顶部品牌：行程管家 + 当前租户名。
- 菜单分组：
  - 业务：行程管理、数据分析
  - 设置：通知渠道、通知规则、偏好设置
  - 运维：发送任务（死信队列）
- 管理员才显示「通知渠道」「发送任务」；普通用户只读规则。
- 底部租户卡片：租户名、当前用户角色、版本号。
- 视觉：白色/浅灰底、细边框、sky 色 active 态，替换当前大面积青色渐变。

**顶栏**
- 左侧：当前页面标题（由路由映射）。
- 右侧：租户徽标、用户名 + 角色、退出登录。
- 移除当前无功能的搜索框和通知铃铛（避免“假控件”）。
- 退出登录后回到登录页。

**路由**

| 路由 | 页面 | 权限 |
|---|---|---|
| `/login` | 登录页 | 公开 |
| `/trips`、`/trips/:id` | 行程管理 | 登录 |
| `/analytics` | 数据分析 | 登录 |
| `/preferences` | 偏好设置 | 登录 |
| `/settings/channels` | 租户渠道配置 | admin |
| `/settings/rules` | 通知规则 | 登录读 / admin 写 |
| `/settings/jobs` | 发送任务（死信） | admin |

### 4.3 租户渠道配置页

路由 `/settings/channels`。页面标题「通知渠道配置」，副标题说明“配置只对当前租户生效，保存后立即用于后续通知”。

三张独立卡片，各有自己的保存按钮、脏状态、成功/失败提示；保存时提交完整快照（后端 upsert 是整条覆盖），即“当前已加载配置 + 本卡修改”。

**未配置状态**：租户从未保存过配置时，`GET` 返回的 `config` 只有 `tenant_id`。所有字段必须以“未配置”为初始态，不能默认成 `aliyun` 或 `mock`；否则保存企业微信卡片会顺带把短信服务商写成默认值。短信服务商下拉固定三项：未配置（沿用系统设置）、阿里云、演示通道。

**卡片 A：企业微信群通知**
- 字段：`wechat_webhook_url`。
- 默认掩码显示，提供“显示/隐藏”切换。
- 状态徽标：已配置 / 未配置。
- 校验：必须以 `https://qyapi.weixin.qq.com/` 开头；否则提示“请输入企业微信官方群机器人地址”。
- 说明文案：未配置时该渠道失败关闭，不会回退到硬编码地址。
- 不做“测试连通性”。

**卡片 B：短信服务**
- 字段：`sms_provider`（下拉：未配置 / 阿里云 / 演示通道）、`sms_sign_name`、`sms_template_code`。
- `mock` 选项标注“演示通道：不会发送真实短信”。
- 未配置时展示“未配置：发送链路将沿用系统级 `SMS_PROVIDER` 设置”。
- 说明：签名与模板需先在短信服务商控制台完成审核。

**卡片 C：凭证与安全**
- 字段：`sms_credential_id`。
- 说明：系统只保存凭证引用 ID，原始 AK/SK 请放在密钥管理服务或环境变量中。
- 只读展示：`updated_at`（若为空显示“尚未保存”）。

**状态与错误**
- 403 显示“仅管理员可配置通知渠道”。
- 保存成功显示“已保存，后续通知将使用新配置”。
- 网络/5xx 统一为可读中文，不展示 trace_id。

### 4.4 通知规则页

路由 `/settings/rules`。采用“列表 / 编辑分离”：

**列表**
- 顶部：标题、说明、右侧「新建规则」（admin）。
- 工具栏：状态筛选（全部/已启用/已停用）+ 规则名搜索（客户端过滤）。
- 表格列：规则名称、状态（switch）、阶段、时段、场景、渠道、优先级、最后修改、操作。
- 空状态：说明“尚未配置通知规则，系统将沿用默认发送行为”，并提供新建按钮。
- 普通用户：隐藏 switch/新建/编辑/删除，只读。

**编辑（大号弹窗，`max-w-3xl`，内容可滚动）**
- 基本信息：规则名称、启用开关。
- 触发条件：阶段、时段、场景三个下拉。
- 发送配置：渠道多选（短信/企业微信；邮件标记“暂未开放”并禁用，因为调度器目前只会发送 `sms` 和 `wechat_work_group`，允许选邮件会静默回落成短信）、绑定模板（从 `GET /api/notifications/templates` 加载）、优先级（数字，说明“数值越小越优先”）。
- 条件组：可增删的行，每行“字段 + 运算符 + 值”。
  - 字段建议：目的地 `destination`、人数 `participants`、时间节点 `time_node`、团号 `team_id`、行程状态 `status`；允许手填其他字段名。
  - 运算符：`==`、`!=`、`>`、`>=`、`<`、`<=`、`in`、`contains`。
  - `in` 的值用逗号分隔，提交时转数组；`==` 提交标量，其余提交 `{op, value}`，与后端 `TriggerEngine.match_value` 兼容。
  - 类型安全：`> >= < <=` 只接受数值并在提交前转 number；`contains` 只接受字符串；`in` 至少一个值。避免 `status > 5` 这类规则在调度器里触发 `TypeError`。
  - 同一字段只允许一行；重复字段在保存前拦截（后端 `conditions` 是对象，重复键会静默覆盖）。
  - 已知字段给出类型提示（`participants` 数值，其余建议字符串）；自定义字段允许，但提示“请确认发送上下文存在该字段且类型一致”。
  - 空条件组表示“该阶段/时段/场景下全部命中”。
- 底部：取消 / 保存；保存失败保留表单并显示可读错误。

**删除**
- 二次确认，说明“删除后该规则立即停止生效”。

**明确不做**
- 规则锁定图标（无后端字段）。
- 命中行程预览（无后端试算接口）。

### 4.5 发送任务（死信）页

路由 `/settings/jobs`，admin only。页面标题「发送任务」，副标题“查看异步发送任务，处理需要人工确认的失败任务”。

- 状态筛选：全部、待发送 `pending`、发送中 `processing`、重试中 `retrying`、需人工处理 `manual_intervention`、失败 `failed`、已发送 `sent`。
- 表格列：任务号（短 ID）、行程 ID / 团队 ID、渠道、尝试次数、下次重试时间、错误摘要、状态、操作。
- 数据来自 `GET /api/admin/notification-jobs`；该接口只返回 `job_id/task_id/trip_id/team_id/channel/status/attempt/next_run_at/last_error/timestamps`，不返回行程名、场景或 `trace_id`。列表只展示 `trip_id`/`team_id`/`channel`，不为名称额外拉取行程接口。
- 可重放状态：`manual_intervention`、`failed`；按钮「重新入队」，二次确认说明会重置尝试预算并写审计日志。
- 状态中文映射：
  - `pending` → 待发送
  - `processing` → 发送中
  - `retrying` → 重试中
  - `sent` → 已发送
  - `failed` → 发送失败
  - `manual_intervention` → 需人工处理
- 错误摘要翻译：`dispatch_exception:*` → 发送异常，可重新入队；`task_not_found` → 关联任务不存在；`*timeout*` → 渠道响应超时；`invalid_phone` → 手机号无效；`empty_content` → 通知内容为空；`missing_config` → 渠道配置缺失；`sms_provider_not_configured` → 短信服务商未配置；`unknown_sms_provider:*` → 短信服务商配置无效。未知错误截断到 120 字符。
- 不展示 `trace_id`（接口也没有）；展开的“技术详情（供技术支持使用）”展示原始 `last_error`，并提供“复制排查编号”复制 `job_id` / `task_id`。

## 5. 字段映射（界面 ↔ 后端 ↔ 参考产品）

### 5.1 租户渠道配置

接口：`GET/PUT /api/admin/tenant-notification-config`（admin）。

| 界面字段 | 后端字段 | 参考产品位置 |
|---|---|---|
| 企业微信群机器人地址 | `wechat_webhook_url` | 携程 ebooking 渠道卡片 |
| 短信服务商 | `sms_provider`（`aliyun`/`mock`） | 阿里云短信控制台服务商选择 |
| 短信签名名称 | `sms_sign_name` | 阿里云「签名管理」 |
| 短信模板 ID | `sms_template_code` | 阿里云「模板管理」 |
| 凭证引用 ID | `sms_credential_id` | 阿里云 AccessKey 与业务配置分离 |
| 最近更新时间 | `updated_at` | 成熟控制台的配置状态区 |

### 5.2 通知规则

接口：`GET/POST /api/notifications/rules`、`GET/PUT/DELETE /api/notifications/rules/{id}`。

| 界面字段 | 后端字段 | 参考产品位置 |
|---|---|---|
| 规则名称 | `name` | Twilio alert rule name |
| 启用/停用 | `enabled` | Twilio active toggle |
| 阶段 | `stage`：`pre_trip`/`in_trip`/`post_trip` | Twilio 规则类型 |
| 时段 | `time_slot`：`morning`/`afternoon`/`evening`/`night`/`all_day` | — |
| 场景 | `scene`：`normal`/`weather_alert`/`delay`/`complaint`/`manual` | — |
| 通知渠道 | `channels[]`：`sms`/`wechat_work_group`；`email` 后端可存但不会发送，界面禁用 | C1.ai 按渠道配置 |
| 绑定模板 | `template_id` | Twilio 模板绑定 |
| 优先级 | `priority`（越小越优先） | Twilio 规则排序 |
| 条件组 | `conditions`：`{字段: 标量 或 {op, value}}` | Twilio `rule_thresholds` |
| 最后修改 | `updated_at` | Twilio 列表页 |

### 5.3 登录与租户

| 界面动作 | 接口 |
|---|---|
| 用户名/密码登录 | `POST /api/auth/login` `{username, password}` |
| 当前用户/角色/租户 | `GET /api/users/me` → `id/username/email/role/tenant_id` |
| 刷新令牌 | `POST /api/auth/refresh` |
| 退出 | `POST /api/auth/logout` |

## 6. 前端实现结构

```
frontend/src/
  app/
    router.tsx                 # 扩展 settings 路由
    session.tsx                # AuthSessionProvider + useSession
    tenant.ts                  # tenant_id → 展示名/角色名
  components/
    layout/
      AppSidebar.tsx           # 替换 Sidebar
      AppHeader.tsx            # 替换 Header
      PageHeader.tsx           # 页面标题/说明/操作区
    ui/
      Field.tsx                # label + 说明 + 错误
      TextInput.tsx / Select.tsx / Switch.tsx
      InlineAlert.tsx          # 成功/错误/提示
      ConfirmDialog.tsx        # 复用 Modal
    settings/
      ChannelConfigCard.tsx
      RuleEditorModal.tsx
      ConditionRowsEditor.tsx
  pages/
    LoginPage.tsx              # 从 App.tsx 拆出
    settings/
      ChannelSettingsPage.tsx
      RuleSettingsPage.tsx
      NotificationJobsPage.tsx
```

**状态**
- `AuthSessionProvider` 持有 `user/tenantId/isAuthenticated/isCheckingAuth`，负责登录、登出、`/users/me` 校验。
- 页面级表单状态留在页面内；不引入 Redux/Zustand。
- 所有 API 调用集中在 `services/api.ts`，新增 `tenantConfigApi` 与 `notificationJobsApi`。

**类型与 adapter 修正**
- `CurrentUser` 增加 `tenant_id`。
- `NotificationRule` 增加 `channels: ChannelCode[]`、`conditions: RuleConditionMap`、`createdAt`、`updatedAt`、`sceneLabel`。
- `NotificationRuleStageCode` 改为 `'pre_trip' | 'in_trip' | 'post_trip' | 'unknown'`；`on_trip`/`custom` 仅作为历史输入映射到 `in_trip`/`unknown`，不再向后端发送。
- `mapRawNotificationRule` 保留 `channels`、`conditions`、时间戳。
- `toNotificationRuleWritePayload` / `toNotificationRulePatchPayload` 发送 `channels`、`conditions`。
- 条件值序列化：`==` → 标量；其他 → `{op, value}`；`in` → 数组。

**错误文案**
- 新增 `friendlyErrorMessage(error)`：401“登录已过期，请重新登录”；403“当前账号没有权限执行此操作”；404“数据不存在或已被删除”；422“填写内容不符合要求，请检查后重试”；0“网络连接异常，请稍后重试”；5xx“服务暂时不可用，请稍后重试”。
- 原始后端 message 仅在开发环境 console 输出。

**视觉规范**
- 中性色 slate，品牌色 sky-600；圆角 `rounded-xl`；卡片 `border-slate-200 + shadow-sm`。
- 标题层级：页面 24px/28px，卡片 16px，正文 14px，辅助 12px。
- 表格行高 48px，状态用徽标，不用颜色作为唯一信息载体。
- 可访问性：label 绑定输入、switch `role="switch"` + `aria-checked`、错误 `role="alert"`、Modal 支持 Esc 关闭、图标按钮有 `aria-label`。

## 7. 后端改动

仅一处：

- `TenantNotificationConfigRepository.upsert` 将 `updated_at` 设置为当前时间（ISO），而不是沿用旧值/空值。这样渠道配置页可以展示“最近更新”。
- 在 `tests/test_api_tenant_isolation.py` 的租户配置用例中补充断言：第二次 PUT 后 `updated_at` 发生变化且非空。

不新增后端接口。

## 8. 实施顺序

### P0：演示主路径
1. Auth session + 登录页 + 应用外壳（顶栏/侧边栏/租户）。
2. 路由扩展与权限守卫。
3. 渠道配置页 + `tenantConfigApi` + 后端 `updated_at` 修正。
4. 规则类型/adapter 修正 + 规则列表/编辑/删除/启停。
5. 演示态清理：移除 mock auth、假搜索/铃铛、重复 Header、工程态文案。

### P1：二级运维页
6. 死信任务列表、筛选、重新入队、确认弹窗。

### P2（本次不做）
7. 规则命中行程预览接口与界面。
8. Playwright 端到端覆盖。

## 9. 验收标准

**登录**
- 首次访问无 token 时显示登录页，不自动注入 mock token。
- 登录页不出现 `admin/123456` 预填、Figma、Mock、演示账号等文案。
- 登录成功后顶栏显示用户名、角色和租户名；刷新页面仍保持登录态。
- 错误密码显示中文错误且为红色提示。

**渠道配置**
- admin 可加载并保存三张卡片；保存任一卡片不会清空其他卡片字段。
- 非 admin 访问显示无权限提示。
- 不出现“测试连通性”按钮。
- 保存后重新进入页面能看到新值和 `updated_at`。

**通知规则**
- 列表正确显示中文阶段/时段/场景/渠道。
- 新建规则后重新加载，`channels` 与 `conditions` 不丢失。
- 条件组支持 8 种运算符；`in` 的逗号分隔值提交为数组。
- 启停、删除、编辑均通过真实 API。
- 普通用户看不到写操作入口。
- 不再向后端发送 `on_trip`/`custom`。

**死信页**
- 按状态筛选正确；`manual_intervention` 显示为「需人工处理」。
- 重新入队前有确认；成功后列表刷新。
- 列表不出现 `trace_id`。

**工程态清理**
- 演示主路径无 raw JSON、`trace_id`、`manual_intervention` 原文。
- 页面无重复 Header；Preferences 不再自带 Header。

**验证命令**
```bash
npm -C frontend run build
npm -C frontend test
.venv/bin/python -m pytest -q tests/test_api_tenant_isolation.py tests/test_api_admin_jobs.py
```

## 10. 风险与取舍

1. **登录前无法显示租户**：当前登录接口没有租户编码；本切片选择登录后展示，不在登录页伪造。若客户强要求登录前识别租户，需要下一轮改登录模型。
2. **条件运算符有两套匹配实现**：调度器走 `NotificationPolicy` 支持 `{op, value}`；`rule_service.match_rules` 仍是精确相等。本切片只写调度器的语义，不做预览，因此不影响线上；后续做预览时需要先统一。
3. **渠道配置是整条覆盖**：三张卡片各自保存时必须合并完整快照，否则会清空其他卡片。已在设计中明确。
4. **模板选择依赖已有模板**：若租户没有模板，规则可先不绑定模板，界面给出提示；完整模板管理不在本切片。
5. **普通用户规则只读**：后端当前允许任意登录用户写规则；前端先按产品权限收口，后端后续补权限校验。
6. **`tenant-a` 展示名**：按需求文档推断为「沙笛旅行」，若实际租户名不同，只需改 `tenant.ts` 映射。
7. **条件类型安全**：前端会校验数值运算与重复字段，但后端 `TriggerEngine.match_value` 仍可能因 API 直写或历史规则类型不匹配抛 `TypeError`；本切片不改后端匹配逻辑，建议后续硬化。
8. **邮件渠道**：规则存储层接受 `email`，但调度器只发送 `sms` / `wechat_work_group`；界面禁用邮件，避免“配了邮件却收到短信”。
9. **死信接口字段有限**：`notification-jobs` 不返回行程名、场景或 `trace_id`；页面按 `trip_id/team_id/channel` 展示，不额外拉行程接口。
10. **未配置默认值**：租户首次配置时所有字段必须为“未配置”，不能默认成 `aliyun`/`mock`，否则保存一张卡片会顺带改写其他渠道。

## 11. 已由实现者决定的事项

- 不引入新依赖，使用原生表单控件 + Tailwind。
- 使用大号 Modal 而非右侧抽屉承载规则编辑，减少新组件面。
- 错误提示采用页面内联 alert，不引入全局 toast 框架。
- 登录页品牌名使用「行程管家」，租户展示名映射在 `tenant.ts`。
- 移除顶栏当前无功能的搜索与铃铛，而不是保留占位。
- 死信页放在「运维」分组，管理员可见。
- 短信服务商提供显式“未配置”选项，不把空配置默认成 `aliyun`/`mock`。
- 邮件渠道在规则编辑器里禁用并标注“暂未开放”。
- 条件组做数值类型校验与重复字段拦截；自定义字段允许但给出类型提示。
- 死信页按接口真实字段展示，不为行程名额外请求接口。

## 12. 需要确认的问题

**渠道配置页是否要求“保存后真正影响发送”？**

现状：
- `wechat_webhook_url` 和 `sms_provider` 已经会被发送链路读取。
- `sms_sign_name`、`sms_template_code` 目前只存不读；发送时使用的是模板或项目配置里的签名字段。
- `sms_credential_id` 是凭证引用，真正 AK/SK 仍走环境变量/密钥管理服务。

两个选项：
- **A（推荐）**：把租户的签名/模板接成发送时的默认值（模板/项目配置没有时才回退），需要小范围后端改动 `scheduler_service` + 测试。这样演示时三张卡片都是“真开关”，不是只写数据库。
- **B（纯前端）**：本切片只做持久化，页面文案收窄为“保存供运营参考，发送仍以模板/项目配置为准”。改动最小，但客户可能会问“我配了为什么没生效”。

你选 A 还是 B？
