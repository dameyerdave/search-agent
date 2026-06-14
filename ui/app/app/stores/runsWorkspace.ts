import type { PaginatedResponse, SearchRun } from 'types/search-agent'

export const useRunsWorkspaceStore = defineStore('runsWorkspaceStore', () => {
  const api = useSearchAgentApi()
  const dashboardStore = useDashboardStore()

  const runsPage = ref<PaginatedResponse<SearchRun> | null>(null)

  const runFilters = reactive({
    topic: '',
    status: '',
  })

  const runs = computed(() => runsPage.value?.results ?? [])

  const selectedRunTopic = computed(
    () => dashboardStore.topics.find((topic) => topic.slug === runFilters.topic) ?? null,
  )

  const latestRun = computed(() => runs.value[0] ?? null)

  const runSuccessRate = computed(() => {
    const totalRuns = dashboardStore.stats?.run_count ?? 0
    if (!totalRuns) return 0
    return Math.round(((dashboardStore.stats?.successful_run_count ?? 0) / totalRuns) * 100)
  })

  const loadRuns = async () => {
    const query: Record<string, string | undefined> = {
      topic: runFilters.topic || undefined,
      status: runFilters.status || undefined,
    }

    runsPage.value = await api.get<PaginatedResponse<SearchRun>>('/api/v1/runs/', query)
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
    selectedRunTopic,
    latestRun,
    runSuccessRate,
    loadRuns,
    clearRunFilters,
    resetRunsState,
  }
})
