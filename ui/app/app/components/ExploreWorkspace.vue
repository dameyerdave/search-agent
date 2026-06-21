<script setup lang="ts">
const authStore = useAuthStore()
const dashboardStore = useDashboardStore()
const exploreStore = useExploreWorkspaceStore()
</script>

<template>
  <section
    v-if="authStore.isAuthenticated && dashboardStore.activeWorkspace === 'explore'"
    class="grid gap-3 sm:gap-5 xl:grid-cols-[0.92fr_1.48fr]"
  >
    <div class="min-w-0 space-y-3 sm:space-y-5">
      <NewResultsDashboard />
      <TopicNavigator />
      <ExploreResultsTerminal />
    </div>

    <div class="min-w-0 space-y-3 sm:space-y-5">
      <SearchMapWorkspace
        :topic-slug="exploreStore.resultFilters.topic"
        :topic-name="exploreStore.selectedTopic?.name ?? ''"
        :q="exploreStore.resultFilters.q"
        :kind="exploreStore.resultFilters.kind"
        :is-new-only="exploreStore.resultFilters.isNewOnly"
      />
    </div>
  </section>
</template>
