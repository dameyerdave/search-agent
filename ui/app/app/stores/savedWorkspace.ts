import { getErrorMessage } from 'errors'
import type { PaginatedResponse, SavedFolder, SearchResult } from 'types/search-agent'

export const useSavedWorkspaceStore = defineStore('savedWorkspaceStore', () => {
  const api = useSearchAgentApi()
  const { t } = useI18n()
  const toast = useToast()

  const folders = ref<SavedFolder[]>([])
  const selectedFolderId = ref<number | 'unfiled' | null>(null)
  const folderResultsPage = ref<PaginatedResponse<SearchResult> | null>(null)
  const isLoadingFolders = ref(false)
  const isLoadingResults = ref(false)
  const editingFolderId = ref<number | null>(null)
  const editingFolderName = ref('')
  const newFolderName = ref('')
  const isCreatingFolder = ref(false)

  const folderResults = computed(() => folderResultsPage.value?.results ?? [])

  const selectedFolder = computed(() =>
    typeof selectedFolderId.value === 'number'
      ? folders.value.find((f) => f.id === selectedFolderId.value) ?? null
      : null,
  )

  const loadFolders = async () => {
    isLoadingFolders.value = true
    try {
      const data = await api.get<PaginatedResponse<SavedFolder>>('/api/v1/folders/')
      folders.value = data.results
    } catch (error: unknown) {
      toast.add({ title: getErrorMessage(error) || t('saved.errors.load_folders_failed'), color: 'error' })
    } finally {
      isLoadingFolders.value = false
    }
  }

  const loadFolderResults = async (folderId: number | 'unfiled' | null) => {
    selectedFolderId.value = folderId
    isLoadingResults.value = true
    try {
      const query: Record<string, string | number | boolean | undefined> =
        folderId === 'unfiled'
          ? { folder: 'unfiled' }
          : folderId !== null
            ? { folder: folderId, is_saved: true }
            : { is_saved: true }
      folderResultsPage.value = await api.get<PaginatedResponse<SearchResult>>('/api/v1/results/', query)
    } catch (error: unknown) {
      toast.add({ title: getErrorMessage(error) || t('saved.errors.load_results_failed'), color: 'error' })
    } finally {
      isLoadingResults.value = false
    }
  }

  const createFolder = async (name: string) => {
    const trimmed = name.trim()
    if (!trimmed) return null
    try {
      const folder = await api.post<SavedFolder>('/api/v1/folders/', { name: trimmed })
      folders.value = [...folders.value, folder].sort((a, b) =>
        a.name.localeCompare(b.name),
      )
      return folder
    } catch (error: unknown) {
      toast.add({ title: getErrorMessage(error) || t('saved.errors.create_folder_failed'), color: 'error' })
      return null
    }
  }

  const renameFolder = async (id: number, name: string) => {
    const trimmed = name.trim()
    if (!trimmed) return
    try {
      const updated = await api.patch<SavedFolder>(`/api/v1/folders/${id}/`, { name: trimmed })
      const idx = folders.value.findIndex((f) => f.id === id)
      if (idx !== -1) folders.value[idx] = updated
      editingFolderId.value = null
    } catch (error: unknown) {
      toast.add({ title: getErrorMessage(error) || t('saved.errors.rename_folder_failed'), color: 'error' })
    }
  }

  const deleteFolder = async (id: number) => {
    try {
      await api.delete(`/api/v1/folders/${id}/`)
      folders.value = folders.value.filter((f) => f.id !== id)
      if (selectedFolderId.value === id) {
        selectedFolderId.value = null
        folderResultsPage.value = null
      }
    } catch (error: unknown) {
      toast.add({ title: getErrorMessage(error) || t('saved.errors.delete_folder_failed'), color: 'error' })
    }
  }

  const moveResult = async (resultId: number, folderId: number | null, newFolderNameVal?: string) => {
    try {
      const body: Record<string, unknown> = {}
      if (newFolderNameVal) {
        body.folder_name = newFolderNameVal
      } else {
        body.folder_id = folderId
      }
      await api.post<SearchResult>(`/api/v1/results/${resultId}/move/`, body)
      // Remove result from current view if it moved to a different folder
      if (folderResultsPage.value) {
        folderResultsPage.value.results = folderResultsPage.value.results.filter(
          (r) => r.id !== resultId,
        )
      }
      await loadFolders()
    } catch (error: unknown) {
      toast.add({ title: getErrorMessage(error) || t('saved.errors.move_result_failed'), color: 'error' })
    }
  }

  const unsaveResult = async (resultId: number) => {
    try {
      await api.post(`/api/v1/results/${resultId}/unsave/`, {})
      if (folderResultsPage.value) {
        folderResultsPage.value.results = folderResultsPage.value.results.filter(
          (r) => r.id !== resultId,
        )
        folderResultsPage.value.count = Math.max(0, folderResultsPage.value.count - 1)
      }
      await loadFolders()
    } catch (error: unknown) {
      toast.add({ title: getErrorMessage(error) || t('saved.errors.unsave_result_failed'), color: 'error' })
    }
  }

  const suggestFolderName = (result: SearchResult): string => {
    if (!folders.value.length) return result.topic_name || result.domain || ''
    const candidates = [
      result.topic_name?.toLowerCase(),
      result.domain?.toLowerCase(),
      ...(result.matched_queries || []).map((q) => q.toLowerCase()),
    ].filter(Boolean) as string[]

    let best: SavedFolder | null = null
    let bestScore = 0
    for (const folder of folders.value) {
      const fl = folder.name.toLowerCase()
      let score = 0
      for (const c of candidates) {
        if (c.includes(fl) || fl.includes(c)) score++
      }
      if (score > bestScore) {
        bestScore = score
        best = folder
      }
    }
    return best ? best.name : result.topic_name || result.domain || ''
  }

  const startEditFolder = (folder: SavedFolder) => {
    editingFolderId.value = folder.id
    editingFolderName.value = folder.name
  }

  const cancelEditFolder = () => {
    editingFolderId.value = null
    editingFolderName.value = ''
  }

  const resetState = () => {
    folders.value = []
    folderResultsPage.value = null
    selectedFolderId.value = null
  }

  return {
    folders,
    selectedFolderId,
    folderResults,
    folderResultsPage,
    selectedFolder,
    isLoadingFolders,
    isLoadingResults,
    editingFolderId,
    editingFolderName,
    newFolderName,
    isCreatingFolder,
    loadFolders,
    loadFolderResults,
    createFolder,
    renameFolder,
    deleteFolder,
    moveResult,
    unsaveResult,
    suggestFolderName,
    startEditFolder,
    cancelEditFolder,
    resetState,
  }
})
