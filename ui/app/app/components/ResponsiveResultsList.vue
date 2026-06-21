<script setup lang="ts">
import type { SearchResult } from 'types/search-agent'

const { t } = useI18n()

const props = defineProps<{
  results: SearchResult[]
  formatDate: (value: string | null) => string
}>()

const emit = defineEmits<{
  save: [id: number, title: string]
  unsave: [id: number]
}>()

const previewText = (result: SearchResult) => result.snippet || result.content || t('results.no_preview')

const editingId = ref<number | null>(null)
const editTitle = ref('')

const openSaveForm = (result: SearchResult) => {
  editingId.value = result.id
  editTitle.value = result.saved_title || result.title
}

const confirmSave = (result: SearchResult) => {
  emit('save', result.id, editTitle.value.trim() || result.title)
  editingId.value = null
}

const cancelSave = () => {
  editingId.value = null
}
</script>

<template>
  <div class="space-y-3">
    <div class="space-y-2 md:hidden">
      <article
        v-for="result in props.results"
        :key="result.id"
        class="rounded-xl border border-[var(--line)] bg-black/25 p-3"
      >
        <div class="space-y-2">
          <div class="flex flex-wrap items-center gap-1.5">
            <span v-if="result.is_new" class="pill bg-[var(--accent-soft)] text-[var(--accent)]">
              {{ t('results.badges.new') }}
            </span>
            <span v-if="result.is_saved" class="pill bg-[rgba(93,255,153,0.06)] text-[var(--accent)]/70">
              {{ t('results.badges.saved') }}
            </span>
            <span v-if="result.domain" class="text-xs tracking-[0.18em] text-[var(--muted)] uppercase">
              {{ result.domain }}
            </span>
          </div>

          <a
            :href="result.url"
            target="_blank"
            rel="noreferrer"
            class="block text-base leading-7 text-white hover:text-[var(--accent)]"
          >
            {{ result.title }}
          </a>

          <p class="text-sm leading-6 text-[var(--muted)]">
            {{ previewText(result) }}
          </p>

          <div class="grid gap-3 rounded-2xl border border-[var(--line)] bg-black/20 p-3">
            <div class="grid gap-1 text-sm text-[var(--muted)]">
              <p>
                {{ t('results.meta.seen', { date: props.formatDate(result.first_seen_at) }) }}
              </p>
              <p>
                {{ t('results.meta.published', { date: props.formatDate(result.published_at) }) }}
              </p>
            </div>
          </div>

          <div v-if="result.matched_queries.length" class="flex flex-wrap gap-2">
            <span
              v-for="query in result.matched_queries.slice(0, 3)"
              :key="query"
              class="rounded-full border border-[var(--line)] px-3 py-1 text-[11px] text-[var(--text)]"
            >
              {{ query }}
            </span>
          </div>

          <div v-if="editingId === result.id" class="space-y-2 rounded-xl border border-[var(--line)] bg-black/30 p-3">
            <label class="space-y-1.5">
              <span class="text-xs tracking-[0.18em] text-[var(--muted)] uppercase">{{ t('results.save.title_label') }}</span>
              <input
                v-model="editTitle"
                class="terminal-input"
                @keyup.enter="confirmSave(result)"
                @keyup.escape="cancelSave"
              />
            </label>
            <div class="flex gap-2">
              <button class="terminal-button terminal-button-primary" @click="confirmSave(result)">
                {{ t('results.save.confirm') }}
              </button>
              <button class="terminal-button terminal-button-secondary" @click="cancelSave">
                {{ t('dashboard.common.buttons.cancel') }}
              </button>
            </div>
          </div>

          <div class="flex gap-2">
            <button
              v-if="!result.is_saved"
              class="terminal-button terminal-button-secondary"
              @click="openSaveForm(result)"
            >
              <UIcon name="i-heroicons-bookmark" class="size-3.5" />
              {{ t('results.save.button') }}
            </button>
            <button
              v-else
              class="terminal-button terminal-button-secondary text-[var(--accent)]"
              @click="emit('unsave', result.id)"
            >
              <UIcon name="i-heroicons-bookmark-solid" class="size-3.5" />
              {{ t('results.save.unsave') }}
            </button>
          </div>
        </div>
      </article>

      <article
        v-if="props.results.length === 0"
        class="rounded-2xl border border-[var(--line)] bg-black/25 p-5 text-center text-sm text-[var(--muted)]"
      >
        {{ t('results.empty') }}
      </article>
    </div>

    <div class="hidden overflow-x-auto rounded-2xl border border-[var(--line)] bg-black/25 md:block">
      <table class="data-table min-w-[760px]">
        <thead>
          <tr>
            <th>{{ t('results.headers.result') }}</th>
            <th>{{ t('results.headers.when') }}</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="result in props.results" :key="result.id">
            <td>
              <div class="space-y-2">
                <div class="flex flex-wrap items-center gap-2">
                  <span v-if="result.is_new" class="pill bg-[var(--accent-soft)] text-[var(--accent)]">
                    {{ t('results.badges.new') }}
                  </span>
                  <span v-if="result.is_saved" class="pill bg-[rgba(93,255,153,0.06)] text-[var(--accent)]/70">
                    {{ t('results.badges.saved') }}
                  </span>
                  <span v-if="result.domain" class="text-xs tracking-[0.18em] text-[var(--muted)] uppercase">
                    {{ result.domain }}
                  </span>
                </div>
                <a
                  :href="result.url"
                  target="_blank"
                  rel="noreferrer"
                  class="text-base text-white hover:text-[var(--accent)]"
                >
                  {{ result.title }}
                </a>
                <p class="max-w-3xl text-sm leading-6 text-[var(--muted)]">
                  {{ previewText(result) }}
                </p>
                <div v-if="result.matched_queries.length" class="flex flex-wrap gap-2">
                  <span
                    v-for="query in result.matched_queries.slice(0, 3)"
                    :key="query"
                    class="rounded-full border border-[var(--line)] px-3 py-1 text-[11px] text-[var(--text)]"
                  >
                    {{ query }}
                  </span>
                </div>
                <div v-if="editingId === result.id" class="space-y-2 rounded-xl border border-[var(--line)] bg-black/30 p-3 max-w-lg">
                  <label class="space-y-1.5">
                    <span class="text-xs tracking-[0.18em] text-[var(--muted)] uppercase">{{ t('results.save.title_label') }}</span>
                    <input
                      v-model="editTitle"
                      class="terminal-input"
                      @keyup.enter="confirmSave(result)"
                      @keyup.escape="cancelSave"
                    />
                  </label>
                  <div class="flex gap-2">
                    <button class="terminal-button terminal-button-primary" @click="confirmSave(result)">
                      {{ t('results.save.confirm') }}
                    </button>
                    <button class="terminal-button terminal-button-secondary" @click="cancelSave">
                      {{ t('dashboard.common.buttons.cancel') }}
                    </button>
                  </div>
                </div>
              </div>
            </td>
            <td class="text-sm text-[var(--muted)]">
              <p>{{ t('results.meta.seen', { date: props.formatDate(result.first_seen_at) }) }}</p>
              <p class="mt-2">
                {{ t('results.meta.published', { date: props.formatDate(result.published_at) }) }}
              </p>
            </td>
            <td class="w-24 text-right">
              <button
                v-if="!result.is_saved"
                class="terminal-button terminal-button-secondary"
                @click="openSaveForm(result)"
              >
                <UIcon name="i-heroicons-bookmark" class="size-3.5" />
                {{ t('results.save.button') }}
              </button>
              <button
                v-else
                class="terminal-button terminal-button-secondary text-[var(--accent)]"
                @click="emit('unsave', result.id)"
              >
                <UIcon name="i-heroicons-bookmark-solid" class="size-3.5" />
                {{ t('results.save.unsave') }}
              </button>
            </td>
          </tr>
          <tr v-if="props.results.length === 0">
            <td colspan="3" class="text-center text-sm text-[var(--muted)]">
              {{ t('results.empty') }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
