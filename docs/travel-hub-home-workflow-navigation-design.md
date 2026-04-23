# Travel Hub 首页四卡片（二级/三级页）结构方案

> 目标：围绕“按工作流处理任务”的运营后台场景，为首页 4 个统计卡片（待办任务、逾期任务、高风险团、待接管）建立清晰的**页面层级、跳转规则、状态机与前端实现骨架**。本方案优先信息架构与交互闭环，不依赖复杂后端改造。

---

## 1. 信息架构图（文字版）

### 1.1 总体页面层级

```text
L1 首页 /travel-hub
├── 卡片1：待办任务（Todo）
│   └── L2 任务工作台 /workbench/tasks?bucket=todo
│       └── L3 任务详情 /workbench/tasks/:taskId
├── 卡片2：逾期任务（Overdue）
│   └── L2 任务工作台 /workbench/tasks?bucket=overdue
│       └── L3 任务详情 /workbench/tasks/:taskId
├── 卡片3：高风险团（High Risk Groups）
│   └── L2 高风险团列表 /workbench/risk-groups?bucket=high
│       └── L3 高风险团详情 /workbench/risk-groups/:groupId
└── 卡片4：待接管（Pending Takeover）
    └── L2 待接管池 /workbench/takeovers?bucket=pending
        ├── （主操作）接管并分配给我
        └── （接管后）跳转 L3 任务详情 /workbench/tasks/:taskId
```

### 1.2 首页卡片点击去向（明确映射）

- 点击“待办任务”卡片（数字区或标题）：进入`任务工作台`并预置筛选`bucket=todo`。
- 点击“逾期任务”卡片：进入`任务工作台`并预置筛选`bucket=overdue`（默认按逾期时长倒序）。
- 点击“高风险团”卡片：进入`高风险团列表`并预置`riskLevel in [high, critical]`。
- 点击“待接管”卡片：进入`待接管池`并预置`status=pending_takeover`。

---

## 2. 4 个二级页方案

## 2.1 待办任务（Todo）

### 业务定义
- **定义**：当前登录运营人员“应处理且未完成”的任务集合。
- **进入条件**：`assignee_id = current_user` 且 `status in [todo, in_progress, blocked]`。
- **筛选逻辑**：按业务阶段（行前/行中/行后）、截止时间、任务类型（通知/确认/回访/投诉）、线路/团号筛选。
- **主要操作**：开始处理、标记阻塞、完成、改派、查看详情。

### 二级页低保真结构（文字）
1. **顶部统计区**
   - 今日待办数
   - 2 小时内到期
   - 已阻塞
   - 平均处理时长（近 7 天）
2. **筛选区**
   - 快捷筛选：全部待办 / 即将到期 / 已阻塞
   - 高级筛选：阶段、任务类型、团号、优先级、渠道
3. **列表区**
   - 列字段：任务标题、关联团、阶段、截止时间、优先级、当前状态、建议动作
   - 默认排序：`优先级 desc` + `截止时间 asc`
4. **批量操作区**
   - 批量“开始处理”
   - 批量“改派”
   - 批量“标记完成”
5. **空状态**
   - 文案：`当前没有待办任务，建议查看高风险团是否有新增预警。`
   - CTA：`前往高风险团`
6. **点击交互**
   - 点击行：进入任务详情
   - 点击状态Tag：弹出状态变更菜单（不离页）
   - 点击“处理”按钮：直接置为`in_progress`并打开右侧抽屉（快速处理）

---

## 2.2 逾期任务（Overdue）

### 业务定义
- **定义**：超过截止时间仍未完成的任务。
- **进入条件**：`status != done` 且 `due_at < now()`。
- **筛选逻辑**：按逾期时长（<2h、2-24h、>24h）、风险等级、是否影响出团节点筛选。
- **主要操作**：立即处理、升级预警、申请延期、转接管。

### 二级页低保真结构（文字）
1. **顶部统计区**
   - 逾期总数
   - 严重逾期（>24h）
   - 影响出行节点数
   - 今日已清理数
2. **筛选区**
   - 快捷：全部 / 严重逾期 / 出发前关键节点
   - 高级：逾期时长、团风险等级、负责人、任务类型
3. **列表区**
   - 强调字段：逾期时长（红色）、是否阻断节点、当前负责人
   - 默认排序：`阻断节点 desc` + `逾期时长 desc`
4. **批量操作区**
   - 批量升级（通知主管）
   - 批量延期申请
   - 批量转入待接管
5. **空状态**
   - 文案：`暂无逾期任务，继续保持。`
6. **点击交互**
   - 行点击：进入任务详情并定位到“逾期原因”区
   - “升级”按钮：弹框填写原因 + 通知对象
   - “延期”按钮：填写新 SLA 与备注

---

## 2.3 高风险团（High Risk Groups）

### 业务定义
- **定义**：以“团”为单位聚合风险信号后，风险评分超过阈值的团。
- **进入条件**：`group_risk_score >= threshold_high` 或命中关键规则（极端天气/大面积延误/多投诉聚集）。
- **筛选逻辑**：按风险等级、出团日期、目的地、风险类型（天气/航班/舆情/投诉）筛选。
- **主要操作**：进入团详情、发起团级预案、批量创建衍生任务、指定值守人。

### 二级页低保真结构（文字）
1. **顶部统计区**
   - 高风险团数
   - 今日新增高风险
   - 临近出发高风险团
   - 已启动预案数
2. **筛选区**
   - 快捷：全部高风险 / 极高风险 / 48h 内出发
   - 高级：线路、目的地、风险来源、当前处置状态
3. **列表区（团视角，不是任务视角）**
   - 列字段：团号、线路、出发时间、风险分、Top3 风险因子、未闭环任务数、值守人
   - 可展开查看团内关键任务摘要
4. **批量操作区**
   - 批量指定值守人
   - 批量触发预警通知
   - 批量生成团级处置任务包
5. **空状态**
   - 文案：`当前无高风险团。建议关注天气与航变监控。`
6. **点击交互**
   - 点击团行：进入高风险团详情（三级）
   - 点击“创建任务包”：按模板生成多条任务并进入待办池

---

## 2.4 待接管（Pending Takeover）

### 业务定义
- **定义**：尚无人负责或原负责人不可用，需要新的处理人接手的任务池。
- **进入条件**：`status = pending_takeover` 或 `assignee_id is null` 且命中接管规则。
- **筛选逻辑**：按来源（自动转入/人工转交）、紧急度、所属团队、是否关键节点筛选。
- **主要操作**：接管、拒绝接管并说明原因、转派、批量接管。

### 二级页低保真结构（文字）
1. **顶部统计区**
   - 待接管总数
   - 紧急待接管
   - 关键节点待接管
   - 平均等待接管时长
2. **筛选区**
   - 快捷：全部 / 紧急 / 关键节点
   - 高级：来源类型、所属业务组、任务类型、团风险等级
3. **列表区**
   - 列字段：任务标题、来源、等待时长、紧急度、关联团、建议接管角色
4. **批量操作区**
   - 批量接管给我
   - 批量转派至某角色
   - 批量拒绝并回退队列
5. **空状态**
   - 文案：`当前没有待接管任务。`
6. **点击交互**
   - 点击行：进入任务详情（只读）
   - 点击“接管”按钮：
     - `assignee_id = current_user`
     - 状态从`pending_takeover -> todo`
     - 成功后 toast：`已接管，已进入待办任务`
     - 支持“接管后立即处理”跳转任务详情

---

## 3. 2 个三级页方案

## 3.1 任务详情页（/workbench/tasks/:taskId）

### 页面分区
1. **头部区（固定）**
   - 任务标题、状态、优先级、剩余 SLA/逾期时长
   - 快捷按钮：开始处理 / 标记完成 / 标记阻塞 / 转接管 / 改派
2. **左栏主体（约 70%）**
   - A. 基本信息卡：任务类型、关联团、阶段（行前/行中/行后）、触发规则、截止时间
   - B. 处理表单区：本次处理动作、备注、通知对象、附件
   - C. 时间线区：创建、状态变更、通知发送、人工处理日志
3. **右栏辅助（约 30%）**
   - D. AI 建议区：建议动作、建议话术、风险提示
   - E. 关联信息区：团关键信息快照（天气/航班/投诉）
   - F. 协同区：@协同人、责任人切换记录

### 关键字段
- `task_id`, `title`, `status`, `priority`, `due_at`, `overdue_minutes`, `assignee`, `trip_id`, `trigger_rule_id`, `source_type`。

### 操作按钮建议
- 主按钮：`开始处理`（todo->in_progress）/`标记完成`（in_progress->done）
- 次按钮：`阻塞`、`改派`、`转待接管`、`升级`

### 时间线 / 处理记录 / AI 建议摆放
- 时间线放左栏中下部（处理表单之后），便于“先处理后复盘”。
- AI 建议固定在右栏顶部，保持始终可见。
- 处理记录与时间线合并展示，按“系统事件 + 人工动作”统一排序。

---

## 3.2 高风险团详情页（/workbench/risk-groups/:groupId）

### 页面分区
1. **头部总览**
   - 团号、线路、出发日期、风险等级、风险分、当前值守人
   - 按钮：启动预案、指定值守、创建任务包、发送团级通知
2. **左栏主体（约 70%）**
   - A. 风险因子面板：天气、航班、投诉、供应商、舆情（分值与趋势）
   - B. 团级任务矩阵：未处理/处理中/逾期任务分布
   - C. 时间线：风险变化、处置动作、通知触达记录
3. **右栏辅助（约 30%）**
   - D. AI 团级建议：优先处置项、沟通策略、预案模板
   - E. 核心成员与联系人：领队、地接、客服主管、应急联系人
   - F. 关键阈值看板：下一风险阈值触发条件

### 关键字段
- `group_id`, `trip_code`, `route_name`, `departure_date`, `risk_level`, `risk_score`, `risk_factors[]`, `open_task_count`, `owner`, `watchers[]`。

### 操作按钮建议
- `启动预案`：生成团级处置流程与任务包。
- `创建任务包`：按风险模板生成若干任务（自动进入待办/待接管）。
- `指定值守人`：保障团级 owner 清晰。

### 时间线 / 处理记录 / AI 建议摆放
- 团级时间线放左栏，体现风险变化和处置闭环。
- AI 团级建议放右栏顶部，支持“一键生成任务包”。
- 处理记录按“事件（风险）—动作（运营）—结果（通知/状态）”三段展示。

---

## 4. 跳转与状态流转说明

## 4.1 首页“待我处理”模块跳转逻辑

1. **点击模块标题“待我处理”**
   - 跳转：`/workbench/tasks?bucket=my_queue`
   - 默认筛选：`assignee_id=current_user` + `status in [todo,in_progress,blocked,overdue]`

2. **点击某条任务**
   - 跳转：`/workbench/tasks/:taskId`
   - 若任务状态为`pending_takeover`且当前人非负责人：先弹接管确认，再进入详情。

3. **点击右侧状态标签或操作按钮**
   - 点击状态标签：打开状态菜单（就地变更）
     - todo -> in_progress
     - in_progress -> done
     - blocked -> in_progress
     - overdue -> in_progress 或 pending_takeover
   - 点击操作按钮（如“处理”“接管”“完成”）：直接执行动作并 toast 提示。

4. **是否展示 done 状态任务**
   - 默认**不展示 done**（保持工作清单纯净）。
   - 提供“显示已完成（近24h）”开关用于复盘，默认关闭。

## 4.2 简化状态机设计

### 状态定义
- `todo`：已分配，待开始。
- `in_progress`：处理中。
- `done`：已完成。
- `overdue`：超时未完成（可视为派生状态，也可持久化为显式状态）。
- `pending_takeover`：待接手。
- `blocked`：受阻，需外部条件解除。

### 流转规则（建议）

```text
todo -> in_progress        （开始处理）
in_progress -> done        （处理完成）
in_progress -> blocked     （遇到阻塞）
blocked -> in_progress     （阻塞解除）

(todo|in_progress|blocked) --超时--> overdue
overdue -> in_progress     （恢复处理）
overdue -> pending_takeover（申请转接）

pending_takeover -> todo   （被某人接管）
pending_takeover -> blocked（无人可接且外部阻塞）

(done) 为终态，默认不可回退；如需回退需“重新打开”特权操作：done -> in_progress。
```

### 关键约束
- `overdue`可由系统定时任务自动标记。
- `pending_takeover -> todo`必须写入新`assignee_id`。
- `blocked`必须填写阻塞原因与预计恢复时间。

---

## 5. 前端目录与类型定义建议

## 5.1 推荐路由结构（React Router）

```ts
/travel-hub                                  // 首页
/workbench/tasks?bucket=todo                 // 二级：待办任务
/workbench/tasks?bucket=overdue              // 二级：逾期任务
/workbench/takeovers?bucket=pending          // 二级：待接管
/workbench/risk-groups?bucket=high           // 二级：高风险团
/workbench/tasks/:taskId                     // 三级：任务详情
/workbench/risk-groups/:groupId              // 三级：高风险团详情
```

## 5.2 推荐页面文件结构

```text
src/
  pages/
    travel-hub/
      HomePage.tsx
      components/
        StatCard.tsx
        MyQueuePanel.tsx
        MyQueueItem.tsx
    workbench/
      tasks/
        TaskWorkbenchPage.tsx
        TaskDetailPage.tsx
        components/
          TaskFilterBar.tsx
          TaskTable.tsx
          TaskBatchActions.tsx
      takeovers/
        TakeoverPoolPage.tsx
      risk-groups/
        RiskGroupListPage.tsx
        RiskGroupDetailPage.tsx
        components/
          RiskFactorPanel.tsx
          GroupTaskMatrix.tsx
  types/
    task.ts
    risk-group.ts
  services/
    taskService.ts
    riskGroupService.ts
  hooks/
    useTaskActions.ts
    useRiskGroupActions.ts
```

## 5.3 任务数据类型定义（TypeScript）

```ts
export type TaskStatus =
  | 'todo'
  | 'in_progress'
  | 'done'
  | 'overdue'
  | 'pending_takeover'
  | 'blocked';

export type JourneyPhase = 'pre_trip' | 'on_trip' | 'post_trip';

export interface TaskItem {
  id: string;
  title: string;
  tripId: string;
  tripCode: string;
  phase: JourneyPhase;
  type: 'notify' | 'confirm' | 'follow_up' | 'complaint' | 'risk_dispose';
  status: TaskStatus;
  priority: 'P0' | 'P1' | 'P2';
  dueAt: string;
  overdueMinutes?: number;
  assigneeId?: string;
  assigneeName?: string;
  source: 'rule_engine' | 'manual' | 'ai_suggestion' | 'takeover';
  canTakeover: boolean;
  blockerReason?: string;
  updatedAt: string;
}
```

## 5.4 风险团数据类型定义（TypeScript）

```ts
export type RiskLevel = 'medium' | 'high' | 'critical';

export interface RiskFactor {
  factorType: 'weather' | 'flight' | 'complaint' | 'supplier' | 'public_opinion';
  score: number;
  trend: 'up' | 'flat' | 'down';
  summary: string;
}

export interface RiskGroupItem {
  id: string;
  tripId: string;
  tripCode: string;
  routeName: string;
  departureDate: string;
  riskLevel: RiskLevel;
  riskScore: number;
  riskFactors: RiskFactor[];
  openTaskCount: number;
  overdueTaskCount: number;
  ownerId?: string;
  ownerName?: string;
  updatedAt: string;
}
```

## 5.5 首页卡片点击事件如何接路由

```ts
const onCardClick = (card: 'todo' | 'overdue' | 'high_risk_group' | 'pending_takeover') => {
  const routeMap = {
    todo: '/workbench/tasks?bucket=todo',
    overdue: '/workbench/tasks?bucket=overdue',
    high_risk_group: '/workbench/risk-groups?bucket=high',
    pending_takeover: '/workbench/takeovers?bucket=pending',
  } as const;

  navigate(routeMap[card]);
};
```

## 5.6 “待我处理”列表项组件抽象建议

- 组件：`MyQueueItem`
- 输入：`task: TaskItem`, `onOpenDetail`, `onQuickAction`
- 输出事件：
  - `open_detail(taskId)`
  - `change_status(taskId, nextStatus)`
  - `takeover(taskId)`
  - `complete(taskId)`
- UI 构成：标题 + 副标题（团号/线路/截止）+ 状态Tag + 快捷按钮区。
- 交互原则：
  - 行点击与按钮点击事件隔离（避免误跳转）
  - done 状态样式弱化，默认不出现在列表
  - overdue/pending_takeover 需要高亮并附带动作按钮

---

## 实现原则对齐（结论）

- 该方案以**旅游管家/行程运营**语境定义字段和流程，不是通用 OA。
- 首页到二级页按“工作流桶（bucket）”组织，保证一眼进入处理上下文。
- 高风险团页面坚持“团视角聚合风险+任务矩阵”，不退化为普通任务列表。
- 待接管显式提供“接管后流入待办（pending_takeover -> todo）”闭环。
- 当前先落地结构、路由、数据模型与交互；后端可先 mock / adapter 对接，逐步替换为真实接口。
