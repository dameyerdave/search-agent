<script setup lang="ts">
import { formatDate } from 'utils/dashboard'
import type { SearchResult } from 'types/search-agent'

withDefaults(
  defineProps<{
    result: SearchResult
    showTopic?: boolean
    showMove?: boolean
  }>(),
  {
    showTopic: true,
    showMove: false,
  },
)

const emit = defineEmits<{
  save: [result: SearchResult]
  unsave: [result: SearchResult]
  follow: [result: SearchResult]
  move: [result: SearchResult]
}>()

const { t } = useI18n()

const formatResultDate = (value: string | null) => formatDate(value) ?? t('dashboard.common.never')
</script>

<template>
  <article class="terminal-panel relative overflow-hidden rounded-[1.2rem] p-3 sm:rounded-2xl">
    <div class="relative z-10 space-y-2.5">
      <ResultThumbnail :src="result.image_url" :alt="result.title" />

      <div class="flex flex-wrap items-center gap-1.5">
        <span v-if="result.is_new" class="pill bg-[var(--accent-soft)] text-[var(--accent)]">
          {{ t('results.badges.new') }}
        </span>
        <span v-if="showTopic" class="text-xs tracking-[0.18em] text-[var(--muted)] uppercase">
          {{ result.topic_name }}
        </span>
      </div>

      <a
        :href="result.url"
        target="_blank"
        rel="noreferrer"
        class="block text-sm leading-6 font-medium text-white hover:text-[var(--accent)]"
      >
        {{ result.title }}
      </a>

      <p class="text-xs leading-5 text-[var(--muted)]">
        {{ result.ai_summary || result.snippet || t('results.no_preview') }}
      </p>

      <div class="flex items-center justify-between gap-2 pt-1">
        <p class="text-[11px] text-[var(--muted)]">
          {{ t('results.meta.published', { date: formatResultDate(result.published_at) }) }}
        </p>
        <div class="flex shrink-0 items-center gap-1.5">
          <button
            v-if="showMove"
            class="terminal-button terminal-button-secondary p-2"
            :title="t('saved.results.move')"
            :aria-label="t('saved.results.move')"
            @click="emit('move', result)"
          >
            <UIcon name="i-heroicons-arrow-right-circle" class="size-3.5" />
          </button>
          <button
            v-if="!result.is_saved"
            class="terminal-button terminal-button-secondary p-2"
            :title="t('results.save.button')"
            :aria-label="t('results.save.button')"
            @click="emit('save', result)"
          >
            <UIcon name="i-heroicons-bookmark" class="size-3.5" />
          </button>
          <button
            v-else
            class="terminal-button terminal-button-secondary p-2 text-[var(--accent)]"
            :title="t('results.save.unsave')"
            :aria-label="t('results.save.unsave')"
            @click="emit('unsave', result)"
          >
            <UIcon name="i-heroicons-bookmark-solid" class="size-3.5" />
          </button>
          <button
            class="terminal-button terminal-button-secondary p-2"
            :title="t('results.follow.button')"
            :aria-label="t('results.follow.button')"
            @click="emit('follow', result)"
          >
            <UIcon name="i-heroicons-signal" class="size-3.5" />
          </button>
        </div>
      </div>
    </div>
  </article>
</template>
