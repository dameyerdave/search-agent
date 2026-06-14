<script setup lang="ts">
import { describeCategories } from 'utils/dashboard'
import type { SourceScope } from 'types/search-agent'

const dashboardStore = useDashboardStore()
const configureStore = useConfigureWorkspaceStore()
const { t } = useI18n()

const kindLabel = (kind: SourceScope['kind']) => {
  if (kind === 'research') return t('dashboard.explore.results_terminal.kind_research')
  if (kind === 'custom') return t('dashboard.explore.results_terminal.kind_custom')
  return t('dashboard.explore.results_terminal.kind_public')
}

const categoryLabel = (source: SourceScope) => {
  const coverage = describeCategories(source)
  if (coverage.kind === 'all') return t('dashboard.search.save_dialog.categories_all')
  if (coverage.kind === 'none') return t('dashboard.search.save_dialog.categories_none')
  return coverage.values.join(', ')
}
</script>

<template>
  <section class="terminal-panel relative overflow-hidden rounded-[1.5rem] p-5">
    <div class="relative z-10 space-y-4">
      <div class="flex items-start justify-between gap-3">
        <p class="mono-heading text-lg tracking-[0.22em] text-white uppercase">
          {{
            configureStore.topicEditorMode === 'edit'
              ? t('dashboard.configure.topic_editor.title_edit')
              : t('dashboard.configure.topic_editor.title_create')
          }}
        </p>
        <button class="terminal-button terminal-button-secondary" @click="configureStore.resetTopicForm">
          {{ t('dashboard.common.buttons.reset') }}
        </button>
      </div>

      <div class="grid gap-3 sm:grid-cols-2">
        <label class="space-y-2 sm:col-span-2">
          <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
            {{ t('dashboard.configure.topic_editor.name_label') }}
          </span>
          <input
            v-model="configureStore.topicForm.name"
            class="terminal-input"
            :placeholder="t('dashboard.configure.topic_editor.name_placeholder')"
          />
        </label>
        <label class="space-y-2 sm:col-span-2">
          <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
            {{ t('dashboard.configure.topic_editor.description_label') }}
          </span>
          <textarea v-model="configureStore.topicForm.description" class="terminal-textarea min-h-[90px]" />
        </label>
        <label class="space-y-2">
          <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
            {{ t('dashboard.configure.topic_editor.queries_label') }}
          </span>
          <textarea v-model="configureStore.topicForm.queries" class="terminal-textarea min-h-[155px]" />
        </label>
        <div class="grid gap-3">
          <label class="space-y-2">
            <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
              {{ t('dashboard.configure.topic_editor.required_terms_label') }}
            </span>
            <textarea
              v-model="configureStore.topicForm.requiredTerms"
              class="terminal-textarea min-h-[70px]"
              :placeholder="t('dashboard.configure.topic_editor.required_terms_placeholder')"
            />
          </label>
          <label class="space-y-2">
            <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
              {{ t('dashboard.configure.topic_editor.excluded_terms_label') }}
            </span>
            <textarea
              v-model="configureStore.topicForm.excludedTerms"
              class="terminal-textarea min-h-[70px]"
              :placeholder="t('dashboard.configure.topic_editor.excluded_terms_placeholder')"
            />
          </label>
        </div>
        <label class="space-y-2">
          <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
            {{ t('dashboard.configure.topic_editor.lookback_days_label') }}
          </span>
          <input v-model="configureStore.topicForm.lookbackDays" class="terminal-input" type="number" min="1" />
        </label>
        <div class="grid gap-3">
          <label class="space-y-2">
            <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
              {{ t('dashboard.configure.topic_editor.schedule_every_label') }}
            </span>
            <input v-model="configureStore.topicForm.scheduleEvery" class="terminal-input" type="number" min="1" />
          </label>
          <label class="space-y-2">
            <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
              {{ t('dashboard.configure.topic_editor.schedule_unit_label') }}
            </span>
            <select v-model="configureStore.topicForm.scheduleUnit" class="terminal-select">
              <option value="minutes">{{ t('dashboard.search.save_dialog.unit_minutes') }}</option>
              <option value="hours">{{ t('dashboard.search.save_dialog.unit_hours') }}</option>
              <option value="days">{{ t('dashboard.search.save_dialog.unit_days') }}</option>
              <option value="weeks">{{ t('dashboard.search.save_dialog.unit_weeks') }}</option>
            </select>
          </label>
        </div>
        <label class="space-y-2">
          <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
            {{ t('dashboard.configure.topic_editor.max_results_label') }}
          </span>
          <input
            v-model="configureStore.topicForm.maxResultsPerQuery"
            class="terminal-input"
            type="number"
            min="1"
            max="20"
          />
        </label>
        <label class="space-y-2 sm:col-span-2">
          <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
            {{ t('dashboard.configure.topic_editor.notes_label') }}
          </span>
          <textarea v-model="configureStore.topicForm.notes" class="terminal-textarea min-h-[90px]" />
        </label>
        <label class="space-y-2">
          <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
            {{ t('dashboard.configure.topic_editor.enabled_label') }}
          </span>
          <select v-model="configureStore.topicForm.enabled" class="terminal-select">
            <option :value="true">{{ t('dashboard.common.enabled') }}</option>
            <option :value="false">{{ t('dashboard.common.disabled') }}</option>
          </select>
        </label>
      </div>

      <div class="space-y-3 rounded-2xl border border-[var(--line)] bg-black/20 p-4">
        <p class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
          {{ t('dashboard.configure.topic_editor.attach_sources') }}
        </p>
        <div class="grid gap-2 sm:grid-cols-2">
          <label
            v-for="source in dashboardStore.sources"
            :key="source.id"
            class="flex cursor-pointer items-start gap-3 rounded-2xl border border-[var(--line)] p-3 text-sm text-[var(--text)]"
          >
            <input
              :checked="configureStore.topicForm.sourceScopeIds.includes(source.id)"
              type="checkbox"
              class="mt-1 accent-[var(--accent)]"
              @change="configureStore.toggleTopicSource(source.id)"
            />
            <span>
              <span class="block">{{ source.name }}</span>
              <span class="mt-1 block text-xs text-[var(--muted)]"
                >{{ kindLabel(source.kind) }} / {{ categoryLabel(source) }}</span
              >
            </span>
          </label>
        </div>
      </div>

      <button
        class="terminal-button terminal-button-primary w-full"
        :disabled="configureStore.isSavingTopic"
        @click="configureStore.saveTopic"
      >
        {{
          configureStore.isSavingTopic
            ? t('dashboard.configure.topic_editor.saving')
            : configureStore.topicEditorMode === 'edit'
              ? t('dashboard.configure.topic_editor.update_button')
              : t('dashboard.configure.topic_editor.save_button')
        }}
      </button>
    </div>
  </section>
</template>
