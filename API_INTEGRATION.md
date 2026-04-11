# 🔌 API 集成指南

> Travel Hub 前后端 API 接口设计与集成说明

## 📋 目录

1. [API 基础配置](#api-基础配置)
2. [认证方案](#认证方案)
3. [API 端点设计](#api-端点设计)
4. [数据模型](#数据模型)
5. [错误处理](#错误处理)
6. [前端集成示例](#前端集成示例)
7. [联调测试](#联调测试)

---

## 🌐 API 基础配置

### 服务器地址

```typescript
// vite.config.ts 中的代理配置
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/api/, '/api'),
  },
}
```

### 请求基础 URL

| 环境 | 地址 | 超时 |
|------|------|------|
| 开发 | http://localhost:8000 | 30s |
| 测试 | https://test-api.travelhub.com | 30s |
| 生产 | https://api.travelhub.com | 30s |

### HTTP Headers

```typescript
// 所有请求都应包含以下 headers
{
  'Content-Type': 'application/json',
  'Accept': 'application/json',
  'Authorization': 'Bearer {token}', // 认证后添加
  'X-Client-Version': '0.1.0',
  'X-Request-ID': '{unique-id}', // 用于追踪
}
```

---

## 🔐 认证方案

### JWT Token 认证 (推荐)

**登录流程:**
```
用户输入用户名/密码
        ↓
发送 POST /api/auth/login
        ↓
返回 { access_token, refresh_token, expires_in }
        ↓
保存 token 到 localStorage
        ↓
后续请求添加 Authorization header
```

**前端实现:**
```typescript
// src/services/auth.ts
import axios from 'axios'

const API = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 30000,
})

// 请求拦截器：自动添加 token
API.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器：处理 401 错误
API.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // token 过期，刷新或重新登录
      localStorage.removeItem('access_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export const login = (username: string, password: string) => {
  return API.post('/auth/login', { username, password })
}

export const logout = () => {
  localStorage.removeItem('access_token')
  return API.post('/auth/logout')
}
```

**后端实现 (FastAPI 示例):**
```python
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials
import jwt

app = FastAPI()
security = HTTPBearer()

@app.post("/api/auth/login")
async def login(username: str, password: str):
    # 验证用户名和密码
    user = authenticate_user(username, password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # 生成 JWT token
    token = jwt.encode(
        {"sub": user.id, "exp": datetime.now() + timedelta(hours=24)},
        "your-secret-key",
        algorithm="HS256"
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": 86400
    }

async def get_current_user(credentials: HTTPAuthCredentials = Depends(security)):
    try:
        payload = jwt.decode(
            credentials.credentials,
            "your-secret-key",
            algorithms=["HS256"]
        )
        user_id = payload.get("sub")
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

    return get_user(user_id)

@app.get("/api/users/me")
async def get_me(current_user = Depends(get_current_user)):
    return current_user
```

### OAuth 2.0 (可选)

支持第三方登录：
- 微信企业号
- 钉钉
- 飞书

---

## 📡 API 端点设计

### 基础规范

| 方法 | 用途 | 返回 |
|------|------|------|
| GET | 获取资源 | 200 OK / 404 Not Found |
| POST | 创建资源 | 201 Created |
| PUT | 完全更新 | 200 OK |
| PATCH | 部分更新 | 200 OK |
| DELETE | 删除资源 | 204 No Content / 200 OK |

### 完整 API 列表

#### 认证相关

```typescript
// 用户登录
POST /api/auth/login
Request:
{
  "username": "admin",
  "password": "123456"
}
Response:
{
  "code": 200,
  "data": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "token_type": "bearer",
    "expires_in": 86400
  }
}

// 用户登出
POST /api/auth/logout
Response: { "code": 200 }

// 刷新 token
POST /api/auth/refresh
Request: { "refresh_token": "..." }
Response: { "access_token": "...", "expires_in": 86400 }

// 获取当前用户
GET /api/users/me
Response:
{
  "code": 200,
  "data": {
    "id": "user-001",
    "username": "admin",
    "email": "admin@travelhub.com",
    "role": "admin",
    "created_at": "2026-04-11T00:00:00Z"
  }
}
```

#### 仪表盘

```typescript
// 获取统计数据
GET /api/dashboard/stats
Response:
{
  "code": 200,
  "data": {
    "today_notifications": 1234,
    "active_trips": 45,
    "total_users": 2856,
    "pending_complaints": 12,
    "notification_success_rate": 98.5
  }
}

// 获取最近通知
GET /api/notifications/recent?limit=10
Response:
{
  "code": 200,
  "data": {
    "total": 10,
    "items": [
      {
        "id": "notif-001",
        "customer_name": "张三",
        "trip": "乌鲁木齐-喀什",
        "channel": "SMS",
        "status": "sent",
        "created_at": "2026-04-11T12:00:00Z"
      }
    ]
  }
}
```

#### 行程管理

```typescript
// 获取行程列表
GET /api/trips?page=1&limit=20&status=active
Response:
{
  "code": 200,
  "data": {
    "total": 45,
    "page": 1,
    "items": [
      {
        "id": "trip-001",
        "destination": "乌鲁木齐-喀什",
        "team_id": "TEAM-001",
        "start_date": "2026-04-15",
        "end_date": "2026-04-20",
        "participants": 28,
        "status": "active"
      }
    ]
  }
}

// 获取单个行程
GET /api/trips/{trip_id}
Response:
{
  "code": 200,
  "data": {
    "id": "trip-001",
    "destination": "乌鲁木齐-喀什",
    "team_id": "TEAM-001",
    "start_date": "2026-04-15",
    "end_date": "2026-04-20",
    "participants": 28,
    "status": "active",
    "created_by": "user-001",
    "created_at": "2026-04-11T00:00:00Z"
  }
}

// 创建行程
POST /api/trips
Request:
{
  "destination": "乌鲁木齐-喀什",
  "team_id": "TEAM-001",
  "start_date": "2026-04-15",
  "end_date": "2026-04-20"
}
Response: { "code": 201, "data": { "id": "trip-001", ... } }

// 更新行程
PUT /api/trips/{trip_id}
Request:
{
  "destination": "乌鲁木齐-伊犁",
  "end_date": "2026-04-22"
}
Response: { "code": 200, "data": { ... } }

// 删除行程
DELETE /api/trips/{trip_id}
Response: { "code": 204 }
```

#### 通知管理

```typescript
// 获取通知模板列表
GET /api/notifications/templates
Response:
{
  "code": 200,
  "data": {
    "items": [
      {
        "id": "tpl-001",
        "name": "每日提醒",
        "content": "{{customer_name}}，您好，明日行程请注意保暖...",
        "channel": "SMS",
        "enabled": true,
        "sent_count": 1234,
        "success_rate": 98.5
      }
    ]
  }
}

// 创建通知模板
POST /api/notifications/templates
Request:
{
  "name": "每日提醒",
  "content": "{{customer_name}}，您好，明日行程...",
  "channel": "SMS"
}
Response: { "code": 201, "data": { "id": "tpl-001", ... } }

// 更新通知模板
PUT /api/notifications/templates/{template_id}
Request: { "content": "...", "enabled": true }
Response: { "code": 200, "data": { ... } }

// 删除通知模板
DELETE /api/notifications/templates/{template_id}
Response: { "code": 204 }

// 发送测试通知
POST /api/notifications/send-test
Request:
{
  "template_id": "tpl-001",
  "customer_id": "C-001",
  "variables": { "customer_name": "张三" }
}
Response:
{
  "code": 200,
  "data": {
    "status": "sent",
    "message": "Test notification sent successfully"
  }
}

// 获取通知历史
GET /api/notifications/history?limit=20
Response:
{
  "code": 200,
  "data": {
    "items": [
      {
        "id": "hist-001",
        "template_id": "tpl-001",
        "customer_id": "C-001",
        "channel": "SMS",
        "status": "sent",
        "sent_at": "2026-04-11T12:00:00Z"
      }
    ]
  }
}
```

#### 偏好设置

```typescript
// 获取用户偏好
GET /api/preferences
Response:
{
  "code": 200,
  "data": {
    "user_id": "user-001",
    "channels": ["SMS", "WECHAT"],
    "quiet_hours": { "start": "22:00", "end": "08:00" },
    "max_notifications_per_hour": 5,
    "auto_escalation": true,
    "aggregate_notifications": true
  }
}

// 更新用户偏好
PUT /api/preferences
Request:
{
  "channels": ["SMS", "WECHAT"],
  "quiet_hours": { "start": "22:00", "end": "08:00" },
  "max_notifications_per_hour": 5
}
Response: { "code": 200, "data": { ... } }
```

#### 数据分析

```typescript
// 获取关键指标
GET /api/analytics/metrics
Response:
{
  "code": 200,
  "data": {
    "notification_success_rate": 98.5,
    "average_response_time": 1.2,
    "weekly_growth": 15.3,
    "customer_satisfaction": 4.5
  }
}

// 获取渠道性能
GET /api/analytics/channels
Response:
{
  "code": 200,
  "data": {
    "items": [
      {
        "channel": "SMS",
        "sent": 5234,
        "successful": 5156,
        "failed": 78,
        "success_rate": 98.5
      }
    ]
  }
}

// 获取行程排行
GET /api/analytics/trips/ranking
Response:
{
  "code": 200,
  "data": {
    "items": [
      {
        "id": "trip-001",
        "name": "乌鲁木齐-喀什",
        "notifications": 1234,
        "satisfaction": 4.6
      }
    ]
  }
}
```

---

## 📦 数据模型

### 用户 (User)

```typescript
interface User {
  id: string
  username: string
  email: string
  password_hash: string // 仅在后端存储
  role: 'admin' | 'manager' | 'user'
  created_at: string // ISO 8601
  updated_at: string
}
```

### 行程 (Trip)

```typescript
interface Trip {
  id: string
  destination: string // 例: "乌鲁木齐-喀什"
  team_id: string // 例: "TEAM-001"
  start_date: string // "2026-04-15"
  end_date: string
  participants: number
  status: 'planned' | 'active' | 'completed' | 'cancelled'
  created_by: string // user_id
  created_at: string
  updated_at: string
}
```

### 通知模板 (NotificationTemplate)

```typescript
interface NotificationTemplate {
  id: string
  name: string // 例: "每日提醒"
  content: string // 支持 {{variable}} 格式
  channel: 'SMS' | 'WECHAT' | 'EMAIL'
  enabled: boolean
  version: number // 版本控制
  ab_bucket?: 'A' | 'B' // A/B 测试
  sent_count: number
  success_rate: number // 0-100
  created_at: string
  updated_at: string
}
```

### 通知任务 (NotificationTask)

```typescript
interface NotificationTask {
  id: string
  template_id: string
  customer_id: string
  team_id: string
  rendered_content: string // 渲染后的内容
  channel: string
  status: 'pending' | 'sent' | 'failed' | 'delivered'
  error_message?: string
  created_at: string
  sent_at?: string
}
```

### 用户偏好 (Preference)

```typescript
interface Preference {
  user_id: string
  channels: string[] // ['SMS', 'WECHAT']
  quiet_hours: {
    start: string // "22:00"
    end: string   // "08:00"
  }
  max_notifications_per_hour: number
  auto_escalation: boolean
  aggregate_notifications: boolean
  created_at: string
  updated_at: string
}
```

### 投诉 (Complaint)

```typescript
interface Complaint {
  id: string
  customer_id: string
  team_id: string
  trip_id: string
  sentiment_score: number // -1.0 to 1.0
  content: string
  status: 'open' | 'in_progress' | 'resolved' | 'closed'
  escalated: boolean
  created_at: string
  resolved_at?: string
}
```

### 满意度反馈 (SurveyResponse)

```typescript
interface SurveyResponse {
  id: string
  customer_id: string
  team_id: string
  trip_id: string
  score: number // 1-5
  comment?: string
  follow_up_required: boolean
  created_at: string
}
```

---

## ❌ 错误处理

### 标准错误响应格式

```typescript
interface ErrorResponse {
  code: number // HTTP 状态码
  message: string // 错误消息
  errors?: Array<{
    field?: string
    message: string
  }>
  timestamp: string
  request_id?: string // 用于追踪
}
```

### 常见错误代码

| 代码 | 含义 | 说明 |
|------|------|------|
| 400 | Bad Request | 请求参数错误 |
| 401 | Unauthorized | 未认证或 token 过期 |
| 403 | Forbidden | 无权限访问 |
| 404 | Not Found | 资源不存在 |
| 409 | Conflict | 资源冲突（重复创建） |
| 422 | Unprocessable Entity | 数据验证失败 |
| 429 | Too Many Requests | 请求过于频繁 |
| 500 | Internal Server Error | 服务器内部错误 |
| 503 | Service Unavailable | 服务不可用 |

### 前端错误处理示例

```typescript
// services/api.ts
const handleError = (error: any) => {
  if (error.response) {
    const { status, data } = error.response

    switch (status) {
      case 400:
        console.error('参数错误:', data.message)
        break
      case 401:
        console.error('未认证，请重新登录')
        redirectToLogin()
        break
      case 403:
        console.error('无权限访问')
        break
      case 404:
        console.error('资源不存在')
        break
      case 422:
        console.error('数据验证失败:', data.errors)
        break
      default:
        console.error('请求失败:', data.message)
    }
  } else if (error.request) {
    console.error('网络错误，请检查连接')
  } else {
    console.error('错误:', error.message)
  }
}

export const getTrips = async () => {
  try {
    const response = await API.get('/trips')
    return response.data.data
  } catch (error) {
    handleError(error)
    throw error
  }
}
```

---

## 🔄 前端集成示例

### 完整的 API 服务层

```typescript
// src/services/api.ts
import axios, { AxiosInstance, AxiosError } from 'axios'

const API: AxiosInstance = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
API.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    config.headers['X-Client-Version'] = '0.1.0'
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器
API.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// 行程 API
export const tripAPI = {
  getTrips: (page = 1, limit = 20) =>
    API.get(`/trips?page=${page}&limit=${limit}`),

  getTrip: (id: string) =>
    API.get(`/trips/${id}`),

  createTrip: (data: any) =>
    API.post('/trips', data),

  updateTrip: (id: string, data: any) =>
    API.put(`/trips/${id}`, data),

  deleteTrip: (id: string) =>
    API.delete(`/trips/${id}`),
}

// 通知 API
export const notificationAPI = {
  getTemplates: () =>
    API.get('/notifications/templates'),

  createTemplate: (data: any) =>
    API.post('/notifications/templates', data),

  updateTemplate: (id: string, data: any) =>
    API.put(`/notifications/templates/${id}`, data),

  sendTestNotification: (templateId: string, customerId: string) =>
    API.post('/notifications/send-test', { template_id: templateId, customer_id: customerId }),

  getHistory: (limit = 20) =>
    API.get(`/notifications/history?limit=${limit}`),
}

// 偏好 API
export const preferenceAPI = {
  getPreferences: () =>
    API.get('/preferences'),

  updatePreferences: (data: any) =>
    API.put('/preferences', data),
}

// 分析 API
export const analyticsAPI = {
  getMetrics: () =>
    API.get('/analytics/metrics'),

  getChannels: () =>
    API.get('/analytics/channels'),

  getTripsRanking: () =>
    API.get('/analytics/trips/ranking'),
}

// 仪表盘 API
export const dashboardAPI = {
  getStats: () =>
    API.get('/dashboard/stats'),

  getRecentNotifications: (limit = 10) =>
    API.get(`/notifications/recent?limit=${limit}`),
}
```

### React Hook 集成

```typescript
// src/hooks/useTrips.ts
import { useState, useEffect } from 'react'
import { tripAPI } from '@/services/api'

export function useTrips() {
  const [trips, setTrips] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchTrips = async () => {
      setLoading(true)
      try {
        const response = await tripAPI.getTrips()
        setTrips(response.data.data.items)
      } catch (err: any) {
        setError(err.response?.data?.message || 'Failed to fetch trips')
      } finally {
        setLoading(false)
      }
    }

    fetchTrips()
  }, [])

  const createTrip = async (data: any) => {
    try {
      const response = await tripAPI.createTrip(data)
      setTrips([...trips, response.data.data])
      return response.data.data
    } catch (err) {
      throw err
    }
  }

  const updateTrip = async (id: string, data: any) => {
    try {
      const response = await tripAPI.updateTrip(id, data)
      setTrips(trips.map(t => t.id === id ? response.data.data : t))
      return response.data.data
    } catch (err) {
      throw err
    }
  }

  const deleteTrip = async (id: string) => {
    try {
      await tripAPI.deleteTrip(id)
      setTrips(trips.filter(t => t.id !== id))
    } catch (err) {
      throw err
    }
  }

  return { trips, loading, error, createTrip, updateTrip, deleteTrip }
}
```

### 在组件中使用

```typescript
// src/pages/Trips.tsx
import { useTrips } from '@/hooks/useTrips'
import { Button } from '@/components/Button'
import { Modal } from '@/components/Modal'
import { useState } from 'react'

export function Trips() {
  const { trips, loading, error, createTrip, deleteTrip } = useTrips()
  const [isModalOpen, setIsModalOpen] = useState(false)

  const handleCreateTrip = async (formData: any) => {
    try {
      await createTrip(formData)
      setIsModalOpen(false)
      // 显示成功提示
    } catch (err) {
      // 显示错误提示
    }
  }

  if (loading) return <div>加载中...</div>
  if (error) return <div>错误: {error}</div>

  return (
    <>
      <Button onClick={() => setIsModalOpen(true)}>新建行程</Button>

      {trips.map(trip => (
        <div key={trip.id}>
          <h3>{trip.destination}</h3>
          <Button onClick={() => deleteTrip(trip.id)}>删除</Button>
        </div>
      ))}

      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)}>
        <TripForm onSubmit={handleCreateTrip} />
      </Modal>
    </>
  )
}
```

---

## 🧪 联调测试

### 使用 Postman 测试

1. 导入 [API 集合](./api-collection.json)
2. 配置环境变量：
   ```
   base_url: http://localhost:8000/api
   token: <your-jwt-token>
   ```
3. 逐个运行请求进行测试

### 使用 cURL 测试

```bash
# 登录获取 token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"123456"}'

# 获取行程列表
curl -X GET http://localhost:8000/api/trips \
  -H "Authorization: Bearer <token>"

# 创建行程
curl -X POST http://localhost:8000/api/trips \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "destination": "乌鲁木齐-喀什",
    "team_id": "TEAM-001",
    "start_date": "2026-04-15",
    "end_date": "2026-04-20"
  }'
```

### 前端集成测试

```typescript
// src/__tests__/api.test.ts
import { tripAPI } from '@/services/api'

describe('Trip API', () => {
  test('should fetch trips', async () => {
    const response = await tripAPI.getTrips()
    expect(response.data.code).toBe(200)
    expect(Array.isArray(response.data.data.items)).toBe(true)
  })

  test('should create trip', async () => {
    const newTrip = {
      destination: '乌鲁木齐-喀什',
      team_id: 'TEAM-001',
      start_date: '2026-04-15',
      end_date: '2026-04-20',
    }
    const response = await tripAPI.createTrip(newTrip)
    expect(response.data.code).toBe(201)
    expect(response.data.data.id).toBeDefined()
  })
})
```

---

## 📊 API 性能指标

| 指标 | 目标 | 说明 |
|------|------|------|
| 平均响应时间 | < 500ms | 大多数请求应在 500ms 内完成 |
| P95 响应时间 | < 1000ms | 95% 的请求应在 1s 内完成 |
| 错误率 | < 0.1% | 99.9% 可用性 |
| QPS (查询每秒) | > 1000 | 单个服务器支持 1000+ QPS |

---

## 🔒 安全性检查清单

- [ ] 所有敏感数据通过 HTTPS 传输
- [ ] API 端点验证用户身份和权限
- [ ] 实施速率限制防止 DDoS
- [ ] 验证和清理所有用户输入
- [ ] 使用 CORS 配置限制跨域请求
- [ ] 敏感信息不记录在日志中
- [ ] 定期轮换 API 密钥和 token
- [ ] 监控异常 API 使用情况

---

## 📝 版本管理

### API 版本策略

```
/api/v1/trips     # 版本 1（当前）
/api/v2/trips     # 版本 2（开发中）
```

### 版本更新流程

1. 新增功能使用 GET 参数或新端点
2. 破坏性更改创建新版本
3. 旧版本支持 6 个月的过渡期
4. 通过 API 变更日志通知客户端

---

## 📚 相关资源

- 📖 [REST API 最佳实践](https://restfulapi.net/)
- 🔐 [JWT 认证指南](https://jwt.io/introduction)
- 📊 [OpenAPI/Swagger 文档](https://swagger.io/)
- 🧪 [API 测试工具对比](https://www.postman.com/)

---

> 本文档最后更新于 2026-04-11
