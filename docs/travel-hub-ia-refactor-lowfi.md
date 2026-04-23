# Travel Hub 二级页 / 三级页低保真重构方案

## 主流程（P0）
1. 行程管理列表页（主入口：Excel / PDF 导入）
2. 导入校验页（识别成功 / 待确认 / 缺失字段）
3. 团详情总览页（导入结果摘要 + 每日时间线 + 客人/接送摘要 + 今日待办）
4. 每日行程页
5. 客人名单页
6. 接送安排页
7. 通知执行页

## 页面级低保真结构

### 1) 行程管理列表页（Trips）
- 顶部 CTA：`Excel导入` `PDF导入` `新建空白团`
- 列表字段：团号、线路、日期范围、当前阶段、数据完整度、今日待办、下一通知节点
- 状态标签：未导入行程、待补全游客、行程已解析、通知未配置、可执行

### 2) 团详情总览页（TripDetail/overview）
- 模块 A：导入结果摘要
- 模块 B：每日行程时间线摘要
- 模块 C：客人名单摘要
- 模块 D：接送安排摘要
- 模块 E：今日待办摘要
- 基础信息下沉到页面底部次级区域

### 3) 导入校验页（TripDetail/import-validation）
- 识别成功字段列表
- 待确认字段（支持手动修正）
- 缺失字段列表
- 按钮：一键确认导入、手动补全

### 4) 三级页
- 每日行程页（TripDetail/itinerary）
- 客人名单页（TripDetail/guests）
- 接送安排页（TripDetail/transfers）
- 通知执行页（TripDetail/notifications）

## 组件拆分（先 IA 后样式）
- `pages/Trips.tsx`
  - 行程管理主容器
  - 导入入口与团列表状态
- `pages/TripDetail.tsx`
  - 团详情容器
  - 二级导航（总览、导入校验、四个三级页）
- `features/trip-management/tripImportAdapter.ts`
  - `buildImportFlowSnapshot()`：基于现有 trip + execution 数据生成导入快照（mock/adapter）
  - 负责字段识别、缺失判断、完整度计算

## 技术策略（约束）
- 不调整后端数据库结构。
- 导入识别、接送安排与字段分组先走前端 adapter/mock。
- 当前以信息架构和任务流为主，不做视觉精修。

## 当前实现状态（已完成前后端联调）
- 前端：
  - `Trips` 保留 Excel/PDF/空白团入口，支持真实 Excel 导入。
  - `TripDetail` 的「导入校验」已改为调用后端接口，不再只依赖前端 mock。
  - 导入校验页的「一键确认导入 / 手动补全」会回写后端并实时刷新快照。
- 后端：
  - 新增 `GET /api/trips/{trip_id}/import-snapshot`：返回识别成功、待确认、缺失字段、完整度、行程/客人/接送摘要。
  - 新增 `PUT /api/trips/{trip_id}/import-validation`：接收手工修正字段并更新行程数据，返回最新校验快照。
  - 保持现有数据库结构不变。

## Excel 验证样例（已落库到仓库）
- 功能验证用（开发侧）：`docs/import-samples/trip-import-validation-internal.csv`
- 交付验证用（你可直接导入验证）：`docs/import-samples/trip-import-validation-client.csv`

> 说明：使用 CSV 是为了避免代码托管平台对二进制 diff 的限制；CSV 可直接用 Excel 打开和编辑。

> 推荐验证步骤：
> 1. 在 Trips 页使用 `Excel导入` 上传 client 文件。
> 2. 进入任一团详情，打开「导入校验」页。
> 3. 确认缺失字段展示（如领队电话），手工补全后点击保存。
> 4. 验证缺失字段数量、完整度、今日待办摘要是否刷新。
