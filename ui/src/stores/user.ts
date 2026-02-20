/**
 * 用户管理状态
 */

import { ref } from 'vue'
import { defineStore } from 'pinia'
import type {
  User,
  CreateUserRequest,
  UserListParams,
  OperationResponse,
} from '@/types/user'
import {
  getUserList,
  createUser,
  promoteUser,
  activateUser,
  deactivateUser,
} from '@/api/user'

export const useUserStore = defineStore('user', () => {
  // State
  const users = ref<User[]>([])
  const loading = ref(false)
  const total = ref(0)
  const currentPage = ref(1)
  const pageSize = ref(10)

  // Actions
  /**
   * 获取用户列表
   */
  const fetchUsers = async (params?: UserListParams): Promise<void> => {
    loading.value = true
    try {
      const response = await getUserList({
        page: currentPage.value,
        pageSize: pageSize.value,
        ...params,
      })
      users.value = response.items
      total.value = response.total
    } finally {
      loading.value = false
    }
  }

  /**
   * 创建用户
   */
  const addUser = async (data: CreateUserRequest): Promise<User> => {
    const user = await createUser(data)
    await fetchUsers()
    return user
  }

  /**
   * 提升用户为超级用户
   */
  const promote = async (userId: number): Promise<OperationResponse> => {
    const result = await promoteUser(userId)
    await fetchUsers()
    return result
  }

  /**
   * 激活用户
   */
  const activate = async (userId: number): Promise<OperationResponse> => {
    const result = await activateUser(userId)
    await fetchUsers()
    return result
  }

  /**
   * 禁用用户
   */
  const deactivate = async (userId: number): Promise<OperationResponse> => {
    const result = await deactivateUser(userId)
    await fetchUsers()
    return result
  }

  /**
   * 设置当前页码
   */
  const setPage = (page: number) => {
    currentPage.value = page
  }

  return {
    // State
    users,
    loading,
    total,
    currentPage,
    pageSize,
    // Actions
    fetchUsers,
    addUser,
    promote,
    activate,
    deactivate,
    setPage,
  }
})
