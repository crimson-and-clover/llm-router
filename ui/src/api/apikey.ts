/**
 * API Key 管理 API
 */

import apiClient from './index'
import type {
  ApiKey,
  CreateApiKeyRequest,
  ApiKeyListParams,
  ApiKeyListResponse,
  RevokeApiKeyResponse,
} from '@/types/apikey'

/**
 * 获取当前用户的 API Key 列表
 */
export const getApiKeyList = async (params: ApiKeyListParams): Promise<ApiKeyListResponse> => {
  const keys: ApiKey[] = await apiClient.get('/api/v1/users/me/keys')
  const page = params.page || 1
  const pageSize = params.pageSize || 10
  const start = (page - 1) * pageSize
  const end = start + pageSize

  return {
    items: keys.slice(start, end),
    total: keys.length,
    page,
    pageSize,
  }
}

/**
 * 创建新的 API Key
 */
export const createApiKey = (data: CreateApiKeyRequest): Promise<ApiKey> => {
  return apiClient.post('/api/v1/users/me/keys', data)
}

/**
 * 吊销 API Key
 */
export const revokeApiKey = (keyId: number): Promise<RevokeApiKeyResponse> => {
  return apiClient.delete(`/api/v1/users/me/keys/${keyId}`)
}
