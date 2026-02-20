/**
 * 认证相关 API
 */

import apiClient from './index'
import type {
  UserLoginRequest,
  UserRegisterRequest,
  LoginResponse,
  UserResponse,
} from '@/types/user'

/**
 * 用户登录
 */
export const login = (data: UserLoginRequest): Promise<LoginResponse> => {
  return apiClient.post('/api/v1/auth/login', data)
}

/**
 * 用户注册
 */
export const register = (data: UserRegisterRequest): Promise<UserResponse> => {
  return apiClient.post('/api/v1/auth/register', data)
}

/**
 * 获取当前用户信息
 */
export const getCurrentUser = (): Promise<UserResponse> => {
  return apiClient.get('/api/v1/users/me')
}
