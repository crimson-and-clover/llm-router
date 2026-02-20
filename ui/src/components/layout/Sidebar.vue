<script setup lang="ts">
/**
 * 侧边栏导航组件
 */

import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

// 导航菜单项
const menuItems = computed(() => {
  const items = [
    {
      key: 'dashboard',
      title: '仪表盘',
      path: '/',
      icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6',
    },
    {
      key: 'apikeys',
      title: 'API Key 管理',
      path: '/apikeys',
      icon: 'M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z',
    },
  ]

  // 超级用户才显示用户管理
  if (authStore.isSuperuser) {
    items.push({
      key: 'users',
      title: '用户管理',
      path: '/users',
      icon: 'M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z',
    })
  }

  return items
})

// 判断是否激活
const isActive = (path: string) => {
  if (path === '/') {
    return route.path === '/'
  }
  return route.path.startsWith(path)
}

// 导航
const handleNavigate = (path: string) => {
  router.push(path)
}

// 退出登录
const handleLogout = () => {
  authStore.logout()
  router.push('/login')
}
</script>

<template>
  <aside class="sidebar h-screen sticky top-0">
    <!-- Logo 区域 -->
    <div class="h-16 flex items-center px-6 border-b border-gray-200">
      <div class="flex items-center gap-2">
        <div class="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
          <svg
            class="w-5 h-5 text-white"
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
        <span class="text-lg font-bold text-gray-900">LLM Router</span>
      </div>
    </div>

    <!-- 导航菜单 -->
    <nav class="flex-1 px-4 py-6 space-y-1 overflow-y-auto">
      <button
        v-for="item in menuItems"
        :key="item.key"
        :class="[
          'nav-link w-full',
          isActive(item.path) ? 'nav-link-active' : '',
        ]"
        @click="handleNavigate(item.path)"
      >
        <svg
          class="w-5 h-5 mr-3"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            :d="item.icon"
          />
        </svg>
        {{ item.title }}
      </button>
    </nav>

    <!-- 底部用户区域 -->
    <div class="border-t border-gray-200 p-4">
      <div class="flex items-center gap-3">
        <div class="w-9 h-9 rounded-full bg-primary-100 flex items-center justify-center">
          <span class="text-sm font-medium text-primary-700">
            {{ authStore.user?.username?.charAt(0).toUpperCase() || 'U' }}
          </span>
        </div>
        <div class="flex-1 min-w-0">
          <p class="text-sm font-medium text-gray-900 truncate">
            {{ authStore.user?.username }}
          </p>
          <p class="text-xs text-gray-500 truncate">
            {{ authStore.user?.email }}
          </p>
        </div>
      </div>
      <button
        class="btn-ghost w-full mt-3 text-left"
        @click="handleLogout"
      >
        <svg
          class="w-4 h-4 mr-2"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
          />
        </svg>
        退出登录
      </button>
    </div>
  </aside>
</template>
