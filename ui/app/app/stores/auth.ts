import { getErrorMessage } from 'errors'
import type { AuthenticatedUser, AuthenticatedUserResponse } from 'types/search-agent'

export const useAuthStore = defineStore('authStore', () => {
  const api = useSearchAgentApi()
  const user = ref<AuthenticatedUser | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const cloudflareLoginUrl = ref<string | null>(null)
  const cloudflareLogoutUrl = ref<string | null>(null)

  const isAuthenticated = computed(() => user.value != null)

  const _applyResponse = (response: AuthenticatedUserResponse) => {
    user.value = response.authenticated ? response.user : null
    cloudflareLoginUrl.value = response.cloudflare_access?.login_url ?? null
    cloudflareLogoutUrl.value = response.cloudflare_access?.logout_url ?? null
  }

  const loadUser = async () => {
    isLoading.value = true
    error.value = null
    try {
      const response = await api.get<AuthenticatedUserResponse>('/api/v1/auth/user/')
      _applyResponse(response)
      return user.value
    } catch (err) {
      user.value = null
      error.value = getErrorMessage(err) || 'Authentication service unavailable.'
      return null
    } finally {
      isLoading.value = false
    }
  }

  const signIn = () => {
    if (cloudflareLoginUrl.value) {
      window.location.href = cloudflareLoginUrl.value
    } else {
      window.location.reload()
    }
  }

  const logout = async () => {
    const cfLogoutUrl = cloudflareLogoutUrl.value
    isLoading.value = true
    error.value = null
    try {
      await api.post<AuthenticatedUserResponse>('/api/v1/auth/logout/', {})
    } catch {
      // ignore — clear local state regardless
    } finally {
      user.value = null
      isLoading.value = false
    }
    if (cfLogoutUrl) {
      window.location.href = cfLogoutUrl
    }
  }

  const initialize = async () => await loadUser()

  return {
    user,
    isAuthenticated,
    isLoading,
    error,
    cloudflareLoginUrl,
    cloudflareLogoutUrl,
    initialize,
    loadUser,
    signIn,
    logout,
  }
})
