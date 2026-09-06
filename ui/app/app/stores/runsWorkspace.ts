import type { PaginatedResponse, SearchRun } from 'types/search-agent'

const MAX_AUTO_LOAD_RUNS = 150

export const useRunsWorkspaceStore = defineStore('runsWorkspaceStore', () => {
  const api = useSearchAgentApi()
  const dashboardStore = useDashboardStore()

  const runsPage = ref<PaginatedResponse<SearchRun> | null>(null)
  const accumulatedRuns = ref<SearchRun[]>([])
  const currentRunPage = ref(1)
  const isLoadingMoreRuns = ref(false)

  const runFilters = reactive({
    topic: '',
    status: '',
  })

  const runs = computed(() => accumulatedRuns.value)
  const canLoadMoreRuns = computed(() => Boolean(runsPage.value?.next))
  const autoLoadCapReachedRuns = computed(() => accumulatedRuns.value.length >= MAX_AUTO_LOAD_RUNS)

  const selectedRunTopic = computed(
    () => dashboardStore.topics.find((topic) => topic.slug === runFilters.topic) ?? null,
  )

  const latestRun = computed(() => runs.value[0] ?? null)

  const runSuccessRate = computed(() => {
    const totalRuns = dashboardStore.stats?.run_count ?? 0
    if (!totalRuns) return 0
    return Math.round(((dashboardStore.stats?.successful_run_count ?? 0) / totalRuns) * 100)
  })

  const loadRuns = async (page = 1, append = false) => {
    if (append) isLoadingMoreRuns.value = true
    const query: Record<string, string | number | undefined> = {
      topic: runFilters.topic || undefined,
      status: runFilters.status || undefined,
      page,
    }

    try {
      const response = await api.get<PaginatedResponse<SearchRun>>('/api/v1/runs/', query)
      runsPage.value = response
      currentRunPage.value = page
      if (append) {
        const existingIds = new Set(accumulatedRuns.value.map((r) => r.id))
        accumulatedRuns.value = [...accumulatedRuns.value, ...response.results.filter((r) => !existingIds.has(r.id))]
      } else {
        accumulatedRuns.value = response.results
      }
    } finally {
      isLoadingMoreRuns.value = false
    }
  }

  const loadMoreRuns = async () => {
    if (!canLoadMoreRuns.value || isLoadingMoreRuns.value) return
    await loadRuns(currentRunPage.value + 1, true)
  }

  const clearRunFilters = async () => {
    const hadFilters = Boolean(runFilters.topic || runFilters.status)
    runFilters.topic = ''
    runFilters.status = ''
    if (!hadFilters) {
      await loadRuns()
    }
  }

  const resetRunsState = () => {
    runsPage.value = null
    accumulatedRuns.value = []
    currentRunPage.value = 1
  }

  const debouncedRunsReload = useDebounceFn(async () => {
    await loadRuns()
  }, 250)

  watch(
    () => [runFilters.topic, runFilters.status],
    () => {
      debouncedRunsReload()
    },
  )

  return {
    runFilters,
    runsPage,
    runs,
    canLoadMoreRuns,
    autoLoadCapReachedRuns,
    isLoadingMoreRuns,
    selectedRunTopic,
    latestRun,
    runSuccessRate,
    loadRuns,
    loadMoreRuns,
    clearRunFilters,
    resetRunsState,
  }
})
