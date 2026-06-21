<script setup lang="ts">
import { formatDate } from 'utils/dashboard'

const searchStore = useSearchWorkspaceStore()
const { t } = useI18n()

useInfiniteScroll(window, () => searchStore.loadMoreLiveSearchResults(), {
  distance: 240,
  canLoadMore: () => searchStore.canLoadMoreLiveSearch && !searchStore.isRunningLiveSearch,
})
</script>

<template>
  <section class="terminal-panel relative overflow-hidden rounded-[1.5rem] p-5">
    <div class="relative z-10 space-y-4">
      <p class="mono-heading text-lg tracking-[0.22em] text-white uppercase">
        {{ t('dashboard.search.live_stream.title') }}
      </p>

      <div
        v-if="searchStore.isLoadingFreshSearch"
        class="flex flex-col items-center gap-4 rounded-2xl border border-[var(--line)] bg-black/25 p-10 text-center"
      >
        <XunoLoadingMark :label="t('dashboard.search.live_stream.searching')" />
        <p class="mono-heading text-sm tracking-[0.22em] text-[var(--muted)] uppercase">
          {{ t('dashboard.search.live_stream.searching') }}
        </p>
      </div>

      <div v-else-if="searchStore.liveSearchResponse && searchStore.liveSearchResults.length" class="space-y-3">
        <article
          v-for="result in searchStore.liveSearchResults"
          :key="`${result.url}-${result.position}`"
          class="rounded-2xl border border-[var(--line)] bg-black/25 p-4"
        >
          <div class="flex flex-wrap items-start justify-between gap-3">
            <div class="space-y-2">
              <div class="flex flex-wrap gap-2">
                <span v-if="result.engine" class="pill text-[var(--accent)]">{{ result.engine }}</span>
                <span v-if="result.category" class="pill text-[var(--text)]">{{ result.category }}</span>
                <span class="pill text-[var(--muted)]">#{{ result.position }}</span>
              </div>
              <a
                :href="result.url"
                target="_blank"
                rel="noreferrer"
                class="break-words text-lg text-white hover:text-[var(--accent)]"
              >
                {{ result.title }}
                <span class="sr-only">{{ t('dashboard.common.opens_new_tab') }}</span>
              </a>
              <p class="break-words text-xs tracking-[0.18em] text-[var(--muted)] uppercase">{{ result.domain }}</p>
            </div>
            <div class="text-left text-xs text-[var(--muted)] sm:text-right">
              <p>
                {{
                  t('results.meta.published', { date: formatDate(result.published_at) ?? t('results.not_available') })
                }}
              </p>
              <p class="mt-2">
                {{ t('dashboard.search.live_stream.score', { score: result.score ?? t('results.not_available') }) }}
              </p>
            </div>
          </div>
          <p class="mt-3 text-sm leading-6 text-[var(--muted)]">
            {{ result.snippet || t('dashboard.search.live_stream.no_snippet') }}
          </p>
        </article>

        <div class="flex justify-center pt-2">
          <p v-if="searchStore.isRunningLiveSearch" class="text-sm text-[var(--muted)]">
            {{ t('dashboard.search.live_stream.loading') }}
          </p>
          <p v-else class="text-sm text-[var(--muted)]">
            {{ t('dashboard.search.live_stream.showing_results', { count: searchStore.liveSearchLoadedCount }) }}
          </p>
        </div>
      </div>

      <article v-else class="rounded-2xl border border-[var(--line)] bg-black/25 p-5 text-sm text-[var(--muted)]">
        {{ t('dashboard.search.live_stream.empty') }}
      </article>
    </div>
  </section>
</template>
