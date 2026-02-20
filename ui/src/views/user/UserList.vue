<script setup lang="ts">
/**
 * 用户列表页面（超级用户专用）
 */

import { ref, h, onMounted } from 'vue'
import { useUserStore } from '@/stores/user'
import { useAuthStore } from '@/stores/auth'
import AppTable from '@/components/common/AppTable.vue'
import AppButton from '@/components/common/AppButton.vue'
import AppModal from '@/components/common/AppModal.vue'
import AppInput from '@/components/common/AppInput.vue'
import type { TableColumn } from '@/components/common/AppTable.vue'
import type { User } from '@/types/user'
import { hashPassword } from '@/utils/crypto'
import { sanitizeInput, validateUsername, validateEmail, validatePassword } from '@/utils/security'

const userStore = useUserStore()
const authStore = useAuthStore()

// 表格列定义
const columns: TableColumn<User>[] = [
  {
    key: 'username',
    title: '用户名',
    render: (row: User) => h('span', { class: 'font-medium text-gray-900' }, row.username),
  },
  {
    key: 'email',
    title: '邮箱',
  },
  {
    key: 'role',
    title: '角色',
    render: (row: User) => {
      if (row.is_superuser) {
        return h('span', { class: 'badge-info' }, '超级用户')
      }
      return h('span', { class: 'badge-inactive' }, '普通用户')
    },
  },
  {
    key: 'status',
    title: '状态',
    render: (row: User) => {
      if (row.is_active) {
        return h('span', { class: 'badge-success' }, '活跃')
      }
      return h('span', { class: 'badge-danger' }, '已禁用')
    },
  },
  {
    key: 'created_at',
    title: '创建时间',
    render: (row: User) => {
      const date = new Date(row.created_at)
      return h('span', {}, date.toLocaleDateString('zh-CN'))
    },
  },
  {
    key: 'actions',
    title: '操作',
    width: '200px',
    render: (row: User) => {
      const buttons = []

      // 不能操作自己
      if (row.id === authStore.user?.id) {
        return h('span', { class: 'text-gray-400 text-sm' }, '当前用户')
      }

      // 提升为超级用户
      if (!row.is_superuser) {
        buttons.push(
          h(AppButton, {
            variant: 'ghost',
            size: 'sm',
            onClick: () => handlePromote(row),
          }, () => '提升'),
        )
      }

      // 激活/禁用
      if (row.is_active) {
        buttons.push(
          h(AppButton, {
            variant: 'ghost',
            size: 'sm',
            class: 'text-danger-600 hover:text-danger-700',
            onClick: () => handleDeactivate(row),
          }, () => '禁用'),
        )
      } else {
        buttons.push(
          h(AppButton, {
            variant: 'ghost',
            size: 'sm',
            class: 'text-success-600 hover:text-success-700',
            onClick: () => handleActivate(row),
          }, () => '激活'),
        )
      }

      return h('div', { class: 'flex items-center gap-2' }, buttons)
    },
  },
]

// 创建用户弹窗
const showCreateModal = ref(false)
const createForm = ref({
  username: '',
  email: '',
  password: '',
})
const createLoading = ref(false)
const createError = ref('')

// 打开创建弹窗
const openCreateModal = () => {
  createForm.value = { username: '', email: '', password: '' }
  createError.value = ''
  showCreateModal.value = true
}

// 创建用户
const handleCreate = async () => {
  // 清理输入
  const username = sanitizeInput(createForm.value.username.trim())
  const email = sanitizeInput(createForm.value.email.trim())

  // 验证输入
  if (!username) {
    createError.value = '请输入用户名'
    return
  }
  if (!validateUsername(username)) {
    createError.value = '用户名格式不正确（3-32位字母、数字、下划线）'
    return
  }
  if (!email) {
    createError.value = '请输入邮箱'
    return
  }
  if (!validateEmail(email)) {
    createError.value = '邮箱格式不正确'
    return
  }
  if (!createForm.value.password) {
    createError.value = '请输入密码'
    return
  }
  const passwordCheck = validatePassword(createForm.value.password)
  if (!passwordCheck.valid) {
    createError.value = passwordCheck.message
    return
  }

  createLoading.value = true
  createError.value = ''

  try {
    // 前端哈希密码后再传输（传输层保护）
    const hashedPassword = hashPassword(createForm.value.password)
    await userStore.addUser({
      username: username,
      email: email,
      password: hashedPassword,
    })
    // 创建成功后清除密码
    createForm.value.password = ''
    showCreateModal.value = false
  } catch (err: unknown) {
    if (err instanceof Error) {
      createError.value = err.message
    } else {
      createError.value = '创建用户失败'
    }
  } finally {
    createLoading.value = false
  }
}

// 提升用户
const handlePromote = async (user: User) => {
  if (!confirm(`确定要将用户 "${user.username}" 提升为超级用户吗？`)) {
    return
  }
  try {
    await userStore.promote(user.id)
    alert('提升成功')
  } catch (err: unknown) {
    if (err instanceof Error) {
      alert(err.message)
    } else {
      alert('操作失败')
    }
  }
}

// 激活用户
const handleActivate = async (user: User) => {
  try {
    await userStore.activate(user.id)
    alert('激活成功')
  } catch (err: unknown) {
    if (err instanceof Error) {
      alert(err.message)
    } else {
      alert('操作失败')
    }
  }
}

// 禁用用户
const handleDeactivate = async (user: User) => {
  if (!confirm(`确定要禁用用户 "${user.username}" 吗？`)) {
    return
  }
  try {
    await userStore.deactivate(user.id)
    alert('禁用成功')
  } catch (err: unknown) {
    if (err instanceof Error) {
      alert(err.message)
    } else {
      alert('操作失败')
    }
  }
}

// 分页变化
const handlePageChange = (page: number) => {
  userStore.setPage(page)
  userStore.fetchUsers()
}

onMounted(() => {
  userStore.fetchUsers()
})
</script>

<template>
  <div class="section-container">
    <!-- 页面标题和操作 -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-heading-medium">
          用户管理
        </h2>
        <p class="text-body-small mt-1">
          管理系统用户，包括创建、激活/禁用和提升权限
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
        创建用户
      </AppButton>
    </div>

    <!-- 用户列表 -->
    <AppTable
      :columns="columns"
      :data="userStore.users"
      :loading="userStore.loading"
      :show-pagination="true"
      :current-page="userStore.currentPage"
      :page-size="userStore.pageSize"
      :total="userStore.total"
      @update:current-page="handlePageChange"
    />

    <!-- 创建用户弹窗 -->
    <AppModal
      v-model="showCreateModal"
      title="创建用户"
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
          v-model="createForm.username"
          label="用户名"
          placeholder="请输入用户名"
          :required="true"
        />

        <AppInput
          v-model="createForm.email"
          type="email"
          label="邮箱"
          placeholder="请输入邮箱"
          :required="true"
        />

        <AppInput
          v-model="createForm.password"
          type="password"
          label="密码"
          placeholder="请输入密码"
          :required="true"
        />
      </div>
    </AppModal>
  </div>
</template>
