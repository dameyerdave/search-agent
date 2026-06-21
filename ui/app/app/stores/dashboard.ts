import { getErrorMessage } from 'errors'
import type { DashboardPayload, ProviderConfig, SearchTopic } from 'types/search-agent'

export const useDashboardStore = defineStore('dashboardStore', () => {
  const api = useSearchAgentApi()
  const authStore = useAuthStore()
  const { t } = useI18n()
  const toast = useToast()

  const dashboard = ref<DashboardPayload | null>(null)
  const busyLabel = ref(t('dashboard.busy.booting'))
  const errorMessage = ref('')
  const isBootstrappingAuth = ref(true)
  const isLoadingDashboard = ref(false)
  const isSavingProvider = ref(false)
  const activeWorkspace = ref<'search' | 'explore' | 'configure' | 'runs'>('search')
  const activeTopicRun = ref<string | null>(null)
  const activeTopicAcknowledge = ref<string | null>(null)

  const providerForm = reactive({
    id: 0,
    enabled: true,
  })

  const topics = computed(() => dashboard.value?.topics ?? [])
  const sources = computed(() => dashboard.value?.sources ?? [])
  const enabledSources = computed(() => sources.value.filter((source) => source.enabled))
  const provider = computed(() => dashboard.value?.provider ?? null)
  const availableCategories = computed(() => provider.value?.available_categories ?? [])
  const availableEngines = computed(() => provider.value?.available_engines ?? [])
  const availableLanguages = computed(() => provider.value?.available_languages ?? [])
  const stats = computed(() => dashboard.value?.stats ?? null)
  const hasProviderIssue = computed(
    () => !!provider.value && (!provider.value.searxng_base_url || !provider.value.crawl4ai_enabled),
  )

  const workspaceTabs = [
    { key: 'search', labelKey: 'dashboard.nav.search.label' },
    { key: 'explore', labelKey: 'dashboard.nav.explore.label' },
    { key: 'configure', labelKey: 'dashboard.nav.configure.label' },
    { key: 'runs', labelKey: 'dashboard.nav.runs.label' },
  ] as const

  const visibleWorkspaceTabs = computed(() =>
    authStore.isAuthenticated ? workspaceTabs : workspaceTabs.filter((tab) => tab.key === 'search'),
  )

  const currentUserLabel = computed(() => {
    const firstName = authStore.user?.first_name?.trim()
    const lastName = authStore.user?.last_name?.trim()
    const fullName = [firstName, lastName].filter(Boolean).join(' ').trim()
    return fullName || authStore.user?.username || authStore.user?.email || t('dashboard.common.operator')
  })

  const setBusy = (key: string, params?: Record<string, unknown>) => {
    busyLabel.value = t(key, params ?? {})
    errorMessage.value = ''
  }

  const hydrateProviderForm = (config: ProviderConfig | null) => {
    providerForm.id = config?.id ?? 0
    providerForm.enabled = config?.enabled ?? true
  }

  const loadDashboard = async () => {
    isLoadingDashboard.value = true
    setBusy('dashboard.busy.refreshing')

    try {
      const payload = await api.get<DashboardPayload>('/api/v1/dashboard/')
      dashboard.value = payload
      hydrateProviderForm(payload.provider)
    } catch (error: unknown) {
      errorMessage.value = getErrorMessage(error) || t('dashboard.errors.dashboard_refresh_failed')
    } finally {
      isLoadingDashboard.value = false
    }
  }

  const refreshAll = async () => {
    try {
      const exploreStore = useExploreWorkspaceStore()
      const runsStore = useRunsWorkspaceStore()
      await Promise.all([
        loadDashboard(),
        exploreStore.loadResults(exploreStore.resultFilters.page),
        runsStore.loadRuns(),
      ])
    } catch (error: unknown) {
      errorMessage.value = getErrorMessage(error) || t('dashboard.errors.refresh_failed')
    } finally {
      busyLabel.value = t('dashboard.busy.online')
    }
  }

  const resetDashboardState = () => {
    dashboard.value = null
    useExploreWorkspaceStore().resetResultsState()
    useRunsWorkspaceStore().resetRunsState()
    busyLabel.value = t('dashboard.busy.awaiting_identity')
    errorMessage.value = ''
  }

  const saveProvider = async () => {
    if (!providerForm.id) return
    isSavingProvider.value = true
    setBusy('dashboard.busy.saving_provider')

    try {
      await api.patch(`/api/v1/provider-config/${providerForm.id}/`, {
        enabled: providerForm.enabled,
      })
      await refreshAll()
      toast.add({ title: t('dashboard.success.provider_saved'), color: 'success' })
    } catch (error: unknown) {
      toast.add({ title: getErrorMessage(error) || t('dashboard.errors.provider_update_failed'), color: 'error' })
    } finally {
      isSavingProvider.value = false
    }
  }

  const runTopic = async (topic: SearchTopic) => {
    activeTopicRun.value = topic.slug
    setBusy('dashboard.busy.running_topic', { name: topic.name })
    try {
      await api.post(`/api/v1/topics/${topic.slug}/run_now/`, {})
      await refreshAll()
      toast.add({ title: t('dashboard.success.topic_run_started', { name: topic.name }), color: 'success' })
    } catch (error: unknown) {
      toast.add({ title: getErrorMessage(error) || t('dashboard.errors.topic_run_failed'), color: 'error' })
    } finally {
      activeTopicRun.value = null
    }
  }

  const acknowledgeTopic = async (topic: SearchTopic) => {
    activeTopicAcknowledge.value = topic.slug
    setBusy('dashboard.busy.acknowledging_topic', { name: topic.name })
    try {
      await api.post(`/api/v1/topics/${topic.slug}/acknowledge/`, {})
      await refreshAll()
      toast.add({ title: t('dashboard.success.topic_acknowledged', { name: topic.name }), color: 'success' })
    } catch (error: unknown) {
      toast.add({ title: getErrorMessage(error) || t('dashboard.errors.acknowledge_failed'), color: 'error' })
    } finally {
      activeTopicAcknowledge.value = null
    }
  }

  const deleteTopic = async (topic: SearchTopic) => {
    if (!window.confirm(t('dashboard.errors.confirm_delete_topic', { name: topic.name }))) return
    setBusy('dashboard.busy.deleting_topic', { name: topic.name })

    try {
      await api.delete(`/api/v1/topics/${topic.slug}/`)
      const configureStore = useConfigureWorkspaceStore()
      if (configureStore.editingTopicSlug === topic.slug) {
        configureStore.resetTopicForm()
      }
      await refreshAll()
      toast.add({ title: t('dashboard.success.topic_deleted'), color: 'success' })
    } catch (error: unknown) {
      toast.add({ title: getErrorMessage(error) || t('dashboard.errors.topic_delete_failed'), color: 'error' })
    }
  }

  const focusTopicResults = async (topic: SearchTopic) => {
    const exploreStore = useExploreWorkspaceStore()
    activeWorkspace.value = 'explore'
    const topicChanged = exploreStore.resultFilters.topic !== topic.slug
    exploreStore.resultFilters.topic = topic.slug
    exploreStore.resultFilters.page = 1
    if (!topicChanged) {
      await exploreStore.loadResults(1)
    }
  }

  const editTopicInConfigure = (topic: SearchTopic) => {
    activeWorkspace.value = 'configure'
    useConfigureWorkspaceStore().openTopicEditor(topic)
  }

  const handleLogout = async () => {
    await authStore.logout()
    resetDashboardState()
    activeWorkspace.value = 'search'
    useSearchWorkspaceStore().closeLiveSearchSaveDialog()
  }

  const bootstrap = async () => {
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
  }

  watch(
    () => authStore.isAuthenticated,
    (isAuthenticated) => {
      if (!isAuthenticated) {
        activeWorkspace.value = 'search'
        useSearchWorkspaceStore().closeLiveSearchSaveDialog()
      }
    },
  )

  return {
    dashboard,
    busyLabel,
    errorMessage,
    isBootstrappingAuth,
    isLoadingDashboard,
    isSavingProvider,
    activeWorkspace,
    activeTopicRun,
    activeTopicAcknowledge,
    providerForm,
    topics,
    sources,
    enabledSources,
    provider,
    availableCategories,
    availableEngines,
    availableLanguages,
    stats,
    hasProviderIssue,
    workspaceTabs,
    visibleWorkspaceTabs,
    currentUserLabel,
    setBusy,
    loadDashboard,
    refreshAll,
    resetDashboardState,
    saveProvider,
    runTopic,
    acknowledgeTopic,
    deleteTopic,
    focusTopicResults,
    editTopicInConfigure,
    handleLogout,
    bootstrap,
  }
})
