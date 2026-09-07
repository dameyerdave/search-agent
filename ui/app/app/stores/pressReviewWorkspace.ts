import { getErrorMessage } from 'errors'
import type { PaginatedResponse, SearchResult } from 'types/search-agent'

const MAX_AUTO_LOAD_RESULTS = 200

export const usePressReviewWorkspaceStore = defineStore('pressReviewWorkspaceStore', () => {
  const api = useSearchAgentApi()
  const { t } = useI18n()
  const toast = useToast()

  const resultsPage = ref<PaginatedResponse<SearchResult> | null>(null)
  const accumulatedResults = ref<SearchResult[]>([])
  const currentPage = ref(1)
  const isLoading = ref(false)
  const isLoadingMore = ref(false)

  const results = computed(() => accumulatedResults.value)
  const canLoadMore = computed(() => Boolean(resultsPage.value?.next))
  const autoLoadCapReached = computed(() => accumulatedResults.value.length >= MAX_AUTO_LOAD_RESULTS)
  const newCount = computed(() => accumulatedResults.value.filter((result) => result.is_new).length)

  const loadResults = async (page = 1, options: { append?: boolean } = {}) => {
    currentPage.value = page
    if (options.append) isLoadingMore.value = true
    else isLoading.value = true

    try {
      const response = await api.get<PaginatedResponse<SearchResult>>('/api/v1/results/press_review/', { page })
      resultsPage.value = response
      if (options.append) {
        const existingIds = new Set(accumulatedResults.value.map((r) => r.id))
        accumulatedResults.value = [
          ...accumulatedResults.value,
          ...response.results.filter((r) => !existingIds.has(r.id)),
        ]
      } else {
        accumulatedResults.value = response.results
      }
    } catch (error: unknown) {
      toast.add({ title: getErrorMessage(error) || t('press_review.errors.load_failed'), color: 'error' })
    } finally {
      isLoading.value = false
      isLoadingMore.value = false
    }
  }

  const loadMoreResults = async () => {
    if (!canLoadMore.value || isLoadingMore.value) return
    await loadResults(currentPage.value + 1, { append: true })
  }

  const saveResult = async (result: SearchResult) => {
    try {
      const updated = await api.post<SearchResult>(`/api/v1/results/${result.id}/save/`, { title: result.title })
      const idx = accumulatedResults.value.findIndex((r) => r.id === result.id)
      if (idx !== -1) accumulatedResults.value[idx] = updated
      toast.add({ title: t('results.save_success'), color: 'success' })
    } catch (error: unknown) {
      toast.add({ title: getErrorMessage(error) || t('results.save_error'), color: 'error' })
    }
  }

  const unsaveResult = async (result: SearchResult) => {
    try {
      const updated = await api.post<SearchResult>(`/api/v1/results/${result.id}/unsave/`, {})
      const idx = accumulatedResults.value.findIndex((r) => r.id === result.id)
      if (idx !== -1) accumulatedResults.value[idx] = updated
    } catch (error: unknown) {
      toast.add({ title: getErrorMessage(error) || t('results.unsave_error'), color: 'error' })
    }
  }

  const acknowledgeAll = async () => {
    try {
      await api.post('/api/v1/results/acknowledge/', { press_review: true })
      accumulatedResults.value = accumulatedResults.value.map((result) => ({ ...result, is_new: false }))
    } catch (error: unknown) {
      toast.add({ title: getErrorMessage(error) || t('press_review.errors.acknowledge_failed'), color: 'error' })
    }
  }

  const resetState = () => {
    resultsPage.value = null
    accumulatedResults.value = []
    currentPage.value = 1
  }

  return {
    resultsPage,
    results,
    canLoadMore,
    autoLoadCapReached,
    newCount,
    isLoading,
    isLoadingMore,
    loadResults,
    loadMoreResults,
    saveResult,
    unsaveResult,
    acknowledgeAll,
    resetState,
  }
})
