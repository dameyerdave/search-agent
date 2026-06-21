<script setup lang="ts">
import { formatDate, statusClass, summarizeStatus } from 'utils/dashboard'
import type { SearchRun } from 'types/search-agent'

const dashboardStore = useDashboardStore()
const runsStore = useRunsWorkspaceStore()
const { t } = useI18n()

const runStatusLabel = (status: SearchRun['status']) => {
  if (status === 'succeeded') return t('dashboard.runs.run_history.status_succeeded')
  if (status === 'failed') return t('dashboard.runs.run_history.status_failed')
  if (status === 'limited') return t('dashboard.runs.run_history.status_limited')
  return t('dashboard.runs.run_history.status_running')
}

const formatRunDate = (value: string | null) => formatDate(value) ?? t('dashboard.common.never')
</script>

<template>
  <section class="terminal-panel relative overflow-hidden rounded-[1.2rem] p-3 sm:rounded-3xl sm:p-5">
    <div class="relative z-10 space-y-3">
      <div class="flex items-center justify-between gap-3">
        <p class="mono-heading text-sm tracking-[0.22em] text-white uppercase sm:text-lg">
          {{ t('dashboard.runs.run_history.title') }}
        </p>
        <div class="flex flex-wrap gap-2">
          <button class="terminal-button terminal-button-secondary" @click="runsStore.clearRunFilters">
            {{ t('dashboard.common.buttons.clear_filters') }}
          </button>
        </div>
      </div>

      <div class="grid gap-2 md:grid-cols-2 sm:gap-3">
        <label class="space-y-2">
          <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
            {{ t('dashboard.explore.results_terminal.topic_filter') }}
          </span>
          <select v-model="runsStore.runFilters.topic" class="terminal-select">
            <option value="">{{ t('dashboard.explore.results_terminal.all_topics') }}</option>
            <option v-for="topic in dashboardStore.topics" :key="topic.slug" :value="topic.slug">
              {{ topic.name }}
            </option>
          </select>
        </label>
        <label class="space-y-2">
          <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
            {{ t('dashboard.runs.run_history.status_filter') }}
          </span>
          <select v-model="runsStore.runFilters.status" class="terminal-select">
            <option value="">{{ t('dashboard.runs.run_history.all_statuses') }}</option>
            <option value="running">{{ t('dashboard.runs.run_history.status_running') }}</option>
            <option value="succeeded">{{ t('dashboard.runs.run_history.status_succeeded') }}</option>
            <option value="failed">{{ t('dashboard.runs.run_history.status_failed') }}</option>
            <option value="limited">{{ t('dashboard.runs.run_history.status_limited') }}</option>
          </select>
        </label>
      </div>

      <p class="text-sm text-[var(--muted)]">
        {{
          t('dashboard.runs.run_history.showing', {
            shown: runsStore.runs.length,
            total: runsStore.runsPage?.count ?? 0,
          })
        }}
        <span v-if="runsStore.selectedRunTopic">
          {{ t('dashboard.explore.results_terminal.showing_for_topic', { name: runsStore.selectedRunTopic.name }) }}
        </span>
      </p>

      <div class="space-y-2 sm:space-y-3">
        <article
          v-for="run in runsStore.runs"
          :key="run.id"
          class="rounded-xl border border-[var(--line)] bg-black/25 p-3 sm:rounded-2xl sm:p-4"
        >
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <p class="text-xs tracking-[0.18em] text-[var(--muted)] uppercase">{{ run.topic_name }}</p>
              <p class="mt-1 text-base" :class="statusClass(run.status)">
                {{ t(`dashboard.common.status.${summarizeStatus(run.status)}`) }}
              </p>
            </div>
            <span class="pill" :class="statusClass(run.status)">{{ runStatusLabel(run.status) }}</span>
          </div>

          <div class="mt-2.5 grid gap-2 grid-cols-3">
            <div>
              <p class="text-[10px] tracking-[0.18em] text-[var(--muted)] uppercase">
                {{ t('dashboard.runs.run_history.requests') }}
              </p>
              <p class="mt-1 text-xl text-white sm:text-2xl">{{ run.request_count }}</p>
            </div>
            <div>
              <p class="text-[10px] tracking-[0.18em] text-[var(--muted)] uppercase">
                {{ t('dashboard.runs.run_history.new_results') }}
              </p>
              <p class="mt-1 text-xl text-white sm:text-2xl">{{ run.new_results_count }}</p>
            </div>
            <div>
              <p class="text-[10px] tracking-[0.18em] text-[var(--muted)] uppercase">
                {{ t('dashboard.runs.run_history.pages_crawled') }}
              </p>
              <p class="mt-1 text-xl text-white sm:text-2xl">{{ run.pages_crawled }}</p>
            </div>
          </div>

          <div class="mt-2 space-y-1 text-xs text-[var(--muted)]">
            <p>{{ t('dashboard.runs.run_history.started', { date: formatRunDate(run.started_at) }) }}</p>
            <p>{{ t('dashboard.runs.run_history.completed', { date: formatRunDate(run.completed_at) }) }}</p>
            <p v-if="run.error_message" class="break-words text-[var(--warn)]">{{ run.error_message }}</p>
          </div>
        </article>

        <article
          v-if="runsStore.runs.length === 0"
          class="rounded-xl border border-[var(--line)] bg-black/25 p-4 text-sm text-[var(--muted)] sm:rounded-2xl"
        >
          {{ t('dashboard.runs.run_history.empty') }}
        </article>
      </div>
    </div>
  </section>
</template>
