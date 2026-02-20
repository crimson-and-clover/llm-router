<script setup lang="ts">
/**
 * 通用输入框组件
 * 支持多种类型和表单验证
 */

import { computed } from 'vue'

export type InputType = 'text' | 'password' | 'email' | 'number'

interface Props {
  /** 输入框类型 */
  type?: InputType
  /** 输入框值 */
  modelValue: string
  /** 标签文本 */
  label?: string
  /** 占位符文本 */
  placeholder?: string
  /** 是否禁用 */
  disabled?: boolean
  /** 是否必填 */
  required?: boolean
  /** 错误信息 */
  error?: string
  /** 帮助文本 */
  help?: string
  /** 自动完成 */
  autocomplete?: string
}

const props = withDefaults(defineProps<Props>(), {
  type: 'text',
  disabled: false,
  required: false,
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
  blur: [event: FocusEvent]
  focus: [event: FocusEvent]
}>()

const handleInput = (event: Event) => {
  const target = event.target as HTMLInputElement
  emit('update:modelValue', target.value)
}

const inputClasses = computed(() => {
  return props.error ? 'input-field input-field-error' : 'input-field'
})
</script>

<template>
  <div class="form-group">
    <!-- 标签 -->
    <label
      v-if="label"
      class="text-label block mb-1.5"
    >
      {{ label }}
      <span
        v-if="required"
        class="text-danger-500 ml-0.5"
      >*</span>
    </label>

    <!-- 输入框 -->
    <input
      :type="type"
      :value="modelValue"
      :placeholder="placeholder"
      :disabled="disabled"
      :required="required"
      :autocomplete="autocomplete"
      :class="inputClasses"
      @input="handleInput"
      @blur="$emit('blur', $event)"
      @focus="$emit('focus', $event)"
    >

    <!-- 错误提示 -->
    <p
      v-if="error"
      class="form-error mt-1"
    >
      {{ error }}
    </p>

    <!-- 帮助文本 -->
    <p
      v-else-if="help"
      class="form-help mt-1"
    >
      {{ help }}
    </p>
  </div>
</template>
