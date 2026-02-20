import apiClient from './index'
import type { LoginResponse, User } from '@/types/user'

export const login = async (credentials: { username: string; password: string }): Promise<LoginResponse> => {
  return await apiClient.post('/internal/auth/login', credentials)
}

export const getCurrentUser = async (): Promise<User> => {
  return await apiClient.get('/internal/users/me')
}

/**
 * 恢复会话密钥（页面刷新后使用）
 * 用 JWT Token 换取 session_secret
 */
export const getSession = async (): Promise<LoginResponse> => {
  return await apiClient.get('/internal/auth/session')
}