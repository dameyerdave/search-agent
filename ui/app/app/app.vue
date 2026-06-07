<script setup lang="ts">
import type {
  DashboardPayload,
  LiveSearxResponse,
  PaginatedResponse,
  ProviderConfig,
  SearchResult,
  SearchRun,
  SearchTopic,
  SourceScope,
} from 'types/search-agent'

const api = useSearchAgentApi()
const authStore = useAuthStore()
const LIVE_SEARCH_PAGE_SIZE = 10

const dashboard = ref<DashboardPayload | null>(null)
const resultsPage = ref<PaginatedResponse<SearchResult> | null>(null)
const runsPage = ref<PaginatedResponse<SearchRun> | null>(null)
const busyLabel = ref('Booting signal deck...')
const errorMessage = ref('')
const isBootstrappingAuth = ref(true)

const isLoadingDashboard = ref(false)
const isSavingTopic = ref(false)
const isSavingSource = ref(false)
const isSavingProvider = ref(false)
const isRunningLiveSearch = ref(false)
const isSavingLiveSearchTopic = ref(false)
const activeTopicRun = ref<string | null>(null)
const activeTopicAcknowledge = ref<string | null>(null)
const activeWorkspace = ref<'search' | 'explore' | 'configure' | 'runs'>('search')
const showAdvancedSearch = ref(false)
const showLiveSearchSaveDialog = ref(false)
const liveSearchPage = ref(1)
const liveSearchHasMore = ref(false)

const topicEditorMode = ref<'create' | 'edit'>('create')
const sourceEditorMode = ref<'create' | 'edit'>('create')
const editingTopicSlug = ref<string | null>(null)
const editingSourceId = ref<number | null>(null)
const liveSearchResponse = ref<LiveSearxResponse | null>(null)

const resultFilters = reactive({
  q: '',
  topic: '',
  kind: '',
  isNewOnly: false,
  page: 1,
})

const runFilters = reactive({
  topic: '',
  status: '',
})

const providerForm = reactive({
  id: 0,
  enabled: true,
})

const emptyLiveSearchForm = () => ({
  q: '',
  categories: [] as string[],
  useAllCategories: true,
  useAllEngines: true,
  engines: [] as string[],
  language: '',
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

const emptyTopicForm = () => ({
  name: '',
  description: '',
  queries: '"data platform"\n"research data exchange"\n"research data exchange format"',
  requiredTerms: '',
  excludedTerms: '',
  lookbackDays: 30,
  scheduleEvery: 1,
  scheduleUnit: 'days' as 'minutes' | 'hours' | 'days' | 'weeks',
  maxResultsPerQuery: 10,
  notes: '',
  enabled: true,
  sourceScopeIds: [] as number[],
})

const emptySourceForm = () => ({
  name: '',
  description: '',
  kind: 'public',
  enabled: true,
  searxngCategories: [] as string[],
  useAllCategories: true,
  useAllEngines: true,
  searxngEngines: [] as string[],
  language: '',
  safeSearch: '0',
  timeRange: 'auto',
  resultOrder: 'relevance' as 'relevance' | 'newest',
  maxResults: 10,
  includeDomains: '',
  excludeDomains: '',
  sortOrder: 10,
})

const liveSearchForm = reactive(emptyLiveSearchForm())
const liveSearchSaveForm = reactive(emptyLiveSearchSaveForm())
const topicForm = reactive(emptyTopicForm())
const sourceForm = reactive(emptySourceForm())

const topics = computed(() => dashboard.value?.topics ?? [])
const sources = computed(() => dashboard.value?.sources ?? [])
const enabledSources = computed(() => sources.value.filter((source) => source.enabled))
const provider = computed(() => dashboard.value?.provider ?? null)
const availableCategories = computed(() => provider.value?.available_categories ?? [])
const availableEngines = computed(() => provider.value?.available_engines ?? [])
const availableLanguages = computed(() => provider.value?.available_languages ?? [])
const stats = computed(() => dashboard.value?.stats ?? null)
const results = computed(() => resultsPage.value?.results ?? [])
const runs = computed(() => runsPage.value?.results ?? [])
const liveSearchResults = computed(() => liveSearchResponse.value?.results ?? [])
const workspaceTabs = [
  {
    key: 'search',
    label: 'Search',
    eyebrow: 'live searxng',
  },
  {
    key: 'explore',
    label: 'Explore',
    eyebrow: 'results terminal',
  },
  {
    key: 'configure',
    label: 'Configure',
    eyebrow: 'topics + sources',
  },
  {
    key: 'runs',
    label: 'Runs',
    eyebrow: 'telemetry + history',
  },
] as const
const canSaveLiveSearch = computed(() => Boolean(liveSearchForm.q.trim()))
const canSaveLiveSearchAsTopic = computed(() => authStore.isAuthenticated && canSaveLiveSearch.value)
const liveSearchLoadedCount = computed(() => liveSearchResults.value.length)
const canLoadMoreLiveSearch = computed(
  () =>
    liveSearchHasMore.value
    && liveSearchResponse.value?.query === liveSearchForm.q.trim()
    && liveSearchResponse.value?.result_order === liveSearchForm.resultOrder,
)
const visibleWorkspaceTabs = computed(() =>
  authStore.isAuthenticated
    ? workspaceTabs
    : workspaceTabs.filter((tab) => tab.key === 'search'),
)
const currentUserLabel = computed(() => {
  const firstName = authStore.user?.first_name?.trim()
  const lastName = authStore.user?.last_name?.trim()
  const fullName = [firstName, lastName].filter(Boolean).join(' ').trim()
  return fullName || authStore.user?.username || authStore.user?.email || 'operator'
})

const selectedTopic = computed(() => topics.value.find((topic) => topic.slug === resultFilters.topic) ?? null)
const selectedRunTopic = computed(() => topics.value.find((topic) => topic.slug === runFilters.topic) ?? null)
const latestRun = computed(() => runs.value[0] ?? null)
const runSuccessRate = computed(() => {
  const totalRuns = stats.value?.run_count ?? 0
  if (!totalRuns) return 0
  return Math.round(((stats.value?.successful_run_count ?? 0) / totalRuns) * 100)
})

const dateFormatter = new Intl.DateTimeFormat('en-CH', {
  dateStyle: 'medium',
  timeStyle: 'short',
})

const splitLines = (value: string) =>
  value
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)

const splitTokens = (value: string) =>
  value
    .split(/[\n,]/)
    .map((entry) => entry.trim())
    .filter(Boolean)

const joinLines = (value: string[]) => value.join('\n')

const normalizeLanguageCode = (value: string) => {
  const trimmed = value.trim()
  if (!trimmed) {
    return ''
  }

  const options = availableLanguages.value
  const exact = options.find((option) => option.code === trimmed)
  if (exact) {
    return exact.code
  }

  const dashed = trimmed.replace(/_/g, '-')
  const normalized = options.find((option) => option.code.toLowerCase() === dashed.toLowerCase())
  if (normalized) {
    return normalized.code
  }

  const baseLanguage = dashed.split('-', 1)[0] ?? dashed
  const baseMatch = options.find((option) => option.code.toLowerCase() === baseLanguage.toLowerCase())
  if (baseMatch) {
    return baseMatch.code
  }

  return trimmed
}

const setBusy = (message: string) => {
  busyLabel.value = message
  errorMessage.value = ''
}

const formatDate = (value: string | null) => {
  if (!value) {
    return 'Never'
  }

  try {
    return dateFormatter.format(new Date(value))
  } catch {
    return value
  }
}

const summarizeStatus = (status: string) => {
  if (status === 'succeeded') return 'Stable'
  if (status === 'limited') return 'Limited'
  if (status === 'failed') return 'Fault'
  if (status === 'running') return 'Running'
  return 'Idle'
}

const statusClass = (status: string) => {
  if (status === 'succeeded') return 'text-[#c8ffd9]'
  if (status === 'limited') return 'text-[var(--warn)]'
  if (status === 'failed') return 'text-[var(--danger)]'
  if (status === 'running') return 'text-[var(--accent)]'
  return 'text-[var(--muted)]'
}

const describeCategories = (source: SourceScope) =>
  source.use_all_categories
    ? 'all categories'
    : source.searxng_categories.length
      ? source.searxng_categories.join(', ')
      : 'restricted category set'

const describeEngines = (source: SourceScope) =>
  source.use_all_engines
    ? 'all available engines'
    : source.searxng_engines.length
      ? source.searxng_engines.join(', ')
      : 'restricted engine set'

const describeResultOrder = (source: SourceScope) =>
  source.result_order === 'newest' ? 'time: newest first' : 'relevance'

const formatNextRun = (topic: SearchTopic) => {
  if (!topic.enabled) {
    return 'Paused'
  }
  return formatDate(topic.next_run_at)
}

const cleanSearchLabel = (value: string) =>
  value
    .replace(/["']/g, '')
    .replace(/\s+/g, ' ')
    .trim()

const fallbackLiveTopicName = () => cleanSearchLabel(liveSearchForm.q) || 'Tracked SearxNG search'

const fallbackLiveScopeName = () => `${fallbackLiveTopicName()} scope`

const deriveLookbackDays = (timeRange: string) => {
  if (timeRange === 'day') return 1
  if (timeRange === 'month') return 30
  if (timeRange === 'year') return 365
  return 30
}

const parseExtraParams = (value: string) => {
  const params: Record<string, string> = {}

  for (const line of value.split('\n')) {
    const trimmed = line.trim()
    if (!trimmed) continue

    const separatorIndex = trimmed.indexOf('=')
    if (separatorIndex === -1) {
      params[trimmed] = '1'
      continue
    }

    const key = trimmed.slice(0, separatorIndex).trim()
    const rawValue = trimmed.slice(separatorIndex + 1).trim()
    if (!key) continue
    params[key] = rawValue || '1'
  }

  return params
}

const sortLiveSearchResults = (results: LiveSearxResponse['results'], resultOrder: 'relevance' | 'newest') => {
  const resolveTimestamp = (value: string | null) => {
    if (!value) {
      return Number.NEGATIVE_INFINITY
    }
    const parsed = new Date(value).getTime()
    return Number.isFinite(parsed) ? parsed : Number.NEGATIVE_INFINITY
  }

  const resolveScore = (value: number | null) => (typeof value === 'number' ? value : Number.NEGATIVE_INFINITY)

  if (resultOrder === 'newest') {
    return [...results].sort((left, right) => {
      const leftDate = resolveTimestamp(left.published_at)
      const rightDate = resolveTimestamp(right.published_at)
      if (leftDate !== rightDate) {
        return rightDate - leftDate
      }

      const leftScore = resolveScore(left.score)
      const rightScore = resolveScore(right.score)
      return rightScore - leftScore
    })
  }

  return [...results].sort((left, right) => {
    const leftScore = resolveScore(left.score)
    const rightScore = resolveScore(right.score)
    return rightScore - leftScore
  })
}

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

const hydrateProviderForm = (config: ProviderConfig | null) => {
  providerForm.id = config?.id ?? 0
  providerForm.enabled = config?.enabled ?? true
}

const resetDashboardState = () => {
  dashboard.value = null
  resultsPage.value = null
  runsPage.value = null
  busyLabel.value = 'Awaiting Cloudflare Access identity...'
  errorMessage.value = ''
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
    errorMessage.value = 'Sign in through Cloudflare Access to save this search as a topic.'
    return
  }
  if (!liveSearchForm.q.trim()) {
    errorMessage.value = 'Enter a search query before saving it as a topic.'
    return
  }
  Object.assign(liveSearchSaveForm, emptyLiveSearchSaveForm())
  ensureLiveSearchDraftDefaults()
  showLiveSearchSaveDialog.value = true
}

const closeLiveSearchSaveDialog = () => {
  showLiveSearchSaveDialog.value = false
}

const resetTopicForm = () => {
  topicEditorMode.value = 'create'
  editingTopicSlug.value = null
  Object.assign(topicForm, emptyTopicForm())
}

const resetSourceForm = () => {
  sourceEditorMode.value = 'create'
  editingSourceId.value = null
  Object.assign(sourceForm, emptySourceForm())
}

const toggleLiveSearchSource = (sourceId: number) => {
  if (liveSearchSaveForm.sourceScopeIds.includes(sourceId)) {
    liveSearchSaveForm.sourceScopeIds = liveSearchSaveForm.sourceScopeIds.filter((id) => id !== sourceId)
  } else {
    liveSearchSaveForm.sourceScopeIds = [...liveSearchSaveForm.sourceScopeIds, sourceId]
  }
}

const openTopicEditor = (topic?: SearchTopic) => {
  if (!topic) {
    resetTopicForm()
    return
  }

  topicEditorMode.value = 'edit'
  editingTopicSlug.value = topic.slug
  Object.assign(topicForm, {
    name: topic.name,
    description: topic.description,
    queries: joinLines(topic.queries),
    requiredTerms: joinLines(topic.required_terms),
    excludedTerms: joinLines(topic.excluded_terms),
    lookbackDays: topic.lookback_days,
    scheduleEvery: topic.schedule_every,
    scheduleUnit: topic.schedule_unit,
    maxResultsPerQuery: topic.max_results_per_query,
    notes: topic.notes,
    enabled: topic.enabled,
    sourceScopeIds: topic.source_scopes.map((scope) => scope.id),
  })
}

const openSourceEditor = (source?: SourceScope) => {
  if (!source) {
    resetSourceForm()
    return
  }

  sourceEditorMode.value = 'edit'
  editingSourceId.value = source.id
  Object.assign(sourceForm, {
    name: source.name,
    description: source.description,
    kind: source.kind,
    enabled: source.enabled,
    searxngCategories: [...source.searxng_categories],
    useAllCategories: source.use_all_categories,
    useAllEngines: source.use_all_engines,
    searxngEngines: [...source.searxng_engines],
    language: normalizeLanguageCode(source.language),
    safeSearch: String(source.safe_search),
    timeRange: source.time_range,
    resultOrder: source.result_order,
    maxResults: source.max_results,
    includeDomains: joinLines(source.include_domains),
    excludeDomains: joinLines(source.exclude_domains),
    sortOrder: source.sort_order,
  })
}

const runLiveSearch = async (appendOrEvent: boolean | Event = false) => {
  const append = typeof appendOrEvent === 'boolean' ? appendOrEvent : false
  const query = liveSearchForm.q.trim()
  if (!query) {
    errorMessage.value = 'Enter a search query before launching SearxNG.'
    return
  }

  const shouldAppend = append && liveSearchResponse.value?.query === query
  const nextPage = shouldAppend ? liveSearchPage.value + 1 : 1
  isRunningLiveSearch.value = true
  setBusy(shouldAppend ? `Loading more live results for ${query}...` : `Running live SearxNG search for ${query}...`)

  try {
    const response = await api.post<LiveSearxResponse>('/api/v1/searxng/search/', {
      q: query,
      categories: liveSearchForm.useAllCategories ? [] : liveSearchForm.categories,
      use_all_categories: liveSearchForm.useAllCategories,
      use_all_engines: liveSearchForm.useAllEngines,
      engines: liveSearchForm.useAllEngines ? [] : liveSearchForm.engines,
      language: normalizeLanguageCode(liveSearchForm.language),
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
    busyLabel.value = shouldAppend
      ? `Loaded ${liveSearchResponse.value.result_count} live results`
      : `Live search returned ${liveSearchResponse.value.result_count} results`
  } catch (error: unknown) {
    errorMessage.value = error instanceof Error ? error.message : 'Live SearxNG search failed.'
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
    errorMessage.value = 'Enter a search query before saving it as a topic.'
    return
  }

  isSavingLiveSearchTopic.value = true
  setBusy('Saving the current SearxNG search as a tracked topic...')
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
        language: normalizeLanguageCode(liveSearchForm.language),
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
      throw new Error('Select at least one existing source scope or create a dedicated scope for this live search.')
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
      notes: `Saved from the Search workspace using the live SearxNG console.`,
      source_scope_ids: sourceScopeIds,
    })
    topicCreated = true

    await refreshAll()
    busyLabel.value = `Saved ${createdTopic.name} as a tracked topic`
    showLiveSearchSaveDialog.value = false
  } catch (error: unknown) {
    if (typeof createdScopeId === 'number' && !topicCreated) {
      try {
        await api.delete(`/api/v1/source-scopes/${createdScopeId}/`)
      } catch {
        // Best effort cleanup for partially created dedicated scopes.
      }
    }
    errorMessage.value = error instanceof Error ? error.message : 'Saving the live search as a topic failed.'
  } finally {
    isSavingLiveSearchTopic.value = false
  }
}

const loadDashboard = async () => {
  isLoadingDashboard.value = true
  setBusy('Refreshing dashboard telemetry...')

  try {
    const payload = await api.get<DashboardPayload>('/api/v1/dashboard/')
    dashboard.value = payload
    hydrateProviderForm(payload.provider)
  } catch (error: unknown) {
    errorMessage.value = error instanceof Error ? error.message : 'Dashboard refresh failed.'
  } finally {
    isLoadingDashboard.value = false
  }
}

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

const loadRuns = async () => {
  const query: Record<string, string | undefined> = {
    topic: runFilters.topic || undefined,
    status: runFilters.status || undefined,
  }

  runsPage.value = await api.get<PaginatedResponse<SearchRun>>('/api/v1/runs/', query)
}

const refreshAll = async () => {
  try {
    await Promise.all([loadDashboard(), loadResults(resultFilters.page), loadRuns()])
  } catch (error: unknown) {
    errorMessage.value = error instanceof Error ? error.message : 'Refresh failed.'
  } finally {
    busyLabel.value = 'Signal deck online'
  }
}

const saveProvider = async () => {
  if (!providerForm.id) return
  isSavingProvider.value = true
  setBusy('Writing provider controls...')

  try {
    await api.patch(`/api/v1/provider-config/${providerForm.id}/`, {
      enabled: providerForm.enabled,
    })
    await refreshAll()
  } catch (error: unknown) {
    errorMessage.value = error instanceof Error ? error.message : 'Provider update failed.'
  } finally {
    isSavingProvider.value = false
  }
}

const saveTopic = async () => {
  isSavingTopic.value = true
  setBusy(topicEditorMode.value === 'edit' ? 'Updating topic matrix...' : 'Creating new topic...')

  const payload = {
    name: topicForm.name.trim(),
    description: topicForm.description.trim(),
    enabled: topicForm.enabled,
    queries: splitLines(topicForm.queries),
    required_terms: splitLines(topicForm.requiredTerms),
    excluded_terms: splitLines(topicForm.excludedTerms),
    lookback_days: Number(topicForm.lookbackDays),
    schedule_every: Number(topicForm.scheduleEvery),
    schedule_unit: topicForm.scheduleUnit,
    max_results_per_query: Number(topicForm.maxResultsPerQuery),
    notes: topicForm.notes.trim(),
    source_scope_ids: topicForm.sourceScopeIds,
  }

  try {
    if (topicEditorMode.value === 'edit' && editingTopicSlug.value) {
      await api.patch(`/api/v1/topics/${editingTopicSlug.value}/`, payload)
    } else {
      await api.post('/api/v1/topics/', payload)
    }
    resetTopicForm()
    await refreshAll()
  } catch (error: unknown) {
    errorMessage.value = error instanceof Error ? error.message : 'Topic save failed.'
  } finally {
    isSavingTopic.value = false
  }
}

const deleteTopic = async (topic: SearchTopic) => {
  if (!window.confirm(`Delete topic "${topic.name}"?`)) return
  setBusy(`Deleting topic ${topic.name}...`)
  await api.delete(`/api/v1/topics/${topic.slug}/`)
  if (editingTopicSlug.value === topic.slug) {
    resetTopicForm()
  }
  await refreshAll()
}

const saveSource = async () => {
  isSavingSource.value = true
  setBusy(sourceEditorMode.value === 'edit' ? 'Updating source scope...' : 'Creating source scope...')

  const payload = {
    name: sourceForm.name.trim(),
    description: sourceForm.description.trim(),
    kind: sourceForm.kind,
    enabled: sourceForm.enabled,
    searxng_categories: sourceForm.useAllCategories ? [] : sourceForm.searxngCategories,
    use_all_categories: sourceForm.useAllCategories,
    use_all_engines: sourceForm.useAllEngines,
    searxng_engines: sourceForm.useAllEngines ? [] : sourceForm.searxngEngines,
    language: normalizeLanguageCode(sourceForm.language),
    safe_search: Number(sourceForm.safeSearch),
    time_range: sourceForm.timeRange,
    result_order: sourceForm.resultOrder,
    max_results: Number(sourceForm.maxResults),
    include_domains: splitLines(sourceForm.includeDomains),
    exclude_domains: splitLines(sourceForm.excludeDomains),
    sort_order: Number(sourceForm.sortOrder),
  }

  try {
    if (sourceEditorMode.value === 'edit' && editingSourceId.value) {
      await api.patch(`/api/v1/source-scopes/${editingSourceId.value}/`, payload)
    } else {
      await api.post('/api/v1/source-scopes/', payload)
    }
    resetSourceForm()
    await refreshAll()
  } catch (error: unknown) {
    errorMessage.value = error instanceof Error ? error.message : 'Source scope save failed.'
  } finally {
    isSavingSource.value = false
  }
}

const deleteSource = async (source: SourceScope) => {
  if (!window.confirm(`Delete source scope "${source.name}"?`)) return
  setBusy(`Deleting source scope ${source.name}...`)
  await api.delete(`/api/v1/source-scopes/${source.id}/`)
  if (editingSourceId.value === source.id) {
    resetSourceForm()
  }
  await refreshAll()
}

const runTopic = async (topic: SearchTopic) => {
  activeTopicRun.value = topic.slug
  setBusy(`Running ${topic.name} through SearxNG and Crawl4AI...`)
  try {
    await api.post(`/api/v1/topics/${topic.slug}/run_now/`, {})
    await refreshAll()
  } catch (error: unknown) {
    errorMessage.value = error instanceof Error ? error.message : 'Topic run failed.'
  } finally {
    activeTopicRun.value = null
  }
}

const acknowledgeTopic = async (topic: SearchTopic) => {
  activeTopicAcknowledge.value = topic.slug
  setBusy(`Acknowledging new results for ${topic.name}...`)
  try {
    await api.post(`/api/v1/topics/${topic.slug}/acknowledge/`, {})
    await refreshAll()
  } catch (error: unknown) {
    errorMessage.value = error instanceof Error ? error.message : 'Acknowledge failed.'
  } finally {
    activeTopicAcknowledge.value = null
  }
}

const acknowledgeVisibleResults = async () => {
  setBusy('Acknowledging visible results...')
  await api.post('/api/v1/results/acknowledge/', {
    topic: resultFilters.topic || undefined,
  })
  await refreshAll()
}

const focusTopicResults = async (topic: SearchTopic) => {
  activeWorkspace.value = 'explore'
  const topicChanged = resultFilters.topic !== topic.slug
  resultFilters.topic = topic.slug
  resultFilters.page = 1
  if (!topicChanged) {
    await loadResults(1)
  }
}

const clearResultFilters = async () => {
  const hadFilters = Boolean(
    resultFilters.q || resultFilters.topic || resultFilters.kind || resultFilters.isNewOnly,
  )
  resultFilters.q = ''
  resultFilters.topic = ''
  resultFilters.kind = ''
  resultFilters.isNewOnly = false
  if (!hadFilters) {
    await loadResults(1)
  }
}

const clearRunFilters = async () => {
  const hadFilters = Boolean(runFilters.topic || runFilters.status)
  runFilters.topic = ''
  runFilters.status = ''
  if (!hadFilters) {
    await loadRuns()
  }
}

const toggleTopicSource = (sourceId: number) => {
  if (topicForm.sourceScopeIds.includes(sourceId)) {
    topicForm.sourceScopeIds = topicForm.sourceScopeIds.filter((id) => id !== sourceId)
  } else {
    topicForm.sourceScopeIds = [...topicForm.sourceScopeIds, sourceId]
  }
}

const selectAllLiveSearchCategories = () => {
  liveSearchForm.categories = [...availableCategories.value]
}

const clearLiveSearchCategories = () => {
  liveSearchForm.categories = []
}

const selectAllLiveSearchEngines = () => {
  liveSearchForm.engines = [...availableEngines.value]
}

const clearLiveSearchEngines = () => {
  liveSearchForm.engines = []
}

const selectAllSourceCategories = () => {
  sourceForm.searxngCategories = [...availableCategories.value]
}

const clearSourceCategories = () => {
  sourceForm.searxngCategories = []
}

const selectAllSourceEngines = () => {
  sourceForm.searxngEngines = [...availableEngines.value]
}

const clearSourceEngines = () => {
  sourceForm.searxngEngines = []
}

const reloadAccessIdentity = () => {
  window.location.reload()
}

const handleLogout = async () => {
  await authStore.logout()
  resetDashboardState()
  activeWorkspace.value = 'search'
  closeLiveSearchSaveDialog()
}

const debouncedResultsReload = useDebounceFn(async () => {
  await loadResults(1)
}, 250)

const debouncedRunsReload = useDebounceFn(async () => {
  await loadRuns()
}, 250)

watch(
  () => [resultFilters.q, resultFilters.topic, resultFilters.kind, resultFilters.isNewOnly],
  () => {
    debouncedResultsReload()
  },
)

watch(
  () => [runFilters.topic, runFilters.status],
  () => {
    debouncedRunsReload()
  },
)

watch(
  () => authStore.isAuthenticated,
  (isAuthenticated) => {
    if (!isAuthenticated) {
      activeWorkspace.value = 'search'
      closeLiveSearchSaveDialog()
    }
  },
)

onMounted(async () => {
  try {
    await authStore.initialize()
    if (authStore.isAuthenticated) {
      await refreshAll()
    } else {
      resetDashboardState()
    }
  } finally {
    isBootstrappingAuth.value = false
  }
})
</script>

<template>
  <div class="screen-shell grid-bg">
    <NuxtRouteAnnouncer />
    <PwaInstallButton />

    <main class="mx-auto flex min-h-screen max-w-[1500px] flex-col gap-5 px-4 pt-5 pb-28 sm:px-6 sm:pb-24 lg:px-8">
      <section class="terminal-panel relative overflow-hidden rounded-[1.8rem] p-6 sm:p-8">
        <div class="relative z-10 flex flex-col gap-8 lg:flex-row lg:items-end lg:justify-between">
          <div class="max-w-3xl space-y-3">
            <XunoBrandMark class="max-w-[30rem]" />
            <div class="pill w-fit bg-[var(--accent-soft)] text-[var(--accent)]">
              <span class="h-2 w-2 rounded-full bg-[var(--accent)] shadow-[0_0_14px_var(--accent)]" />
              searxng + crawl4ai
            </div>
          </div>

          <div class="grid gap-4 sm:grid-cols-2 lg:w-[420px]">
            <div class="rounded-2xl border border-[var(--line)] bg-black/30 p-4">
              <p class="text-xs uppercase tracking-[0.25em] text-[var(--muted)]">Operator</p>
              <p class="mt-2 text-3xl text-white">
                {{
                  isBootstrappingAuth
                    ? 'Checking'
                    : authStore.isAuthenticated
                      ? 'Verified'
                      : 'Required'
                }}
              </p>
              <p class="mt-1 text-xs text-[var(--muted)]">
                {{
                  isBootstrappingAuth
                    ? 'Verifying identity...'
                    : authStore.isAuthenticated
                      ? currentUserLabel
                      : 'Not signed in'
                }}
              </p>
              <div v-if="authStore.isAuthenticated" class="mt-3">
                <button class="terminal-button terminal-button-secondary text-xs" @click="handleLogout">
                  Sign out
                </button>
              </div>
            </div>
            <div class="rounded-2xl border border-[var(--line)] bg-black/30 p-4">
              <p class="text-xs uppercase tracking-[0.25em] text-[var(--muted)]">Status</p>
              <template v-if="authStore.isAuthenticated">
                <p class="mt-2 text-sm text-white">{{ busyLabel }}</p>
                <p class="mt-4 text-xs text-[var(--muted)]">
                  SearxNG:
                  <span class="text-[var(--accent)]">{{ provider?.searxng_base_url || 'n/a' }}</span>
                </p>
                <p class="mt-2 text-xs text-[var(--muted)]">
                  Crawl4AI:
                  <span :class="provider?.crawl4ai_enabled ? 'text-[var(--accent)]' : 'text-[var(--danger)]'">
                    {{ provider?.crawl4ai_enabled ? 'enabled' : 'disabled' }}
                  </span>
                </p>
              </template>
              <template v-else-if="isBootstrappingAuth">
                <p class="mt-2 text-sm text-[var(--muted)]">Checking authentication...</p>
              </template>
              <template v-else>
                <p class="mt-2 text-sm text-white">
                  {{ authStore.error ? 'Auth service unavailable' : 'Live search available' }}
                </p>
                <p class="mt-1 text-xs text-[var(--muted)]">
                  {{ authStore.error || 'Sign in to access saved searches and operator workspaces.' }}
                </p>
                <div class="mt-4">
                  <button class="terminal-button terminal-button-primary" @click="authStore.signIn()">
                    Sign in
                  </button>
                </div>
              </template>
            </div>
          </div>
        </div>
      </section>

      <section
        v-if="isBootstrappingAuth"
        class="rounded-2xl border border-[var(--line)] bg-black/30 px-4 py-6 text-sm text-[var(--muted)]"
      >
        Checking Cloudflare Access...
      </section>

      <template v-else>
        <section
          v-if="!authStore.isAuthenticated"
          class="terminal-panel relative overflow-hidden rounded-[1.6rem] p-5 sm:p-7"
        >
          <div class="relative z-10 space-y-5">
            <div>
              <p class="mono-heading text-lg uppercase tracking-[0.22em] text-white">
                Public live search enabled
              </p>
            </div>

            <article class="rounded-[1.4rem] border border-[var(--line)] bg-black/20 p-5 text-sm text-[var(--muted)]">
              <p>
                Live SearxNG search is available without signing in.
              </p>
              <p class="mt-3">
                Saving searches, inspecting stored results, and managing topics or source scopes still requires a Cloudflare-authenticated user.
              </p>
              <p v-if="authStore.error" class="mt-3 text-[#ffd8d8]">
                {{ authStore.error }}
              </p>
              <div class="mt-4">
                <button class="terminal-button terminal-button-secondary" @click="reloadAccessIdentity">
                  Reload identity
                </button>
              </div>
            </article>
          </div>
        </section>

        <section v-if="errorMessage" class="rounded-2xl border border-[rgba(255,125,125,0.35)] bg-[rgba(64,7,7,0.6)] px-4 py-3 text-sm text-[#ffd8d8]">
          {{ errorMessage }}
        </section>

        <section class="terminal-panel relative overflow-hidden rounded-[1.5rem] p-3 sm:p-4">
          <div class="relative z-10 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <button
              v-for="tab in visibleWorkspaceTabs"
              :key="tab.key"
              class="rounded-[1.2rem] border px-4 py-4 text-left transition-all"
              :class="
                activeWorkspace === tab.key
                  ? 'border-[var(--accent)] bg-[var(--accent-soft)] shadow-[0_0_24px_rgba(91,255,147,0.12)]'
                  : 'border-[var(--line)] bg-black/25 hover:border-[var(--accent)]/60 hover:bg-black/35'
              "
              @click="activeWorkspace = tab.key"
            >
              <p class="text-[11px] uppercase tracking-[0.28em]" :class="activeWorkspace === tab.key ? 'text-[var(--accent)]' : 'text-[var(--muted)]'">
                {{ tab.eyebrow }}
              </p>
              <p class="mt-2 mono-heading text-lg text-white">{{ tab.label }}</p>
            </button>
          </div>
        </section>

      <template v-if="activeWorkspace === 'search' || !authStore.isAuthenticated">
        <section>
          <section class="terminal-panel relative overflow-hidden rounded-[1.5rem] p-5">
            <div class="relative z-10 space-y-5">
              <div class="flex flex-col gap-3 xl:flex-row xl:items-end xl:justify-between">
                <div>
                  <p class="mono-heading text-lg uppercase tracking-[0.22em] text-white">Live SearxNG terminal</p>
                </div>
                <div class="flex flex-wrap gap-2">
                  <button class="terminal-button terminal-button-secondary" @click="showAdvancedSearch = !showAdvancedSearch">
                    {{ showAdvancedSearch ? 'Hide advanced' : 'Advanced search' }}
                  </button>
                  <button
                    class="terminal-button terminal-button-secondary"
                    :disabled="!canSaveLiveSearchAsTopic"
                    @click="openLiveSearchSaveDialog"
                  >
                    Save search
                  </button>
                  <button class="terminal-button terminal-button-secondary" @click="resetLiveSearchWorkspace">
                    Reset
                  </button>
                </div>
              </div>

              <div class="grid gap-3 sm:grid-cols-[1fr_auto]">
                <label class="space-y-2">
                  <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Search query</span>
                  <input
                    v-model="liveSearchForm.q"
                    class="terminal-input"
                    placeholder="&quot;data platform&quot; OR &quot;research data exchange&quot;"
                    @keyup.enter="runLiveSearch"
                  />
                </label>
                <button
                  class="terminal-button terminal-button-primary h-[46px] self-end px-6"
                  :disabled="isRunningLiveSearch"
                  @click="runLiveSearch"
                >
                  {{ isRunningLiveSearch ? 'Searching...' : 'Search now' }}
                </button>
              </div>

              <article
                v-if="!authStore.isAuthenticated"
                class="rounded-[1.3rem] border border-dashed border-[var(--line)] bg-black/20 p-4 text-sm text-[var(--muted)]"
              >
                Sign in through Cloudflare Access to save this live search as a tracked topic or attach it to source scopes.
              </article>

              <div v-if="showAdvancedSearch" class="space-y-4 rounded-[1.4rem] border border-[var(--line)] bg-black/20 p-4">
                <div class="grid gap-3 lg:grid-cols-4">
                  <label class="space-y-2">
                    <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Language</span>
                    <select v-model="liveSearchForm.language" class="terminal-select">
                      <option value="">All languages</option>
                      <option v-for="language in availableLanguages" :key="language.code" :value="language.code">
                        {{ language.label }} ({{ language.code }})
                      </option>
                    </select>
                  </label>
                  <label class="space-y-2">
                    <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Safe search</span>
                    <select v-model="liveSearchForm.safeSearch" class="terminal-select">
                      <option value="0">Off</option>
                      <option value="1">Moderate</option>
                      <option value="2">Strict</option>
                    </select>
                  </label>
                  <label class="space-y-2">
                    <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Time range</span>
                    <select v-model="liveSearchForm.timeRange" class="terminal-select">
                      <option value="">None</option>
                      <option value="day">Day</option>
                      <option value="month">Month</option>
                      <option value="year">Year</option>
                    </select>
                  </label>
                  <label class="space-y-2">
                    <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Result order</span>
                    <select v-model="liveSearchForm.resultOrder" class="terminal-select">
                      <option value="relevance">Relevance</option>
                      <option value="newest">Time (newest first)</option>
                    </select>
                  </label>
                </div>

                <div class="grid gap-3 lg:grid-cols-2">
                  <label class="space-y-2">
                    <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Category coverage</span>
                    <select v-model="liveSearchForm.useAllCategories" class="terminal-select">
                      <option :value="true">All available SearxNG categories</option>
                      <option :value="false">Restrict to selected categories</option>
                    </select>
                  </label>
                  <label class="space-y-2">
                    <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Engine coverage</span>
                    <select v-model="liveSearchForm.useAllEngines" class="terminal-select">
                      <option :value="true">All available SearxNG engines</option>
                      <option :value="false">Restrict to specific engines</option>
                    </select>
                  </label>
                  <label class="space-y-2">
                    <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Include domains</span>
                    <textarea
                      v-model="liveSearchForm.includeDomains"
                      class="terminal-textarea min-h-[80px]"
                      placeholder="zenodo.org&#10;datacite.org"
                    />
                  </label>
                  <label class="space-y-2">
                    <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Exclude domains</span>
                    <textarea
                      v-model="liveSearchForm.excludeDomains"
                      class="terminal-textarea min-h-[80px]"
                      placeholder="linkedin.com&#10;jobs.example.com"
                    />
                  </label>
                  <label class="space-y-2 lg:col-span-2">
                    <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Raw SearxNG params</span>
                    <textarea
                      v-model="liveSearchForm.extraParams"
                      class="terminal-textarea min-h-[110px]"
                      placeholder="theme=simple&#10;enabled_plugins=Hash_plugin,Tracker_URL_remover&#10;disabled_plugins=Open_Access_DOI_rewrite"
                    />
                  </label>
                </div>

                <div v-if="!liveSearchForm.useAllCategories" class="space-y-3 rounded-[1.3rem] border border-[var(--line)] bg-black/20 p-4">
                  <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <p class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">
                      Selected categories: <span class="text-[var(--text)]">{{ liveSearchForm.categories.length }}</span>
                      / {{ availableCategories.length || '0' }}
                    </p>
                    <div class="flex flex-wrap gap-2">
                      <button type="button" class="terminal-button terminal-button-secondary" @click="selectAllLiveSearchCategories">
                        Select all
                      </button>
                      <button type="button" class="terminal-button terminal-button-secondary" @click="clearLiveSearchCategories">
                        Clear
                      </button>
                    </div>
                  </div>
                  <select
                    v-if="availableCategories.length"
                    v-model="liveSearchForm.categories"
                    class="terminal-select min-h-[220px]"
                    multiple
                  >
                    <option v-for="category in availableCategories" :key="category" :value="category">
                      {{ category }}
                    </option>
                  </select>
                  <p v-else class="text-sm text-[var(--muted)]">
                    No categories are advertised by the connected SearxNG instance right now.
                  </p>
                </div>

                <div v-if="!liveSearchForm.useAllEngines" class="space-y-3 rounded-[1.3rem] border border-[var(--line)] bg-black/20 p-4">
                  <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <p class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">
                      Selected engines: <span class="text-[var(--text)]">{{ liveSearchForm.engines.length }}</span>
                      / {{ availableEngines.length || '0' }}
                    </p>
                    <div class="flex flex-wrap gap-2">
                      <button type="button" class="terminal-button terminal-button-secondary" @click="selectAllLiveSearchEngines">
                        Select all
                      </button>
                      <button type="button" class="terminal-button terminal-button-secondary" @click="clearLiveSearchEngines">
                        Clear
                      </button>
                    </div>
                  </div>
                  <select
                    v-if="availableEngines.length"
                    v-model="liveSearchForm.engines"
                    class="terminal-select min-h-[220px]"
                    multiple
                  >
                    <option v-for="engine in availableEngines" :key="engine" :value="engine">
                      {{ engine }}
                    </option>
                  </select>
                  <p v-else class="text-sm text-[var(--muted)]">
                    No enabled engines are advertised by the connected SearxNG instance right now.
                  </p>
                </div>
              </div>

            </div>
          </section>
        </section>

        <section class="terminal-panel relative overflow-hidden rounded-[1.5rem] p-5">
          <div class="relative z-10 space-y-4">
            <p class="mono-heading text-lg uppercase tracking-[0.22em] text-white">Live result stream</p>

            <div v-if="liveSearchResponse && liveSearchResults.length" class="space-y-3">
              <article
                v-for="result in liveSearchResults"
                :key="`${result.url}-${result.position}`"
                class="rounded-2xl border border-[var(--line)] bg-black/25 p-4"
              >
                <div class="flex flex-wrap items-start justify-between gap-3">
                  <div class="space-y-2">
                    <div class="flex flex-wrap gap-2">
                      <span v-if="result.engine" class="pill text-[var(--accent)]">{{ result.engine }}</span>
                      <span v-if="result.category" class="pill text-[var(--text)]">{{ result.category }}</span>
                      <span class="pill text-[var(--muted)]">#{{ result.position }}</span>
                    </div>
                    <a :href="result.url" target="_blank" rel="noreferrer" class="text-lg text-white hover:text-[var(--accent)]">
                      {{ result.title }}
                    </a>
                    <p class="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">{{ result.domain }}</p>
                  </div>
                  <div class="text-right text-xs text-[var(--muted)]">
                    <p>Published {{ formatDate(result.published_at) }}</p>
                    <p class="mt-2">Score {{ result.score ?? 'n/a' }}</p>
                  </div>
                </div>
                <p class="mt-3 text-sm leading-6 text-[var(--muted)]">{{ result.snippet || 'No snippet returned by SearxNG.' }}</p>
              </article>

              <div class="flex justify-center pt-2">
                <button
                  v-if="canLoadMoreLiveSearch"
                  class="terminal-button terminal-button-secondary"
                  :disabled="isRunningLiveSearch"
                  @click="loadMoreLiveSearchResults"
                >
                  {{ isRunningLiveSearch ? 'Loading...' : 'Load more results' }}
                </button>
                <p v-else class="text-sm text-[var(--muted)]">
                  Showing {{ liveSearchLoadedCount }} results in 10-result pages.
                </p>
              </div>
            </div>

            <article v-else class="rounded-2xl border border-[var(--line)] bg-black/25 p-5 text-sm text-[var(--muted)]">
              Run a live search to inspect results here.
            </article>
          </div>
        </section>

        <div
          v-if="showLiveSearchSaveDialog && authStore.isAuthenticated"
          class="fixed inset-0 z-50 flex items-center justify-center bg-black/72 px-4 py-6 backdrop-blur-sm"
          @click.self="closeLiveSearchSaveDialog"
        >
          <section class="terminal-panel relative max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-[1.6rem] p-5 sm:p-6">
            <div class="relative z-10 space-y-4">
              <div class="flex items-start justify-between gap-3">
                <div>
                  <p class="mono-heading text-lg uppercase tracking-[0.22em] text-white">Save current search</p>
                  <p class="mt-2 text-xs uppercase tracking-[0.22em] text-[var(--muted)]">
                    Active query: <span class="text-[var(--text)]">{{ liveSearchForm.q || 'n/a' }}</span>
                  </p>
                </div>
                <button class="terminal-button terminal-button-secondary" @click="closeLiveSearchSaveDialog">
                  Close
                </button>
              </div>

              <div class="grid gap-3 sm:grid-cols-2">
                <label class="space-y-2 sm:col-span-2">
                  <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Topic name</span>
                  <input v-model="liveSearchSaveForm.name" class="terminal-input" :placeholder="fallbackLiveTopicName()" />
                </label>
                <label class="space-y-2 sm:col-span-2">
                  <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Description</span>
                  <textarea v-model="liveSearchSaveForm.description" class="terminal-textarea min-h-[90px]" />
                </label>
                <label class="space-y-2">
                  <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Schedule every</span>
                  <input v-model="liveSearchSaveForm.scheduleEvery" class="terminal-input" type="number" min="1" />
                </label>
                <label class="space-y-2">
                  <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Schedule unit</span>
                  <select v-model="liveSearchSaveForm.scheduleUnit" class="terminal-select">
                    <option value="minutes">Minutes</option>
                    <option value="hours">Hours</option>
                    <option value="days">Days</option>
                    <option value="weeks">Weeks</option>
                  </select>
                </label>
                <label class="space-y-2">
                  <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Topic enabled</span>
                  <select v-model="liveSearchSaveForm.enabled" class="terminal-select">
                    <option :value="true">Enabled</option>
                    <option :value="false">Disabled</option>
                  </select>
                </label>
                <label class="space-y-2">
                  <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Dedicated scope</span>
                  <select v-model="liveSearchSaveForm.createScope" class="terminal-select">
                    <option :value="true">Create from current filters</option>
                    <option :value="false">Reuse existing scopes only</option>
                  </select>
                </label>
              </div>

              <div v-if="liveSearchSaveForm.createScope" class="grid gap-3 rounded-[1.4rem] border border-[var(--line)] bg-black/20 p-4 sm:grid-cols-2">
                <label class="space-y-2 sm:col-span-2">
                  <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Scope name</span>
                  <input v-model="liveSearchSaveForm.scopeName" class="terminal-input" :placeholder="fallbackLiveScopeName()" />
                </label>
                <label class="space-y-2 sm:col-span-2">
                  <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Scope description</span>
                  <textarea v-model="liveSearchSaveForm.scopeDescription" class="terminal-textarea min-h-[80px]" />
                </label>
                <label class="space-y-2">
                  <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Scope kind</span>
                  <select v-model="liveSearchSaveForm.scopeKind" class="terminal-select">
                    <option value="public">Public</option>
                    <option value="research">Research</option>
                    <option value="custom">Custom</option>
                  </select>
                </label>
                <article class="rounded-2xl border border-[var(--line)] bg-black/25 p-4 text-sm text-[var(--muted)]">
                  <p>Derived lookback: <span class="text-[var(--text)]">{{ deriveLookbackDays(liveSearchForm.timeRange) }} days</span></p>
                </article>
              </div>

              <div class="space-y-3 rounded-[1.4rem] border border-[var(--line)] bg-black/20 p-4">
                <p class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Attach existing source scopes</p>
                <div class="grid gap-2 sm:grid-cols-2">
                  <label
                    v-for="source in enabledSources"
                    :key="source.id"
                    class="flex cursor-pointer items-start gap-3 rounded-2xl border border-[var(--line)] p-3 text-sm text-[var(--text)]"
                  >
                    <input
                      :checked="liveSearchSaveForm.sourceScopeIds.includes(source.id)"
                      type="checkbox"
                      class="mt-1 accent-[var(--accent)]"
                      @change="toggleLiveSearchSource(source.id)"
                    />
                    <span>
                      <span class="block">{{ source.name }}</span>
                      <span class="mt-1 block text-xs text-[var(--muted)]">{{ source.kind }} / {{ describeCategories(source) }}</span>
                    </span>
                  </label>
                </div>
              </div>

              <div class="flex flex-wrap justify-end gap-2">
                <button class="terminal-button terminal-button-secondary" @click="closeLiveSearchSaveDialog">
                  Cancel
                </button>
                <button
                  class="terminal-button terminal-button-primary"
                  :disabled="isSavingLiveSearchTopic || !canSaveLiveSearch"
                  @click="saveLiveSearchAsTopic"
                >
                  {{ isSavingLiveSearchTopic ? 'Saving topic...' : 'Save as new topic' }}
                </button>
              </div>
            </div>
          </section>
        </div>
      </template>

      <section
        v-if="authStore.isAuthenticated && activeWorkspace === 'explore'"
        class="grid gap-5 xl:grid-cols-[0.92fr_1.48fr]"
      >
        <div class="space-y-5">
          <section class="terminal-panel relative overflow-hidden rounded-[1.5rem] p-5">
            <div class="relative z-10 space-y-4">
              <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <p class="mono-heading text-lg uppercase tracking-[0.22em] text-white">Topic navigator</p>
                </div>
                <button class="terminal-button terminal-button-secondary" :disabled="isLoadingDashboard" @click="refreshAll">
                  Refresh
                </button>
              </div>

              <div class="space-y-3">
                <article
                  v-for="topic in topics"
                  :key="topic.slug"
                  class="rounded-2xl border border-[var(--line)] bg-black/25 p-4"
                >
                  <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <div class="flex flex-wrap gap-2">
                        <span class="pill" :class="topic.enabled ? 'text-[var(--accent)]' : 'text-[var(--muted)]'">
                          {{ topic.enabled ? 'armed' : 'paused' }}
                        </span>
                        <span class="pill" :class="statusClass(topic.last_run_status)">
                          {{ summarizeStatus(topic.last_run_status) }}
                        </span>
                      </div>
                      <p class="mt-3 text-lg text-white">{{ topic.name }}</p>
                    </div>
                    <div class="sm:min-w-[92px] sm:text-right">
                      <p class="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">New</p>
                      <p class="mt-1 text-3xl text-white">{{ topic.new_results_count }}</p>
                    </div>
                  </div>

                  <div class="mt-4 space-y-2 text-xs text-[var(--muted)]">
                    <p>Schedule: <span class="text-[var(--text)]">{{ topic.schedule_description }}</span></p>
                    <p>Next run: <span class="text-[var(--text)]">{{ formatNextRun(topic) }}</span></p>
                    <p>Stored results: <span class="text-[var(--text)]">{{ topic.result_count }}</span></p>
                    <p>Last checked: <span class="text-[var(--text)]">{{ formatDate(topic.last_checked_at) }}</span></p>
                    <p>Sources: <span class="text-[var(--text)]">{{ topic.source_scopes.map((scope) => scope.name).join(', ') || 'None' }}</span></p>
                  </div>

                  <div class="mt-4 flex flex-wrap gap-2">
                    <button class="terminal-button terminal-button-primary" @click="focusTopicResults(topic)">
                      Inspect
                    </button>
                    <button
                      class="terminal-button terminal-button-secondary"
                      :disabled="activeTopicRun === topic.slug"
                      @click="runTopic(topic)"
                    >
                      {{ activeTopicRun === topic.slug ? 'Running...' : 'Run now' }}
                    </button>
                    <button
                      class="terminal-button terminal-button-secondary"
                      :disabled="activeTopicAcknowledge === topic.slug"
                      @click="acknowledgeTopic(topic)"
                    >
                      Ack new
                    </button>
                  </div>
                </article>

                <article v-if="topics.length === 0" class="rounded-2xl border border-[var(--line)] bg-black/25 p-5 text-sm text-[var(--muted)]">
                  No topics configured yet. Open the configure workspace to create the first one.
                </article>
              </div>
            </div>
          </section>

          <section class="grid gap-4 sm:grid-cols-2">
            <article class="terminal-panel relative overflow-hidden rounded-[1.4rem] p-5">
              <p class="text-xs uppercase tracking-[0.28em] text-[var(--muted)]">New findings</p>
              <p class="mt-3 text-4xl text-white">{{ stats?.new_result_count ?? 0 }}</p>
            </article>
            <article class="terminal-panel relative overflow-hidden rounded-[1.4rem] p-5">
              <p class="text-xs uppercase tracking-[0.28em] text-[var(--muted)]">Stored results</p>
              <p class="mt-3 text-4xl text-white">{{ stats?.result_count ?? 0 }}</p>
            </article>
          </section>
        </div>

        <div class="space-y-5">
          <SearchMapWorkspace
            :topic-slug="resultFilters.topic"
            :topic-name="selectedTopic?.name ?? ''"
            :q="resultFilters.q"
            :kind="resultFilters.kind"
            :is-new-only="resultFilters.isNewOnly"
          />

          <section class="terminal-panel relative overflow-hidden rounded-[1.5rem] p-5">
            <div class="relative z-10 space-y-4">
              <div class="flex flex-col gap-3 xl:flex-row xl:items-end xl:justify-between">
                <div>
                  <p class="mono-heading text-lg uppercase tracking-[0.22em] text-white">Results terminal</p>
                </div>
                <div class="flex flex-wrap gap-2">
                  <button class="terminal-button terminal-button-secondary" @click="clearResultFilters">Clear filters</button>
                  <button class="terminal-button terminal-button-secondary" @click="acknowledgeVisibleResults">Ack visible</button>
                </div>
              </div>

              <div class="grid gap-3 lg:grid-cols-4">
                <label class="space-y-2 lg:col-span-2">
                  <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Search text</span>
                  <input v-model="resultFilters.q" class="terminal-input" placeholder="zenodo, metadata, exchange format..." />
                </label>
                <label class="space-y-2">
                  <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Topic filter</span>
                  <select v-model="resultFilters.topic" class="terminal-select">
                    <option value="">All topics</option>
                    <option v-for="topic in topics" :key="topic.slug" :value="topic.slug">{{ topic.name }}</option>
                  </select>
                </label>
                <label class="space-y-2">
                  <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Scope kind</span>
                  <select v-model="resultFilters.kind" class="terminal-select">
                    <option value="">All kinds</option>
                    <option value="public">Public</option>
                    <option value="research">Research</option>
                    <option value="custom">Custom</option>
                  </select>
                </label>
              </div>

              <label class="flex items-center gap-3 text-sm text-[var(--muted)]">
                <input v-model="resultFilters.isNewOnly" type="checkbox" class="accent-[var(--accent)]" />
                Show only new results
              </label>

              <ResponsiveResultsList :results="results" :format-date="formatDate" />

              <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <p class="text-sm text-[var(--muted)]">
                  Showing {{ results.length }} of {{ resultsPage?.count ?? 0 }} results
                  <span v-if="selectedTopic"> for {{ selectedTopic.name }}</span>
                </p>
                <div class="flex gap-2">
                  <button
                    class="terminal-button terminal-button-secondary"
                    :disabled="!resultsPage?.previous"
                    @click="loadResults(resultFilters.page - 1)"
                  >
                    Prev
                  </button>
                  <button
                    class="terminal-button terminal-button-secondary"
                    :disabled="!resultsPage?.next"
                    @click="loadResults(resultFilters.page + 1)"
                  >
                    Next
                  </button>
                </div>
              </div>
            </div>
          </section>
        </div>
      </section>

      <section
        v-else-if="authStore.isAuthenticated && activeWorkspace === 'configure'"
        class="grid gap-5 xl:grid-cols-[1.45fr_0.95fr]"
      >
        <div class="space-y-5">
          <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p class="mono-heading text-lg uppercase tracking-[0.22em] text-white">Topic matrix</p>
            </div>
            <div class="flex flex-wrap gap-2">
              <button class="terminal-button terminal-button-secondary" :disabled="isLoadingDashboard" @click="refreshAll">
                Refresh
              </button>
              <button class="terminal-button terminal-button-secondary" @click="resetSourceForm">
                New source
              </button>
              <button class="terminal-button terminal-button-primary" @click="openTopicEditor()">
                New topic
              </button>
            </div>
          </div>

          <div class="grid gap-4 lg:grid-cols-2">
            <article
              v-for="topic in topics"
              :key="topic.slug"
              class="terminal-panel relative overflow-hidden rounded-[1.5rem] p-5"
            >
              <div class="relative z-10 flex h-full flex-col gap-4">
                <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                  <div class="space-y-2">
                    <div class="flex flex-wrap gap-2">
                      <span class="pill" :class="topic.enabled ? 'text-[var(--accent)]' : 'text-[var(--muted)]'">
                        {{ topic.enabled ? 'armed' : 'paused' }}
                      </span>
                      <span class="pill" :class="statusClass(topic.last_run_status)">
                        {{ summarizeStatus(topic.last_run_status) }}
                      </span>
                    </div>
                    <h2 class="text-xl text-white">{{ topic.name }}</h2>
                  </div>

                  <div class="sm:min-w-[110px] sm:text-right">
                    <p class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">New</p>
                    <p class="mt-1 text-3xl text-white">{{ topic.new_results_count }}</p>
                  </div>
                </div>

                <div class="space-y-3 rounded-2xl border border-[var(--line)] bg-black/25 p-4">
                  <p class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Queries</p>
                  <div class="flex flex-wrap gap-2">
                    <span v-for="query in topic.query_preview" :key="query" class="rounded-full border border-[var(--line)] px-3 py-1 text-xs text-[var(--text)]">
                      {{ query }}
                    </span>
                  </div>
                </div>

                <div class="grid gap-3 sm:grid-cols-3">
                  <div class="rounded-2xl border border-[var(--line)] bg-black/20 p-3">
                    <p class="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Scope count</p>
                    <p class="mt-2 text-2xl text-white">{{ topic.source_scopes.length }}</p>
                  </div>
                  <div class="rounded-2xl border border-[var(--line)] bg-black/20 p-3">
                    <p class="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Lookback</p>
                    <p class="mt-2 text-2xl text-white">{{ topic.lookback_days }}d</p>
                  </div>
                  <div class="rounded-2xl border border-[var(--line)] bg-black/20 p-3">
                    <p class="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Stored</p>
                    <p class="mt-2 text-2xl text-white">{{ topic.result_count }}</p>
                  </div>
                </div>

                <div class="space-y-2 text-xs text-[var(--muted)]">
                  <p>Schedule: <span class="text-[var(--text)]">{{ topic.schedule_description }}</span></p>
                  <p>Next run: <span class="text-[var(--text)]">{{ formatNextRun(topic) }}</span></p>
                  <p>Last checked: <span class="text-[var(--text)]">{{ formatDate(topic.last_checked_at) }}</span></p>
                  <p>Last new result: <span class="text-[var(--text)]">{{ formatDate(topic.last_new_results_at) }}</span></p>
                  <p>
                    Sources:
                    <span class="text-[var(--text)]">{{ topic.source_scopes.map((scope) => scope.name).join(', ') || 'None' }}</span>
                  </p>
                </div>

                <div class="mt-auto flex flex-wrap gap-2">
                  <button
                    class="terminal-button terminal-button-primary"
                    :disabled="activeTopicRun === topic.slug"
                    @click="runTopic(topic)"
                  >
                    {{ activeTopicRun === topic.slug ? 'Running...' : 'Run now' }}
                  </button>
                  <button
                    class="terminal-button terminal-button-secondary"
                    :disabled="activeTopicAcknowledge === topic.slug"
                    @click="acknowledgeTopic(topic)"
                  >
                    Ack new
                  </button>
                  <button class="terminal-button terminal-button-secondary" @click="focusTopicResults(topic)">Inspect</button>
                  <button class="terminal-button terminal-button-secondary" @click="openTopicEditor(topic)">Edit</button>
                  <button class="terminal-button terminal-button-danger" @click="deleteTopic(topic)">Delete</button>
                </div>
              </div>
            </article>
          </div>
        </div>

        <div class="space-y-5">
          <section class="terminal-panel relative overflow-hidden rounded-[1.5rem] p-5">
            <div class="relative z-10 space-y-4">
              <div class="flex items-start justify-between gap-3">
                <div>
                  <p class="mono-heading text-lg uppercase tracking-[0.22em] text-white">Provider control</p>
                </div>
              </div>

              <div class="grid gap-3">
                <label class="space-y-2">
                  <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Provider enabled</span>
                  <select v-model="providerForm.enabled" class="terminal-select">
                    <option :value="true">Enabled</option>
                    <option :value="false">Disabled</option>
                  </select>
                </label>
              </div>

              <div class="rounded-2xl border border-[var(--line)] bg-black/20 p-4 text-sm text-[var(--muted)]">
                <p>Provider: <span class="text-[var(--text)]">{{ provider?.name ?? 'searxng' }}</span></p>
                <p class="mt-2">Base URL: <span class="text-[var(--text)]">{{ provider?.searxng_base_url || 'n/a' }}</span></p>
                <p class="mt-2">
                  Crawl4AI:
                  <span :class="provider?.crawl4ai_enabled ? 'text-[var(--accent)]' : 'text-[var(--danger)]'">
                    {{ provider?.crawl4ai_enabled ? 'enabled' : 'disabled' }}
                  </span>
                </p>
              </div>

              <button class="terminal-button terminal-button-primary w-full" :disabled="isSavingProvider" @click="saveProvider">
                {{ isSavingProvider ? 'Saving...' : 'Save provider settings' }}
              </button>
            </div>
          </section>

          <section class="terminal-panel relative overflow-hidden rounded-[1.5rem] p-5">
            <div class="relative z-10 space-y-4">
              <div class="flex items-start justify-between gap-3">
                <div>
                  <p class="mono-heading text-lg uppercase tracking-[0.22em] text-white">
                    {{ topicEditorMode === 'edit' ? 'Edit topic' : 'Create topic' }}
                  </p>
                </div>
                <button class="terminal-button terminal-button-secondary" @click="resetTopicForm">Reset</button>
              </div>

              <div class="grid gap-3 sm:grid-cols-2">
                <label class="space-y-2 sm:col-span-2">
                  <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Topic name</span>
                  <input v-model="topicForm.name" class="terminal-input" placeholder="Research data exchange landscape" />
                </label>
                <label class="space-y-2 sm:col-span-2">
                  <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Description</span>
                  <textarea v-model="topicForm.description" class="terminal-textarea min-h-[90px]" />
                </label>
                <label class="space-y-2">
                  <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Queries</span>
                  <textarea v-model="topicForm.queries" class="terminal-textarea min-h-[155px]" />
                </label>
                <div class="grid gap-3">
                  <label class="space-y-2">
                    <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Required terms</span>
                    <textarea v-model="topicForm.requiredTerms" class="terminal-textarea min-h-[70px]" placeholder="open science" />
                  </label>
                  <label class="space-y-2">
                    <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Excluded terms</span>
                    <textarea v-model="topicForm.excludedTerms" class="terminal-textarea min-h-[70px]" placeholder="jobs" />
                  </label>
                </div>
                <label class="space-y-2">
                  <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Lookback days</span>
                  <input v-model="topicForm.lookbackDays" class="terminal-input" type="number" min="1" />
                </label>
                <div class="grid gap-3">
                  <label class="space-y-2">
                    <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Schedule every</span>
                    <input v-model="topicForm.scheduleEvery" class="terminal-input" type="number" min="1" />
                  </label>
                  <label class="space-y-2">
                    <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Schedule unit</span>
                    <select v-model="topicForm.scheduleUnit" class="terminal-select">
                      <option value="minutes">Minutes</option>
                      <option value="hours">Hours</option>
                      <option value="days">Days</option>
                      <option value="weeks">Weeks</option>
                    </select>
                  </label>
                </div>
                <label class="space-y-2">
                  <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Max results / query</span>
                  <input v-model="topicForm.maxResultsPerQuery" class="terminal-input" type="number" min="1" max="20" />
                </label>
                <label class="space-y-2 sm:col-span-2">
                  <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Notes</span>
                  <textarea v-model="topicForm.notes" class="terminal-textarea min-h-[90px]" />
                </label>
                <label class="space-y-2">
                  <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Enabled</span>
                  <select v-model="topicForm.enabled" class="terminal-select">
                    <option :value="true">Enabled</option>
                    <option :value="false">Disabled</option>
                  </select>
                </label>
              </div>

              <div class="space-y-3 rounded-2xl border border-[var(--line)] bg-black/20 p-4">
                <p class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Attach source scopes</p>
                <div class="grid gap-2 sm:grid-cols-2">
                  <label
                    v-for="source in sources"
                    :key="source.id"
                    class="flex cursor-pointer items-start gap-3 rounded-2xl border border-[var(--line)] p-3 text-sm text-[var(--text)]"
                  >
                    <input
                      :checked="topicForm.sourceScopeIds.includes(source.id)"
                      type="checkbox"
                      class="mt-1 accent-[var(--accent)]"
                      @change="toggleTopicSource(source.id)"
                    />
                    <span>
                      <span class="block">{{ source.name }}</span>
                      <span class="mt-1 block text-xs text-[var(--muted)]">{{ source.kind }} / {{ describeCategories(source) }}</span>
                    </span>
                  </label>
                </div>
              </div>

              <button class="terminal-button terminal-button-primary w-full" :disabled="isSavingTopic" @click="saveTopic">
                {{ isSavingTopic ? 'Saving topic...' : topicEditorMode === 'edit' ? 'Update topic' : 'Create topic' }}
              </button>
            </div>
          </section>

          <section class="terminal-panel relative overflow-hidden rounded-[1.5rem] p-5">
            <div class="relative z-10 space-y-4">
              <div class="flex items-start justify-between gap-3">
                <div>
                  <p class="mono-heading text-lg uppercase tracking-[0.22em] text-white">
                    {{ sourceEditorMode === 'edit' ? 'Edit source scope' : 'Create source scope' }}
                  </p>
                </div>
                <button class="terminal-button terminal-button-secondary" @click="resetSourceForm">Reset</button>
              </div>

              <div class="grid gap-3 sm:grid-cols-2">
                <label class="space-y-2 sm:col-span-2">
                  <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Scope name</span>
                  <input v-model="sourceForm.name" class="terminal-input" placeholder="Research repositories" />
                </label>
                <label class="space-y-2 sm:col-span-2">
                  <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Description</span>
                  <textarea v-model="sourceForm.description" class="terminal-textarea min-h-[90px]" />
                </label>
                <label class="space-y-2">
                  <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Kind</span>
                  <select v-model="sourceForm.kind" class="terminal-select">
                    <option value="public">Public</option>
                    <option value="research">Research</option>
                    <option value="custom">Custom</option>
                  </select>
                </label>
                <label class="space-y-2">
                  <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Language</span>
                  <select v-model="sourceForm.language" class="terminal-select">
                    <option value="">Any language</option>
                    <option v-for="language in availableLanguages" :key="language.code" :value="language.code">
                      {{ language.label }} ({{ language.code }})
                    </option>
                  </select>
                </label>
                <label class="space-y-2">
                  <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Safe search</span>
                  <select v-model="sourceForm.safeSearch" class="terminal-select">
                    <option value="0">Off</option>
                    <option value="1">Moderate</option>
                    <option value="2">Strict</option>
                  </select>
                </label>
                <label class="space-y-2">
                  <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Max results</span>
                  <input v-model="sourceForm.maxResults" class="terminal-input" type="number" min="1" max="20" />
                </label>
                <label class="space-y-2">
                  <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Time range</span>
                  <select v-model="sourceForm.timeRange" class="terminal-select">
                    <option value="auto">Auto from topic lookback</option>
                    <option value="any">No time filter</option>
                    <option value="day">Day</option>
                    <option value="month">Month</option>
                    <option value="year">Year</option>
                  </select>
                </label>
                <label class="space-y-2">
                  <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Result order</span>
                  <select v-model="sourceForm.resultOrder" class="terminal-select">
                    <option value="relevance">Relevance</option>
                    <option value="newest">Time (newest first)</option>
                  </select>
                </label>
                <label class="space-y-2">
                  <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Sort order</span>
                  <input v-model="sourceForm.sortOrder" class="terminal-input" type="number" min="0" />
                </label>
                <label class="space-y-2">
                  <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Enabled</span>
                  <select v-model="sourceForm.enabled" class="terminal-select">
                    <option :value="true">Enabled</option>
                    <option :value="false">Disabled</option>
                  </select>
                </label>
                <label class="space-y-2 sm:col-span-2">
                  <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Category coverage</span>
                  <select v-model="sourceForm.useAllCategories" class="terminal-select">
                    <option :value="true">All available SearxNG categories</option>
                    <option :value="false">Restrict to selected categories</option>
                  </select>
                </label>
                <div v-if="!sourceForm.useAllCategories" class="space-y-3 rounded-[1.3rem] border border-[var(--line)] bg-black/20 p-4 sm:col-span-2">
                  <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <p class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">
                      Selected categories: <span class="text-[var(--text)]">{{ sourceForm.searxngCategories.length }}</span>
                      / {{ availableCategories.length || '0' }}
                    </p>
                    <div class="flex flex-wrap gap-2">
                      <button type="button" class="terminal-button terminal-button-secondary" @click="selectAllSourceCategories">
                        Select all
                      </button>
                      <button type="button" class="terminal-button terminal-button-secondary" @click="clearSourceCategories">
                        Clear
                      </button>
                    </div>
                  </div>
                  <select
                    v-if="availableCategories.length"
                    v-model="sourceForm.searxngCategories"
                    class="terminal-select min-h-[220px]"
                    multiple
                  >
                    <option v-for="category in availableCategories" :key="`source-${category}`" :value="category">
                      {{ category }}
                    </option>
                  </select>
                  <p v-else class="text-sm text-[var(--muted)]">
                    No categories are advertised by the connected SearxNG instance right now.
                  </p>
                </div>
                <label class="space-y-2 sm:col-span-2">
                  <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Engine coverage</span>
                  <select v-model="sourceForm.useAllEngines" class="terminal-select">
                    <option :value="true">All available SearxNG engines</option>
                    <option :value="false">Restrict to specific engines</option>
                  </select>
                </label>
                <div v-if="!sourceForm.useAllEngines" class="space-y-3 rounded-[1.3rem] border border-[var(--line)] bg-black/20 p-4 sm:col-span-2">
                  <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <p class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">
                      Selected engines: <span class="text-[var(--text)]">{{ sourceForm.searxngEngines.length }}</span>
                      / {{ availableEngines.length || '0' }}
                    </p>
                    <div class="flex flex-wrap gap-2">
                      <button type="button" class="terminal-button terminal-button-secondary" @click="selectAllSourceEngines">
                        Select all
                      </button>
                      <button type="button" class="terminal-button terminal-button-secondary" @click="clearSourceEngines">
                        Clear
                      </button>
                    </div>
                  </div>
                  <select
                    v-if="availableEngines.length"
                    v-model="sourceForm.searxngEngines"
                    class="terminal-select min-h-[220px]"
                    multiple
                  >
                    <option v-for="engine in availableEngines" :key="`source-engine-${engine}`" :value="engine">
                      {{ engine }}
                    </option>
                  </select>
                  <p v-else class="text-sm text-[var(--muted)]">
                    No enabled engines are advertised by the connected SearxNG instance right now.
                  </p>
                </div>
                <label class="space-y-2 sm:col-span-2">
                  <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Include domains</span>
                  <textarea v-model="sourceForm.includeDomains" class="terminal-textarea min-h-[90px]" placeholder="zenodo.org&#10;figshare.com" />
                </label>
                <label class="space-y-2 sm:col-span-2">
                  <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Exclude domains</span>
                  <textarea v-model="sourceForm.excludeDomains" class="terminal-textarea min-h-[90px]" placeholder="x.com&#10;facebook.com" />
                </label>
              </div>

              <div class="flex flex-wrap gap-2">
                <button class="terminal-button terminal-button-primary" :disabled="isSavingSource" @click="saveSource">
                  {{ isSavingSource ? 'Saving source...' : sourceEditorMode === 'edit' ? 'Update source' : 'Create source' }}
                </button>
              </div>

              <div class="space-y-2 rounded-2xl border border-[var(--line)] bg-black/20 p-4">
                <p class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Current source scopes</p>
                <div
                  v-for="source in sources"
                  :key="source.id"
                  class="flex flex-col gap-3 rounded-2xl border border-[var(--line)] p-3 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div>
                    <p class="text-sm text-[var(--text)]">{{ source.name }}</p>
                    <p class="mt-1 text-xs text-[var(--muted)]">
                      {{ source.kind }} / {{ describeCategories(source) }} / {{ describeEngines(source) }} / {{ describeResultOrder(source) }}
                    </p>
                  </div>
                  <div class="flex flex-wrap gap-2">
                    <button class="terminal-button terminal-button-secondary" @click="openSourceEditor(source)">Edit</button>
                    <button class="terminal-button terminal-button-danger" @click="deleteSource(source)">Delete</button>
                  </div>
                </div>
              </div>
            </div>
          </section>
        </div>
      </section>

      <section v-else-if="authStore.isAuthenticated && activeWorkspace === 'runs'" class="space-y-5">
        <section class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <article class="terminal-panel relative overflow-hidden rounded-[1.4rem] p-5">
            <p class="text-xs uppercase tracking-[0.28em] text-[var(--muted)]">Tracked topics</p>
            <p class="mt-3 text-4xl text-white">{{ stats?.topic_count ?? 0 }}</p>
          </article>
          <article class="terminal-panel relative overflow-hidden rounded-[1.4rem] p-5">
            <p class="text-xs uppercase tracking-[0.28em] text-[var(--muted)]">Runs</p>
            <p class="mt-3 text-4xl text-white">{{ stats?.run_count ?? 0 }}</p>
          </article>
          <article class="terminal-panel relative overflow-hidden rounded-[1.4rem] p-5">
            <p class="text-xs uppercase tracking-[0.28em] text-[var(--muted)]">Success rate</p>
            <p class="mt-3 text-4xl text-white">{{ runSuccessRate }}%</p>
          </article>
          <article class="terminal-panel relative overflow-hidden rounded-[1.4rem] p-5">
            <p class="text-xs uppercase tracking-[0.28em] text-[var(--muted)]">Latest run</p>
            <p class="mt-3 text-lg text-white">{{ latestRun?.topic_name || 'No runs yet' }}</p>
            <p v-if="latestRun" class="mt-2 text-sm text-[var(--muted)]">{{ formatDate(latestRun.started_at) }}</p>
          </article>
        </section>

        <section class="grid gap-5 xl:grid-cols-[1.35fr_0.95fr]">
          <section class="terminal-panel relative overflow-hidden rounded-[1.5rem] p-5">
            <div class="relative z-10 space-y-4">
              <div class="flex flex-col gap-3 xl:flex-row xl:items-end xl:justify-between">
                <div>
                  <p class="mono-heading text-lg uppercase tracking-[0.22em] text-white">Run history</p>
                </div>
                <div class="flex flex-wrap gap-2">
                  <button class="terminal-button terminal-button-secondary" @click="clearRunFilters">Clear filters</button>
                </div>
              </div>

              <div class="grid gap-3 md:grid-cols-2">
                <label class="space-y-2">
                  <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Topic filter</span>
                  <select v-model="runFilters.topic" class="terminal-select">
                    <option value="">All topics</option>
                    <option v-for="topic in topics" :key="topic.slug" :value="topic.slug">{{ topic.name }}</option>
                  </select>
                </label>
                <label class="space-y-2">
                  <span class="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Status filter</span>
                  <select v-model="runFilters.status" class="terminal-select">
                    <option value="">All statuses</option>
                    <option value="running">Running</option>
                    <option value="succeeded">Succeeded</option>
                    <option value="failed">Failed</option>
                    <option value="limited">Limited</option>
                  </select>
                </label>
              </div>

              <p class="text-sm text-[var(--muted)]">
                Showing {{ runs.length }} of {{ runsPage?.count ?? 0 }} runs
                <span v-if="selectedRunTopic"> for {{ selectedRunTopic.name }}</span>
              </p>

              <div class="space-y-3">
                <article
                  v-for="run in runs"
                  :key="run.id"
                  class="rounded-2xl border border-[var(--line)] bg-black/25 p-4"
                >
                  <div class="flex items-start justify-between gap-3">
                    <div>
                      <p class="text-sm uppercase tracking-[0.18em] text-[var(--muted)]">{{ run.topic_name }}</p>
                      <p class="mt-2 text-lg" :class="statusClass(run.status)">{{ summarizeStatus(run.status) }}</p>
                    </div>
                    <span class="pill" :class="statusClass(run.status)">{{ run.status }}</span>
                  </div>

                  <div class="mt-4 grid gap-3 sm:grid-cols-3">
                    <div>
                      <p class="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">Requests</p>
                      <p class="mt-2 text-2xl text-white">{{ run.request_count }}</p>
                    </div>
                    <div>
                      <p class="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">New results</p>
                      <p class="mt-2 text-2xl text-white">{{ run.new_results_count }}</p>
                    </div>
                    <div>
                      <p class="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">Pages crawled</p>
                      <p class="mt-2 text-2xl text-white">{{ run.pages_crawled }}</p>
                    </div>
                  </div>

                  <div class="mt-4 space-y-2 text-sm text-[var(--muted)]">
                    <p>Started {{ formatDate(run.started_at) }}</p>
                    <p>Completed {{ formatDate(run.completed_at) }}</p>
                    <p v-if="run.error_message" class="text-[var(--warn)]">{{ run.error_message }}</p>
                  </div>
                </article>

                <article v-if="runs.length === 0" class="rounded-2xl border border-[var(--line)] bg-black/25 p-5 text-sm text-[var(--muted)]">
                  No runs captured yet. Trigger a topic or wait for its scheduled cadence to fire.
                </article>
              </div>
            </div>
          </section>

          <div class="space-y-5">
            <section class="terminal-panel relative overflow-hidden rounded-[1.5rem] p-5">
              <div class="relative z-10 space-y-4">
                <div>
                  <p class="mono-heading text-lg uppercase tracking-[0.22em] text-white">Topic pulse</p>
                </div>

                <div class="space-y-3">
                  <article
                    v-for="topic in topics"
                    :key="topic.slug"
                    class="rounded-2xl border border-[var(--line)] bg-black/25 p-4"
                  >
                    <div class="flex items-start justify-between gap-3">
                      <div>
                        <p class="text-sm text-white">{{ topic.name }}</p>
                        <p class="mt-2 text-xs text-[var(--muted)]">Checked {{ formatDate(topic.last_checked_at) }}</p>
                        <p class="mt-2 text-xs text-[var(--muted)]">{{ topic.schedule_description }} / next {{ formatNextRun(topic) }}</p>
                      </div>
                      <span class="pill" :class="statusClass(topic.last_run_status)">
                        {{ summarizeStatus(topic.last_run_status) }}
                      </span>
                    </div>

                    <div class="mt-4 grid gap-3 sm:grid-cols-3">
                      <div>
                        <p class="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">New</p>
                        <p class="mt-2 text-xl text-white">{{ topic.new_results_count }}</p>
                      </div>
                      <div>
                        <p class="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">Stored</p>
                        <p class="mt-2 text-xl text-white">{{ topic.result_count }}</p>
                      </div>
                      <div>
                        <p class="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">Sources</p>
                        <p class="mt-2 text-xl text-white">{{ topic.source_scopes.length }}</p>
                      </div>
                    </div>

                    <div class="mt-4 flex flex-wrap gap-2">
                      <button class="terminal-button terminal-button-primary" @click="focusTopicResults(topic)">Inspect</button>
                      <button class="terminal-button terminal-button-secondary" @click="activeWorkspace = 'configure'; openTopicEditor(topic)">Edit</button>
                    </div>
                  </article>
                </div>
              </div>
            </section>

            <section class="terminal-panel relative overflow-hidden rounded-[1.5rem] p-5">
              <div class="relative z-10 space-y-3">
                <div>
                  <p class="mono-heading text-lg uppercase tracking-[0.22em] text-white">Pipeline status</p>
                </div>

                <div class="rounded-2xl border border-[var(--line)] bg-black/20 p-4 text-sm text-[var(--muted)]">
                  <p>Provider: <span class="text-[var(--text)]">{{ provider?.name ?? 'searxng' }}</span></p>
                  <p class="mt-2">Enabled: <span class="text-[var(--text)]">{{ provider?.enabled ? 'yes' : 'no' }}</span></p>
                  <p class="mt-2">SearxNG: <span class="text-[var(--text)]">{{ provider?.searxng_base_url || 'n/a' }}</span></p>
                  <p class="mt-2">
                    Crawl4AI:
                    <span :class="provider?.crawl4ai_enabled ? 'text-[var(--accent)]' : 'text-[var(--danger)]'">
                      {{ provider?.crawl4ai_enabled ? 'enabled' : 'disabled' }}
                    </span>
                  </p>
                </div>
              </div>
            </section>
          </div>
        </section>
      </section>
      </template>
    </main>

  </div>
</template>
