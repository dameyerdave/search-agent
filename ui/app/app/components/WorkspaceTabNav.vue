<script setup lang="ts">
const dashboardStore = useDashboardStore()
const { t } = useI18n()
</script>

<template>
  <section class="terminal-panel relative overflow-hidden rounded-[1.5rem] p-3 sm:p-4">
    <div class="relative z-10 grid gap-3 md:grid-cols-2 xl:grid-cols-4" role="tablist">
      <button
        v-for="tab in dashboardStore.visibleWorkspaceTabs"
        :key="tab.key"
        role="tab"
        :aria-selected="dashboardStore.activeWorkspace === tab.key"
        class="rounded-[1.2rem] border px-4 py-4 text-left transition-all"
        :class="
          dashboardStore.activeWorkspace === tab.key
            ? 'border-[var(--accent)] bg-[var(--accent-soft)] shadow-[0_0_24px_rgba(91,255,147,0.12)]'
            : 'border-[var(--line)] bg-black/25 hover:border-[var(--accent)]/60 hover:bg-black/35'
        "
        @click="dashboardStore.activeWorkspace = tab.key"
      >
        <p
          class="text-[11px] tracking-[0.28em] uppercase"
          :class="dashboardStore.activeWorkspace === tab.key ? 'text-[var(--accent)]' : 'text-[var(--muted)]'"
        >
          {{ t(tab.eyebrowKey) }}
        </p>
        <p class="mono-heading mt-2 text-lg text-white">{{ t(tab.labelKey) }}</p>
      </button>
    </div>
  </section>
</template>
