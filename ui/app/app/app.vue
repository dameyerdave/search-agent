<script setup lang="ts">
const dashboardStore = useDashboardStore()

onMounted(() => {
  dashboardStore.bootstrap()
})
</script>

<template>
  <UApp>
    <div class="screen-shell grid-bg">
      <NuxtRouteAnnouncer />
      <PwaInstallButton />

      <main class="mx-auto flex min-h-screen max-w-[1500px] flex-col gap-5 px-4 pt-5 pb-28 sm:px-6 sm:pb-24 lg:px-8">
        <DashboardHeader />
        <DashboardStatusBanner />

        <template v-if="!dashboardStore.isBootstrappingAuth">
          <WorkspaceTabNav />

          <SearchWorkspace />
          <ExploreWorkspace />
          <ConfigureWorkspace />
          <RunsWorkspace />
        </template>
      </main>
    </div>
  </UApp>
</template>
