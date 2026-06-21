<script setup lang="ts">
const authStore = useAuthStore()
const dashboardStore = useDashboardStore()
</script>

<template>
  <section v-if="authStore.isAuthenticated && dashboardStore.activeWorkspace === 'runs'" class="space-y-5">
    <RunsStatsRow />

    <section class="grid gap-5 xl:grid-cols-[1.35fr_0.95fr]">
      <RunHistory />
      <div class="min-w-0 space-y-5">
        <TopicPulse />
      </div>
    </section>
  </section>
</template>
