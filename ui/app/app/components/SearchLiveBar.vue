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
        class="terminal-button terminal-button-secondary"
        :aria-expanded="searchStore.showAdvancedSearch"
        aria-controls="search-advanced-panel"
        @click="searchStore.showAdvancedSearch = !searchStore.showAdvancedSearch"
      >
        {{
          searchStore.showAdvancedSearch
            ? t('dashboard.search.live_bar.hide_advanced')
            : t('dashboard.search.live_bar.show_advanced')
        }}
      </button>
      <button
        class="terminal-button terminal-button-secondary"
        :disabled="!searchStore.canSaveLiveSearchAsTopic"
        @click="searchStore.openLiveSearchSaveDialog"
      >
        {{ t('dashboard.search.live_bar.save_search') }}
      </button>
      <button class="terminal-button terminal-button-secondary" @click="searchStore.resetLiveSearchWorkspace">
        {{ t('dashboard.common.buttons.reset') }}
      </button>
    </div>
  </div>

  <div class="grid gap-3 sm:grid-cols-[1fr_auto]">
    <label class="space-y-2">
      <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
        {{ t('dashboard.search.live_bar.query_label') }}
      </span>
      <input
        v-model="searchStore.liveSearchForm.q"
        class="terminal-input"
        :placeholder="t('dashboard.search.live_bar.query_placeholder')"
        @keyup.enter="searchStore.runLiveSearch()"
      />
    </label>
    <button
      class="terminal-button terminal-button-primary h-[46px] self-end px-6"
      :disabled="searchStore.isRunningLiveSearch"
      @click="searchStore.runLiveSearch()"
    >
      {{
        searchStore.isRunningLiveSearch
          ? t('dashboard.search.live_bar.searching')
          : t('dashboard.search.live_bar.search_now')
      }}
    </button>
  </div>
</template>
