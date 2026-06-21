<script setup lang="ts">
import { formatDate, formatNextRun, statusClass, summarizeStatus } from 'utils/dashboard'
import type { SearchTopic } from 'types/search-agent'

const dashboardStore = useDashboardStore()
const { t } = useI18n()

const nextRunLabel = (topic: SearchTopic) => {
  const next = formatNextRun(topic)
  if (next.paused) return t('dashboard.common.paused')
  return formatDate(next.date) ?? t('dashboard.common.never')
}

const sourceNames = (topic: SearchTopic) =>
  topic.source_scopes.map((scope) => scope.name).join(', ') || t('dashboard.explore.topic_navigator.sources_none')
</script>

<template>
  <section class="terminal-panel relative overflow-hidden rounded-[1.2rem] p-3 sm:rounded-3xl sm:p-5">
    <div class="relative z-10 space-y-3">
      <div class="flex items-center justify-between gap-3">
        <div>
          <p class="mono-heading text-sm tracking-[0.22em] text-white uppercase sm:text-lg">
            {{ t('dashboard.explore.topic_navigator.title') }}
          </p>
        </div>
        <button
          class="terminal-button terminal-button-secondary"
          :disabled="dashboardStore.isLoadingDashboard"
          @click="dashboardStore.refreshAll"
        >
          {{ t('dashboard.common.buttons.refresh') }}
        </button>
      </div>

      <div class="space-y-2 sm:space-y-3">
        <article
          v-for="topic in dashboardStore.topics"
          :key="topic.slug"
          class="overflow-hidden rounded-xl border border-[var(--line)] bg-black/25 p-3 sm:rounded-2xl sm:p-4"
        >
          <div class="flex flex-wrap items-start justify-between gap-2">
            <div class="min-w-0">
              <div class="flex flex-wrap gap-1.5">
                <span class="pill" :class="topic.enabled ? 'text-[var(--accent)]' : 'text-[var(--muted)]'">
                  {{ topic.enabled ? t('dashboard.common.armed') : t('dashboard.common.paused_badge') }}
                </span>
                <span class="pill" :class="statusClass(topic.last_run_status)">
                  {{ t(`dashboard.common.status.${summarizeStatus(topic.last_run_status)}`) }}
                </span>
              </div>
              <p class="mt-2 text-base break-words text-white">{{ topic.name }}</p>
            </div>
            <div
              class="flex shrink-0 divide-x divide-[var(--line)] overflow-hidden rounded-xl border border-[var(--line)] bg-black/20 text-center"
            >
              <div class="px-2.5 py-1">
                <p class="text-[10px] tracking-[0.18em] text-[var(--muted)] uppercase">
                  {{ t('dashboard.explore.topic_navigator.new') }}
                </p>
                <p class="mt-0.5 text-base text-white">{{ topic.new_results_count }}</p>
              </div>
              <div class="px-2.5 py-1">
                <p class="text-[10px] tracking-[0.18em] text-[var(--muted)] uppercase">
                  {{ t('dashboard.configure.topic_matrix.stored') }}
                </p>
                <p class="mt-0.5 text-base text-white">{{ topic.result_count }}</p>
              </div>
            </div>
          </div>

          <div class="mt-2.5 space-y-1 text-xs text-[var(--muted)]">
            <p>
              {{ t('dashboard.explore.topic_navigator.schedule') }}
              <span class="text-[var(--text)]">{{ topic.schedule_description }}</span>
            </p>
            <p>
              {{ t('dashboard.explore.topic_navigator.next_run') }}
              <span class="text-[var(--text)]">{{ nextRunLabel(topic) }}</span>
            </p>
            <p>
              {{ t('dashboard.explore.topic_navigator.last_checked') }}
              <span class="text-[var(--text)]">{{
                formatDate(topic.last_checked_at) ?? t('dashboard.common.never')
              }}</span>
            </p>
            <p class="break-words">
              {{ t('dashboard.explore.topic_navigator.sources') }}
              <span class="text-[var(--text)]">{{ sourceNames(topic) }}</span>
            </p>
          </div>

          <div class="mt-2.5 flex flex-wrap gap-1.5">
            <button class="terminal-button terminal-button-primary" @click="dashboardStore.focusTopicResults(topic)">
              {{ t('dashboard.common.buttons.inspect') }}
            </button>
            <button
              class="terminal-button terminal-button-secondary"
              :disabled="dashboardStore.activeTopicRun === topic.slug"
              @click="dashboardStore.runTopic(topic)"
            >
              {{
                dashboardStore.activeTopicRun === topic.slug
                  ? t('dashboard.common.buttons.running')
                  : t('dashboard.common.buttons.run_now')
              }}
            </button>
            <button
              class="terminal-button terminal-button-secondary"
              :disabled="dashboardStore.activeTopicAcknowledge === topic.slug"
              @click="dashboardStore.acknowledgeTopic(topic)"
            >
              {{ t('dashboard.common.buttons.ack_new') }}
            </button>
            <button
              class="terminal-button terminal-button-secondary"
              @click="dashboardStore.editTopicInConfigure(topic)"
            >
              {{ t('dashboard.common.buttons.edit') }}
            </button>
            <button class="terminal-button terminal-button-danger" @click="dashboardStore.deleteTopic(topic)">
              {{ t('dashboard.common.buttons.delete') }}
            </button>
          </div>
        </article>

        <article
          v-if="dashboardStore.topics.length === 0"
          class="rounded-xl border border-[var(--line)] bg-black/25 p-4 text-sm text-[var(--muted)] sm:rounded-2xl"
        >
          {{ t('dashboard.explore.topic_navigator.empty') }}
        </article>
      </div>
    </div>
  </section>
</template>
