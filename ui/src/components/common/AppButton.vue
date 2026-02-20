<script setup lang="ts">
/**
 * 通用按钮组件
 * 支持多种变体、尺寸和状态
 */

export type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost'
export type ButtonSize = 'sm' | 'md' | 'lg'

interface Props {
  /** 按钮变体样式 */
  variant?: ButtonVariant
  /** 按钮尺寸 */
  size?: ButtonSize
  /** 是否禁用 */
  disabled?: boolean
  /** 是否加载中 */
  loading?: boolean
  /** 按钮类型 */
  type?: 'button' | 'submit' | 'reset'
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'primary',
  size: 'md',
  disabled: false,
  loading: false,
  type: 'button',
})

const emit = defineEmits<{
  click: [event: MouseEvent]
}>()

const handleClick = (event: MouseEvent) => {
  if (props.disabled || props.loading) return
  emit('click', event)
}

const sizeClasses: Record<ButtonSize, string> = {
  sm: 'btn-sm',
  md: '',
  lg: 'btn-lg',
}

const variantClasses: Record<ButtonVariant, string> = {
  primary: 'btn-primary',
  secondary: 'btn-secondary',
  danger: 'btn-danger',
  ghost: 'btn-ghost',
}
</script>

<template>
  <button
    :type="type"
    :disabled="disabled || loading"
    :class="[variantClasses[variant], sizeClasses[size]]"
    @click="handleClick"
  >
    <!-- 加载状态 -->
    <span
      v-if="loading"
      class="spinner mr-2"
      aria-hidden="true"
    />
    <!-- 按钮内容 -->
    <slot />
  </button>
</template>
