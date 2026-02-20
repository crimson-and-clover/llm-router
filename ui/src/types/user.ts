/**
 * 用户相关类型定义
 * 与后端模型保持一致
 */

/** 用户基础信息 */
export interface User {
  id: number
  username: string
  email: string
  is_active: boolean
  is_superuser: boolean
  created_at: string
}

/** 用户登录请求 */
export interface UserLoginRequest {
  username: string
  password: string
}

/** 用户注册请求 */
export interface UserRegisterRequest {
  username: string
  email: string
  password: string
}

/** 创建用户请求（超级用户） */
export interface CreateUserRequest {
  username: string
  email: string
  password: string
}

/** 用户信息响应 */
export interface UserResponse extends User {}

/** 登录响应 */
export interface LoginResponse {
  access_token: string
  token_type: string
  session_secret: string  // 用于请求签名的会话密钥
}

/** 用户列表查询参数 */
export interface UserListParams {
  page?: number
  pageSize?: number
  search?: string
}

/** 用户列表响应 */
export interface UserListResponse {
  items: User[]
  total: number
  page: number
  pageSize: number
}

/** 通用操作响应 */
export interface OperationResponse {
  message: string
}
