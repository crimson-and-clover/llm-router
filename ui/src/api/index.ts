/**
 * API 基础配置
 */

import axios from 'axios'
import { generateNonce } from '@/utils/crypto'

// 创建 axios 实例
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器 - 添加认证 token 和安全头
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    // 添加请求唯一标识，用于防止重放攻击
    config.headers['X-Request-Nonce'] = generateNonce()
    config.headers['X-Request-Timestamp'] = Date.now().toString()
    return config
  },
  (error) => {
    return Promise.reject(error)
  },
)

// 响应拦截器 - 统一错误处理
apiClient.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    // 处理 401 未授权（Token 过期或无效）
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      // 如果不是在登录页，则跳转到登录
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login'
      }
    }

    // 提取错误信息
    const message = error.response?.data?.detail || error.message || '请求失败'
    return Promise.reject(new Error(message))
  },
)

export default apiClient
