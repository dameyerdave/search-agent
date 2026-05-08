import type { SocialAuthProvider, SocialAuthProvidersPayload } from 'types/search-agent'

type AuthUser = {
  pk: number
  username: string
  email: string
  first_name: string
  last_name: string
}

export const useAuthStore = defineStore('authStore', () => {
  const api = useSearchAgentApi()
  const user = ref<AuthUser | null>(null)
  const providers = ref<SocialAuthProvider[]>([])
  const isLoading = ref(false)
  const isLoadingProviders = ref(false)
  const error = ref<string | null>(null)

  const isAuthenticated = computed(() => user.value != null)

  const clearError = () => {
    error.value = null
  }

  const loadProviders = async () => {
    isLoadingProviders.value = true

    try {
      const response = await api.get<SocialAuthProvidersPayload>('/api/v1/auth/providers/')
      providers.value = response.providers
      return providers.value
    } catch {
      providers.value = []
      return []
    } finally {
      isLoadingProviders.value = false
    }
  }

  const loadUser = async () => {
    isLoading.value = true
    error.value = null

    try {
      user.value = await api.get<AuthUser>('/api/v1/auth/user/')
      return user.value
    } catch {
      user.value = null
      return null
    } finally {
      isLoading.value = false
    }
  }

  const initialize = async () => {
    await Promise.all([loadProviders(), loadUser()])
  }

  const startSocialLogin = (providerId: string) => {
    const provider = providers.value.find((entry) => entry.id === providerId)
    if (!provider) {
      error.value = 'This login provider is not configured.'
      return
    }

    const nextPath = `${window.location.pathname}${window.location.search}`
    const loginUrl = provider.login_url || provider.login_path
    const separator = loginUrl.includes('?') ? '&' : '?'
    window.location.href = `${loginUrl}${separator}process=login&next=${encodeURIComponent(nextPath || '/')}`
  }

  const login = async (username: string, password: string) => {
    isLoading.value = true
    error.value = null

    try {
      await api.post('/api/v1/auth/login/', {
        username,
        password,
      })
      await loadUser()
      return true
    } catch (err) {
      user.value = null
      error.value = err instanceof Error ? err.message : 'Login failed'
      return false
    } finally {
      isLoading.value = false
    }
  }

  const logout = async () => {
    isLoading.value = true
    error.value = null

    try {
      await api.post('/api/v1/auth/logout/', {})
    } finally {
      user.value = null
      isLoading.value = false
    }
  }

  return {
    user,
    providers,
    isAuthenticated,
    isLoading,
    isLoadingProviders,
    error,
    clearError,
    initialize,
    loadProviders,
    loadUser,
    startSocialLogin,
    login,
    logout,
  }
})
