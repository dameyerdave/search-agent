<script setup lang="ts">
const searchStore = useSearchWorkspaceStore()
const { t } = useI18n()
</script>

<template>
  <div class="flex flex-col gap-3 xl:flex-row xl:items-end xl:justify-between">
    <div>
      <p class="mono-heading text-lg tracking-[0.22em] text-white uppercase">
        {{ t('dashboard.search.live_bar.title') }}
      </p>
    </div>
    <div class="flex flex-wrap gap-2">
      <button
        class="terminal-button terminal-button-secondary p-2.5"
        :aria-expanded="searchStore.showAdvancedSearch"
        aria-controls="search-advanced-panel"
        :title="
          searchStore.showAdvancedSearch
            ? t('dashboard.search.live_bar.hide_advanced')
            : t('dashboard.search.live_bar.show_advanced')
        "
        :aria-label="
          searchStore.showAdvancedSearch
            ? t('dashboard.search.live_bar.hide_advanced')
            : t('dashboard.search.live_bar.show_advanced')
        "
        @click="searchStore.showAdvancedSearch = !searchStore.showAdvancedSearch"
      >
        <UIcon name="i-heroicons-adjustments-horizontal" class="size-4" />
      </button>
      <button
        class="terminal-button terminal-button-secondary p-2.5"
        :disabled="!searchStore.canSaveLiveSearchAsTopic"
        :title="t('dashboard.search.live_bar.save_search')"
        :aria-label="t('dashboard.search.live_bar.save_search')"
        @click="searchStore.openLiveSearchSaveDialog"
      >
        <UIcon name="i-heroicons-bookmark-square" class="size-4" />
      </button>
      <button
        class="terminal-button terminal-button-secondary p-2.5"
        :title="t('dashboard.common.buttons.reset')"
        :aria-label="t('dashboard.common.buttons.reset')"
        @click="searchStore.resetLiveSearchWorkspace"
      >
        <UIcon name="i-heroicons-arrow-uturn-left" class="size-4" />
      </button>
    </div>
  </div>

  <div class="grid gap-3 sm:grid-cols-[1fr_auto]">
    <label class="space-y-2">
      <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
        {{ t('dashboard.search.live_bar.query_label') }}
      </span>
      <div class="relative">
        <input
          v-model="searchStore.liveSearchForm.q"
          class="terminal-input pr-9"
          :placeholder="t('dashboard.search.live_bar.query_placeholder')"
          @keyup.enter="searchStore.runLiveSearch()"
        />
        <button
          v-if="searchStore.liveSearchForm.q"
          type="button"
          class="absolute inset-y-0 right-3 flex items-center text-[var(--muted)] hover:text-[var(--text)] transition-colors"
          :aria-label="t('dashboard.search.live_bar.clear_query')"
          @click="searchStore.liveSearchForm.q = ''"
        >
          <UIcon name="i-heroicons-x-mark" class="size-4" />
        </button>
      </div>
    </label>
    <button
      class="terminal-button terminal-button-primary flex h-[46px] items-center justify-center gap-2 self-end px-6"
      :disabled="searchStore.isRunningLiveSearch"
      @click="searchStore.runLiveSearch()"
    >
      <UIcon name="i-heroicons-magnifying-glass" class="size-4" />
      {{
        searchStore.isRunningLiveSearch
          ? t('dashboard.search.live_bar.searching')
          : t('dashboard.search.live_bar.search_now')
      }}
    </button>
  </div>
</template>
