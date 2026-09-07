<script setup lang="ts">
import type { SearchResult } from 'types/search-agent'

const { t } = useI18n()

const props = defineProps<{
  results: SearchResult[]
}>()

const emit = defineEmits<{
  save: [result: SearchResult]
  unsave: [result: SearchResult]
  follow: [result: SearchResult]
}>()
</script>

<template>
  <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
    <ResultCard
      v-for="result in props.results"
      :key="result.id"
      :result="result"
      @save="emit('save', result)"
      @unsave="emit('unsave', result)"
      @follow="emit('follow', result)"
    />

    <article
      v-if="props.results.length === 0"
      class="col-span-full rounded-2xl border border-[var(--line)] bg-black/25 p-5 text-center text-sm text-[var(--muted)]"
    >
      {{ t('results.empty') }}
    </article>
  </div>
</template>
