import type { LanguageOption, LiveSearxResponse, SearchTopic, SourceScope } from 'types/search-agent'

const dateFormatter = new Intl.DateTimeFormat('en-CH', {
  dateStyle: 'medium',
  timeStyle: 'short',
})

export const formatDate = (value: string | null): string | null => {
  if (!value) {
    return null
  }

  try {
    return dateFormatter.format(new Date(value))
  } catch {
    return value
  }
}

export type StatusSummary = 'stable' | 'limited' | 'fault' | 'running' | 'idle'

export const summarizeStatus = (status: string): StatusSummary => {
  if (status === 'succeeded') return 'stable'
  if (status === 'limited') return 'limited'
  if (status === 'failed') return 'fault'
  if (status === 'running') return 'running'
  return 'idle'
}

export const statusClass = (status: string): string => {
  if (status === 'succeeded') return 'text-[#c8ffd9]'
  if (status === 'limited') return 'text-[var(--warn)]'
  if (status === 'failed') return 'text-[var(--danger)]'
  if (status === 'running') return 'text-[var(--accent)]'
  return 'text-[var(--muted)]'
}

export type CoverageDescription = { kind: 'all' | 'list' | 'none'; values: string[] }

export const describeCategories = (source: SourceScope): CoverageDescription => {
  if (source.use_all_categories) return { kind: 'all', values: [] }
  if (source.searxng_categories.length) return { kind: 'list', values: source.searxng_categories }
  return { kind: 'none', values: [] }
}

export const describeEngines = (source: SourceScope): CoverageDescription => {
  if (source.use_all_engines) return { kind: 'all', values: [] }
  if (source.searxng_engines.length) return { kind: 'list', values: source.searxng_engines }
  return { kind: 'none', values: [] }
}

export const describeResultOrder = (source: SourceScope): 'newest' | 'relevance' =>
  source.result_order === 'newest' ? 'newest' : 'relevance'

export type NextRun = { paused: boolean; date: string | null }

export const formatNextRun = (topic: SearchTopic): NextRun => {
  if (!topic.enabled) {
    return { paused: true, date: null }
  }
  return { paused: false, date: topic.next_run_at }
}

export const cleanSearchLabel = (value: string): string => value.replace(/["']/g, '').replace(/\s+/g, ' ').trim()

export const splitLines = (value: string): string[] =>
  value
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)

export const splitTokens = (value: string): string[] =>
  value
    .split(/[\n,]/)
    .map((entry) => entry.trim())
    .filter(Boolean)

export const joinLines = (value: string[]): string => value.join('\n')

export const deriveLookbackDays = (timeRange: string): number => {
  if (timeRange === 'day') return 1
  if (timeRange === 'month') return 30
  if (timeRange === 'year') return 365
  return 30
}

export const parseExtraParams = (value: string): Record<string, string> => {
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

export const sortLiveSearchResults = (
  results: LiveSearxResponse['results'],
  resultOrder: 'relevance' | 'newest',
): LiveSearxResponse['results'] => {
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

      return resolveScore(right.score) - resolveScore(left.score)
    })
  }

  return [...results].sort((left, right) => resolveScore(right.score) - resolveScore(left.score))
}

export const normalizeLanguageCode = (value: string, availableLanguages: LanguageOption[]): string => {
  const trimmed = value.trim()
  if (!trimmed) {
    return ''
  }

  const exact = availableLanguages.find((option) => option.code === trimmed)
  if (exact) {
    return exact.code
  }

  const dashed = trimmed.replace(/_/g, '-')
  const normalized = availableLanguages.find((option) => option.code.toLowerCase() === dashed.toLowerCase())
  if (normalized) {
    return normalized.code
  }

  const baseLanguage = dashed.split('-', 1)[0] ?? dashed
  const baseMatch = availableLanguages.find((option) => option.code.toLowerCase() === baseLanguage.toLowerCase())
  if (baseMatch) {
    return baseMatch.code
  }

  return trimmed
}
