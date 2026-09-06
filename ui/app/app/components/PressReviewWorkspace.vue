<script setup lang="ts">
import { formatDate } from 'utils/dashboard'

const authStore = useAuthStore()
const dashboardStore = useDashboardStore()
const pressReviewStore = usePressReviewWorkspaceStore()
const { t } = useI18n()
const { followResult } = useFollowResult()

const formatResultDate = (value: string | null) => formatDate(value) ?? t('dashboard.common.never')

useInfiniteScroll(window, () => pressReviewStore.loadMoreResults(), {
  distance: 240,
  canLoadMore: () =>
    pressReviewStore.canLoadMore && !pressReviewStore.autoLoadCapReached && !pressReviewStore.isLoadingMore,
})
</script>

<template>
  <section
    v-if="authStore.isAuthenticated && dashboardStore.activeWorkspace === 'press'"
    class="space-y-3 sm:space-y-5"
  >
    <section class="terminal-panel relative overflow-hidden rounded-[1.2rem] p-3 sm:rounded-3xl sm:p-5">
      <div class="relative z-10 space-y-3">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p class="mono-heading text-sm tracking-[0.22em] text-white uppercase sm:text-lg">
              {{ t('press_review.title') }}
            </p>
            <p class="mt-1 text-xs text-[var(--muted)]">
              {{ t('press_review.subtitle') }}
            </p>
          </div>
          <div class="flex flex-wrap gap-1.5">
            <span v-if="pressReviewStore.newCount > 0" class="pill bg-[var(--accent-soft)] text-[var(--accent)]">
              {{ t('press_review.new_count', { count: pressReviewStore.newCount }) }}
            </span>
            <button
              class="terminal-button terminal-button-secondary"
              :disabled="pressReviewStore.newCount === 0"
              @click="pressReviewStore.acknowledgeAll"
            >
              {{ t('press_review.acknowledge_all') }}
            </button>
            <button class="terminal-button terminal-button-secondary" @click="pressReviewStore.loadResults(1)">
              {{ t('dashboard.common.buttons.refresh') }}
            </button>
          </div>
        </div>
      </div>
    </section>

    <div v-if="pressReviewStore.isLoading" class="flex justify-center py-10">
      <XunoLoadingMark class="xuno-loading-mark--sm" />
    </div>

    <div
      v-else-if="pressReviewStore.results.length === 0"
      class="terminal-panel rounded-[1.2rem] p-5 text-sm text-[var(--muted)] sm:rounded-3xl"
    >
      {{ t('press_review.empty') }}
    </div>

    <div v-else class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <article
        v-for="result in pressReviewStore.results"
        :key="result.id"
        class="terminal-panel relative overflow-hidden rounded-[1.2rem] p-3 sm:rounded-2xl"
      >
        <div class="relative z-10 space-y-2.5">
          <ResultThumbnail :src="result.image_url" :alt="result.title" />

          <div class="flex flex-wrap items-center gap-1.5">
            <span v-if="result.is_new" class="pill bg-[var(--accent-soft)] text-[var(--accent)]">
              {{ t('results.badges.new') }}
            </span>
            <span class="text-xs tracking-[0.18em] text-[var(--muted)] uppercase">{{ result.topic_name }}</span>
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
            <button class="terminal-button terminal-button-secondary text-xs" @click="followResult(result)">
              <UIcon name="i-heroicons-signal" class="size-3.5" />
              {{ t('results.follow.button') }}
            </button>
          </div>
        </div>
      </article>
    </div>

    <div class="flex justify-center pt-2">
      <p v-if="pressReviewStore.isLoadingMore" class="text-sm text-[var(--muted)]">
        {{ t('press_review.loading_more') }}
      </p>
      <button
        v-else-if="pressReviewStore.canLoadMore && pressReviewStore.autoLoadCapReached"
        class="terminal-button terminal-button-secondary"
        @click="pressReviewStore.loadMoreResults"
      >
        {{ t('dashboard.common.buttons.load_more') }}
      </button>
    </div>
  </section>
</template>
