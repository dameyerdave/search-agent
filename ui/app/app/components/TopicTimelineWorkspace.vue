<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { getErrorMessage } from 'errors'
import type { TopicTimelineEntry, TopicTimelineSummary } from 'types/search-agent'

const props = defineProps<{
  topicSlug: string
  topicName: string
}>()

const { t } = useI18n()
const api = useSearchAgentApi()
const toast = useToast()

const isGenerating = ref(false)
const hasSelectedTopic = computed(() => Boolean(props.topicSlug))

const timelineQuery = useQuery({
  queryKey: computed(() => ['topic-timeline', props.topicSlug]),
  queryFn: async () => {
    if (!props.topicSlug) return null
    return api.get<TopicTimelineSummary | null>(`/api/v1/topics/${props.topicSlug}/timeline/`)
  },
})

const entries = computed(() => timelineQuery.data.value?.entries ?? [])

const generateTimeline = async () => {
  if (!props.topicSlug) return
  isGenerating.value = true
  try {
    await api.post<TopicTimelineSummary>(`/api/v1/topics/${props.topicSlug}/timeline/`, {})
    await timelineQuery.refetch()
    toast.add({ title: t('timeline.success.generated'), color: 'success' })
  } catch (error: unknown) {
    toast.add({ title: getErrorMessage(error) || t('timeline.errors.generate_failed'), color: 'error' })
  } finally {
    isGenerating.value = false
  }
}

const dateFormatter = new Intl.DateTimeFormat('en-CH', { dateStyle: 'medium' })

const formatEntryDate = (entry: TopicTimelineEntry) => {
  if (!entry.date) return t('timeline.entry.unknown_date')
  try {
    const iso = entry.time ? `${entry.date}T${entry.time}:00` : entry.date
    const formatted = dateFormatter.format(new Date(iso))
    return entry.time ? `${formatted}, ${entry.time}` : formatted
  } catch {
    return entry.date
  }
}

const ordinalLabel = (n: number) => {
  const mod100 = n % 100
  if (mod100 >= 11 && mod100 <= 13) return `${n}th`
  const suffix = { 1: 'st', 2: 'nd', 3: 'rd' }[n % 10] ?? 'th'
  return `${n}${suffix}`
}
</script>

<template>
  <section class="terminal-panel relative overflow-hidden rounded-[1.5rem] p-5">
    <div class="relative z-10 space-y-4">
      <div class="flex flex-col gap-3 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <p class="mono-heading text-lg tracking-[0.22em] text-white uppercase">
            {{ t('timeline.title') }}
          </p>
          <p class="mt-2 text-sm text-[var(--muted)]">
            {{ hasSelectedTopic ? t('timeline.subtitle_topic', { topic: props.topicName }) : t('timeline.select_topic_prompt') }}
          </p>
        </div>

        <button
          class="terminal-button terminal-button-secondary"
          :disabled="!hasSelectedTopic || isGenerating"
          @click="generateTimeline"
        >
          {{ isGenerating ? t('timeline.controls.generating') : t('timeline.controls.generate') }}
        </button>
      </div>

      <p v-if="timelineQuery.data.value" class="text-xs text-[var(--muted)]">
        {{ t('timeline.generated_at', { date: dateFormatter.format(new Date(timelineQuery.data.value.generated_at)) }) }}
      </p>

      <div v-if="entries.length" class="space-y-3">
        <article
          v-for="entry in entries"
          :key="entry.order"
          class="rounded-2xl border border-[var(--line)] bg-black/25 p-4"
        >
          <div class="flex flex-wrap items-center gap-2">
            <span class="pill bg-[var(--accent-soft)] text-[var(--accent)]">
              {{ ordinalLabel(entry.order) }}
            </span>
            <span class="text-xs tracking-[0.18em] text-[var(--muted)] uppercase">
              {{ formatEntryDate(entry) }}
            </span>
            <span v-if="entry.place" class="text-xs tracking-[0.18em] text-[var(--muted)] uppercase">
              · {{ entry.place }}
            </span>
          </div>
          <p class="mt-2 text-sm leading-6 text-white">{{ entry.summary }}</p>
          <div v-if="entry.results.length" class="mt-2 flex flex-wrap gap-2">
            <a
              v-for="result in entry.results"
              :key="result.id"
              :href="result.url"
              target="_blank"
              rel="noreferrer"
              class="text-xs text-[var(--muted)] underline hover:text-[var(--accent)]"
            >
              {{ result.title }}
            </a>
          </div>
        </article>
      </div>

      <article
        v-else
        class="rounded-2xl border border-[var(--line)] bg-black/25 p-5 text-sm text-[var(--muted)]"
      >
        {{ hasSelectedTopic ? t('timeline.empty_topic') : t('timeline.select_topic_prompt') }}
      </article>
    </div>
  </section>
</template>
