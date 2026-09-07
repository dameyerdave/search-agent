<script setup lang="ts">
import type { SearchResult } from 'types/search-agent'

const authStore = useAuthStore()
const dashboardStore = useDashboardStore()
const pressReviewStore = usePressReviewWorkspaceStore()
const { t } = useI18n()
const { followResult } = useFollowResult()

useInfiniteScroll(window, () => pressReviewStore.loadMoreResults(), {
  distance: 240,
  canLoadMore: () =>
    pressReviewStore.canLoadMore && !pressReviewStore.autoLoadCapReached && !pressReviewStore.isLoadingMore,
})

const topicGroups = computed(() => {
  const groups = new Map<number, { topicId: number; topicName: string; results: SearchResult[]; newCount: number }>()
  for (const result of pressReviewStore.results) {
    let group = groups.get(result.topic)
    if (!group) {
      group = { topicId: result.topic, topicName: result.topic_name, results: [], newCount: 0 }
      groups.set(result.topic, group)
    }
    group.results.push(result)
    if (result.is_new) group.newCount += 1
  }
  return [...groups.values()].sort((a, b) => b.newCount - a.newCount || a.topicName.localeCompare(b.topicName))
})

const selectedTopicId = ref<number | null>(null)
const selectedGroup = computed(() => topicGroups.value.find((group) => group.topicId === selectedTopicId.value) ?? null)

const openTopic = (topicId: number) => {
  selectedTopicId.value = topicId
  window.scrollTo({ top: 0 })
}

const backToTopics = () => {
  selectedTopicId.value = null
  window.scrollTo({ top: 0 })
}
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
              class="terminal-button terminal-button-secondary p-2.5"
              :disabled="pressReviewStore.newCount === 0"
              :title="t('press_review.acknowledge_all')"
              :aria-label="t('press_review.acknowledge_all')"
              @click="pressReviewStore.acknowledgeAll"
            >
              <UIcon name="i-heroicons-check-circle" class="size-4" />
            </button>
            <button
              class="terminal-button terminal-button-secondary p-2.5"
              :title="t('dashboard.common.buttons.refresh')"
              :aria-label="t('dashboard.common.buttons.refresh')"
              @click="pressReviewStore.loadResults(1)"
            >
              <UIcon name="i-heroicons-arrow-path" class="size-4" />
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

    <!-- Topics overview -->
    <div v-else-if="!selectedGroup" class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <button
        v-for="group in topicGroups"
        :key="group.topicId"
        type="button"
        class="terminal-panel relative overflow-hidden rounded-[1.2rem] p-4 text-left transition-transform hover:-translate-y-0.5 sm:rounded-2xl"
        @click="openTopic(group.topicId)"
      >
        <div class="relative z-10 flex items-start justify-between gap-3">
          <div class="min-w-0">
            <p class="truncate text-sm font-medium text-white sm:text-base">{{ group.topicName }}</p>
            <p class="mt-1 text-xs text-[var(--muted)]">
              {{ t('press_review.topic_total_count', { count: group.results.length }) }}
            </p>
          </div>
          <UIcon name="i-heroicons-chevron-right" class="mt-0.5 size-4 shrink-0 text-[var(--muted)]" />
        </div>
        <div class="relative z-10 mt-3">
          <span v-if="group.newCount > 0" class="pill bg-[var(--accent-soft)] text-[var(--accent)]">
            {{ t('press_review.new_count', { count: group.newCount }) }}
          </span>
          <span v-else class="text-xs text-[var(--muted)]">{{ t('press_review.no_new') }}</span>
        </div>
      </button>
    </div>

    <!-- Topic detail -->
    <div v-else class="space-y-4">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div class="flex items-center gap-2.5">
          <button
            class="terminal-button terminal-button-secondary p-2"
            :title="t('press_review.back_to_topics')"
            :aria-label="t('press_review.back_to_topics')"
            @click="backToTopics"
          >
            <UIcon name="i-heroicons-arrow-left" class="size-4" />
          </button>
          <p class="text-sm font-medium text-white sm:text-base">{{ selectedGroup.topicName }}</p>
        </div>
        <div class="flex shrink-0 flex-wrap items-center gap-1.5">
          <span v-if="selectedGroup.newCount > 0" class="pill bg-[var(--accent-soft)] text-[var(--accent)]">
            {{ t('press_review.new_count', { count: selectedGroup.newCount }) }}
          </span>
          <span class="text-xs text-[var(--muted)]">
            {{ t('press_review.topic_total_count', { count: selectedGroup.results.length }) }}
          </span>
        </div>
      </div>

      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <ResultCard
          v-for="result in selectedGroup.results"
          :key="result.id"
          :result="result"
          :show-topic="false"
          @save="pressReviewStore.saveResult"
          @unsave="pressReviewStore.unsaveResult"
          @follow="followResult"
        />
      </div>
    </div>

    <div class="flex justify-center pt-2">
      <p v-if="pressReviewStore.isLoadingMore" class="text-sm text-[var(--muted)]">
        {{ t('press_review.loading_more') }}
      </p>
      <button
        v-else-if="pressReviewStore.canLoadMore && pressReviewStore.autoLoadCapReached"
        class="terminal-button terminal-button-secondary flex items-center gap-1.5"
        @click="pressReviewStore.loadMoreResults"
      >
        <UIcon name="i-heroicons-chevron-down" class="size-4" />
        {{ t('dashboard.common.buttons.load_more') }}
      </button>
    </div>
  </section>
</template>
