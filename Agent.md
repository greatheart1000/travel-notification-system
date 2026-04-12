# 旅游行程管家服务流程数字化 - 工业级代码指导（Agent.md）

## 1. 目标与适用范围
本规范用于本仓库后端代码（`src/app`）的设计、开发、测试、发布与故障处理。
目标：在“通知、触发、投诉、满意度、审计、外部集成”场景下，最大化稳定性、可维护性与可追溯性，避免低级错误进入主干。

## 2. 架构与模块边界（必须遵守）
- `core/`：仅放通用模型、枚举、事件基类，不放业务分支判断。
- `modules/<domain>/models.py`：领域数据结构；`service.py`/`engine.py`：领域行为。
- `integration/adapters.py`：唯一外部系统入口，禁止在其他模块直接调用第三方 SDK/HTTP。
- 依赖方向：`core -> modules` 单向，模块间通过事件/接口协作，禁止循环依赖。

## 3. 编码硬性规则
- Python 3.11+，4 空格缩进，完整类型注解。
- 一个函数只做一件事；超过 60 行必须拆分。
- 禁止魔法值：阈值、模板类型、渠道类型必须枚举化。
- 时间统一使用 UTC 存储（`datetime.now(timezone.utc)`）；展示层再做时区转换。
- 任何 `except` 必须指定异常类型，禁止裸 `except:`。
- 新增接口必须定义输入校验与失败返回结构，错误码可机器解析。

## 4. 业务关键防错清单
- 通知发送：必须支持幂等键（如 `team_id + customer_id + notification_type + window`）。
- 失败重试：区分可重试错误（网络/限流）与不可重试错误（参数非法）。
- 触发规则：默认“安全失败”（条件不满足不发送），必发节点需显式标记 `is_mandatory`。
- 投诉升级：阈值与策略配置化，不允许硬编码在业务分支。
- 满意度回访：低分跟进逻辑必须有审计记录与责任人字段。
- 审计日志：关键动作（建模板、改模板、群发、重发、撤回）必须落审计。

## 5. 测试与质量门禁
- 测试框架：`pytest`。
- 最低要求：
  - 单元测试覆盖核心分支、异常分支、边界值。
  - 每个模块至少包含“成功 + 失败 + 幂等/重复调用”3 类用例。
- 推荐命令：
  - `python -m pip install -e .`
  - `python -m pytest -q`
  - `PYTHONPATH=src python -m app.main`
- 合并门禁（建议 CI 强制）：测试全绿、lint 全绿、无高危安全问题。

## 6. 日志、监控与可观测性
- 日志必须结构化（JSON 风格字段）：`trace_id`, `team_id`, `module`, `event_type`, `result`。
- 不记录敏感信息（手机号、证件号、token 明文）。
- 每个外部调用记录耗时、重试次数、最终状态。
- 至少定义 4 个核心指标：发送成功率、漏发率、触发命中率、投诉升级处理时效。

## 7. 配置与安全
- 所有环境差异项放环境变量，禁止写死在代码。
- 密钥使用 `.env` 或密钥管理服务，禁止入库。
- 新增配置项必须给默认值、注释、样例。
- 对外部输入做白名单校验，避免注入与脏数据扩散。

## 8. Git 与 PR 规范
- Commit 使用 Conventional Commits：`feat:`, `fix:`, `refactor:`, `test:`, `docs:`。
- 一个 PR 只解决一个问题域，禁止“大杂烩提交”。
- PR 必须包含：
  - 变更动机与影响范围。
  - 回滚方案。
  - 测试证据（命令与结果）。
  - 关键日志/监控字段变更说明（如有）。

## 9. 禁止事项（红线）
- 禁止跳过测试直接合并。
- 禁止在业务代码中直接 `print` 调试输出。
- 禁止吞异常后继续返回成功。
- 禁止修改线上数据结构却不提供迁移/兼容策略。
- 禁止绕过审计日志写入关键操作。

## 10. 交付定义（Definition of Done）
满足以下条件才算完成：代码实现 + 测试通过 + 文档更新 + 可观测性到位 + 可回滚。

## 11. 需求提炼 Skill 约定
- 当输入包含 `docx/xlsx` 流程资料并要求输出需求文档时，优先使用：
  - `project-skills/travel-notification-requirements/SKILL.md`
- 标准产出落地到：
  - `docs/travel-notification-system-requirements.md`
- 产出必须包含：
  - 行前/行中/行后全流程
  - 角色职责与协同边界
  - 触发-通知-渠道-兜底矩阵
  - 审计与验收指标
  - P0/P1/P2 与待决策清单

## 12. 自主进化 Memory Skill 约定
- 当需求强调“持续学习、记录每次指令、命令复盘、自我优化”时，必须使用：
  - `project-skills/autonomous-dev-evolution/SKILL.md`
- 最低执行要求：
  - 每条用户新指导记录一条 `user_guidance` 事件。
  - 关键命令通过 `run_with_memory.sh` 执行并自动记录结果。
  - 每个实现周期结束后执行 `distill_playbook.py` 生成快速路径。
- 记忆产物：
  - `.codex-memory/self-evolution/events.ndjson`
  - `.codex-memory/self-evolution/fast_path.md`
  - `.codex-memory/self-evolution/metrics.json`
