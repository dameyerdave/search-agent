<script setup lang="ts">
const authStore = useAuthStore()
const dashboardStore = useDashboardStore()
</script>

<template>
  <section
    v-if="authStore.isAuthenticated && dashboardStore.activeWorkspace === 'configure'"
    class="grid gap-5 xl:grid-cols-[1.45fr_0.95fr]"
  >
    <div class="min-w-0 space-y-5">
      <TopicMatrix />
    </div>

    <div class="min-w-0 space-y-5">
      <ProviderControl />
      <TopicEditor />
      <SourceEditor />
    </div>
  </section>
</template>
