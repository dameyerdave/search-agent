interface StandaloneNavigator extends Navigator {
  standalone?: boolean
}

export const useStandalone = () => {
  const isStandalone = ref(false)

  const refresh = () => {
    const navigatorWithStandalone = window.navigator as StandaloneNavigator
    isStandalone.value =
      window.matchMedia('(display-mode: standalone)').matches ||
      window.matchMedia('(display-mode: fullscreen)').matches ||
      navigatorWithStandalone.standalone === true
  }

  onMounted(() => {
    refresh()
    window.matchMedia('(display-mode: standalone)').addEventListener('change', refresh)
  })

  onBeforeUnmount(() => {
    window.matchMedia('(display-mode: standalone)').removeEventListener('change', refresh)
  })

  return { isStandalone, refresh }
}
