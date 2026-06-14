<script setup lang="ts">
const authStore = useAuthStore()
const dashboardStore = useDashboardStore()
const searchStore = useSearchWorkspaceStore()
</script>

<template>
  <template v-if="dashboardStore.activeWorkspace === 'search' || !authStore.isAuthenticated">
    <section>
      <section class="terminal-panel relative overflow-hidden rounded-[1.5rem] p-5">
        <div class="relative z-10 space-y-5">
          <SearchLiveBar />
          <SearchAdvancedPanel v-if="searchStore.showAdvancedSearch" />
        </div>
      </section>
    </section>

    <LiveResultStream />

    <SaveSearchDialog v-if="searchStore.showLiveSearchSaveDialog && authStore.isAuthenticated" />
  </template>
</template>
