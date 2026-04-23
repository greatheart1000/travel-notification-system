# Workbench API Blueprint (Mock-first -> Real API)

## 1) Dashboard
- GET `/api/workbench/dashboard`
  - query: `owner_scope=mine`
  - response: `{ todo_count, overdue_count, high_risk_group_count, pending_takeover_count, my_queue: TaskSummary[] }`
  - consumed fields: card counts + my queue list
  - mock-only now: `ai_hint_cards`

## 2) Tasks
- GET `/api/workbench/tasks`
  - query: `bucket`, `keyword`, `risk_level`, `overdue_window`
  - response: `{ items: TaskDTO[], stats: { total, urgent, due_soon, high_risk } }`

- GET `/api/workbench/tasks/{task_id}`
  - response: `TaskDetailDTO`

- POST `/api/workbench/tasks/{task_id}/takeover`
  - body: `{ operator_id }`
  - mutation: `pending_takeover -> todo`

- POST `/api/workbench/tasks/{task_id}/status`
  - body: `{ status, reason? }`
  - mutation actions: 完成、延期、转派、标记风险

## 3) High Risk Groups
- GET `/api/workbench/groups/high-risk`
  - query: `risk_level`, `departure_window`
  - response: `{ items: RiskGroupDTO[], stats: { total, critical, departing_soon, pending_tasks } }`

- GET `/api/workbench/groups/high-risk/{group_id}`
  - response: `RiskGroupDetailDTO`

## 4) Field completion plan
- Already mocked and consumed by frontend:
  - Task: `aiSuggestion`, `history`, `destination`, `tags`
  - Group: `timeline`, `collaborators`, `riskTags`, `summary`
- Need backend completion later:
  - `overdue_minutes`, `sla_remaining_minutes`, `channel_delivery_status`, `risk_factor_breakdown`
