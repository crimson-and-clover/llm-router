<script setup lang="ts">
/**
 * 登录页面
 */

import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import AppButton from '@/components/common/AppButton.vue'
import AppInput from '@/components/common/AppInput.vue'
import { hashPassword } from '@/utils/crypto'
import { sanitizeInput, validateUsername } from '@/utils/security'

const router = useRouter()
const authStore = useAuthStore()

// 表单数据
const form = reactive({
  username: '',
  password: '',
})

// 错误信息
const error = ref('')
const loading = ref(false)

// 登录处理
const handleLogin = async () => {
  // 清理输入
  const username = sanitizeInput(form.username.trim())

  // 表单验证
  if (!username) {
    error.value = '请输入用户名'
    return
  }
  if (!validateUsername(username)) {
    error.value = '用户名格式不正确（3-32位字母、数字、下划线）'
    return
  }
  if (!form.password) {
    error.value = '请输入密码'
    return
  }

  error.value = ''
  loading.value = true

  try {
    // 前端哈希密码后再传输（传输层保护）
    const hashedPassword = hashPassword(form.password)
    await authStore.login({
      username: username,
      password: hashedPassword,
    })
    // 登录成功后立即清除密码
    form.password = ''
    router.push('/')
  } catch (err: any) {
    error.value = err.message || '登录失败，请检查用户名和密码'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
    <div class="max-w-md w-full space-y-8">
      <!-- Logo 和标题 -->
      <div class="text-center">
        <div class="mx-auto h-12 w-12 bg-primary-600 rounded-lg flex items-center justify-center">
          <svg
            class="h-7 w-7 text-white"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M13 10V3L4 14h7v7l9-11h-7z"
            />
          </svg>
        </div>
        <h2 class="mt-6 text-heading-large">
          LLM Router 管理后台
        </h2>
        <p class="mt-2 text-body-small">
          请输入您的账号密码进行登录
        </p>
      </div>

      <!-- 登录表单 -->
      <form
        class="mt-8 space-y-6"
        @submit.prevent="handleLogin"
      >
        <div class="card p-6 space-y-4">
          <!-- 错误提示 -->
          <div
            v-if="error"
            class="bg-danger-50 border border-danger-200 text-danger-700 px-4 py-3 rounded-lg text-sm"
          >
            {{ error }}
          </div>

          <!-- 用户名 -->
          <AppInput
            v-model="form.username"
            label="用户名"
            placeholder="请输入用户名"
            autocomplete="username"
            :required="true"
          />

          <!-- 密码 -->
          <AppInput
            v-model="form.password"
            type="password"
            label="密码"
            placeholder="请输入密码"
            autocomplete="current-password"
            :required="true"
          />

          <!-- 登录按钮 -->
          <AppButton
            type="submit"
            variant="primary"
            class="w-full"
            :loading="loading"
          >
            登录
          </AppButton>
        </div>

        <!-- 提示信息 -->
        <p class="text-center text-xs text-gray-500">
          首次使用？请联系超级用户创建账号
        </p>
      </form>
    </div>
  </div>
</template>
