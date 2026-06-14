<script setup lang="ts">
const dashboardStore = useDashboardStore()
const { t } = useI18n()
</script>

<template>
  <section class="grid gap-4 sm:grid-cols-2">
    <article class="terminal-panel relative overflow-hidden rounded-[1.4rem] p-5">
      <p class="text-xs tracking-[0.28em] text-[var(--muted)] uppercase">
        {{ t('dashboard.explore.stats.new_findings') }}
      </p>
      <p class="mt-3 text-4xl text-white">{{ dashboardStore.stats?.new_result_count ?? 0 }}</p>
    </article>
    <article class="terminal-panel relative overflow-hidden rounded-[1.4rem] p-5">
      <p class="text-xs tracking-[0.28em] text-[var(--muted)] uppercase">
        {{ t('dashboard.explore.stats.stored_results') }}
      </p>
      <p class="mt-3 text-4xl text-white">{{ dashboardStore.stats?.result_count ?? 0 }}</p>
    </article>
  </section>
</template>
