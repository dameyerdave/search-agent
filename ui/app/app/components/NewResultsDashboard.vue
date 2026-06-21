<script setup lang="ts">
const dashboardStore = useDashboardStore()
const { t } = useI18n()

const topicsWithNew = computed(() => dashboardStore.topics.filter((t) => t.new_results_count > 0))
</script>

<template>
  <section class="terminal-panel relative overflow-hidden rounded-[1.5rem] p-5">
    <div class="relative z-10 space-y-4">
      <p class="mono-heading text-lg tracking-[0.22em] text-white uppercase">
        {{ t('dashboard.explore.new_results_dashboard.title') }}
        <span v-if="dashboardStore.totalNewResults > 0" class="ml-2 text-[var(--accent)]">
          {{ dashboardStore.totalNewResults }}
        </span>
      </p>

      <div v-if="topicsWithNew.length > 0" class="grid gap-3 sm:grid-cols-2">
        <button
          v-for="topic in topicsWithNew"
          :key="topic.slug"
          class="group flex items-center justify-between gap-3 rounded-2xl border border-[var(--line)] bg-black/25 p-4 text-left transition-colors hover:border-[var(--accent)]/50 hover:bg-black/35"
          @click="dashboardStore.focusTopicNewResults(topic)"
        >
          <p class="min-w-0 text-sm break-words text-white">{{ topic.name }}</p>
          <div
            class="flex shrink-0 items-center gap-1.5 rounded-xl border border-[var(--accent)]/30 bg-[var(--accent-soft)] px-2.5 py-1"
          >
            <span class="h-1.5 w-1.5 rounded-full bg-[var(--accent)] shadow-[0_0_6px_var(--accent)]" />
            <span class="text-sm font-medium text-[var(--accent)]">{{ topic.new_results_count }}</span>
            <span class="text-xs text-[var(--accent)]/70">
              {{
                topic.new_results_count === 1
                  ? t('dashboard.explore.new_results_dashboard.result')
                  : t('dashboard.explore.new_results_dashboard.results')
              }}
            </span>
          </div>
        </button>
      </div>

      <p v-else class="text-sm text-[var(--muted)]">
        {{ t('dashboard.explore.new_results_dashboard.all_caught_up') }}
      </p>
    </div>
  </section>
</template>
