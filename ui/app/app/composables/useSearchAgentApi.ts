type RequestMethod = 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE'

const UNSAFE_METHODS = new Set<RequestMethod>(['POST', 'PATCH', 'PUT', 'DELETE'])

let csrfToken: string | null = null
let csrfPromise: Promise<string> | null = null

export const useSearchAgentApi = () => {
  const config = useRuntimeConfig()

  const fetchCsrfToken = async () => {
    if (!csrfPromise) {
      csrfPromise = $fetch<{ csrfToken: string }>('/api/v1/auth/csrf/', {
        baseURL: config.public.baseURL || undefined,
        credentials: 'include',
      })
        .then((response) => {
          csrfToken = response.csrfToken
          return response.csrfToken
        })
        .finally(() => {
          csrfPromise = null
        })
    }

    return csrfPromise
  }

  const request = async <T>(
    path: string,
    options: {
      method?: RequestMethod
      body?: Record<string, unknown>
      query?: Record<string, string | number | boolean | undefined>
    } = {},
  ) => {
    const method = options.method ?? 'GET'
    const headers: Record<string, string> = {}

    if (UNSAFE_METHODS.has(method)) {
      if (!csrfToken) {
        await fetchCsrfToken()
      }
      if (csrfToken) {
        headers['X-CSRFToken'] = csrfToken
      }
    }

    return await $fetch<T>(path, {
      method,
      body: options.body,
      query: options.query,
      headers,
      credentials: 'include',
      baseURL: config.public.baseURL || undefined,
    })
  }

  return {
    request,
    get: <T>(path: string, query?: Record<string, string | number | boolean | undefined>) =>
      request<T>(path, { method: 'GET', query }),
    post: <T>(path: string, body?: Record<string, unknown>) => request<T>(path, { method: 'POST', body }),
    patch: <T>(path: string, body?: Record<string, unknown>) => request<T>(path, { method: 'PATCH', body }),
    put: <T>(path: string, body?: Record<string, unknown>) => request<T>(path, { method: 'PUT', body }),
    delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
  }
}
