<script setup lang="ts">
/**
 * 通用模态框组件
 * 支持标题、内容和底部操作区
 */

import AppButton from './AppButton.vue'

interface Props {
  /** 是否显示 */
  modelValue: boolean
  /** 标题 */
  title: string
  /** 是否显示关闭按钮 */
  showClose?: boolean
  /** 确认按钮文本 */
  confirmText?: string
  /** 取消按钮文本 */
  cancelText?: string
  /** 确认按钮变体 */
  confirmVariant?: 'primary' | 'danger'
  /** 是否加载中 */
  loading?: boolean
  /** 是否禁用确认按钮 */
  confirmDisabled?: boolean
  /** 点击遮罩是否关闭 */
  closeOnOverlay?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  showClose: true,
  confirmText: '确认',
  cancelText: '取消',
  confirmVariant: 'primary',
  loading: false,
  confirmDisabled: false,
  closeOnOverlay: true,
})

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  confirm: []
  cancel: []
}>()

const close = () => {
  emit('update:modelValue', false)
}

const handleOverlayClick = () => {
  if (props.closeOnOverlay) {
    close()
  }
}

const handleConfirm = () => {
  emit('confirm')
}

const handleCancel = () => {
  emit('cancel')
  close()
}
</script>

<template>
  <Teleport to="body">
    <!-- 遮罩层 -->
    <Transition
      enter-active-class="ease-out duration-300"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="ease-in duration-200"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="modelValue"
        class="modal-overlay"
        aria-hidden="true"
        @click="handleOverlayClick"
      />
    </Transition>

    <!-- 模态框 -->
    <Transition
      enter-active-class="ease-out duration-300"
      enter-from-class="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
      enter-to-class="opacity-100 translate-y-0 sm:scale-100"
      leave-active-class="ease-in duration-200"
      leave-from-class="opacity-100 translate-y-0 sm:scale-100"
      leave-to-class="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
    >
      <div
        v-if="modelValue"
        class="modal-container"
      >
        <div class="modal-content">
          <div class="modal-panel">
            <!-- 头部 -->
            <div class="modal-header flex items-center justify-between">
              <h3 class="text-heading-small">
                {{ title }}
              </h3>
              <button
                v-if="showClose"
                type="button"
                class="text-gray-400 hover:text-gray-500 focus:outline-none"
                @click="close"
              >
                <svg
                  class="h-5 w-5"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>

            <!-- 内容区 -->
            <div class="modal-body">
              <slot />
            </div>

            <!-- 底部操作区 -->
            <div class="modal-footer gap-2">
              <slot name="footer">
                <AppButton
                  variant="secondary"
                  @click="handleCancel"
                >
                  {{ cancelText }}
                </AppButton>
                <AppButton
                  :variant="confirmVariant"
                  :loading="loading"
                  :disabled="confirmDisabled"
                  @click="handleConfirm"
                >
                  {{ confirmText }}
                </AppButton>
              </slot>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
