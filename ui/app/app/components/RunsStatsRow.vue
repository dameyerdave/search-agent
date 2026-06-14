<script setup lang="ts">
import { formatDate } from 'utils/dashboard'

const dashboardStore = useDashboardStore()
const runsStore = useRunsWorkspaceStore()
const { t } = useI18n()
</script>

<template>
  <section class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
    <article class="terminal-panel relative overflow-hidden rounded-[1.4rem] p-5">
      <p class="text-xs tracking-[0.28em] text-[var(--muted)] uppercase">
        {{ t('dashboard.runs.stats.tracked_topics') }}
      </p>
      <p class="mt-3 text-4xl text-white">{{ dashboardStore.stats?.topic_count ?? 0 }}</p>
    </article>
    <article class="terminal-panel relative overflow-hidden rounded-[1.4rem] p-5">
      <p class="text-xs tracking-[0.28em] text-[var(--muted)] uppercase">{{ t('dashboard.runs.stats.runs') }}</p>
      <p class="mt-3 text-4xl text-white">{{ dashboardStore.stats?.run_count ?? 0 }}</p>
    </article>
    <article class="terminal-panel relative overflow-hidden rounded-[1.4rem] p-5">
      <p class="text-xs tracking-[0.28em] text-[var(--muted)] uppercase">
        {{ t('dashboard.runs.stats.success_rate') }}
      </p>
      <p class="mt-3 text-4xl text-white">{{ runsStore.runSuccessRate }}%</p>
    </article>
    <article class="terminal-panel relative overflow-hidden rounded-[1.4rem] p-5">
      <p class="text-xs tracking-[0.28em] text-[var(--muted)] uppercase">{{ t('dashboard.runs.stats.latest_run') }}</p>
      <p class="mt-3 text-lg text-white">
        {{ runsStore.latestRun?.topic_name || t('dashboard.runs.stats.no_runs_yet') }}
      </p>
      <p v-if="runsStore.latestRun" class="mt-2 text-sm text-[var(--muted)]">
        {{ formatDate(runsStore.latestRun.started_at) }}
      </p>
    </article>
  </section>
</template>
