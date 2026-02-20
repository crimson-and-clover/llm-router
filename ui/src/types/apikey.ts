/**
 * API Key 相关类型定义
 * 与后端模型保持一致
 */

/** API Key 信息 */
export interface ApiKey {
  id: number
  key_value?: string // 只在创建时返回完整 key
  key_masked: string // 脱敏显示
  is_active: boolean
  created_at: string
  purpose: string
  user_id: number
}

/** 创建 API Key 请求 */
export interface CreateApiKeyRequest {
  purpose: string
  prefix?: string // 默认为 'sk'
}

/** API Key 响应 */
export interface ApiKeyResponse extends ApiKey {}

/** API Key 列表查询参数 */
export interface ApiKeyListParams {
  page?: number
  pageSize?: number
}

/** API Key 列表响应 */
export interface ApiKeyListResponse {
  items: ApiKey[]
  total: number
  page: number
  pageSize: number
}

/** 吊销 API Key 响应 */
export interface RevokeApiKeyResponse {
  message: string
}
