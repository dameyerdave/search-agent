<script setup lang="ts">
const props = defineProps<{
  src: string
  alt: string
}>()

const failed = ref(false)

watch(
  () => props.src,
  () => {
    failed.value = false
  },
)
</script>

<template>
  <div class="result-thumbnail">
    <img v-if="src && !failed" :src="src" :alt="alt" loading="lazy" @error="failed = true" />
    <div v-else class="result-thumbnail__placeholder">
      <UIcon name="i-heroicons-photo" class="size-6" />
    </div>
  </div>
</template>
