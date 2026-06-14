<script setup lang="ts">
const dashboardStore = useDashboardStore()
const searchStore = useSearchWorkspaceStore()
const { t } = useI18n()

const categoriesHintId = 'live-search-categories-hint'
const enginesHintId = 'live-search-engines-hint'
const languagesHintId = 'live-search-languages-hint'
</script>

<template>
  <div id="search-advanced-panel" class="space-y-4 rounded-[1.4rem] border border-[var(--line)] bg-black/20 p-4">
    <div class="grid gap-3 lg:grid-cols-3">
      <label class="space-y-2">
        <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
          {{ t('dashboard.search.advanced.safe_search') }}
        </span>
        <select v-model="searchStore.liveSearchForm.safeSearch" class="terminal-select">
          <option value="0">{{ t('dashboard.search.advanced.safe_search_off') }}</option>
          <option value="1">{{ t('dashboard.search.advanced.safe_search_moderate') }}</option>
          <option value="2">{{ t('dashboard.search.advanced.safe_search_strict') }}</option>
        </select>
      </label>
      <label class="space-y-2">
        <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
          {{ t('dashboard.search.advanced.time_range') }}
        </span>
        <select v-model="searchStore.liveSearchForm.timeRange" class="terminal-select">
          <option value="">{{ t('dashboard.search.advanced.time_range_none') }}</option>
          <option value="day">{{ t('dashboard.search.advanced.time_range_day') }}</option>
          <option value="month">{{ t('dashboard.search.advanced.time_range_month') }}</option>
          <option value="year">{{ t('dashboard.search.advanced.time_range_year') }}</option>
        </select>
      </label>
      <label class="space-y-2">
        <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
          {{ t('dashboard.search.advanced.result_order') }}
        </span>
        <select v-model="searchStore.liveSearchForm.resultOrder" class="terminal-select">
          <option value="relevance">{{ t('dashboard.search.advanced.result_order_relevance') }}</option>
          <option value="newest">{{ t('dashboard.search.advanced.result_order_newest') }}</option>
        </select>
      </label>
    </div>

    <div class="grid gap-3 lg:grid-cols-2">
      <label class="space-y-2">
        <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
          {{ t('dashboard.search.advanced.category_coverage') }}
        </span>
        <select v-model="searchStore.liveSearchForm.useAllCategories" class="terminal-select">
          <option :value="true">{{ t('dashboard.search.advanced.all_categories_option') }}</option>
          <option :value="false">{{ t('dashboard.search.advanced.restricted_categories_option') }}</option>
        </select>
      </label>
      <label class="space-y-2">
        <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
          {{ t('dashboard.search.advanced.engine_coverage') }}
        </span>
        <select v-model="searchStore.liveSearchForm.useAllEngines" class="terminal-select">
          <option :value="true">{{ t('dashboard.search.advanced.all_engines_option') }}</option>
          <option :value="false">{{ t('dashboard.search.advanced.restricted_engines_option') }}</option>
        </select>
      </label>
      <label class="space-y-2">
        <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
          {{ t('dashboard.search.advanced.include_domains') }}
        </span>
        <textarea
          v-model="searchStore.liveSearchForm.includeDomains"
          class="terminal-textarea min-h-[80px]"
          placeholder="zenodo.org&#10;datacite.org"
        />
      </label>
      <label class="space-y-2">
        <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
          {{ t('dashboard.search.advanced.exclude_domains') }}
        </span>
        <textarea
          v-model="searchStore.liveSearchForm.excludeDomains"
          class="terminal-textarea min-h-[80px]"
          placeholder="linkedin.com&#10;jobs.example.com"
        />
      </label>
      <label class="space-y-2 lg:col-span-2">
        <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
          {{ t('dashboard.search.advanced.raw_params') }}
        </span>
        <textarea
          v-model="searchStore.liveSearchForm.extraParams"
          class="terminal-textarea min-h-[110px]"
          placeholder="theme=simple&#10;enabled_plugins=Hash_plugin,Tracker_URL_remover&#10;disabled_plugins=Open_Access_DOI_rewrite"
        />
      </label>
    </div>

    <div class="space-y-3 rounded-[1.3rem] border border-[var(--line)] bg-black/20 p-4">
      <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
          {{ t('dashboard.search.advanced.selected_languages') }}
          <span class="text-[var(--text)]">{{ searchStore.liveSearchForm.languages.length }}</span> /
          {{ dashboardStore.availableLanguages.length || '0' }}
        </p>
        <div class="flex flex-wrap gap-2">
          <button
            type="button"
            class="terminal-button terminal-button-secondary"
            @click="searchStore.selectAllLiveSearchLanguages"
          >
            {{ t('dashboard.common.buttons.select_all') }}
          </button>
          <button
            type="button"
            class="terminal-button terminal-button-secondary"
            @click="searchStore.clearLiveSearchLanguages"
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
          v-model="searchStore.liveSearchForm.languages"
          class="terminal-select min-h-[220px]"
          multiple
          :aria-describedby="languagesHintId"
        >
          <option v-for="language in dashboardStore.availableLanguages" :key="language.code" :value="language.code">
            {{ language.label }} ({{ language.code }})
          </option>
        </select>
      </template>
      <p v-else class="text-sm text-[var(--muted)]">{{ t('dashboard.search.advanced.no_languages') }}</p>
    </div>

    <div
      v-if="!searchStore.liveSearchForm.useAllCategories"
      class="space-y-3 rounded-[1.3rem] border border-[var(--line)] bg-black/20 p-4"
    >
      <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
          {{ t('dashboard.search.advanced.selected_categories') }}
          <span class="text-[var(--text)]">{{ searchStore.liveSearchForm.categories.length }}</span> /
          {{ dashboardStore.availableCategories.length || '0' }}
        </p>
        <div class="flex flex-wrap gap-2">
          <button
            type="button"
            class="terminal-button terminal-button-secondary"
            @click="searchStore.selectAllLiveSearchCategories"
          >
            {{ t('dashboard.common.buttons.select_all') }}
          </button>
          <button
            type="button"
            class="terminal-button terminal-button-secondary"
            @click="searchStore.clearLiveSearchCategories"
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
          v-model="searchStore.liveSearchForm.categories"
          class="terminal-select min-h-[220px]"
          multiple
          :aria-describedby="categoriesHintId"
        >
          <option v-for="category in dashboardStore.availableCategories" :key="category" :value="category">
            {{ category }}
          </option>
        </select>
      </template>
      <p v-else class="text-sm text-[var(--muted)]">{{ t('dashboard.search.advanced.no_categories') }}</p>
    </div>

    <div
      v-if="!searchStore.liveSearchForm.useAllEngines"
      class="space-y-3 rounded-[1.3rem] border border-[var(--line)] bg-black/20 p-4"
    >
      <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
          {{ t('dashboard.search.advanced.selected_engines') }}
          <span class="text-[var(--text)]">{{ searchStore.liveSearchForm.engines.length }}</span> /
          {{ dashboardStore.availableEngines.length || '0' }}
        </p>
        <div class="flex flex-wrap gap-2">
          <button
            type="button"
            class="terminal-button terminal-button-secondary"
            @click="searchStore.selectAllLiveSearchEngines"
          >
            {{ t('dashboard.common.buttons.select_all') }}
          </button>
          <button
            type="button"
            class="terminal-button terminal-button-secondary"
            @click="searchStore.clearLiveSearchEngines"
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
          v-model="searchStore.liveSearchForm.engines"
          class="terminal-select min-h-[220px]"
          multiple
          :aria-describedby="enginesHintId"
        >
          <option v-for="engine in dashboardStore.availableEngines" :key="engine" :value="engine">
            {{ engine }}
          </option>
        </select>
      </template>
      <p v-else class="text-sm text-[var(--muted)]">{{ t('dashboard.search.advanced.no_engines') }}</p>
    </div>
  </div>
</template>
