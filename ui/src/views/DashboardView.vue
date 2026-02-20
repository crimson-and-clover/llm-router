<script setup lang="ts">
/**
 * 仪表盘页面
 */

import { computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useApiKeyStore } from '@/stores/apikey'

const authStore = useAuthStore()
const apiKeyStore = useApiKeyStore()

// 统计信息
const stats = computed(() => {
  const activeKeys = apiKeyStore.apiKeys.filter(k => k.is_active).length
  return [
    {
      title: 'API Key 总数',
      value: apiKeyStore.total,
      icon: 'M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z',
      color: 'primary',
    },
    {
      title: '活跃的 Key',
      value: activeKeys,
      icon: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z',
      color: 'success',
    },
    {
      title: '用户角色',
      value: authStore.isSuperuser ? '超级用户' : '普通用户',
      icon: 'M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z',
      color: authStore.isSuperuser ? 'warning' : 'info',
    },
  ]
})

// 快捷操作
const quickActions = [
  {
    title: '管理 API Key',
    description: '创建、查看和管理您的 API Key',
    path: '/apikeys',
    icon: 'M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z',
  },
]

// 如果是超级用户，添加用户管理快捷入口
if (authStore.isSuperuser) {
  quickActions.push({
    title: '用户管理',
    description: '管理系统用户和权限',
    path: '/users',
    icon: 'M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z',
  })
}

onMounted(() => {
  apiKeyStore.fetchApiKeys()
})
</script>

<template>
  <div class="section-container">
    <!-- 欢迎语 -->
    <div class="card p-6">
      <h2 class="text-heading-medium mb-2">
        欢迎回来，{{ authStore.user?.username }}
      </h2>
      <p class="text-body-small">
        这是您的 LLM Router 管理控制台。您可以在这里管理 API Key 和查看系统状态。
      </p>
    </div>

    <!-- 统计卡片 -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <div
        v-for="stat in stats"
        :key="stat.title"
        class="card p-6"
      >
        <div class="flex items-center">
          <div
            :class="[
              'w-12 h-12 rounded-lg flex items-center justify-center mr-4',
              stat.color === 'primary' ? 'bg-primary-100' : '',
              stat.color === 'success' ? 'bg-success-100' : '',
              stat.color === 'warning' ? 'bg-warning-100' : '',
              stat.color === 'info' ? 'bg-primary-100' : '',
            ]"
          >
            <svg
              :class="[
                'w-6 h-6',
                stat.color === 'primary' ? 'text-primary-600' : '',
                stat.color === 'success' ? 'text-success-600' : '',
                stat.color === 'warning' ? 'text-warning-600' : '',
                stat.color === 'info' ? 'text-primary-600' : '',
              ]"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                :d="stat.icon"
              />
            </svg>
          </div>
          <div>
            <p class="text-sm text-gray-500">
              {{ stat.title }}
            </p>
            <p class="text-2xl font-bold text-gray-900">
              {{ stat.value }}
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- 快捷操作 -->
    <div>
      <h3 class="text-heading-small mb-4">
        快捷操作
      </h3>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <RouterLink
          v-for="action in quickActions"
          :key="action.title"
          :to="action.path"
          class="card p-6 hover:shadow-md transition-shadow duration-200 group"
        >
          <div class="flex items-start">
            <div class="w-10 h-10 bg-primary-50 rounded-lg flex items-center justify-center mr-4 group-hover:bg-primary-100 transition-colors">
              <svg
                class="w-5 h-5 text-primary-600"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  :d="action.icon"
                />
              </svg>
            </div>
            <div class="flex-1">
              <h4 class="text-base font-medium text-gray-900 group-hover:text-primary-600 transition-colors">
                {{ action.title }}
              </h4>
              <p class="text-sm text-gray-500 mt-1">
                {{ action.description }}
              </p>
            </div>
            <svg
              class="w-5 h-5 text-gray-400 group-hover:text-primary-600 transition-colors"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M9 5l7 7-7 7"
              />
            </svg>
          </div>
        </RouterLink>
      </div>
    </div>
  </div>
</template>
