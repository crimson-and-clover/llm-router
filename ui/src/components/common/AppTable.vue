<script setup lang="ts" generic="T extends Record<string, any>">
/**
 * 通用表格组件
 * 支持列定义配置和操作列
 */

import AppPagination from './AppPagination.vue'

export interface TableColumn<T = any> {
  /** 列标识 */
  key: string
  /** 列标题 */
  title: string
  /** 列宽度 */
  width?: string
  /** 对齐方式 */
  align?: 'left' | 'center' | 'right'
  /** 自定义渲染函数 */
  render?: (row: T, index: number) => any
}

interface Props {
  /** 表格列定义 */
  columns: TableColumn<T>[]
  /** 表格数据 */
  data: T[]
  /** 是否加载中 */
  loading?: boolean
  /** 空状态文本 */
  emptyText?: string
  /** 是否显示分页 */
  showPagination?: boolean
  /** 当前页码 */
  currentPage?: number
  /** 每页条数 */
  pageSize?: number
  /** 总条数 */
  total?: number
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  emptyText: '暂无数据',
  showPagination: false,
  currentPage: 1,
  pageSize: 10,
  total: 0,
})

const emit = defineEmits<{
  'update:currentPage': [page: number]
  'update:pageSize': [size: number]
}>()

const handlePageChange = (page: number) => {
  emit('update:currentPage', page)
}

const getCellStyle = (column: TableColumn<T>) => {
  const style: Record<string, string> = {}
  if (column.width) {
    style.width = column.width
  }
  if (column.align) {
    style.textAlign = column.align
  }
  return style
}
</script>

<template>
  <div class="data-container">
    <!-- 表格容器 -->
    <div class="table-container">
      <table class="table-base">
        <!-- 表头 -->
        <thead class="table-header">
          <tr>
            <th
              v-for="column in columns"
              :key="column.key"
              class="table-header-cell"
              :style="getCellStyle(column)"
            >
              {{ column.title }}
            </th>
          </tr>
        </thead>

        <!-- 表体 -->
        <tbody class="table-body">
          <template v-if="!loading && data.length > 0">
            <tr
              v-for="(row, index) in data"
              :key="index"
              class="table-row-hover"
            >
              <td
                v-for="column in columns"
                :key="column.key"
                class="table-cell"
                :style="getCellStyle(column)"
              >
                <template v-if="column.render">
                  <component :is="column.render(row, index)" />
                </template>
                <template v-else>
                  {{ row[column.key] }}
                </template>
              </td>
            </tr>
          </template>

          <!-- 加载状态 -->
          <tr v-if="loading">
            <td
              :colspan="columns.length"
              class="py-12 text-center"
            >
              <div class="flex items-center justify-center">
                <span class="spinner text-primary-600 mr-2" />
                <span class="text-gray-500">加载中...</span>
              </div>
            </td>
          </tr>

          <!-- 空状态 -->
          <tr v-else-if="data.length === 0">
            <td
              :colspan="columns.length"
              class="py-12"
            >
              <div class="empty-state">
                <svg
                  class="empty-state-icon"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                <p class="empty-state-title">
                  {{ emptyText }}
                </p>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 分页 -->
    <AppPagination
      v-if="showPagination && total > 0"
      :current-page="currentPage"
      :page-size="pageSize"
      :total="total"
      @update:current-page="handlePageChange"
    />
  </div>
</template>
