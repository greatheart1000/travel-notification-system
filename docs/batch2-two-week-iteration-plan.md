# Batch 2 两周迭代任务单（RBAC/租户数据域、异步重试、可观测告警、规则运营审批）

- 文档版本：v1
- 制定日期：2026-04-12
- 适用仓库：`travel-notification-system`
- 迭代周期：2 周（10 个工作日）

---

## 1. 迭代目标（Definition of Outcome）

本轮聚焦把系统从“可演示 MVP”推进到“可受控试运行”：

1. **RBAC 与租户数据域**：实现角色-权限矩阵、接口权限闸门、跨租户访问拒绝闭环。
2. **异步队列与重试**：把关键通知发送切换为“可异步、可重试、可追踪”的任务模型。
3. **可观测与告警**：形成 metrics/log/alert 最小闭环，支持值班排障。
4. **规则运营与审批流**：规则变更进入“草稿-提交-审批-发布/驳回”流程并留痕。

---

## 2. 工作分解结构（WBS）

## Track A：RBAC + 租户数据域（优先级 P0）

### A1. 权限模型定义
- 产出：`docs/rbac-permission-matrix.md`
- 内容：
  - 角色（admin/ops/concierge/cs/sales/user）
  - 资源域（trip/notification/rule/template/audit/ops）
  - 动作（read/write/approve/export/manage）
  - 数据域约束（tenant/team/user 三级）

### A2. API 权限闸门中间层
- 产出：
  - `src/app/modules/integration/rbac.py`
  - 在 `src/app/api/http.py` 接入 `require_permission()`
- 验收：
  - 403 行为统一（错误码与错误文案）
  - 关键写接口必须通过权限校验

### A3. 跨租户与跨团队访问防护
- 产出：
  - 统一 `assert_tenant_scope()` 与 `assert_team_scope()`
  - 对 trip/rule/template/audit 查询补充分页 + 域过滤
- 验收：
  - 非本租户访问命中 403
  - 管理员可按租户汇总；普通角色只能访问授权范围

---

## Track B：异步任务与重试（优先级 P0）

### B1. 发送任务模型
- 产出：`notification_job` 逻辑模型（或等价存储结构）
- 字段：job_id、task_id、tenant_id、channel、status、attempt、next_run_at、last_error

### B2. 调度与重试执行器（最小可用）
- 产出：
  - `src/app/services/async_dispatch.py`
  - 指数退避（例如 1m/3m/9m）
  - 死信标记（超过阈值转 `manual_intervention`）

### B3. API 对接
- 产出：
  - 新增异步投递入口（保留同步 fallback）
  - 增加任务查询接口（按 tenant/team/trip）
- 验收：
  - 可追踪每次 attempt、错误码、耗时、下一次重试时间

---

## Track C：可观测与告警（优先级 P0）

### C1. 指标定义与埋点
- 指标：
  - notification_success_rate
  - notification_retry_rate
  - notification_manual_takeover_rate
  - rule_publish_lead_time
  - cross_tenant_forbidden_count

### C2. 健康检查增强
- 产出：`/api/health/detail` 增加：
  - queue_backlog
  - oldest_pending_job_age
  - error_burst_5m

### C3. 告警规则（MVP）
- 规则：
  - 5 分钟失败率 > 阈值
  - 队列堆积 > 阈值
  - 人工接管率异常上升
- 产出：`docs/ops-alert-runbook.md`

---

## Track D：规则运营与审批流（优先级 P1）

### D1. 规则状态机
- 状态：`draft -> pending_approval -> approved -> published -> archived/rejected`
- 约束：
  - 非 approved 不可生效
  - 发布必须携带审批人和审批时间

### D2. 审批接口
- 产出：
  - submit/approve/reject/publish 端点
  - 审批意见与审计记录

### D3. 规则仿真（最小版）
- 产出：
  - `simulate` 端点：输入上下文，返回命中规则、优先级、冲突提示

---

## 3. 10 个工作日排期（可直接执行）

### Week 1
- Day 1：权限矩阵定稿（A1）+ API 清点与风险评审
- Day 2：RBAC 中间层实现（A2）
- Day 3：租户/团队数据域防护改造（A3）
- Day 4：异步 job 模型与持久化（B1）
- Day 5：重试执行器与死信策略（B2）

### Week 2
- Day 6：异步 API 接入与任务查询（B3）
- Day 7：指标埋点 + health/detail 增强（C1/C2）
- Day 8：告警规则 + 值班 Runbook（C3）
- Day 9：规则状态机 + 审批接口（D1/D2）
- Day 10：规则仿真 + 回归测试 + 发布检查单（D3）

---

## 4. 每日交付模板（逐项提交）

每个工作日最少提交 1 个 PR，PR 模板统一包含：

1. 目标与范围（只做 1~2 个子任务）
2. 代码变更清单（文件级）
3. 测试命令与结果
4. 回滚方式
5. 风险与后续项

---

## 5. 验收标准（Definition of Done）

- 安全：关键写接口全部受权限控制；跨租户越权不可达。
- 可靠性：通知任务具备异步重试 + 死信 + 人工接管标记。
- 可观测：关键指标可查询，告警规则可触发并有处理手册。
- 运营：规则审批链路可走通，所有动作有审计。
- 测试：新增/更新单测 + 契约测试，核心链路通过。

---

## 6. 风险与缓冲

- 风险 1：权限改造影响面大，易引发 403 误伤。
  - 缓冲：先灰度到 rules/template 写接口，再扩展到其他域。
- 风险 2：异步队列引入后时序复杂度上升。
  - 缓冲：先保留同步 fallback，逐步切换。
- 风险 3：告警阈值初期误报。
  - 缓冲：设置观察窗口并支持阈值热更新。

---

## 7. 本轮首个可执行提交建议

优先从 **A1 + A2** 开始（权限矩阵 + API 权限闸门基础层），因为这是后续审批流与异步任务的安全前提。
