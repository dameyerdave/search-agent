<script setup lang="ts">
const dashboardStore = useDashboardStore()
const { t } = useI18n()

const tabIcons: Record<string, string> = {
  search: 'i-heroicons-magnifying-glass',
  explore: 'i-heroicons-globe-alt',
  press: 'i-heroicons-newspaper',
  saved: 'i-heroicons-bookmark',
  configure: 'i-heroicons-cog-6-tooth',
  runs: 'i-heroicons-clock',
}

const tabBadgeCount = (key: string) => {
  if (key === 'explore') return dashboardStore.totalNewResults
  if (key === 'press') return dashboardStore.totalNewPressResults
  return 0
}
</script>

<template>
  <nav class="workspace-tab-bar" role="tablist">
    <button
      v-for="tab in dashboardStore.visibleWorkspaceTabs"
      :key="tab.key"
      role="tab"
      :aria-selected="dashboardStore.activeWorkspace === tab.key"
      class="workspace-tab-bar__item"
      :class="{ 'workspace-tab-bar__item--active': dashboardStore.activeWorkspace === tab.key }"
      @click="dashboardStore.activeWorkspace = tab.key"
    >
      <span class="relative">
        <UIcon :name="tabIcons[tab.key]" class="size-5" />
        <span v-if="tabBadgeCount(tab.key) > 0" class="workspace-tab-bar__badge">
          {{ tabBadgeCount(tab.key) > 99 ? '99+' : tabBadgeCount(tab.key) }}
        </span>
      </span>
      <span class="workspace-tab-bar__label">{{ t(tab.labelKey) }}</span>
    </button>
  </nav>
</template>
