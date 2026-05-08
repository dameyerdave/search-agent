export const useCoreStore = defineStore('coreStore', {
  state: () => ({
    colorMode: null as ReturnType<typeof useColorMode> | null,
  }),
  getters: {
    isDark(): boolean {
      return this.colorMode?.value === 'dark'
    },
  },
  actions: {
    initColorMode() {
      if (import.meta.client) {
        this.colorMode = useColorMode()
      }
    },
    toggleDarkMode(value: boolean) {
      if (this.colorMode) {
        this.colorMode.preference = value ? 'dark' : 'light'
      }
    },
    initFavicon() {
      if (import.meta.client) {
        useFavicon('/favicon/xuno-mark.svg', {
          rel: 'icon',
        })
      }
    },
  },
})
