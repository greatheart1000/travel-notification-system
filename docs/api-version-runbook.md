# API 版本启动与验证命令

本文档用于启动当前“前端通过 API 渲染”的版本。目标是让 API 返回结果与 `frontend/src/data/figmaMockData.ts` 中的 mock 数据严格一致，并让前端通过同源 `/api` 调用渲染页面。

## 前置条件

- MySQL 已启动。
- MySQL 用户名：`root`
- MySQL 密码：`testpass123`
- MySQL 数据库：`travel_hub`
- 当前工作目录：项目根目录 `/mnt/d/project/travel-notification-system`

## 1. 安装前端依赖

首次运行或依赖缺失时执行：

```bash
npm --prefix frontend install
```

如果 `frontend/node_modules` 已存在，可以跳过这一步。

## 2. 初始化 MySQL Mock 数据

后端会读取 `frontend/src/data/figmaMockData.ts`，写入 MySQL 的 `travel_hub.mock_documents`，再由 API 从数据库读取返回。

```bash
node mock-mysql-api.cjs --init-only
```

成功时会输出类似：

```bash
{"ok":true,"sourceHash":"...","keys":["makeStatusColorMap","mockTrips","mockWeather","mockTripDetails","mockImportedTourists","mockAnalyticsData","all","tripList","warningWeather"]}
```

## 3. 启动后端 API

新开一个终端，执行：

```bash
node mock-mysql-api.cjs
```

默认监听：

```text
http://127.0.0.1:3001
```

健康检查：

```bash
curl http://127.0.0.1:3001/health
```

## 4. 启动前端 API 版本

新开另一个终端，执行：

```bash
npm --prefix frontend run dev -- --host 0.0.0.0
```

默认访问：

```text
http://127.0.0.1:5173
```

当前前端 API 调用使用同源 `/api`，由 `frontend/vite.config.ts` 代理到 `http://127.0.0.1:3001`。不要使用 Python 静态服务启动 5173，否则 `/api` 代理不会生效，页面可能显示 `Failed to fetch`。

## 5. 验证 API 与 Mock 严格一致

执行：

```bash
node verify-mock-mysql-api.cjs
```

成功结果：

```bash
strict JSON equality ok: 71 endpoints
```

该验证会检查字段名称、JSON 结构、数据类型、嵌套层级、数组内容和行程详情路由参数等关键 API 输出。

## 6. 验证前端同源 API

```bash
curl http://127.0.0.1:5173/api/trips
curl http://127.0.0.1:5173/api/analytics
```

快速检查首条行程：

```bash
curl -sS http://127.0.0.1:5173/api/trips | node -e 'let s="";process.stdin.on("data",c=>s+=c).on("end",()=>{const d=JSON.parse(s); console.log(d.length, d[0].id, d[0].teamId, d[0].name)})'
```

期望输出：

```bash
12 trip-001 TEAM-DEMO-POST 阿勒泰本地冬营团
```

## 7. 页面访问地址

- 行程列表：http://127.0.0.1:5173/trips
- 行程详情：http://127.0.0.1:5173/trips/TEAM-DEMO-POST
- 数据分析：http://127.0.0.1:5173/analytics

如果浏览器仍显示旧错误，强制刷新：

```text
Ctrl + Shift + R
```

## 8. 常见问题

### 页面显示 `Failed to fetch`

优先检查：

```bash
curl http://127.0.0.1:3001/health
curl http://127.0.0.1:5173/api/trips
```

如果 `3001` 正常但 `5173/api/trips` 不正常，说明前端不是由 Vite 启动，或者 5173 被其他静态服务占用。停止占用 5173 的进程后重新执行：

```bash
npm --prefix frontend run dev -- --host 0.0.0.0
```

### 需要重置 API 数据到 Mock 初始状态

```bash
curl -X POST http://127.0.0.1:3001/api/mock-data/reset
node verify-mock-mysql-api.cjs
```

### 需要生产构建检查

```bash
npm --prefix frontend run build
```

## 9. 一键本地验证顺序

按顺序执行以下命令：

```bash
node mock-mysql-api.cjs --init-only
node verify-mock-mysql-api.cjs
npm --prefix frontend run build
```

然后分别启动后端和前端：

```bash
node mock-mysql-api.cjs
```

```bash
npm --prefix frontend run dev -- --host 0.0.0.0
```
