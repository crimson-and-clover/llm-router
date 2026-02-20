<script setup lang="ts">
/**
 * 分页组件
 */

import { computed } from 'vue'

interface Props {
  /** 当前页码 */
  currentPage: number
  /** 每页条数 */
  pageSize: number
  /** 总条数 */
  total: number
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:currentPage': [page: number]
}>()

// 计算总页数
const totalPages = computed(() => Math.ceil(props.total / props.pageSize))

// 计算显示的页码范围
const displayedPages = computed(() => {
  const pages: (number | string)[] = []
  const current = props.currentPage
  const total = totalPages.value

  if (total <= 7) {
    for (let i = 1; i <= total; i++) {
      pages.push(i)
    }
  } else {
    if (current <= 3) {
      for (let i = 1; i <= 5; i++) {
        pages.push(i)
      }
      pages.push('...')
      pages.push(total)
    } else if (current >= total - 2) {
      pages.push(1)
      pages.push('...')
      for (let i = total - 4; i <= total; i++) {
        pages.push(i)
      }
    } else {
      pages.push(1)
      pages.push('...')
      for (let i = current - 1; i <= current + 1; i++) {
        pages.push(i)
      }
      pages.push('...')
      pages.push(total)
    }
  }

  return pages
})

// 是否有上一页
const hasPrev = computed(() => props.currentPage > 1)

// 是否有下一页
const hasNext = computed(() => props.currentPage < totalPages.value)

const handlePrev = () => {
  if (hasPrev.value) {
    emit('update:currentPage', props.currentPage - 1)
  }
}

const handleNext = () => {
  if (hasNext.value) {
    emit('update:currentPage', props.currentPage + 1)
  }
}

const handlePageClick = (page: number | string) => {
  if (typeof page === 'number' && page !== props.currentPage) {
    emit('update:currentPage', page)
  }
}
</script>

<template>
  <div class="pagination">
    <!-- 左侧信息 -->
    <div class="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
      <p class="text-sm text-gray-700">
        显示第
        <span class="font-medium">{{ (currentPage - 1) * pageSize + 1 }}</span>
        到
        <span class="font-medium">{{ Math.min(currentPage * pageSize, total) }}</span>
        条，共
        <span class="font-medium">{{ total }}</span>
        条
      </p>
    </div>

    <!-- 分页按钮 -->
    <nav
      class="relative z-0 inline-flex rounded-md shadow-sm -space-x-px"
      aria-label="Pagination"
    >
      <!-- 上一页 -->
      <button
        :disabled="!hasPrev"
        class="pagination-btn rounded-l-md"
        @click="handlePrev"
      >
        <span class="sr-only">上一页</span>
        <svg
          class="h-4 w-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M15 19l-7-7 7-7"
          />
        </svg>
      </button>

      <!-- 页码 -->
      <template
        v-for="(page, index) in displayedPages"
        :key="index"
      >
        <span
          v-if="page === '...'"
          class="relative inline-flex items-center px-3 py-1.5 border border-gray-300 bg-white text-sm font-medium text-gray-700"
        >
          ...
        </span>
        <button
          v-else
          :class="[
            'pagination-btn',
            page === currentPage ? 'pagination-btn-active' : '',
          ]"
          @click="handlePageClick(page)"
        >
          {{ page }}
        </button>
      </template>

      <!-- 下一页 -->
      <button
        :disabled="!hasNext"
        class="pagination-btn rounded-r-md"
        @click="handleNext"
      >
        <span class="sr-only">下一页</span>
        <svg
          class="h-4 w-4"
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
      </button>
    </nav>
  </div>
</template>
