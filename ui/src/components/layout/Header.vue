<script setup lang="ts">
/**
 * 顶部导航栏组件
 */

import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const authStore = useAuthStore()

// 页面标题映射
const titleMap: Record<string, string> = {
  '/': '仪表盘',
  '/apikeys': 'API Key 管理',
  '/users': '用户管理',
}

// 当前页面标题
const pageTitle = computed(() => {
  return titleMap[route.path] || '仪表盘'
})

// 当前时间
const currentTime = computed(() => {
  return new Date().toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'long',
  })
})
</script>

<template>
  <header class="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6 sticky top-0 z-10">
    <!-- 左侧标题 -->
    <div>
      <h1 class="text-heading-medium">
        {{ pageTitle }}
      </h1>
    </div>

    <!-- 右侧信息 -->
    <div class="flex items-center gap-6">
      <!-- 日期 -->
      <span class="text-sm text-gray-500 hidden sm:block">
        {{ currentTime }}
      </span>

      <!-- 用户角色标签 -->
      <span
        v-if="authStore.isSuperuser"
        class="badge-info"
      >
        超级用户
      </span>
      <span
        v-else
        class="badge-inactive"
      >
        普通用户
      </span>

      <!-- 通知图标 -->
      <button class="text-gray-400 hover:text-gray-500 relative">
        <svg
          class="w-6 h-6"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
          />
        </svg>
      </button>
    </div>
  </header>
</template>
