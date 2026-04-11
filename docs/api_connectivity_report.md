# 前后端联调接口连通性检查报告

> 检查时间：2026-04-11（UTC）

## 结论（TL;DR）

当前仓库中的**前端页面尚未发起真实 API 请求**，并且后端代码中**未实现 HTTP Web 框架路由**（如 FastAPI `@app.get/@app.post`）。
因此从“前后端联调”的角度看，文档里列出的接口目前都属于“未打通”（不是单个接口 404，而是整层 API 尚未落地）。

## 检查范围

1. 前端是否存在实际 API 调用代码（`axios` / `fetch`）。
2. 后端是否存在 HTTP 入口（FastAPI/Flask 路由与 `app` 实例）。
3. 文档中“预期接口”与现状差异。

## 1) 前端实际调用状态

### 发现

- `frontend` 页面代码目前均为本地 mock 数据/本地状态（`useState`），未调用 `/api/*`。
- 全局只看到了 Vite 代理配置（`/api -> http://localhost:8000`），但没有请求发起方。

### 证据

- 代理存在：`frontend/vite.config.ts`
- 但业务页（`Dashboard/Trips/Notifications/Preferences/Analytics`）均未出现 `axios` 或 `fetch` 调用。

## 2) 后端 HTTP 接口状态

### 发现

- 后端没有发现 FastAPI/Flask 路由定义。
- `src/app/main.py` 仅包含 `bootstrap_demo()` 演示逻辑，不存在 `app = FastAPI()`。
- `src/app/api/bff.py` 是 Python 业务编排类（`ManagementBFF`），不是 HTTP Controller。

### 证据

- 全仓搜索不到 `FastAPI`、`APIRouter`、`@app.get`、`@app.post` 等模式。
- `dev-server.py` 里给出的 `uvicorn app.main:app` 目前与实际代码不一致（`main.py` 无 `app` 对象）。

## 3) 文档预期接口 vs 当前可用性

基于 `frontend/README.md` 与 `API_INTEGRATION.md` 里的接口清单，当前状态如下：

- `GET /api/dashboard/stats`：未实现
- `GET /api/trips`：未实现
- `POST /api/trips`：未实现
- `PUT /api/trips/:id`：未实现
- `DELETE /api/trips/:id`：未实现
- `GET /api/notifications/templates`：未实现
- `POST /api/notifications/send`：未实现
- `GET /api/analytics/metrics`：未实现
- `POST /api/auth/login`：未实现
- `POST /api/auth/logout`：未实现
- `POST /api/auth/refresh`：未实现
- `GET /api/users/me`：未实现

## 4) 为什么你会感觉“联调没通”

不是某 1~2 个接口参数问题，而是当前代码阶段还停留在：

- 前端：UI 原型 + mock 数据。
- 后端：领域模型/服务层 + demo，不是 HTTP API 服务。

这会导致前端即使配置了代理，也没有真实请求；即便补前端请求，后端也无路由可接。

## 5) 建议的最小打通顺序（MVP）

1. 先在后端落地 FastAPI `app` 与最小路由：
   - `GET /api/health`
   - `GET /api/dashboard/stats`
   - `GET /api/trips`
   - `POST /api/trips`
2. 前端先接 `Dashboard` 与 `Trips` 两页，替换掉本地 mock。
3. 增加接口契约测试（后端）+ 前端 API 层封装（`frontend/src/services/api.ts`）。
4. 再逐步补 `notifications/preferences/analytics/auth`。

---

如果你愿意，我下一步可以直接给你补一版“可跑通联调”的最小 FastAPI 路由 + 前端 API Service（先打通 Dashboard + Trips）。
