<script setup lang="ts">
const dashboardStore = useDashboardStore()
const { t } = useI18n()

const hasProviderIssue = computed(
  () => !dashboardStore.provider?.searxng_base_url || !dashboardStore.provider?.crawl4ai_enabled,
)
</script>

<template>
  <section class="terminal-panel relative overflow-hidden rounded-[1.5rem] p-5">
    <div class="relative z-10 space-y-4">
      <p class="mono-heading text-lg tracking-[0.22em] text-white uppercase">
        {{ t('dashboard.configure.provider.title') }}
      </p>

      <div class="grid gap-3">
        <label class="space-y-2">
          <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
            {{ t('dashboard.configure.provider.enabled_label') }}
          </span>
          <select v-model="dashboardStore.providerForm.enabled" class="terminal-select">
            <option :value="true">{{ t('dashboard.configure.provider.enabled') }}</option>
            <option :value="false">{{ t('dashboard.configure.provider.disabled') }}</option>
          </select>
        </label>
      </div>

      <div
        v-if="hasProviderIssue"
        class="rounded-2xl border border-[var(--line)] bg-black/20 p-4 text-sm text-[var(--muted)]"
      >
        <p>
          {{ t('dashboard.configure.provider.provider_label') }}
          <span class="text-[var(--text)]">{{
            dashboardStore.provider?.name ?? t('dashboard.configure.provider.default_name')
          }}</span>
        </p>
        <p class="mt-2">
          {{ t('dashboard.configure.provider.base_url_label') }}
          <span class="text-[var(--text)]">{{
            dashboardStore.provider?.searxng_base_url || t('results.not_available')
          }}</span>
        </p>
        <p class="mt-2">
          {{ t('dashboard.configure.provider.crawl4ai_label') }}
          <span :class="dashboardStore.provider?.crawl4ai_enabled ? 'text-[var(--accent)]' : 'text-[var(--danger)]'">
            {{
              dashboardStore.provider?.crawl4ai_enabled
                ? t('dashboard.configure.provider.crawl4ai_enabled')
                : t('dashboard.configure.provider.crawl4ai_disabled')
            }}
          </span>
        </p>
      </div>

      <button
        class="terminal-button terminal-button-primary w-full"
        :disabled="dashboardStore.isSavingProvider"
        @click="dashboardStore.saveProvider"
      >
        {{
          dashboardStore.isSavingProvider
            ? t('dashboard.configure.provider.saving')
            : t('dashboard.configure.provider.save_button')
        }}
      </button>
    </div>
  </section>
</template>
