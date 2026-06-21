<script setup lang="ts">
import { formatDate, formatNextRun, statusClass, summarizeStatus } from 'utils/dashboard'
import type { SearchTopic } from 'types/search-agent'

const dashboardStore = useDashboardStore()
const { t } = useI18n()

const nextRunInline = (topic: SearchTopic) => {
  const next = formatNextRun(topic)
  if (next.paused) return t('dashboard.common.paused')
  return formatDate(next.date) ?? t('dashboard.common.never')
}
</script>

<template>
  <section class="terminal-panel relative overflow-hidden rounded-[1.5rem] p-5">
    <div class="relative z-10 space-y-4">
      <p class="mono-heading text-lg tracking-[0.22em] text-white uppercase">
        {{ t('dashboard.runs.topic_pulse.title') }}
      </p>

      <div class="space-y-3">
        <article
          v-for="topic in dashboardStore.topics"
          :key="topic.slug"
          class="rounded-2xl border border-[var(--line)] bg-black/25 p-4"
        >
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <p class="text-sm break-words text-white">{{ topic.name }}</p>
              <p class="mt-2 text-xs text-[var(--muted)]">
                {{
                  t('dashboard.runs.topic_pulse.checked', {
                    date: formatDate(topic.last_checked_at) ?? t('dashboard.common.never'),
                  })
                }}
              </p>
              <p class="mt-2 text-xs text-[var(--muted)]">
                {{ topic.schedule_description }} /
                {{ t('dashboard.runs.topic_pulse.next_run_inline', { value: nextRunInline(topic) }) }}
              </p>
            </div>
            <span class="pill" :class="statusClass(topic.last_run_status)">
              {{ t(`dashboard.common.status.${summarizeStatus(topic.last_run_status)}`) }}
            </span>
          </div>

          <div class="mt-4 grid gap-3 sm:grid-cols-3">
            <div>
              <p class="text-xs tracking-[0.18em] text-[var(--muted)] uppercase">
                {{ t('dashboard.explore.topic_navigator.new') }}
              </p>
              <p class="mt-2 text-xl text-white">{{ topic.new_results_count }}</p>
            </div>
            <div>
              <p class="text-xs tracking-[0.18em] text-[var(--muted)] uppercase">
                {{ t('dashboard.configure.topic_matrix.stored') }}
              </p>
              <p class="mt-2 text-xl text-white">{{ topic.result_count }}</p>
            </div>
            <div>
              <p class="text-xs tracking-[0.18em] text-[var(--muted)] uppercase">
                {{ t('dashboard.runs.topic_pulse.sources_label') }}
              </p>
              <p class="mt-2 text-xl text-white">{{ topic.source_scopes.length }}</p>
            </div>
          </div>

          <div class="mt-4 flex flex-wrap gap-2">
            <button class="terminal-button terminal-button-primary" @click="dashboardStore.focusTopicResults(topic)">
              {{ t('dashboard.common.buttons.inspect') }}
            </button>
            <button
              class="terminal-button terminal-button-secondary"
              @click="dashboardStore.editTopicInConfigure(topic)"
            >
              {{ t('dashboard.common.buttons.edit') }}
            </button>
          </div>
        </article>
      </div>
    </div>
  </section>
</template>
