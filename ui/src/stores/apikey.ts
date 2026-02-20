/**
 * API Key 管理状态
 */

import { ref } from 'vue'
import { defineStore } from 'pinia'
import type {
  ApiKey,
  CreateApiKeyRequest,
  ApiKeyListParams,
  RevokeApiKeyResponse,
} from '@/types/apikey'
import {
  getApiKeyList,
  createApiKey,
  revokeApiKey,
} from '@/api/apikey'

export const useApiKeyStore = defineStore('apikey', () => {
  // State
  const apiKeys = ref<ApiKey[]>([])
  const loading = ref(false)
  const total = ref(0)
  const currentPage = ref(1)
  const pageSize = ref(10)

  // 新创建的 key（用于显示）
  const newlyCreatedKey = ref<string | null>(null)

  // Actions
  /**
   * 获取 API Key 列表
   */
  const fetchApiKeys = async (params?: ApiKeyListParams): Promise<void> => {
    loading.value = true
    try {
      const response = await getApiKeyList({
        page: currentPage.value,
        pageSize: pageSize.value,
        ...params,
      })
      apiKeys.value = response.items
      total.value = response.total
    } finally {
      loading.value = false
    }
  }

  /**
   * 创建 API Key
   */
  const addApiKey = async (data: CreateApiKeyRequest): Promise<ApiKey> => {
    const apiKey = await createApiKey(data)
    newlyCreatedKey.value = apiKey.key_value || null
    await fetchApiKeys()
    return apiKey
  }

  /**
   * 吊销 API Key
   */
  const revoke = async (keyId: number): Promise<RevokeApiKeyResponse> => {
    const result = await revokeApiKey(keyId)
    await fetchApiKeys()
    return result
  }

  /**
   * 清除新创建的 key
   */
  const clearNewlyCreatedKey = () => {
    newlyCreatedKey.value = null
  }

  /**
   * 设置当前页码
   */
  const setPage = (page: number) => {
    currentPage.value = page
  }

  return {
    // State
    apiKeys,
    loading,
    total,
    currentPage,
    pageSize,
    newlyCreatedKey,
    // Actions
    fetchApiKeys,
    addApiKey,
    revoke,
    clearNewlyCreatedKey,
    setPage,
  }
})
