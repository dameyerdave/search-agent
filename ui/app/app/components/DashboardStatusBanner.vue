<script setup lang="ts">
const dashboardStore = useDashboardStore()
const { t } = useI18n()
</script>

<template>
  <section
    v-if="dashboardStore.isBootstrappingAuth"
    class="rounded-2xl border border-[var(--line)] bg-black/30 px-4 py-6 text-sm text-[var(--muted)]"
  >
    {{ t('dashboard.shell.status.checking_access') }}
  </section>
  <section
    v-else-if="dashboardStore.errorMessage"
    role="alert"
    class="rounded-2xl border border-[rgba(255,125,125,0.35)] bg-[rgba(64,7,7,0.6)] px-4 py-3 text-sm text-[#ffd8d8]"
  >
    {{ dashboardStore.errorMessage }}
  </section>
</template>
