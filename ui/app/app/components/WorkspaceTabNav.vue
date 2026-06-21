<script setup lang="ts">
const dashboardStore = useDashboardStore()
const { t } = useI18n()

const tabIcons: Record<string, string> = {
  search: 'i-heroicons-magnifying-glass',
  explore: 'i-heroicons-globe-alt',
  configure: 'i-heroicons-cog-6-tooth',
  runs: 'i-heroicons-clock',
}
</script>

<template>
  <section class="terminal-panel relative overflow-hidden rounded-[1.5rem] p-2 sm:p-3">
    <div class="relative z-10 flex justify-center gap-2" role="tablist">
      <UTooltip v-for="tab in dashboardStore.visibleWorkspaceTabs" :key="tab.key" :text="t(tab.labelKey)">
        <button
          role="tab"
          :aria-selected="dashboardStore.activeWorkspace === tab.key"
          :aria-label="t(tab.labelKey)"
          class="relative flex h-12 w-12 items-center justify-center rounded-[1rem] border transition-all sm:h-14 sm:w-14"
          :class="
            dashboardStore.activeWorkspace === tab.key
              ? 'border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent)] shadow-[0_0_24px_rgba(91,255,147,0.12)]'
              : 'border-[var(--line)] bg-black/25 text-[var(--muted)] hover:border-[var(--accent)]/60 hover:bg-black/35 hover:text-[var(--accent)]'
          "
          @click="dashboardStore.activeWorkspace = tab.key"
        >
          <UIcon :name="tabIcons[tab.key]" class="size-5 sm:size-6" />
          <span
            v-if="tab.key === 'explore' && dashboardStore.totalNewResults > 0"
            class="absolute -top-1.5 -right-1.5 flex h-5 min-w-5 items-center justify-center rounded-full bg-[var(--accent)] px-1 text-[10px] font-bold text-black"
          >
            {{ dashboardStore.totalNewResults > 99 ? '99+' : dashboardStore.totalNewResults }}
          </span>
        </button>
      </UTooltip>
    </div>
  </section>
</template>
