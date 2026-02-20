<script setup lang="ts">
/**
 * 主布局组件
 * 包含侧边栏、顶部导航和主内容区
 */

import Sidebar from './Sidebar.vue'
import Header from './Header.vue'
</script>

<template>
  <div class="flex min-h-screen bg-gray-50">
    <!-- 侧边栏 -->
    <Sidebar />

    <!-- 主内容区 -->
    <div class="flex-1 flex flex-col min-w-0">
      <!-- 顶部导航 -->
      <Header />

      <!-- 页面内容 -->
      <main class="flex-1 overflow-auto">
        <div class="page-container">
          <slot />
        </div>
      </main>
    </div>
  </div>
</template>
