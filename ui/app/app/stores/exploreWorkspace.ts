import { getErrorMessage } from 'errors'
import type { PaginatedResponse, SearchResult } from 'types/search-agent'

const MAX_AUTO_LOAD_RESULTS = 200

export const useExploreWorkspaceStore = defineStore('exploreWorkspaceStore', () => {
  const api = useSearchAgentApi()
  const { t } = useI18n()
  const toast = useToast()
  const dashboardStore = useDashboardStore()

  const resultsPage = ref<PaginatedResponse<SearchResult> | null>(null)
  const accumulatedResults = ref<SearchResult[]>([])
  const isLoadingMore = ref(false)

  const resultFilters = reactive({
    q: '',
    topic: '',
    kind: '',
    isNewOnly: false,
    page: 1,
  })

  const results = computed(() => accumulatedResults.value)
  const canLoadMore = computed(() => Boolean(resultsPage.value?.next))
  const autoLoadCapReached = computed(() => accumulatedResults.value.length >= MAX_AUTO_LOAD_RESULTS)

  const selectedTopic = computed(
    () => dashboardStore.topics.find((topic) => topic.slug === resultFilters.topic) ?? null,
  )

  const loadResults = async (page = 1, options: { append?: boolean } = {}) => {
    resultFilters.page = page
    if (options.append) isLoadingMore.value = true

    const query: Record<string, string | number | boolean | undefined> = {
      page,
      q: resultFilters.q || undefined,
      topic: resultFilters.topic || undefined,
      kind: resultFilters.kind || undefined,
      is_new: resultFilters.isNewOnly ? true : undefined,
    }

    try {
      const response = await api.get<PaginatedResponse<SearchResult>>('/api/v1/results/', query)
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
    } finally {
      isLoadingMore.value = false
    }
  }

  const loadMoreResults = async () => {
    if (!canLoadMore.value || isLoadingMore.value) return
    await loadResults(resultFilters.page + 1, { append: true })
  }

  const clearResultFilters = async () => {
    const hadFilters = Boolean(resultFilters.q || resultFilters.topic || resultFilters.kind || resultFilters.isNewOnly)
    resultFilters.q = ''
    resultFilters.topic = ''
    resultFilters.kind = ''
    resultFilters.isNewOnly = false
    if (!hadFilters) {
      await loadResults(1)
    }
  }

  const acknowledgeVisibleResults = async () => {
    dashboardStore.setBusy('dashboard.busy.acknowledging_visible')
    try {
      await api.post('/api/v1/results/acknowledge/', {
        topic: resultFilters.topic || undefined,
      })
      toast.add({ title: t('dashboard.success.results_acknowledged'), color: 'success' })
    } catch (error: unknown) {
      toast.add({ title: getErrorMessage(error) || t('dashboard.errors.acknowledge_failed'), color: 'error' })
      return
    }
    await dashboardStore.refreshAll()
  }

  const saveResult = async (id: number, title: string, folderId: number | null = null, newFolderName: string = '') => {
    try {
      const body: Record<string, unknown> = { title }
      if (newFolderName) body.folder_name = newFolderName
      else if (folderId) body.folder_id = folderId
      const updated = await api.post<SearchResult>(`/api/v1/results/${id}/save/`, body)
      const idx = accumulatedResults.value.findIndex((r) => r.id === id)
      if (idx !== -1) accumulatedResults.value[idx] = updated
      await useSavedWorkspaceStore().loadFolders()
      toast.add({ title: t('results.save_success'), color: 'success' })
    } catch (error: unknown) {
      toast.add({ title: getErrorMessage(error) || t('results.save_error'), color: 'error' })
    }
  }

  const unsaveResult = async (id: number) => {
    try {
      const updated = await api.post<SearchResult>(`/api/v1/results/${id}/unsave/`, {})
      const idx = accumulatedResults.value.findIndex((r) => r.id === id)
      if (idx !== -1) accumulatedResults.value[idx] = updated
    } catch (error: unknown) {
      toast.add({ title: getErrorMessage(error) || t('results.unsave_error'), color: 'error' })
    }
  }

  const resetResultsState = () => {
    resultsPage.value = null
    accumulatedResults.value = []
  }

  const debouncedResultsReload = useDebounceFn(async () => {
    await loadResults(1)
  }, 250)

  watch(
    () => [resultFilters.q, resultFilters.topic, resultFilters.kind, resultFilters.isNewOnly],
    () => {
      debouncedResultsReload()
    },
  )

  return {
    resultFilters,
    resultsPage,
    results,
    canLoadMore,
    autoLoadCapReached,
    isLoadingMore,
    selectedTopic,
    loadResults,
    loadMoreResults,
    clearResultFilters,
    acknowledgeVisibleResults,
    saveResult,
    unsaveResult,
    resetResultsState,
  }
})
