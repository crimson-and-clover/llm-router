/**
 * 认证状态管理
 */

import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { User, UserLoginRequest, LoginResponse } from '@/types/user'
import { login as loginApi, getCurrentUser, getSession } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  // State
  const token = ref<string | null>(localStorage.getItem('token'))
  const sessionSecret = ref<string | null>(null)  // 仅内存存储，用于请求签名
  const user = ref<User | null>(null)
  const loading = ref(false)

  // Getters
  const isLoggedIn = computed(() => !!token.value && !!user.value)
  const isSuperuser = computed(() => user.value?.is_superuser ?? false)

  // Actions
  /**
   * 设置 token
   */
  const setToken = (newToken: string | null) => {
    token.value = newToken
    if (newToken) {
      localStorage.setItem('token', newToken)
    } else {
      localStorage.removeItem('token')
    }
  }

  /**
   * 设置 session_secret（仅内存存储，用于请求签名）
   */
  const setSessionSecret = (secret: string | null) => {
    sessionSecret.value = secret
  }

  /**
   * 登录
   */
  const login = async (credentials: UserLoginRequest): Promise<void> => {
    loading.value = true
    try {
      const response: LoginResponse = await loginApi(credentials)
      setToken(response.access_token)
      setSessionSecret(response.session_secret)  // 保存会话密钥用于签名
      // 获取用户信息
      await fetchUserInfo()
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取当前用户信息
   */
  const fetchUserInfo = async (): Promise<void> => {
    try {
      const userInfo = await getCurrentUser()
      user.value = userInfo
    } catch (error) {
      // 获取失败，清除登录状态
      logout()
      throw error
    }
  }

  /**
   * 退出登录
   */
  const logout = () => {
    setToken(null)
    setSessionSecret(null)
    user.value = null
  }

  /**
   * 初始化（检查本地存储的 token，页面刷新后恢复 session_secret）
   */
  const init = async (): Promise<boolean> => {
    if (token.value) {
      try {
        // 页面刷新后 sessionSecret 丢失，需要恢复
        if (!sessionSecret.value) {
          const response = await getSession()
          setToken(response.access_token)
          setSessionSecret(response.session_secret)
        }
        // 获取用户信息（后续请求需要签名）
        await fetchUserInfo()
        return true
      } catch {
        // 恢复 session 失败，清除登录状态要求重新登录
        logout()
        return false
      }
    }
    return false
  }

  return {
    // State
    token,
    sessionSecret,
    user,
    loading,
    // Getters
    isLoggedIn,
    isSuperuser,
    // Actions
    login,
    logout,
    init,
    fetchUserInfo,
    setSessionSecret,
  }
})
