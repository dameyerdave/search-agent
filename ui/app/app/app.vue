<script setup lang="ts">
const dashboardStore = useDashboardStore()

// Instantiate eagerly during this component's synchronous setup so their
// useI18n()/useToast() calls run with a valid Vue instance - bootstrap()
// later calls these stores from an async continuation (no current instance),
// which would otherwise throw.
useExploreWorkspaceStore()
useRunsWorkspaceStore()
useSavedWorkspaceStore()

watch(
  () => dashboardStore.totalNewResults,
  (count) => {
    if (!('setAppBadge' in navigator)) return
    if (count > 0) {
      navigator.setAppBadge(count)
    } else {
      navigator.clearAppBadge()
    }
  },
)

onMounted(() => {
  dashboardStore.bootstrap()
})
</script>

<template>
  <UApp>
    <div class="screen-shell grid-bg">
      <NuxtRouteAnnouncer />
      <PullToRefresh />
      <PwaInstallButton />

      <main class="mx-auto flex min-h-screen max-w-[1500px] flex-col gap-3 px-3 pt-3 pb-20 sm:gap-5 sm:px-6 sm:pt-5 sm:pb-24 lg:px-8">
        <DashboardHeader />
        <DashboardStatusBanner />

        <template v-if="!dashboardStore.isBootstrappingAuth">
          <WorkspaceTabNav />

          <SearchWorkspace />
          <ExploreWorkspace />
          <SavedWorkspace />
          <ConfigureWorkspace />
          <RunsWorkspace />
        </template>
      </main>
    </div>
  </UApp>
</template>
