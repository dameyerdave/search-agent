export interface LanguageOption {
  code: string
  label: string
}

export interface SourceScope {
  id: number
  name: string
  description: string
  kind: 'public' | 'research' | 'custom'
  enabled: boolean
  searxng_categories: string[]
  use_all_categories: boolean
  use_all_engines: boolean
  searxng_engines: string[]
  languages: string[]
  safe_search: number
  time_range: 'auto' | 'any' | 'day' | 'month' | 'year'
  result_order: 'relevance' | 'newest'
  max_results: number
  include_domains: string[]
  exclude_domains: string[]
  sort_order: number
  created_at: string
  updated_at: string
}

export interface SearchTopic {
  id: number
  name: string
  slug: string
  description: string
  enabled: boolean
  queries: string[]
  required_terms: string[]
  excluded_terms: string[]
  lookback_days: number
  schedule_every: number
  schedule_unit: 'minutes' | 'hours' | 'days' | 'weeks'
  max_results_per_query: number
  notes: string
  source_scopes: SourceScope[]
  result_count: number
  new_results_count: number
  next_run_at: string | null
  last_checked_at: string | null
  last_success_at: string | null
  last_new_results_at: string | null
  last_run_status: 'idle' | 'running' | 'succeeded' | 'failed' | 'limited'
  query_preview: string[]
  schedule_description: string
  created_at: string
  updated_at: string
}

export interface ProviderConfig {
  id: number
  name: string
  enabled: boolean
  searxng_base_url: string
  crawl4ai_enabled: boolean
  available_categories: string[]
  available_engines: string[]
  available_languages: LanguageOption[]
  created_at: string
  updated_at: string
}

export interface AuthenticatedUser {
  pk: number
  username: string
  email: string
  first_name: string
  last_name: string
}

export interface CloudflareAccessUrls {
  login_url: string | null
  logout_url: string | null
}

export interface AuthenticatedUserResponse {
  authenticated: boolean
  user: AuthenticatedUser | null
  cloudflare_access: CloudflareAccessUrls
}

export interface SearchRun {
  id: number
  topic: number
  topic_name: string
  status: 'running' | 'succeeded' | 'failed' | 'limited'
  started_at: string
  completed_at: string | null
  source_scope_count: number
  request_count: number
  pages_crawled: number
  results_collected: number
  new_results_count: number
  query_snapshot: Array<Record<string, unknown>>
  error_message: string
  created_at: string
  updated_at: string
}

export interface SearchResult {
  id: number
  topic: number
  topic_name: string
  source_scope: number | null
  source_scope_name: string | null
  last_run: number | null
  title: string
  url: string
  domain: string
  snippet: string
  content: string
  favicon_url: string
  score: number | null
  published_at: string | null
  matched_queries: string[]
  first_seen_at: string
  last_seen_at: string
  is_new: boolean
  is_saved: boolean
  saved_title: string
  created_at: string
  updated_at: string
}

export interface SearchResultMapPreview {
  id: number
  title: string
  url: string
  topic_name: string
  source_scope_name: string | null
  domain: string
  published_at: string | null
  is_new: boolean
}

export interface SearchResultMapMarker {
  id: string
  name: string
  display_name: string
  latitude: number
  longitude: number
  place_type: string
  related_result_count: number
  remaining_result_count: number
  results: SearchResultMapPreview[]
}

export interface SearchResultMapResponse {
  result_count: number
  mapped_result_count: number
  location_count: number
  markers: SearchResultMapMarker[]
}

export interface LiveSearxResult {
  position: number
  title: string
  url: string
  domain: string
  snippet: string
  engine: string
  engines: string[]
  published_at: string | null
  score: number | null
  category: string
  thumbnail: string
  raw_result: Record<string, unknown>
}

export interface LiveSearxResponse {
  query: string
  params: Record<string, string | number>
  result_order: 'relevance' | 'newest'
  result_count: number
  number_of_results: number | null
  suggestions: string[]
  answers: string[]
  corrections: string[]
  infoboxes: Array<Record<string, unknown>>
  unresponsive_engines: string[]
  results: LiveSearxResult[]
}

export interface DashboardStats {
  topic_count: number
  enabled_topic_count: number
  source_count: number
  result_count: number
  new_result_count: number
  run_count: number
  successful_run_count: number
}

export interface DashboardPayload {
  provider: ProviderConfig
  stats: DashboardStats
  topics: SearchTopic[]
  sources: SourceScope[]
  recent_results: SearchResult[]
  recent_runs: SearchRun[]
}

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}
