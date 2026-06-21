<script setup lang="ts">
import { formatDate } from 'utils/dashboard'

const dashboardStore = useDashboardStore()
const runsStore = useRunsWorkspaceStore()
const { t } = useI18n()
</script>

<template>
  <section class="grid grid-cols-2 gap-2 sm:gap-4 xl:grid-cols-4">
    <article class="terminal-panel relative overflow-hidden rounded-xl p-3 sm:rounded-[1.4rem] sm:p-5">
      <p class="text-[10px] tracking-[0.22em] text-[var(--muted)] uppercase sm:text-xs sm:tracking-[0.28em]">
        {{ t('dashboard.runs.stats.tracked_topics') }}
      </p>
      <p class="mt-1.5 text-2xl text-white sm:mt-3 sm:text-4xl">{{ dashboardStore.stats?.topic_count ?? 0 }}</p>
    </article>
    <article class="terminal-panel relative overflow-hidden rounded-xl p-3 sm:rounded-[1.4rem] sm:p-5">
      <p class="text-[10px] tracking-[0.22em] text-[var(--muted)] uppercase sm:text-xs sm:tracking-[0.28em]">{{ t('dashboard.runs.stats.runs') }}</p>
      <p class="mt-1.5 text-2xl text-white sm:mt-3 sm:text-4xl">{{ dashboardStore.stats?.run_count ?? 0 }}</p>
    </article>
    <article class="terminal-panel relative overflow-hidden rounded-xl p-3 sm:rounded-[1.4rem] sm:p-5">
      <p class="text-[10px] tracking-[0.22em] text-[var(--muted)] uppercase sm:text-xs sm:tracking-[0.28em]">
        {{ t('dashboard.runs.stats.success_rate') }}
      </p>
      <p class="mt-1.5 text-2xl text-white sm:mt-3 sm:text-4xl">{{ runsStore.runSuccessRate }}%</p>
    </article>
    <article class="terminal-panel relative overflow-hidden rounded-xl p-3 sm:rounded-[1.4rem] sm:p-5 col-span-2 xl:col-span-1">
      <p class="text-[10px] tracking-[0.22em] text-[var(--muted)] uppercase sm:text-xs sm:tracking-[0.28em]">{{ t('dashboard.runs.stats.latest_run') }}</p>
      <p class="mt-1.5 text-base text-white sm:mt-3 sm:text-lg">
        {{ runsStore.latestRun?.topic_name || t('dashboard.runs.stats.no_runs_yet') }}
      </p>
      <p v-if="runsStore.latestRun" class="mt-1 text-xs text-[var(--muted)] sm:mt-2 sm:text-sm">
        {{ formatDate(runsStore.latestRun.started_at) }}
      </p>
    </article>
  </section>
</template>
