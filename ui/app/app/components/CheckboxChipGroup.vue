<script setup lang="ts">
interface ChipOption {
  value: string
  label: string
}

const props = defineProps<{
  modelValue: string[]
  options: ChipOption[]
}>()

const emit = defineEmits<{ 'update:modelValue': [string[]] }>()

const toggle = (value: string) => {
  emit(
    'update:modelValue',
    props.modelValue.includes(value) ? props.modelValue.filter((v) => v !== value) : [...props.modelValue, value],
  )
}
</script>

<template>
  <div class="grid max-h-[280px] grid-cols-2 gap-2 overflow-y-auto sm:grid-cols-3">
    <label
      v-for="option in options"
      :key="option.value"
      class="pill flex min-h-11 cursor-pointer items-center gap-2 border-transparent"
      :class="
        modelValue.includes(option.value)
          ? 'bg-[var(--accent-soft)] text-[var(--accent)]'
          : 'text-[var(--muted)] hover:text-white'
      "
    >
      <input
        type="checkbox"
        class="accent-[var(--accent)]"
        :checked="modelValue.includes(option.value)"
        @change="toggle(option.value)"
      />
      <span class="truncate normal-case">{{ option.label }}</span>
    </label>
  </div>
</template>
