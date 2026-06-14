<script setup lang="ts">
import { describeCategories, describeEngines, describeLanguages, describeResultOrder } from 'utils/dashboard'
import type { SourceScope } from 'types/search-agent'

const dashboardStore = useDashboardStore()
const configureStore = useConfigureWorkspaceStore()
const { t } = useI18n()

const categoriesHintId = 'configure-source-categories-hint'
const enginesHintId = 'configure-source-engines-hint'
const languagesHintId = 'configure-source-languages-hint'

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

const engineLabel = (source: SourceScope) => {
  const coverage = describeEngines(source)
  if (coverage.kind === 'all') return t('dashboard.configure.source_editor.engines_all')
  if (coverage.kind === 'none') return t('dashboard.configure.source_editor.engines_none')
  return coverage.values.join(', ')
}

const languageLabel = (source: SourceScope) => {
  const coverage = describeLanguages(source)
  if (coverage.kind === 'all') return t('dashboard.search.advanced.all_languages')
  return coverage.values.join(', ')
}

const resultOrderLabel = (source: SourceScope) =>
  describeResultOrder(source) === 'newest'
    ? t('dashboard.search.advanced.result_order_newest')
    : t('dashboard.search.advanced.result_order_relevance')
</script>

<template>
  <section class="terminal-panel relative overflow-hidden rounded-[1.5rem] p-5">
    <div class="relative z-10 space-y-4">
      <div class="flex items-start justify-between gap-3">
        <p class="mono-heading text-lg tracking-[0.22em] text-white uppercase">
          {{
            configureStore.sourceEditorMode === 'edit'
              ? t('dashboard.configure.source_editor.title_edit')
              : t('dashboard.configure.source_editor.title_create')
          }}
        </p>
        <button class="terminal-button terminal-button-secondary" @click="configureStore.resetSourceForm">
          {{ t('dashboard.common.buttons.reset') }}
        </button>
      </div>

      <div class="grid gap-3 sm:grid-cols-2">
        <label class="space-y-2 sm:col-span-2">
          <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
            {{ t('dashboard.configure.source_editor.name_label') }}
          </span>
          <input
            v-model="configureStore.sourceForm.name"
            class="terminal-input"
            :placeholder="t('dashboard.configure.source_editor.name_placeholder')"
          />
        </label>
        <label class="space-y-2 sm:col-span-2">
          <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
            {{ t('dashboard.configure.source_editor.description_label') }}
          </span>
          <textarea v-model="configureStore.sourceForm.description" class="terminal-textarea min-h-[90px]" />
        </label>
        <label class="space-y-2">
          <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
            {{ t('dashboard.configure.source_editor.kind_label') }}
          </span>
          <select v-model="configureStore.sourceForm.kind" class="terminal-select">
            <option value="public">{{ t('dashboard.explore.results_terminal.kind_public') }}</option>
            <option value="research">{{ t('dashboard.explore.results_terminal.kind_research') }}</option>
            <option value="custom">{{ t('dashboard.explore.results_terminal.kind_custom') }}</option>
          </select>
        </label>
        <label class="space-y-2">
          <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
            {{ t('dashboard.search.advanced.safe_search') }}
          </span>
          <select v-model="configureStore.sourceForm.safeSearch" class="terminal-select">
            <option value="0">{{ t('dashboard.search.advanced.safe_search_off') }}</option>
            <option value="1">{{ t('dashboard.search.advanced.safe_search_moderate') }}</option>
            <option value="2">{{ t('dashboard.search.advanced.safe_search_strict') }}</option>
          </select>
        </label>
        <label class="space-y-2">
          <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
            {{ t('dashboard.configure.source_editor.max_results_label') }}
          </span>
          <input v-model="configureStore.sourceForm.maxResults" class="terminal-input" type="number" min="1" max="20" />
        </label>
        <label class="space-y-2">
          <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
            {{ t('dashboard.search.advanced.time_range') }}
          </span>
          <select v-model="configureStore.sourceForm.timeRange" class="terminal-select">
            <option value="auto">{{ t('dashboard.configure.source_editor.time_range_auto') }}</option>
            <option value="any">{{ t('dashboard.configure.source_editor.time_range_any') }}</option>
            <option value="day">{{ t('dashboard.search.advanced.time_range_day') }}</option>
            <option value="month">{{ t('dashboard.search.advanced.time_range_month') }}</option>
            <option value="year">{{ t('dashboard.search.advanced.time_range_year') }}</option>
          </select>
        </label>
        <label class="space-y-2">
          <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
            {{ t('dashboard.search.advanced.result_order') }}
          </span>
          <select v-model="configureStore.sourceForm.resultOrder" class="terminal-select">
            <option value="relevance">{{ t('dashboard.search.advanced.result_order_relevance') }}</option>
            <option value="newest">{{ t('dashboard.search.advanced.result_order_newest') }}</option>
          </select>
        </label>
        <label class="space-y-2">
          <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
            {{ t('dashboard.configure.source_editor.sort_order_label') }}
          </span>
          <input v-model="configureStore.sourceForm.sortOrder" class="terminal-input" type="number" min="0" />
        </label>
        <label class="space-y-2">
          <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
            {{ t('dashboard.configure.source_editor.enabled_label') }}
          </span>
          <select v-model="configureStore.sourceForm.enabled" class="terminal-select">
            <option :value="true">{{ t('dashboard.common.enabled') }}</option>
            <option :value="false">{{ t('dashboard.common.disabled') }}</option>
          </select>
        </label>
        <label class="space-y-2 sm:col-span-2">
          <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
            {{ t('dashboard.search.advanced.category_coverage') }}
          </span>
          <select v-model="configureStore.sourceForm.useAllCategories" class="terminal-select">
            <option :value="true">{{ t('dashboard.search.advanced.all_categories_option') }}</option>
            <option :value="false">{{ t('dashboard.search.advanced.restricted_categories_option') }}</option>
          </select>
        </label>
        <div
          v-if="!configureStore.sourceForm.useAllCategories"
          class="space-y-3 rounded-[1.3rem] border border-[var(--line)] bg-black/20 p-4 sm:col-span-2"
        >
          <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
              {{ t('dashboard.search.advanced.selected_categories') }}
              <span class="text-[var(--text)]">{{ configureStore.sourceForm.searxngCategories.length }}</span> /
              {{ dashboardStore.availableCategories.length || '0' }}
            </p>
            <div class="flex flex-wrap gap-2">
              <button
                type="button"
                class="terminal-button terminal-button-secondary"
                @click="configureStore.selectAllSourceCategories"
              >
                {{ t('dashboard.common.buttons.select_all') }}
              </button>
              <button
                type="button"
                class="terminal-button terminal-button-secondary"
                @click="configureStore.clearSourceCategories"
              >
                {{ t('dashboard.common.buttons.clear') }}
              </button>
            </div>
          </div>
          <template v-if="dashboardStore.availableCategories.length">
            <p :id="categoriesHintId" class="text-xs text-[var(--muted)]">
              {{ t('dashboard.search.advanced.multi_select_hint') }}
            </p>
            <select
              v-model="configureStore.sourceForm.searxngCategories"
              class="terminal-select min-h-[220px]"
              multiple
              :aria-describedby="categoriesHintId"
            >
              <option
                v-for="category in dashboardStore.availableCategories"
                :key="`source-${category}`"
                :value="category"
              >
                {{ category }}
              </option>
            </select>
          </template>
          <p v-else class="text-sm text-[var(--muted)]">{{ t('dashboard.search.advanced.no_categories') }}</p>
        </div>
        <label class="space-y-2 sm:col-span-2">
          <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
            {{ t('dashboard.search.advanced.engine_coverage') }}
          </span>
          <select v-model="configureStore.sourceForm.useAllEngines" class="terminal-select">
            <option :value="true">{{ t('dashboard.search.advanced.all_engines_option') }}</option>
            <option :value="false">{{ t('dashboard.search.advanced.restricted_engines_option') }}</option>
          </select>
        </label>
        <div
          v-if="!configureStore.sourceForm.useAllEngines"
          class="space-y-3 rounded-[1.3rem] border border-[var(--line)] bg-black/20 p-4 sm:col-span-2"
        >
          <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
              {{ t('dashboard.search.advanced.selected_engines') }}
              <span class="text-[var(--text)]">{{ configureStore.sourceForm.searxngEngines.length }}</span> /
              {{ dashboardStore.availableEngines.length || '0' }}
            </p>
            <div class="flex flex-wrap gap-2">
              <button
                type="button"
                class="terminal-button terminal-button-secondary"
                @click="configureStore.selectAllSourceEngines"
              >
                {{ t('dashboard.common.buttons.select_all') }}
              </button>
              <button
                type="button"
                class="terminal-button terminal-button-secondary"
                @click="configureStore.clearSourceEngines"
              >
                {{ t('dashboard.common.buttons.clear') }}
              </button>
            </div>
          </div>
          <template v-if="dashboardStore.availableEngines.length">
            <p :id="enginesHintId" class="text-xs text-[var(--muted)]">
              {{ t('dashboard.search.advanced.multi_select_hint') }}
            </p>
            <select
              v-model="configureStore.sourceForm.searxngEngines"
              class="terminal-select min-h-[220px]"
              multiple
              :aria-describedby="enginesHintId"
            >
              <option
                v-for="engine in dashboardStore.availableEngines"
                :key="`source-engine-${engine}`"
                :value="engine"
              >
                {{ engine }}
              </option>
            </select>
          </template>
          <p v-else class="text-sm text-[var(--muted)]">{{ t('dashboard.search.advanced.no_engines') }}</p>
        </div>
        <div class="space-y-3 rounded-[1.3rem] border border-[var(--line)] bg-black/20 p-4 sm:col-span-2">
          <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
              {{ t('dashboard.search.advanced.selected_languages') }}
              <span class="text-[var(--text)]">{{ configureStore.sourceForm.languages.length }}</span> /
              {{ dashboardStore.availableLanguages.length || '0' }}
            </p>
            <div class="flex flex-wrap gap-2">
              <button
                type="button"
                class="terminal-button terminal-button-secondary"
                @click="configureStore.selectAllSourceLanguages"
              >
                {{ t('dashboard.common.buttons.select_all') }}
              </button>
              <button
                type="button"
                class="terminal-button terminal-button-secondary"
                @click="configureStore.clearSourceLanguages"
              >
                {{ t('dashboard.common.buttons.clear') }}
              </button>
            </div>
          </div>
          <template v-if="dashboardStore.availableLanguages.length">
            <p :id="languagesHintId" class="text-xs text-[var(--muted)]">
              {{ t('dashboard.search.advanced.multi_select_hint') }}
            </p>
            <select
              v-model="configureStore.sourceForm.languages"
              class="terminal-select min-h-[220px]"
              multiple
              :aria-describedby="languagesHintId"
            >
              <option
                v-for="language in dashboardStore.availableLanguages"
                :key="`source-language-${language.code}`"
                :value="language.code"
              >
                {{ language.label }} ({{ language.code }})
              </option>
            </select>
          </template>
          <p v-else class="text-sm text-[var(--muted)]">{{ t('dashboard.search.advanced.no_languages') }}</p>
        </div>
        <label class="space-y-2 sm:col-span-2">
          <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
            {{ t('dashboard.search.advanced.include_domains') }}
          </span>
          <textarea
            v-model="configureStore.sourceForm.includeDomains"
            class="terminal-textarea min-h-[90px]"
            placeholder="zenodo.org&#10;figshare.com"
          />
        </label>
        <label class="space-y-2 sm:col-span-2">
          <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
            {{ t('dashboard.search.advanced.exclude_domains') }}
          </span>
          <textarea
            v-model="configureStore.sourceForm.excludeDomains"
            class="terminal-textarea min-h-[90px]"
            placeholder="x.com&#10;facebook.com"
          />
        </label>
      </div>

      <div class="flex flex-wrap gap-2">
        <button
          class="terminal-button terminal-button-primary"
          :disabled="configureStore.isSavingSource"
          @click="configureStore.saveSource"
        >
          {{
            configureStore.isSavingSource
              ? t('dashboard.configure.source_editor.saving')
              : configureStore.sourceEditorMode === 'edit'
                ? t('dashboard.configure.source_editor.update_button')
                : t('dashboard.configure.source_editor.save_button')
          }}
        </button>
      </div>

      <div class="space-y-2 rounded-2xl border border-[var(--line)] bg-black/20 p-4">
        <p class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
          {{ t('dashboard.configure.source_editor.current_scopes_title') }}
        </p>
        <div
          v-for="source in dashboardStore.sources"
          :key="source.id"
          class="flex flex-col gap-3 rounded-2xl border border-[var(--line)] p-3 sm:flex-row sm:items-center sm:justify-between"
        >
          <div>
            <p class="text-sm text-[var(--text)]">{{ source.name }}</p>
            <p class="mt-1 text-xs text-[var(--muted)]">
              {{ kindLabel(source.kind) }} / {{ categoryLabel(source) }} / {{ engineLabel(source) }} /
              {{ languageLabel(source) }} / {{ resultOrderLabel(source) }}
            </p>
          </div>
          <div class="flex flex-wrap gap-2">
            <button class="terminal-button terminal-button-secondary" @click="configureStore.openSourceEditor(source)">
              {{ t('dashboard.common.buttons.edit') }}
            </button>
            <button class="terminal-button terminal-button-danger" @click="configureStore.deleteSource(source)">
              {{ t('dashboard.common.buttons.delete') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
