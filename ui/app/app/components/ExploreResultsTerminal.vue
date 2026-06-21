<script setup lang="ts">
import { formatDate } from 'utils/dashboard'

const dashboardStore = useDashboardStore()
const exploreStore = useExploreWorkspaceStore()
const { t } = useI18n()

const formatResultDate = (value: string | null) => formatDate(value) ?? t('dashboard.common.never')
</script>

<template>
  <section class="terminal-panel relative overflow-hidden rounded-[1.2rem] p-3 sm:rounded-3xl sm:p-5">
    <div class="relative z-10 space-y-3">
      <div class="flex items-center justify-between gap-3">
        <p class="mono-heading text-sm tracking-[0.22em] text-white uppercase sm:text-lg">
          {{ t('dashboard.explore.results_terminal.title') }}
        </p>
        <div class="flex flex-wrap gap-1.5">
          <button class="terminal-button terminal-button-secondary" @click="exploreStore.clearResultFilters">
            {{ t('dashboard.common.buttons.clear_filters') }}
          </button>
          <button class="terminal-button terminal-button-secondary" @click="exploreStore.acknowledgeVisibleResults">
            {{ t('dashboard.explore.results_terminal.ack_visible') }}
          </button>
        </div>
      </div>

      <div class="grid gap-3 lg:grid-cols-4">
        <label class="space-y-2 lg:col-span-2">
          <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
            {{ t('dashboard.explore.results_terminal.search_text') }}
          </span>
          <input
            v-model="exploreStore.resultFilters.q"
            class="terminal-input"
            :placeholder="t('dashboard.explore.results_terminal.search_placeholder')"
          />
        </label>
        <label class="space-y-2">
          <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
            {{ t('dashboard.explore.results_terminal.topic_filter') }}
          </span>
          <select v-model="exploreStore.resultFilters.topic" class="terminal-select">
            <option value="">{{ t('dashboard.explore.results_terminal.all_topics') }}</option>
            <option v-for="topic in dashboardStore.topics" :key="topic.slug" :value="topic.slug">
              {{ topic.name }}
            </option>
          </select>
        </label>
        <label class="space-y-2">
          <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
            {{ t('dashboard.explore.results_terminal.scope_kind') }}
          </span>
          <select v-model="exploreStore.resultFilters.kind" class="terminal-select">
            <option value="">{{ t('dashboard.explore.results_terminal.all_kinds') }}</option>
            <option value="public">{{ t('dashboard.explore.results_terminal.kind_public') }}</option>
            <option value="research">{{ t('dashboard.explore.results_terminal.kind_research') }}</option>
            <option value="custom">{{ t('dashboard.explore.results_terminal.kind_custom') }}</option>
          </select>
        </label>
      </div>

      <label class="flex items-center gap-3 text-sm text-[var(--muted)]">
        <input v-model="exploreStore.resultFilters.isNewOnly" type="checkbox" class="accent-[var(--accent)]" />
        {{ t('dashboard.explore.results_terminal.new_only') }}
      </label>

      <ResponsiveResultsList :results="exploreStore.results" :format-date="formatResultDate" />

      <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p class="text-sm text-[var(--muted)]">
          {{
            t('dashboard.explore.results_terminal.showing', {
              shown: exploreStore.results.length,
              total: exploreStore.resultsPage?.count ?? 0,
            })
          }}
          <span v-if="exploreStore.selectedTopic">
            {{ t('dashboard.explore.results_terminal.showing_for_topic', { name: exploreStore.selectedTopic.name }) }}
          </span>
        </p>
        <div class="flex gap-2">
          <button
            class="terminal-button terminal-button-secondary flex-1 sm:flex-initial"
            :disabled="!exploreStore.resultsPage?.previous"
            @click="exploreStore.loadResults(exploreStore.resultFilters.page - 1)"
          >
            {{ t('dashboard.explore.results_terminal.prev') }}
          </button>
          <button
            class="terminal-button terminal-button-secondary flex-1 sm:flex-initial"
            :disabled="!exploreStore.resultsPage?.next"
            @click="exploreStore.loadResults(exploreStore.resultFilters.page + 1)"
          >
            {{ t('dashboard.explore.results_terminal.next') }}
          </button>
        </div>
      </div>
    </div>
  </section>
</template>
