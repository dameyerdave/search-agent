<script setup lang="ts">
const authStore = useAuthStore()
const dashboardStore = useDashboardStore()
const { t } = useI18n()
</script>

<template>
  <section class="terminal-panel relative overflow-hidden rounded-[1.2rem] p-3 sm:rounded-[1.8rem] sm:p-8">
    <div class="relative z-10 flex items-start justify-between gap-4">
      <div class="max-w-3xl space-y-2 sm:space-y-3">
        <XunoBrandMark class="max-w-36 sm:max-w-120" />
        <div v-if="dashboardStore.hasProviderIssue" class="pill w-fit bg-[rgba(255,125,125,0.12)] text-[var(--danger)]">
          <span class="h-2 w-2 rounded-full bg-[var(--danger)] shadow-[0_0_14px_var(--danger)]" />
          {{ t('dashboard.shell.header.provider_warning') }}
        </div>
      </div>

      <UPopover
        :content="{ side: 'bottom', align: 'end', sideOffset: 8 }"
        :ui="{ content: 'bg-transparent ring-0 shadow-none rounded-2xl' }"
      >
        <UButton
          square
          variant="ghost"
          color="neutral"
          icon="i-heroicons-bars-3"
          :aria-label="t('dashboard.shell.header.operator_label')"
        />

        <template #content>
          <div class="terminal-panel relative min-w-64 overflow-hidden rounded-2xl p-4">
            <p class="text-xs tracking-[0.25em] text-[var(--muted)] uppercase">
              {{ t('dashboard.shell.header.operator_label') }}
            </p>
            <template v-if="dashboardStore.isBootstrappingAuth">
              <p class="mt-2 text-sm text-[var(--muted)]">{{ t('dashboard.shell.header.checking_identity') }}</p>
            </template>
            <template v-else-if="authStore.isAuthenticated">
              <p class="mt-2 truncate text-sm text-white">{{ dashboardStore.currentUserLabel }}</p>
              <p class="mt-1 truncate text-xs text-[var(--muted)]">{{ dashboardStore.busyLabel }}</p>
              <div class="mt-3">
                <button class="terminal-button terminal-button-secondary text-xs" @click="dashboardStore.handleLogout">
                  {{ t('dashboard.shell.header.sign_out') }}
                </button>
              </div>
            </template>
            <template v-else>
              <p class="mt-2 text-sm text-white">{{ t('dashboard.shell.header.not_signed_in') }}</p>
              <p v-if="authStore.error" class="mt-1 text-xs break-words text-[#ffd8d8]">{{ authStore.error }}</p>
              <div class="mt-3">
                <button class="terminal-button terminal-button-primary" @click="authStore.signIn()">
                  {{ t('dashboard.shell.header.sign_in') }}
                </button>
              </div>
            </template>
          </div>
        </template>
      </UPopover>
    </div>
  </section>
</template>
