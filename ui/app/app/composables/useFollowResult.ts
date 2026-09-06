import { getErrorMessage } from 'errors'
import type { SearchResult } from 'types/search-agent'

export const useFollowResult = () => {
  const api = useSearchAgentApi()
  const { t } = useI18n()
  const toast = useToast()

  const isFollowing = ref(false)

  const followResult = async (result: SearchResult) => {
    isFollowing.value = true
    try {
      await api.post(`/api/v1/results/${result.id}/follow/`, {})
      toast.add({ title: t('results.follow.success'), color: 'success' })
      await useDashboardStore().refreshAll()
    } catch (error: unknown) {
      toast.add({ title: getErrorMessage(error) || t('results.follow.error'), color: 'error' })
    } finally {
      isFollowing.value = false
    }
  }

  return { followResult, isFollowing }
}
