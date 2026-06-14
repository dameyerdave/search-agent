import { getErrorMessage } from 'errors'
import type { LiveSearxResponse, SearchTopic, SourceScope } from 'types/search-agent'
import {
  cleanSearchLabel,
  deriveLookbackDays,
  normalizeLanguageCodes,
  parseExtraParams,
  sortLiveSearchResults,
  splitTokens,
} from 'utils/dashboard'

const LIVE_SEARCH_PAGE_SIZE = 10

export const useSearchWorkspaceStore = defineStore('searchWorkspaceStore', () => {
  const api = useSearchAgentApi()
  const authStore = useAuthStore()
  const { t } = useI18n()
  const toast = useToast()
  const dashboardStore = useDashboardStore()

  const emptyLiveSearchForm = () => ({
    q: '',
    categories: [] as string[],
    useAllCategories: true,
    useAllEngines: true,
    engines: [] as string[],
    languages: [] as string[],
    safeSearch: '0',
    timeRange: '',
    resultOrder: 'relevance' as 'relevance' | 'newest',
    includeDomains: '',
    excludeDomains: '',
    extraParams: '',
  })

  const emptyLiveSearchSaveForm = () => ({
    name: '',
    description: '',
    scheduleEvery: 1,
    scheduleUnit: 'days' as 'minutes' | 'hours' | 'days' | 'weeks',
    enabled: true,
    sourceScopeIds: [] as number[],
    createScope: true,
    scopeName: '',
    scopeDescription: '',
    scopeKind: 'custom' as 'public' | 'research' | 'custom',
  })

  const liveSearchForm = reactive(emptyLiveSearchForm())
  const liveSearchSaveForm = reactive(emptyLiveSearchSaveForm())
  const liveSearchResponse = ref<LiveSearxResponse | null>(null)
  const liveSearchPage = ref(1)
  const liveSearchHasMore = ref(false)
  const showAdvancedSearch = ref(false)
  const showLiveSearchSaveDialog = ref(false)
  const isRunningLiveSearch = ref(false)
  const isSavingLiveSearchTopic = ref(false)

  const liveSearchResults = computed(() => liveSearchResponse.value?.results ?? [])
  const canSaveLiveSearch = computed(() => Boolean(liveSearchForm.q.trim()))
  const canSaveLiveSearchAsTopic = computed(() => authStore.isAuthenticated && canSaveLiveSearch.value)
  const liveSearchLoadedCount = computed(() => liveSearchResults.value.length)
  const canLoadMoreLiveSearch = computed(
    () =>
      liveSearchHasMore.value &&
      liveSearchResponse.value?.query === liveSearchForm.q.trim() &&
      liveSearchResponse.value?.result_order === liveSearchForm.resultOrder,
  )

  const fallbackLiveTopicName = () => cleanSearchLabel(liveSearchForm.q) || 'Tracked SearxNG search'
  const fallbackLiveScopeName = () => `${fallbackLiveTopicName()} scope`

  const ensureLiveSearchDraftDefaults = () => {
    if (!liveSearchSaveForm.name.trim()) {
      liveSearchSaveForm.name = fallbackLiveTopicName()
    }
    if (!liveSearchSaveForm.description.trim()) {
      liveSearchSaveForm.description = `Track fresh SearxNG results for ${cleanSearchLabel(liveSearchForm.q) || 'this live search'}.`
    }
    if (!liveSearchSaveForm.scopeName.trim()) {
      liveSearchSaveForm.scopeName = fallbackLiveScopeName()
    }
    if (!liveSearchSaveForm.scopeDescription.trim()) {
      liveSearchSaveForm.scopeDescription = `Dedicated scope captured from the Search workspace for ${cleanSearchLabel(liveSearchForm.q) || 'this live search'}.`
    }
  }

  const resetLiveSearchWorkspace = () => {
    Object.assign(liveSearchForm, emptyLiveSearchForm())
    Object.assign(liveSearchSaveForm, emptyLiveSearchSaveForm())
    liveSearchResponse.value = null
    liveSearchPage.value = 1
    liveSearchHasMore.value = false
    showAdvancedSearch.value = false
    showLiveSearchSaveDialog.value = false
  }

  const openLiveSearchSaveDialog = () => {
    if (!authStore.isAuthenticated) {
      toast.add({ title: t('dashboard.errors.sign_in_required_for_save'), color: 'error' })
      return
    }
    if (!liveSearchForm.q.trim()) {
      toast.add({ title: t('dashboard.errors.query_required_for_save'), color: 'error' })
      return
    }
    Object.assign(liveSearchSaveForm, emptyLiveSearchSaveForm())
    ensureLiveSearchDraftDefaults()
    showLiveSearchSaveDialog.value = true
  }

  const closeLiveSearchSaveDialog = () => {
    showLiveSearchSaveDialog.value = false
  }

  const toggleLiveSearchSource = (sourceId: number) => {
    if (liveSearchSaveForm.sourceScopeIds.includes(sourceId)) {
      liveSearchSaveForm.sourceScopeIds = liveSearchSaveForm.sourceScopeIds.filter((id) => id !== sourceId)
    } else {
      liveSearchSaveForm.sourceScopeIds = [...liveSearchSaveForm.sourceScopeIds, sourceId]
    }
  }

  const selectAllLiveSearchCategories = () => {
    liveSearchForm.categories = [...dashboardStore.availableCategories]
  }

  const clearLiveSearchCategories = () => {
    liveSearchForm.categories = []
  }

  const selectAllLiveSearchEngines = () => {
    liveSearchForm.engines = [...dashboardStore.availableEngines]
  }

  const clearLiveSearchEngines = () => {
    liveSearchForm.engines = []
  }

  const selectAllLiveSearchLanguages = () => {
    liveSearchForm.languages = dashboardStore.availableLanguages.map((language) => language.code)
  }

  const clearLiveSearchLanguages = () => {
    liveSearchForm.languages = []
  }

  const runLiveSearch = async (append = false) => {
    const query = liveSearchForm.q.trim()
    if (!query) {
      toast.add({ title: t('dashboard.errors.query_required'), color: 'error' })
      return
    }

    const shouldAppend = append && liveSearchResponse.value?.query === query
    const nextPage = shouldAppend ? liveSearchPage.value + 1 : 1
    isRunningLiveSearch.value = true
    dashboardStore.setBusy(
      shouldAppend ? 'dashboard.busy.loading_more_live_results' : 'dashboard.busy.running_live_search',
      { query },
    )

    try {
      const response = await api.post<LiveSearxResponse>('/api/v1/searxng/search/', {
        q: query,
        categories: liveSearchForm.useAllCategories ? [] : liveSearchForm.categories,
        use_all_categories: liveSearchForm.useAllCategories,
        use_all_engines: liveSearchForm.useAllEngines,
        engines: liveSearchForm.useAllEngines ? [] : liveSearchForm.engines,
        languages: normalizeLanguageCodes(liveSearchForm.languages, dashboardStore.availableLanguages),
        safesearch: Number(liveSearchForm.safeSearch),
        time_range: liveSearchForm.timeRange,
        result_order: liveSearchForm.resultOrder,
        pageno: nextPage,
        max_results: LIVE_SEARCH_PAGE_SIZE,
        include_domains: splitTokens(liveSearchForm.includeDomains),
        exclude_domains: splitTokens(liveSearchForm.excludeDomains),
        extra_params: parseExtraParams(liveSearchForm.extraParams),
      })

      const combinedResults = sortLiveSearchResults(
        [...(shouldAppend ? liveSearchResults.value : []), ...response.results],
        response.result_order,
      ).map((result, index) => ({
        ...result,
        position: index + 1,
      }))

      liveSearchResponse.value = {
        ...response,
        result_count: combinedResults.length,
        results: combinedResults,
      }
      liveSearchPage.value = nextPage
      liveSearchHasMore.value = response.results.length === LIVE_SEARCH_PAGE_SIZE

      ensureLiveSearchDraftDefaults()
      dashboardStore.setBusy(
        shouldAppend ? 'dashboard.busy.live_search_results_loaded' : 'dashboard.busy.live_search_completed',
        { count: liveSearchResponse.value.result_count },
      )
    } catch (error: unknown) {
      toast.add({ title: getErrorMessage(error) || t('dashboard.errors.live_search_failed'), color: 'error' })
    } finally {
      isRunningLiveSearch.value = false
    }
  }

  const loadMoreLiveSearchResults = async () => {
    await runLiveSearch(true)
  }

  const saveLiveSearchAsTopic = async () => {
    const query = liveSearchForm.q.trim()
    if (!query) {
      toast.add({ title: t('dashboard.errors.query_required_for_save'), color: 'error' })
      return
    }

    isSavingLiveSearchTopic.value = true
    dashboardStore.setBusy('dashboard.busy.saving_live_search_topic')
    let createdScopeId: number | null = null
    let topicCreated = false

    try {
      ensureLiveSearchDraftDefaults()

      let sourceScopeIds = [...liveSearchSaveForm.sourceScopeIds]
      if (liveSearchSaveForm.createScope) {
        const createdScope = await api.post<SourceScope>('/api/v1/source-scopes/', {
          name: liveSearchSaveForm.scopeName.trim() || fallbackLiveScopeName(),
          description: liveSearchSaveForm.scopeDescription.trim(),
          kind: liveSearchSaveForm.scopeKind,
          enabled: true,
          searxng_categories: liveSearchForm.useAllCategories ? [] : liveSearchForm.categories,
          use_all_categories: liveSearchForm.useAllCategories,
          use_all_engines: liveSearchForm.useAllEngines,
          searxng_engines: liveSearchForm.useAllEngines ? [] : liveSearchForm.engines,
          languages: normalizeLanguageCodes(liveSearchForm.languages, dashboardStore.availableLanguages),
          safe_search: Number(liveSearchForm.safeSearch),
          time_range: liveSearchForm.timeRange || 'any',
          result_order: liveSearchForm.resultOrder,
          max_results: Math.min(20, LIVE_SEARCH_PAGE_SIZE),
          include_domains: splitTokens(liveSearchForm.includeDomains),
          exclude_domains: splitTokens(liveSearchForm.excludeDomains),
          sort_order: 50,
        })
        createdScopeId = createdScope.id
        sourceScopeIds = Array.from(new Set([...sourceScopeIds, createdScope.id]))
      }

      if (!sourceScopeIds.length) {
        throw new Error(t('dashboard.errors.scope_required'))
      }

      const createdTopic = await api.post<SearchTopic>('/api/v1/topics/', {
        name: liveSearchSaveForm.name.trim() || fallbackLiveTopicName(),
        description: liveSearchSaveForm.description.trim(),
        enabled: liveSearchSaveForm.enabled,
        queries: [query],
        required_terms: [],
        excluded_terms: [],
        lookback_days: deriveLookbackDays(liveSearchForm.timeRange),
        schedule_every: Number(liveSearchSaveForm.scheduleEvery),
        schedule_unit: liveSearchSaveForm.scheduleUnit,
        max_results_per_query: Math.min(20, LIVE_SEARCH_PAGE_SIZE),
        notes: 'Saved from the Search workspace using the live SearxNG console.',
        source_scope_ids: sourceScopeIds,
      })
      topicCreated = true

      await dashboardStore.refreshAll()
      toast.add({
        title: t('dashboard.success.live_search_saved_as_topic', { name: createdTopic.name }),
        color: 'success',
      })
      showLiveSearchSaveDialog.value = false
    } catch (error: unknown) {
      if (typeof createdScopeId === 'number' && !topicCreated) {
        try {
          await api.delete(`/api/v1/source-scopes/${createdScopeId}/`)
        } catch {
          // Best effort cleanup for partially created dedicated scopes.
        }
      }
      toast.add({ title: getErrorMessage(error) || t('dashboard.errors.live_search_save_failed'), color: 'error' })
    } finally {
      isSavingLiveSearchTopic.value = false
    }
  }

  return {
    liveSearchForm,
    liveSearchSaveForm,
    liveSearchResponse,
    liveSearchPage,
    liveSearchHasMore,
    showAdvancedSearch,
    showLiveSearchSaveDialog,
    isRunningLiveSearch,
    isSavingLiveSearchTopic,
    liveSearchResults,
    canSaveLiveSearch,
    canSaveLiveSearchAsTopic,
    liveSearchLoadedCount,
    canLoadMoreLiveSearch,
    fallbackLiveTopicName,
    fallbackLiveScopeName,
    runLiveSearch,
    loadMoreLiveSearchResults,
    saveLiveSearchAsTopic,
    resetLiveSearchWorkspace,
    openLiveSearchSaveDialog,
    closeLiveSearchSaveDialog,
    toggleLiveSearchSource,
    ensureLiveSearchDraftDefaults,
    selectAllLiveSearchCategories,
    clearLiveSearchCategories,
    selectAllLiveSearchEngines,
    clearLiveSearchEngines,
    selectAllLiveSearchLanguages,
    clearLiveSearchLanguages,
  }
})
