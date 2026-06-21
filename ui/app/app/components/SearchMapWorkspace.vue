<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import type { SearchResultMapMarker, SearchResultMapResponse } from 'types/search-agent'

const props = defineProps<{
  topicSlug: string
  topicName: string
  q?: string
  kind?: string
  isNewOnly?: boolean
}>()

const { t } = useI18n()
const api = useSearchAgentApi()

const debouncedQueryText = ref('')
const selectedMarkerId = ref<string | null>(null)
const hasSelectedTopic = computed(() => Boolean(props.topicSlug))

const syncDebouncedText = useDebounceFn((value: string) => {
  debouncedQueryText.value = value.trim()
}, 250)

watch(
  () => props.q ?? '',
  (value) => {
    syncDebouncedText(value)
  },
  { immediate: true },
)

const mapQuery = useQuery({
  queryKey: computed(() => [
    'search-result-map',
    props.topicSlug,
    debouncedQueryText.value,
    props.kind ?? '',
    Boolean(props.isNewOnly),
  ]),
  queryFn: async () => {
    if (!props.topicSlug) {
      return {
        result_count: 0,
        mapped_result_count: 0,
        location_count: 0,
        markers: [],
      }
    }

    return api.get<SearchResultMapResponse>('/api/v1/results/map/', {
      q: debouncedQueryText.value || undefined,
      topic: props.topicSlug,
      kind: props.kind || undefined,
      is_new: props.isNewOnly ? true : undefined,
    })
  },
})

const markers = computed(() => mapQuery.data.value?.markers ?? [])
const selectedMarker = computed<SearchResultMapMarker | null>(
  () => markers.value.find((marker) => marker.id === selectedMarkerId.value) ?? null,
)

watch(
  markers,
  (nextMarkers) => {
    if (!nextMarkers.length) {
      selectedMarkerId.value = null
      return
    }
    if (!selectedMarkerId.value || !nextMarkers.some((marker) => marker.id === selectedMarkerId.value)) {
      selectedMarkerId.value = nextMarkers[0].id
    }
  },
  { immediate: true },
)

const dateFormatter = new Intl.DateTimeFormat('en-CH', {
  dateStyle: 'medium',
  timeStyle: 'short',
})

const formatDate = (value: string | null) => {
  if (!value) {
    return t('map.results.never')
  }

  try {
    return dateFormatter.format(new Date(value))
  } catch {
    return value
  }
}

const mapEmptyLabel = computed(() => (hasSelectedTopic.value ? t('map.empty_topic_map') : t('map.select_topic_prompt')))
</script>

<template>
  <section class="grid gap-5 2xl:grid-cols-[1.35fr_0.95fr]">
    <section class="terminal-panel relative overflow-hidden rounded-[1.5rem] p-5">
      <div class="relative z-10 space-y-5">
        <div class="flex flex-col gap-3 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <p class="mono-heading text-lg tracking-[0.22em] text-white uppercase">
              {{ t('map.title') }}
            </p>
            <p class="mt-2 text-sm text-[var(--muted)]">
              {{
                hasSelectedTopic ? t('map.subtitle_topic', { topic: props.topicName }) : t('map.select_topic_prompt')
              }}
            </p>
          </div>

          <div class="flex flex-wrap gap-2">
            <button
              class="terminal-button terminal-button-secondary"
              :disabled="!hasSelectedTopic"
              @click="mapQuery.refetch()"
            >
              {{ t('map.controls.refresh') }}
            </button>
          </div>
        </div>

        <SearchResultsMap
          :markers="markers"
          :selected-marker-id="selectedMarkerId"
          :empty-label="mapEmptyLabel"
          @select="selectedMarkerId = $event"
        />
      </div>
    </section>

    <div class="min-w-0 space-y-5">
      <section class="terminal-panel relative overflow-hidden rounded-[1.5rem] p-5">
        <div class="relative z-10 space-y-4">
          <div>
            <p class="mono-heading text-lg tracking-[0.22em] text-white uppercase">
              {{ selectedMarker ? selectedMarker.name : t('map.selection.title') }}
            </p>
            <p class="mt-2 text-sm text-[var(--muted)]">
              {{ selectedMarker ? selectedMarker.display_name : t('map.selection.placeholder') }}
            </p>
          </div>

          <template v-if="selectedMarker">
            <div class="rounded-2xl border border-[var(--line)] bg-black/20 p-4">
              <p class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
                {{ t('map.selection.related') }}
              </p>
              <p class="mt-3 text-3xl text-white">{{ selectedMarker.related_result_count }}</p>
              <p v-if="selectedMarker.remaining_result_count" class="mt-2 text-sm text-[var(--muted)]">
                {{ t('map.selection.more_results', { count: selectedMarker.remaining_result_count }) }}
              </p>
            </div>

            <div class="space-y-3">
              <article
                v-for="result in selectedMarker.results"
                :key="result.id"
                class="rounded-2xl border border-[var(--line)] bg-black/25 p-4"
              >
                <div class="flex flex-wrap items-center gap-2">
                  <span v-if="result.is_new" class="pill bg-[var(--accent-soft)] text-[var(--accent)]">
                    {{ t('map.results.new') }}
                  </span>
                  <span class="text-xs tracking-[0.18em] text-[var(--muted)] uppercase">
                    {{ result.topic_name }}
                  </span>
                </div>
                <a
                  :href="result.url"
                  target="_blank"
                  rel="noreferrer"
                  class="mt-3 block text-base leading-7 text-white hover:text-[var(--accent)]"
                >
                  {{ result.title }}
                </a>
                <p class="mt-2 text-sm text-[var(--muted)]">
                  {{ result.domain || t('map.results.unknown_domain') }}
                </p>
                <p class="mt-2 text-xs text-[var(--muted)]">
                  {{ t('map.results.published', { date: formatDate(result.published_at) }) }}
                </p>
              </article>
            </div>
          </template>

          <article v-else class="rounded-2xl border border-[var(--line)] bg-black/25 p-5 text-sm text-[var(--muted)]">
            {{ t('map.selection.empty') }}
          </article>
        </div>
      </section>
    </div>
  </section>
</template>
