<script setup lang="ts">
/**
 * API Key 管理页面
 */

import { ref, h, onMounted } from 'vue'
import { useApiKeyStore } from '@/stores/apikey'
import AppTable from '@/components/common/AppTable.vue'
import AppButton from '@/components/common/AppButton.vue'
import AppModal from '@/components/common/AppModal.vue'
import AppInput from '@/components/common/AppInput.vue'
import type { TableColumn } from '@/components/common/AppTable.vue'
import type { ApiKey } from '@/types/apikey'

const apiKeyStore = useApiKeyStore()

// 表格列定义
const columns: TableColumn<ApiKey>[] = [
  {
    key: 'name',
    title: '用途',
    render: (row: ApiKey) => h('span', { class: 'font-medium text-gray-900' }, row.purpose),
  },
  {
    key: 'key_masked',
    title: 'API Key',
    render: (row: ApiKey) => {
      return h('code', { class: 'text-sm bg-gray-100 px-2 py-1 rounded' }, row.key_masked)
    },
  },
  {
    key: 'status',
    title: '状态',
    render: (row: ApiKey) => {
      if (row.is_active) {
        return h('span', { class: 'badge-success' }, '活跃')
      }
      return h('span', { class: 'badge-danger' }, '已吊销')
    },
  },
  {
    key: 'created_at',
    title: '创建时间',
    render: (row: ApiKey) => {
      const date = new Date(row.created_at)
      return h('span', {}, date.toLocaleDateString('zh-CN'))
    },
  },
  {
    key: 'actions',
    title: '操作',
    width: '120px',
    render: (row: ApiKey) => {
      if (!row.is_active) {
        return h('span', { class: 'text-gray-400 text-sm' }, '已吊销')
      }
      return h(AppButton, {
        variant: 'ghost',
        size: 'sm',
        class: 'text-danger-600 hover:text-danger-700',
        onClick: () => handleRevoke(row),
      }, () => '吊销')
    },
  },
]

// 创建 API Key 弹窗
const showCreateModal = ref(false)
const createForm = ref({
  purpose: '',
})
const createLoading = ref(false)
const createError = ref('')

// 显示新创建的 Key
const showNewKeyModal = ref(false)

// 打开创建弹窗
const openCreateModal = () => {
  createForm.value = { purpose: '' }
  createError.value = ''
  showCreateModal.value = true
}

// 创建 API Key
const handleCreate = async () => {
  if (!createForm.value.purpose.trim()) {
    createError.value = '请输入用途'
    return
  }

  createLoading.value = true
  createError.value = ''

  try {
    await apiKeyStore.addApiKey({
      purpose: createForm.value.purpose.trim(),
    })
    showCreateModal.value = false
    // 显示新创建的 Key
    if (apiKeyStore.newlyCreatedKey) {
      showNewKeyModal.value = true
    }
  } catch (err: any) {
    createError.value = err.message || '创建 API Key 失败'
  } finally {
    createLoading.value = false
  }
}

// 吊销 API Key
const handleRevoke = async (key: ApiKey) => {
  if (!confirm(`确定要吊销用途为 "${key.purpose}" 的 API Key 吗？此操作不可恢复。`)) {
    return
  }
  try {
    await apiKeyStore.revoke(key.id)
    alert('吊销成功')
  } catch (err: any) {
    alert(err.message || '操作失败')
  }
}

// 复制到剪贴板
const copyToClipboard = (text: string) => {
  navigator.clipboard.writeText(text).then(() => {
    alert('已复制到剪贴板')
  })
}

// 关闭新 Key 弹窗时清除记录
const closeNewKeyModal = () => {
  apiKeyStore.clearNewlyCreatedKey()
  showNewKeyModal.value = false
}

// 分页变化
const handlePageChange = (page: number) => {
  apiKeyStore.setPage(page)
  apiKeyStore.fetchApiKeys()
}

onMounted(() => {
  apiKeyStore.fetchApiKeys()
})
</script>

<template>
  <div class="section-container">
    <!-- 页面标题和操作 -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-heading-medium">
          API Key 管理
        </h2>
        <p class="text-body-small mt-1">
          管理您的 API Key，用于访问 LLM Router 服务
        </p>
      </div>
      <AppButton
        variant="primary"
        @click="openCreateModal"
      >
        <svg
          class="w-4 h-4 mr-1.5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M12 4v16m8-8H4"
          />
        </svg>
        创建 API Key
      </AppButton>
    </div>

    <!-- 安全提示 -->
    <div class="bg-primary-50 border border-primary-200 rounded-lg p-4 flex items-start gap-3">
      <svg
        class="w-5 h-5 text-primary-600 mt-0.5 flex-shrink-0"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
      <div>
        <p class="text-sm font-medium text-primary-800">
          安全提示
        </p>
        <p class="text-sm text-primary-700 mt-1">
          API Key 只会在创建时显示一次，请妥善保管。如果 Key 泄露，请立即吊销并重新创建。
        </p>
      </div>
    </div>

    <!-- API Key 列表 -->
    <AppTable
      :columns="columns"
      :data="apiKeyStore.apiKeys"
      :loading="apiKeyStore.loading"
      :show-pagination="true"
      :current-page="apiKeyStore.currentPage"
      :page-size="apiKeyStore.pageSize"
      :total="apiKeyStore.total"
      @update:current-page="handlePageChange"
    />

    <!-- 创建 API Key 弹窗 -->
    <AppModal
      v-model="showCreateModal"
      title="创建 API Key"
      confirm-text="创建"
      :loading="createLoading"
      @confirm="handleCreate"
    >
      <div class="space-y-4">
        <!-- 错误提示 -->
        <div
          v-if="createError"
          class="bg-danger-50 border border-danger-200 text-danger-700 px-4 py-3 rounded-lg text-sm"
        >
          {{ createError }}
        </div>

        <AppInput
          v-model="createForm.purpose"
          label="用途"
          placeholder="例如：测试环境、生产环境"
          help="用于标识这个 API Key 的用途"
          :required="true"
        />
      </div>
    </AppModal>

    <!-- 显示新创建的 Key 弹窗 -->
    <AppModal
      v-model="showNewKeyModal"
      title="API Key 创建成功"
      confirm-text="我已保存"
      :show-close="false"
      :close-on-overlay="false"
      @confirm="closeNewKeyModal"
    >
      <div class="space-y-4">
        <div class="bg-warning-50 border border-warning-200 rounded-lg p-4">
          <p class="text-sm font-medium text-warning-800">
            请立即复制并保存您的 API Key
          </p>
          <p class="text-sm text-warning-700 mt-1">
            出于安全考虑，此 Key 只显示一次，关闭后将无法再次查看。
          </p>
        </div>

        <div class="bg-gray-900 rounded-lg p-4">
          <div class="flex items-center justify-between">
            <code class="text-green-400 text-sm font-mono break-all">
              {{ apiKeyStore.newlyCreatedKey }}
            </code>
            <AppButton
              variant="ghost"
              size="sm"
              class="text-white hover:text-gray-200 ml-4 flex-shrink-0"
              @click="copyToClipboard(apiKeyStore.newlyCreatedKey || '')"
            >
              <svg
                class="w-4 h-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                />
              </svg>
            </AppButton>
          </div>
        </div>
      </div>
    </AppModal>
  </div>
</template>
