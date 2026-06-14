import { getErrorMessage } from 'errors'
import type { SearchTopic, SourceScope } from 'types/search-agent'
import { joinLines, normalizeLanguageCodes, splitLines } from 'utils/dashboard'

export const useConfigureWorkspaceStore = defineStore('configureWorkspaceStore', () => {
  const api = useSearchAgentApi()
  const { t } = useI18n()
  const toast = useToast()
  const dashboardStore = useDashboardStore()

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
    languages: [] as string[],
    safeSearch: '0',
    timeRange: 'auto',
    resultOrder: 'relevance' as 'relevance' | 'newest',
    maxResults: 10,
    includeDomains: '',
    excludeDomains: '',
    sortOrder: 10,
  })

  const topicForm = reactive(emptyTopicForm())
  const sourceForm = reactive(emptySourceForm())

  const topicEditorMode = ref<'create' | 'edit'>('create')
  const sourceEditorMode = ref<'create' | 'edit'>('create')
  const editingTopicSlug = ref<string | null>(null)
  const editingSourceId = ref<number | null>(null)
  const isSavingTopic = ref(false)
  const isSavingSource = ref(false)

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
      languages: normalizeLanguageCodes(source.languages, dashboardStore.availableLanguages),
      safeSearch: String(source.safe_search),
      timeRange: source.time_range,
      resultOrder: source.result_order,
      maxResults: source.max_results,
      includeDomains: joinLines(source.include_domains),
      excludeDomains: joinLines(source.exclude_domains),
      sortOrder: source.sort_order,
    })
  }

  const toggleTopicSource = (sourceId: number) => {
    if (topicForm.sourceScopeIds.includes(sourceId)) {
      topicForm.sourceScopeIds = topicForm.sourceScopeIds.filter((id) => id !== sourceId)
    } else {
      topicForm.sourceScopeIds = [...topicForm.sourceScopeIds, sourceId]
    }
  }

  const selectAllSourceCategories = () => {
    sourceForm.searxngCategories = [...dashboardStore.availableCategories]
  }

  const clearSourceCategories = () => {
    sourceForm.searxngCategories = []
  }

  const selectAllSourceEngines = () => {
    sourceForm.searxngEngines = [...dashboardStore.availableEngines]
  }

  const clearSourceEngines = () => {
    sourceForm.searxngEngines = []
  }

  const selectAllSourceLanguages = () => {
    sourceForm.languages = dashboardStore.availableLanguages.map((language) => language.code)
  }

  const clearSourceLanguages = () => {
    sourceForm.languages = []
  }

  const saveTopic = async () => {
    isSavingTopic.value = true
    dashboardStore.setBusy(
      topicEditorMode.value === 'edit' ? 'dashboard.busy.updating_topic' : 'dashboard.busy.creating_topic',
    )

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
      await dashboardStore.refreshAll()
      toast.add({ title: t('dashboard.success.topic_saved'), color: 'success' })
    } catch (error: unknown) {
      toast.add({ title: getErrorMessage(error) || t('dashboard.errors.topic_save_failed'), color: 'error' })
    } finally {
      isSavingTopic.value = false
    }
  }

  const saveSource = async () => {
    isSavingSource.value = true
    dashboardStore.setBusy(
      sourceEditorMode.value === 'edit' ? 'dashboard.busy.updating_source' : 'dashboard.busy.creating_source',
    )

    const payload = {
      name: sourceForm.name.trim(),
      description: sourceForm.description.trim(),
      kind: sourceForm.kind,
      enabled: sourceForm.enabled,
      searxng_categories: sourceForm.useAllCategories ? [] : sourceForm.searxngCategories,
      use_all_categories: sourceForm.useAllCategories,
      use_all_engines: sourceForm.useAllEngines,
      searxng_engines: sourceForm.useAllEngines ? [] : sourceForm.searxngEngines,
      languages: normalizeLanguageCodes(sourceForm.languages, dashboardStore.availableLanguages),
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
      await dashboardStore.refreshAll()
      toast.add({ title: t('dashboard.success.source_saved'), color: 'success' })
    } catch (error: unknown) {
      toast.add({ title: getErrorMessage(error) || t('dashboard.errors.source_save_failed'), color: 'error' })
    } finally {
      isSavingSource.value = false
    }
  }

  const deleteSource = async (source: SourceScope) => {
    if (!window.confirm(t('dashboard.errors.confirm_delete_source', { name: source.name }))) return
    dashboardStore.setBusy('dashboard.busy.deleting_source', { name: source.name })

    try {
      await api.delete(`/api/v1/source-scopes/${source.id}/`)
      if (editingSourceId.value === source.id) {
        resetSourceForm()
      }
      await dashboardStore.refreshAll()
      toast.add({ title: t('dashboard.success.source_deleted'), color: 'success' })
    } catch (error: unknown) {
      toast.add({ title: getErrorMessage(error) || t('dashboard.errors.source_delete_failed'), color: 'error' })
    }
  }

  return {
    topicForm,
    sourceForm,
    topicEditorMode,
    sourceEditorMode,
    editingTopicSlug,
    editingSourceId,
    isSavingTopic,
    isSavingSource,
    resetTopicForm,
    resetSourceForm,
    openTopicEditor,
    openSourceEditor,
    toggleTopicSource,
    selectAllSourceCategories,
    clearSourceCategories,
    selectAllSourceEngines,
    clearSourceEngines,
    selectAllSourceLanguages,
    clearSourceLanguages,
    saveTopic,
    saveSource,
    deleteSource,
  }
})
