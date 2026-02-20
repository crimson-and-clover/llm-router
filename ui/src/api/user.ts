/**
 * 用户管理 API（超级用户专用）
 */

import apiClient from './index'
import type {
  User,
  CreateUserRequest,
  UserListParams,
  UserListResponse,
  OperationResponse,
} from '@/types/user'

/**
 * 获取用户列表
 */
export const getUserList = async (params: UserListParams): Promise<UserListResponse> => {
  // 暂时返回所有数据，后端分页后再调整
  const users: User[] = await apiClient.get('/api/v1/admin/users')
  const page = params.page || 1
  const pageSize = params.pageSize || 10
  const start = (page - 1) * pageSize
  const end = start + pageSize

  return {
    items: users.slice(start, end),
    total: users.length,
    page,
    pageSize,
  }
}

/**
 * 创建用户（超级用户）
 */
export const createUser = (data: CreateUserRequest): Promise<User> => {
  return apiClient.post('/api/v1/admin/users', data)
}

/**
 * 提升用户为超级用户
 */
export const promoteUser = (userId: number): Promise<OperationResponse> => {
  return apiClient.post(`/api/v1/admin/users/${userId}/promote`)
}

/**
 * 激活用户账号
 */
export const activateUser = (userId: number): Promise<OperationResponse> => {
  return apiClient.post(`/api/v1/admin/users/${userId}/activate`)
}

/**
 * 禁用用户账号
 */
export const deactivateUser = (userId: number): Promise<OperationResponse> => {
  return apiClient.post(`/api/v1/admin/users/${userId}/deactivate`)
}
