import { getErrorMessage } from 'errors'
import type { PaginatedResponse, SearchResult } from 'types/search-agent'

export const useExploreWorkspaceStore = defineStore('exploreWorkspaceStore', () => {
  const api = useSearchAgentApi()
  const { t } = useI18n()
  const toast = useToast()
  const dashboardStore = useDashboardStore()

  const resultsPage = ref<PaginatedResponse<SearchResult> | null>(null)

  const resultFilters = reactive({
    q: '',
    topic: '',
    kind: '',
    isNewOnly: false,
    page: 1,
  })

  const results = computed(() => resultsPage.value?.results ?? [])

  const selectedTopic = computed(
    () => dashboardStore.topics.find((topic) => topic.slug === resultFilters.topic) ?? null,
  )

  const loadResults = async (page = 1) => {
    resultFilters.page = page

    const query: Record<string, string | number | boolean | undefined> = {
      page,
      q: resultFilters.q || undefined,
      topic: resultFilters.topic || undefined,
      kind: resultFilters.kind || undefined,
      is_new: resultFilters.isNewOnly ? true : undefined,
    }

    resultsPage.value = await api.get<PaginatedResponse<SearchResult>>('/api/v1/results/', query)
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

  const saveResult = async (
    id: number,
    title: string,
    folderId: number | null = null,
    newFolderName: string = '',
  ) => {
    try {
      const body: Record<string, unknown> = { title }
      if (newFolderName) body.folder_name = newFolderName
      else if (folderId) body.folder_id = folderId
      const updated = await api.post<SearchResult>(`/api/v1/results/${id}/save/`, body)
      if (resultsPage.value) {
        const idx = resultsPage.value.results.findIndex((r) => r.id === id)
        if (idx !== -1) resultsPage.value.results[idx] = updated
      }
      await useSavedWorkspaceStore().loadFolders()
      toast.add({ title: t('results.save_success'), color: 'success' })
    } catch (error: unknown) {
      toast.add({ title: getErrorMessage(error) || t('results.save_error'), color: 'error' })
    }
  }

  const unsaveResult = async (id: number) => {
    try {
      const updated = await api.post<SearchResult>(`/api/v1/results/${id}/unsave/`, {})
      if (resultsPage.value) {
        const idx = resultsPage.value.results.findIndex((r) => r.id === id)
        if (idx !== -1) resultsPage.value.results[idx] = updated
      }
    } catch (error: unknown) {
      toast.add({ title: getErrorMessage(error) || t('results.unsave_error'), color: 'error' })
    }
  }

  const resetResultsState = () => {
    resultsPage.value = null
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
    selectedTopic,
    loadResults,
    clearResultFilters,
    acknowledgeVisibleResults,
    saveResult,
    unsaveResult,
    resetResultsState,
  }
})
