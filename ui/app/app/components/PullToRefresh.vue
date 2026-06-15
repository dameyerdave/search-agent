<script setup lang="ts">
const PULL_THRESHOLD = 64
const MAX_PULL = 96

const dashboardStore = useDashboardStore()
const { t } = useI18n()
const { isStandalone } = useStandalone()

const pullDistance = ref(0)
const isRefreshing = ref(false)
const isDragging = ref(false)
let startY = 0
let tracking = false

const statusLabel = computed(() => {
  if (isRefreshing.value) return t('dashboard.shell.pull_to_refresh.refreshing')
  if (pullDistance.value >= PULL_THRESHOLD) return t('dashboard.shell.pull_to_refresh.release')
  return t('dashboard.shell.pull_to_refresh.pull')
})

const offset = computed(() => {
  const distance = isRefreshing.value ? PULL_THRESHOLD : pullDistance.value
  return Math.min(distance, PULL_THRESHOLD) - PULL_THRESHOLD
})

const onTouchStart = (event: TouchEvent) => {
  if (!isStandalone.value || isRefreshing.value || window.scrollY > 0) return
  const touch = event.touches[0]
  if (!touch) return
  startY = touch.clientY
  tracking = true
  isDragging.value = true
}

const onTouchMove = (event: TouchEvent) => {
  if (!tracking) return
  const touch = event.touches[0]
  if (!touch) return

  const delta = touch.clientY - startY
  if (delta <= 0 || window.scrollY > 0) {
    tracking = false
    isDragging.value = false
    pullDistance.value = 0
    return
  }

  pullDistance.value = Math.min(delta * 0.5, MAX_PULL)
  event.preventDefault()
}

const onTouchEnd = async () => {
  if (!tracking) return
  tracking = false
  isDragging.value = false

  if (pullDistance.value >= PULL_THRESHOLD) {
    isRefreshing.value = true
    pullDistance.value = 0
    await dashboardStore.refreshAll()
    isRefreshing.value = false
  } else {
    pullDistance.value = 0
  }
}

onMounted(() => {
  window.addEventListener('touchstart', onTouchStart, { passive: true })
  window.addEventListener('touchmove', onTouchMove, { passive: false })
  window.addEventListener('touchend', onTouchEnd)
})

onBeforeUnmount(() => {
  window.removeEventListener('touchstart', onTouchStart)
  window.removeEventListener('touchmove', onTouchMove)
  window.removeEventListener('touchend', onTouchEnd)
})
</script>

<template>
  <div
    v-if="isStandalone"
    class="pull-to-refresh"
    :class="{ 'pull-to-refresh-dragging': isDragging }"
    :style="{ transform: `translateY(${offset}px)` }"
  >
    <XunoLoadingMark small :label="statusLabel" />
    <p class="mono-heading text-xs tracking-[0.22em] text-[var(--muted)] uppercase">{{ statusLabel }}</p>
  </div>
</template>
