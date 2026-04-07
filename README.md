# Travel Notification System (MVP)

已按你给出的架构建议重构为“接入层 + 业务服务层 + 事件异步层 + 数据能力抽象”的后端实现骨架。

## 本期范围

- **P0（已实现骨架）**
  - 用户/行程/偏好模型
  - 事件接入（内部 API + Outbox + EventBus）
  - 固定规则引擎（优先级、基础频控）
  - 模板服务（zh/en 结构可扩展，当前示例含 zh）
  - 多渠道分发（Email + Push）
  - 发送记录（成功/失败/重试/跳过）
  - 幂等 + 去重 + 重试 + 基础降级
  - 管理后台最小能力（模板、规则、偏好开关接口）

- **P1（已实现部分能力）**
  - 增加 SMS provider 适配器
  - 用户级免打扰时段
  - 模板版本 + A/B bucket 字段
  - 主通道失败自动回退

## 代码结构

```text
src/app/
  api/bff.py                 # 接入层（行程/偏好/模板/规则/事件）
  core/entities.py           # 领域模型
  core/event_bus.py          # Outbox + InMemory EventBus
  services/
    trip_service.py
    preference_service.py
    template_service.py
    rule_engine.py
    dispatch_service.py
  providers/adapters.py      # Email/Push/SMS Provider Adapter
  main.py                    # 启动与端到端示例
```

## 运行

```bash
PYTHONPATH=src python -m pytest -q
PYTHONPATH=src python -m app.main
```
