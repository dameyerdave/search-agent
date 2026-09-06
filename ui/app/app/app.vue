<script setup lang="ts">
const dashboardStore = useDashboardStore()
const pushStore = usePushNotificationsStore()

// Instantiate eagerly during this component's synchronous setup so their
// useI18n()/useToast() calls run with a valid Vue instance - bootstrap()
// later calls these stores from an async continuation (no current instance),
// which would otherwise throw.
useExploreWorkspaceStore()
useRunsWorkspaceStore()
useSavedWorkspaceStore()
usePressReviewWorkspaceStore()

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
  { immediate: true },
)

watch(
  () => dashboardStore.isBootstrappingAuth,
  async (booting) => {
    if (!booting) await pushStore.initForUser()
  },
)

onMounted(() => {
  pushStore.syncState()
  dashboardStore.bootstrap()
})
</script>

<template>
  <UApp>
    <div class="screen-shell grid-bg">
      <NuxtRouteAnnouncer />
      <PullToRefresh />
      <PwaInstallButton />
      <WorkspaceTabNav v-if="!dashboardStore.isBootstrappingAuth" />

      <main
        class="mx-auto flex min-h-screen max-w-[1500px] flex-col gap-3 px-3 pt-3 pb-28 sm:gap-5 sm:px-6 sm:pt-5 lg:px-8"
      >
        <DashboardHeader />
        <DashboardStatusBanner />

        <template v-if="!dashboardStore.isBootstrappingAuth">
          <SearchWorkspace />
          <ExploreWorkspace />
          <PressReviewWorkspace />
          <SavedWorkspace />
          <ConfigureWorkspace />
          <RunsWorkspace />
        </template>
      </main>
    </div>
  </UApp>
</template>
