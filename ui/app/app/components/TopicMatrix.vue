<script setup lang="ts">
import { formatDate, formatNextRun, statusClass, summarizeStatus } from 'utils/dashboard'
import type { SearchTopic } from 'types/search-agent'

const dashboardStore = useDashboardStore()
const configureStore = useConfigureWorkspaceStore()
const { t } = useI18n()

const nextRunLabel = (topic: SearchTopic) => {
  const next = formatNextRun(topic)
  if (next.paused) return t('dashboard.common.paused')
  return formatDate(next.date) ?? t('dashboard.common.never')
}

const sourceNames = (topic: SearchTopic) =>
  topic.source_scopes.map((scope) => scope.name).join(', ') || t('dashboard.explore.topic_navigator.sources_none')

const lookbackLabel = (topic: SearchTopic) =>
  t('dashboard.configure.topic_matrix.lookback_suffix', { days: topic.lookback_days })
</script>

<template>
  <section class="terminal-panel relative overflow-hidden rounded-[1.5rem] p-5">
    <div class="relative z-10 space-y-4">
      <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p class="mono-heading text-lg tracking-[0.22em] text-white uppercase">
          {{ t('dashboard.configure.topic_matrix.title') }}
        </p>
        <div class="flex flex-wrap gap-2">
          <button
            class="terminal-button terminal-button-secondary p-2.5"
            :disabled="dashboardStore.isLoadingDashboard"
            :title="t('dashboard.common.buttons.refresh')"
            :aria-label="t('dashboard.common.buttons.refresh')"
            @click="dashboardStore.refreshAll"
          >
            <UIcon name="i-heroicons-arrow-path" class="size-4" />
          </button>
          <button
            class="terminal-button terminal-button-secondary flex items-center gap-1.5"
            @click="configureStore.resetSourceForm"
          >
            <UIcon name="i-heroicons-document-plus" class="size-4" />
            {{ t('dashboard.configure.topic_matrix.new_source') }}
          </button>
          <button
            class="terminal-button terminal-button-primary flex items-center gap-1.5"
            @click="configureStore.openTopicEditor()"
          >
            <UIcon name="i-heroicons-plus" class="size-4" />
            {{ t('dashboard.configure.topic_matrix.new_topic') }}
          </button>
        </div>
      </div>

      <div class="grid gap-4 lg:grid-cols-2">
        <article
          v-for="topic in dashboardStore.topics"
          :key="topic.slug"
          class="terminal-panel relative overflow-hidden rounded-[1.5rem] p-5"
        >
          <div class="relative z-10 flex h-full flex-col gap-4">
            <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              <div class="space-y-2">
                <div class="flex flex-wrap gap-2">
                  <span class="pill" :class="topic.enabled ? 'text-[var(--accent)]' : 'text-[var(--muted)]'">
                    {{ topic.enabled ? t('dashboard.common.armed') : t('dashboard.common.paused_badge') }}
                  </span>
                  <span class="pill" :class="statusClass(topic.last_run_status)">
                    {{ t(`dashboard.common.status.${summarizeStatus(topic.last_run_status)}`) }}
                  </span>
                  <span v-if="topic.origin_kind === 'followed'" class="pill text-[var(--accent)]">
                    <UIcon name="i-heroicons-signal" class="size-3" />
                    {{ t('dashboard.configure.topic_editor.followed_from') }}
                  </span>
                </div>
                <h2 class="text-xl text-white">{{ topic.name }}</h2>
                <a
                  v-if="topic.origin_result"
                  :href="topic.origin_result.url"
                  target="_blank"
                  rel="noreferrer"
                  class="block max-w-md truncate text-xs text-[var(--muted)] hover:text-[var(--accent)]"
                >
                  ↳ {{ topic.origin_result.title }}
                </a>
              </div>

              <div class="sm:min-w-[110px] sm:text-right">
                <p class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
                  {{ t('dashboard.explore.topic_navigator.new') }}
                </p>
                <p class="mt-1 text-3xl text-white">{{ topic.new_results_count }}</p>
              </div>
            </div>

            <div class="space-y-3 rounded-2xl border border-[var(--line)] bg-black/25 p-4">
              <p class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
                {{ t('dashboard.configure.topic_matrix.queries') }}
              </p>
              <div class="flex flex-wrap gap-2">
                <span
                  v-for="query in topic.query_preview"
                  :key="query"
                  class="rounded-full border border-[var(--line)] px-3 py-1 text-xs text-[var(--text)]"
                >
                  {{ query }}
                </span>
              </div>
            </div>

            <div class="grid gap-3 sm:grid-cols-3">
              <div class="rounded-2xl border border-[var(--line)] bg-black/20 p-3">
                <p class="text-xs tracking-[0.2em] text-[var(--muted)] uppercase">
                  {{ t('dashboard.configure.topic_matrix.scope_count') }}
                </p>
                <p class="mt-2 text-2xl text-white">{{ topic.source_scopes.length }}</p>
              </div>
              <div class="rounded-2xl border border-[var(--line)] bg-black/20 p-3">
                <p class="text-xs tracking-[0.2em] text-[var(--muted)] uppercase">
                  {{ t('dashboard.configure.topic_matrix.lookback') }}
                </p>
                <p class="mt-2 text-2xl text-white">{{ lookbackLabel(topic) }}</p>
              </div>
              <div class="rounded-2xl border border-[var(--line)] bg-black/20 p-3">
                <p class="text-xs tracking-[0.2em] text-[var(--muted)] uppercase">
                  {{ t('dashboard.configure.topic_matrix.stored') }}
                </p>
                <p class="mt-2 text-2xl text-white">{{ topic.result_count }}</p>
              </div>
            </div>

            <div class="space-y-2 text-xs text-[var(--muted)]">
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
              <p>
                {{ t('dashboard.configure.topic_matrix.last_new_result') }}
                <span class="text-[var(--text)]">{{
                  formatDate(topic.last_new_results_at) ?? t('dashboard.common.never')
                }}</span>
              </p>
              <p>
                {{ t('dashboard.explore.topic_navigator.sources') }}
                <span class="text-[var(--text)]">{{ sourceNames(topic) }}</span>
              </p>
            </div>

            <div class="mt-auto flex flex-wrap gap-2">
              <button
                class="terminal-button terminal-button-primary p-2"
                :disabled="dashboardStore.activeTopicRun === topic.slug"
                :title="
                  dashboardStore.activeTopicRun === topic.slug
                    ? t('dashboard.common.buttons.running')
                    : t('dashboard.common.buttons.run_now')
                "
                :aria-label="t('dashboard.common.buttons.run_now')"
                @click="dashboardStore.runTopic(topic)"
              >
                <UIcon
                  :name="dashboardStore.activeTopicRun === topic.slug ? 'i-heroicons-arrow-path' : 'i-heroicons-play'"
                  class="size-4"
                  :class="{ 'animate-spin': dashboardStore.activeTopicRun === topic.slug }"
                />
              </button>
              <button
                class="terminal-button terminal-button-secondary p-2"
                :disabled="dashboardStore.activeTopicAcknowledge === topic.slug"
                :title="t('dashboard.common.buttons.ack_new')"
                :aria-label="t('dashboard.common.buttons.ack_new')"
                @click="dashboardStore.acknowledgeTopic(topic)"
              >
                <UIcon name="i-heroicons-check" class="size-4" />
              </button>
              <button
                class="terminal-button terminal-button-secondary p-2"
                :title="t('dashboard.common.buttons.inspect')"
                :aria-label="t('dashboard.common.buttons.inspect')"
                @click="dashboardStore.focusTopicResults(topic)"
              >
                <UIcon name="i-heroicons-eye" class="size-4" />
              </button>
              <button
                class="terminal-button terminal-button-secondary p-2"
                :title="t('dashboard.common.buttons.edit')"
                :aria-label="t('dashboard.common.buttons.edit')"
                @click="configureStore.openTopicEditor(topic)"
              >
                <UIcon name="i-heroicons-pencil" class="size-4" />
              </button>
              <button
                class="terminal-button terminal-button-danger p-2"
                :title="t('dashboard.common.buttons.delete')"
                :aria-label="t('dashboard.common.buttons.delete')"
                @click="dashboardStore.deleteTopic(topic)"
              >
                <UIcon name="i-heroicons-trash" class="size-4" />
              </button>
            </div>
          </div>
        </article>
      </div>
    </div>
  </section>
</template>
