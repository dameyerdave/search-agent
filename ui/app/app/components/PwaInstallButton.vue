<script setup lang="ts">
interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>
  userChoice: Promise<{
    outcome: 'accepted' | 'dismissed'
    platform: string
  }>
}

interface StandaloneNavigator extends Navigator {
  standalone?: boolean
}

const { t } = useI18n()

const deferredPrompt = shallowRef<BeforeInstallPromptEvent | null>(null)
const isInstalled = ref(false)
const isIos = ref(false)
const isSafari = ref(false)
const isPanelOpen = ref(false)
const hasSecureInstallContext = ref(true)
let standaloneMediaQuery: MediaQueryList | null = null

const canUseNativePrompt = computed(
  () => hasSecureInstallContext.value && Boolean(deferredPrompt.value) && !isInstalled.value,
)

const badgeColor = computed(() => {
  if (isInstalled.value) return 'green'
  if (!hasSecureInstallContext.value) return 'red'
  if (canUseNativePrompt.value) return 'primary'
  if (isIos.value) return 'amber'
  return 'neutral'
})

const badgeLabel = computed(() => {
  if (isInstalled.value) return t('pwa.badge.installed')
  if (!hasSecureInstallContext.value) return t('pwa.badge.secure')
  if (canUseNativePrompt.value) return t('pwa.badge.ready')
  if (isIos.value) return t('pwa.badge.phone')
  return t('pwa.badge.manual')
})

const buttonIcon = computed(() => {
  if (isInstalled.value) return 'i-heroicons-check-circle'
  if (!hasSecureInstallContext.value) return 'i-heroicons-lock-closed'
  if (canUseNativePrompt.value) return 'i-heroicons-arrow-down-tray'
  if (isIos.value) return 'i-heroicons-device-phone-mobile'
  return 'i-heroicons-arrow-down-tray'
})

const buttonLabel = computed(() => (isInstalled.value ? t('pwa.button.installed') : t('pwa.button.install')))

const panelTitle = computed(() => {
  if (isInstalled.value) return t('pwa.panel.installed_title')
  if (!hasSecureInstallContext.value) return t('pwa.panel.secure_title')
  if (canUseNativePrompt.value) return t('pwa.panel.ready_title')
  if (isIos.value && isSafari.value) return t('pwa.panel.ios_title')
  if (isIos.value) return t('pwa.panel.ios_browser_title')
  return t('pwa.panel.manual_title')
})

const panelDescription = computed(() => {
  if (isInstalled.value) return t('pwa.panel.installed_description')
  if (!hasSecureInstallContext.value) return t('pwa.panel.secure_description')
  if (canUseNativePrompt.value) return t('pwa.panel.ready_description')
  if (isIos.value && isSafari.value) return t('pwa.panel.ios_description')
  if (isIos.value) return t('pwa.panel.ios_browser_description')
  return t('pwa.panel.manual_description')
})

const instructionSteps = computed(() => {
  if (isInstalled.value) {
    return [t('pwa.steps.installed')]
  }

  if (!hasSecureInstallContext.value) {
    return [t('pwa.steps.secure_context')]
  }

  if (canUseNativePrompt.value) {
    return [t('pwa.steps.native_prompt')]
  }

  if (isIos.value && isSafari.value) {
    return [t('pwa.steps.ios_share'), t('pwa.steps.ios_add')]
  }

  if (isIos.value) {
    return [t('pwa.steps.ios_open_safari')]
  }

  return [t('pwa.steps.browser_menu'), t('pwa.steps.confirm_install')]
})

const syncInstalledState = () => {
  const navigatorWithStandalone = window.navigator as StandaloneNavigator
  isInstalled.value =
    window.matchMedia('(display-mode: standalone)').matches ||
    window.matchMedia('(display-mode: fullscreen)').matches ||
    navigatorWithStandalone.standalone === true
}

const syncPlatformState = () => {
  const userAgent = window.navigator.userAgent.toLowerCase()
  hasSecureInstallContext.value = window.isSecureContext
  isIos.value =
    /iphone|ipad|ipod/.test(userAgent) ||
    (window.navigator.platform === 'MacIntel' && window.navigator.maxTouchPoints > 1)
  isSafari.value = /safari/.test(userAgent) && !/chrome|crios|fxios|edgios|opr\//.test(userAgent)
}

const registerServiceWorker = async () => {
  if (!hasSecureInstallContext.value || !('serviceWorker' in window.navigator)) {
    return
  }

  try {
    await window.navigator.serviceWorker.register('/sw.js', { scope: '/' })
  } catch (error) {
    console.error('PWA service worker registration failed', error)
  }
}

const onBeforeInstallPrompt = (event: Event) => {
  const installEvent = event as BeforeInstallPromptEvent
  installEvent.preventDefault()
  deferredPrompt.value = installEvent
}

const onAppInstalled = () => {
  deferredPrompt.value = null
  isPanelOpen.value = false
  syncInstalledState()
}

const onDisplayModeChange = () => {
  syncInstalledState()
}

const toggleInstallSurface = async () => {
  if (canUseNativePrompt.value) {
    await promptInstall()
    return
  }

  isPanelOpen.value = !isPanelOpen.value
}

const promptInstall = async () => {
  const installEvent = deferredPrompt.value
  if (!installEvent) {
    isPanelOpen.value = true
    return
  }

  await installEvent.prompt()
  const choiceResult = await installEvent.userChoice
  deferredPrompt.value = null
  isPanelOpen.value = choiceResult.outcome !== 'accepted'
  syncInstalledState()
}

onMounted(() => {
  syncPlatformState()
  syncInstalledState()
  void registerServiceWorker()

  standaloneMediaQuery = window.matchMedia('(display-mode: standalone)')
  if ('addEventListener' in standaloneMediaQuery) {
    standaloneMediaQuery.addEventListener('change', onDisplayModeChange)
  } else {
    standaloneMediaQuery.addListener(onDisplayModeChange)
  }

  window.addEventListener('beforeinstallprompt', onBeforeInstallPrompt)
  window.addEventListener('appinstalled', onAppInstalled)
})

onBeforeUnmount(() => {
  if (standaloneMediaQuery) {
    if ('removeEventListener' in standaloneMediaQuery) {
      standaloneMediaQuery.removeEventListener('change', onDisplayModeChange)
    } else {
      standaloneMediaQuery.removeListener(onDisplayModeChange)
    }
  }

  window.removeEventListener('beforeinstallprompt', onBeforeInstallPrompt)
  window.removeEventListener('appinstalled', onAppInstalled)
})
</script>

<template>
  <div class="pwa-install-dock">
    <Transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="translate-y-3 opacity-0"
      enter-to-class="translate-y-0 opacity-100"
      leave-active-class="transition duration-150 ease-in"
      leave-from-class="translate-y-0 opacity-100"
      leave-to-class="translate-y-2 opacity-0"
    >
      <div
        v-if="isPanelOpen"
        class="terminal-panel pwa-install-panel relative mb-3 overflow-hidden rounded-[1.45rem] p-4"
      >
        <div class="relative z-10 space-y-4">
          <div class="flex items-start justify-between gap-3">
            <div class="space-y-2">
              <p class="mono-heading text-sm tracking-[0.24em] text-white uppercase">
                {{ panelTitle }}
              </p>
              <p class="text-sm leading-6 text-[var(--muted)]">
                {{ panelDescription }}
              </p>
            </div>
            <UBadge :color="badgeColor" variant="soft">
              {{ badgeLabel }}
            </UBadge>
          </div>

          <ol class="space-y-2">
            <li
              v-for="(step, index) in instructionSteps"
              :key="step"
              class="flex items-start gap-3 text-sm leading-6 text-[var(--text)]"
            >
              <span
                class="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-[var(--line)] bg-black/25 text-xs text-[var(--accent)]"
              >
                {{ index + 1 }}
              </span>
              <span>{{ step }}</span>
            </li>
          </ol>

          <div class="flex flex-wrap gap-2">
            <UButton v-if="canUseNativePrompt" size="sm" icon="i-heroicons-arrow-down-tray" @click="promptInstall">
              {{ t('pwa.panel.install_now') }}
            </UButton>
            <UButton size="sm" variant="ghost" @click="isPanelOpen = false">
              {{ t('pwa.panel.close') }}
            </UButton>
          </div>
        </div>
      </div>
    </Transition>

    <div class="flex items-center gap-2">
      <UBadge :color="badgeColor" variant="soft" class="hidden sm:inline-flex">
        {{ badgeLabel }}
      </UBadge>
      <UButton
        size="lg"
        :icon="buttonIcon"
        class="pwa-install-button w-full justify-center sm:w-auto"
        @click="toggleInstallSurface"
      >
        {{ buttonLabel }}
      </UButton>
    </div>
  </div>
</template>
