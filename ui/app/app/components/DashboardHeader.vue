<script setup lang="ts">
const authStore = useAuthStore()
const dashboardStore = useDashboardStore()
const { t } = useI18n()
</script>

<template>
  <section class="terminal-panel relative overflow-hidden rounded-[1.8rem] p-6 sm:p-8">
    <div class="relative z-10 flex flex-col gap-8 lg:flex-row lg:items-end lg:justify-between">
      <div class="max-w-3xl space-y-3">
        <XunoBrandMark class="max-w-[30rem]" />
        <div class="pill w-fit bg-[var(--accent-soft)] text-[var(--accent)]">
          <span class="h-2 w-2 rounded-full bg-[var(--accent)] shadow-[0_0_14px_var(--accent)]" />
          {{ t('dashboard.shell.header.tagline') }}
        </div>
      </div>

      <div class="min-w-0 rounded-2xl border border-[var(--line)] bg-black/30 p-4 lg:w-[320px]">
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
    </div>
  </section>
</template>
