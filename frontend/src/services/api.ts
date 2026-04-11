import axios from 'axios'

const client = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
    'X-Client-Version': '0.1.0',
  },
})

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export interface ApiResponse<T> {
  code: number
  data: T
}

export const authApi = {
  async login(username: string, password: string) {
    const res = await client.post<ApiResponse<{ access_token: string }>>('/auth/login', {
      username,
      password,
    })
    const token = res.data.data.access_token
    if (token) {
      localStorage.setItem('access_token', token)
    }
    return res.data
  },
  async logout() {
    const res = await client.post('/auth/logout')
    localStorage.removeItem('access_token')
    return res.data
  },
  async refresh(refreshToken: string) {
    const res = await client.post<ApiResponse<{ access_token: string }>>('/auth/refresh', {
      refresh_token: refreshToken,
    })
    return res.data
  },
  async me() {
    const res = await client.get('/users/me')
    return res.data
  },
}

export const dashboardApi = {
  getStats: async () => (await client.get('/dashboard/stats')).data,
  getRecentNotifications: async (limit = 10) => (await client.get(`/notifications/recent?limit=${limit}`)).data,
}

export const tripsApi = {
  list: async () => (await client.get('/trips')).data,
  create: async (payload: Record<string, unknown>) => (await client.post('/trips', payload)).data,
  update: async (id: string, payload: Record<string, unknown>) => (await client.put(`/trips/${id}`, payload)).data,
  remove: async (id: string) => (await client.delete(`/trips/${id}`)).data,
}

export const notificationsApi = {
  listTemplates: async () => (await client.get('/notifications/templates')).data,
  send: async (payload: Record<string, unknown>) => (await client.post('/notifications/send', payload)).data,
}

export const analyticsApi = {
  metrics: async () => (await client.get('/analytics/metrics')).data,
}
