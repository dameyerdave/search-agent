<script setup lang="ts">
import { deriveLookbackDays, describeCategories } from 'utils/dashboard'
import type { SourceScope } from 'types/search-agent'

const dashboardStore = useDashboardStore()
const searchStore = useSearchWorkspaceStore()
const { t } = useI18n()

const categoryLabel = (source: SourceScope) => {
  const coverage = describeCategories(source)
  if (coverage.kind === 'all') return t('dashboard.search.save_dialog.categories_all')
  if (coverage.kind === 'none') return t('dashboard.search.save_dialog.categories_none')
  return coverage.values.join(', ')
}
</script>

<template>
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/72 px-4 py-6 backdrop-blur-sm"
    @click.self="searchStore.closeLiveSearchSaveDialog"
    @keydown.esc="searchStore.closeLiveSearchSaveDialog"
  >
    <section
      role="dialog"
      aria-modal="true"
      aria-labelledby="save-search-dialog-title"
      class="terminal-panel relative max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-[1.6rem] p-5 sm:p-6"
    >
      <div class="relative z-10 space-y-4">
        <div class="flex items-start justify-between gap-3">
          <div>
            <p id="save-search-dialog-title" class="mono-heading text-lg tracking-[0.22em] text-white uppercase">
              {{ t('dashboard.search.save_dialog.title') }}
            </p>
            <p class="mt-2 text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
              {{ t('dashboard.search.save_dialog.active_query') }}
              <span class="text-[var(--text)]">{{ searchStore.liveSearchForm.q || t('results.not_available') }}</span>
            </p>
          </div>
          <button class="terminal-button terminal-button-secondary" @click="searchStore.closeLiveSearchSaveDialog">
            {{ t('dashboard.common.buttons.close') }}
          </button>
        </div>

        <div class="grid gap-3 sm:grid-cols-2">
          <label class="space-y-2 sm:col-span-2">
            <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
              {{ t('dashboard.search.save_dialog.topic_name') }}
            </span>
            <input
              v-model="searchStore.liveSearchSaveForm.name"
              class="terminal-input"
              :placeholder="searchStore.fallbackLiveTopicName()"
            />
          </label>
          <label class="space-y-2 sm:col-span-2">
            <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
              {{ t('dashboard.search.save_dialog.description') }}
            </span>
            <textarea v-model="searchStore.liveSearchSaveForm.description" class="terminal-textarea min-h-[90px]" />
          </label>
          <label class="space-y-2">
            <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
              {{ t('dashboard.search.save_dialog.schedule_every') }}
            </span>
            <input
              v-model="searchStore.liveSearchSaveForm.scheduleEvery"
              class="terminal-input"
              type="number"
              min="1"
            />
          </label>
          <label class="space-y-2">
            <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
              {{ t('dashboard.search.save_dialog.schedule_unit') }}
            </span>
            <select v-model="searchStore.liveSearchSaveForm.scheduleUnit" class="terminal-select">
              <option value="minutes">{{ t('dashboard.search.save_dialog.unit_minutes') }}</option>
              <option value="hours">{{ t('dashboard.search.save_dialog.unit_hours') }}</option>
              <option value="days">{{ t('dashboard.search.save_dialog.unit_days') }}</option>
              <option value="weeks">{{ t('dashboard.search.save_dialog.unit_weeks') }}</option>
            </select>
          </label>
          <label class="space-y-2">
            <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
              {{ t('dashboard.search.save_dialog.topic_enabled') }}
            </span>
            <select v-model="searchStore.liveSearchSaveForm.enabled" class="terminal-select">
              <option :value="true">{{ t('dashboard.search.save_dialog.enabled') }}</option>
              <option :value="false">{{ t('dashboard.search.save_dialog.disabled') }}</option>
            </select>
          </label>
          <label class="space-y-2">
            <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
              {{ t('dashboard.search.save_dialog.dedicated_scope') }}
            </span>
            <select v-model="searchStore.liveSearchSaveForm.createScope" class="terminal-select">
              <option :value="true">{{ t('dashboard.search.save_dialog.create_scope_option') }}</option>
              <option :value="false">{{ t('dashboard.search.save_dialog.reuse_scopes_option') }}</option>
            </select>
          </label>
        </div>

        <div
          v-if="searchStore.liveSearchSaveForm.createScope"
          class="grid gap-3 rounded-[1.4rem] border border-[var(--line)] bg-black/20 p-4 sm:grid-cols-2"
        >
          <label class="space-y-2 sm:col-span-2">
            <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
              {{ t('dashboard.search.save_dialog.scope_name') }}
            </span>
            <input
              v-model="searchStore.liveSearchSaveForm.scopeName"
              class="terminal-input"
              :placeholder="searchStore.fallbackLiveScopeName()"
            />
          </label>
          <label class="space-y-2 sm:col-span-2">
            <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
              {{ t('dashboard.search.save_dialog.scope_description') }}
            </span>
            <textarea
              v-model="searchStore.liveSearchSaveForm.scopeDescription"
              class="terminal-textarea min-h-[80px]"
            />
          </label>
          <label class="space-y-2">
            <span class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
              {{ t('dashboard.search.save_dialog.scope_kind') }}
            </span>
            <select v-model="searchStore.liveSearchSaveForm.scopeKind" class="terminal-select">
              <option value="public">{{ t('dashboard.search.save_dialog.kind_public') }}</option>
              <option value="research">{{ t('dashboard.search.save_dialog.kind_research') }}</option>
              <option value="custom">{{ t('dashboard.search.save_dialog.kind_custom') }}</option>
            </select>
          </label>
          <article class="rounded-2xl border border-[var(--line)] bg-black/25 p-4 text-sm text-[var(--muted)]">
            <p>
              {{ t('dashboard.search.save_dialog.derived_lookback') }}
              <span class="text-[var(--text)]">{{
                t('dashboard.search.save_dialog.days_suffix', {
                  days: deriveLookbackDays(searchStore.liveSearchForm.timeRange),
                })
              }}</span>
            </p>
          </article>
        </div>

        <div class="space-y-3 rounded-[1.4rem] border border-[var(--line)] bg-black/20 p-4">
          <p class="text-xs tracking-[0.22em] text-[var(--muted)] uppercase">
            {{ t('dashboard.search.save_dialog.attach_sources') }}
          </p>
          <div class="grid gap-2 sm:grid-cols-2">
            <label
              v-for="source in dashboardStore.enabledSources"
              :key="source.id"
              class="flex cursor-pointer items-start gap-3 rounded-2xl border border-[var(--line)] p-3 text-sm text-[var(--text)]"
            >
              <input
                :checked="searchStore.liveSearchSaveForm.sourceScopeIds.includes(source.id)"
                type="checkbox"
                class="mt-1 accent-[var(--accent)]"
                @change="searchStore.toggleLiveSearchSource(source.id)"
              />
              <span>
                <span class="block">{{ source.name }}</span>
                <span class="mt-1 block text-xs text-[var(--muted)]"
                  >{{ source.kind }} / {{ categoryLabel(source) }}</span
                >
              </span>
            </label>
          </div>
        </div>

        <div class="flex flex-wrap justify-end gap-2">
          <button class="terminal-button terminal-button-secondary" @click="searchStore.closeLiveSearchSaveDialog">
            {{ t('dashboard.common.buttons.cancel') }}
          </button>
          <button
            class="terminal-button terminal-button-primary"
            :disabled="searchStore.isSavingLiveSearchTopic || !searchStore.canSaveLiveSearch"
            @click="searchStore.saveLiveSearchAsTopic"
          >
            {{
              searchStore.isSavingLiveSearchTopic
                ? t('dashboard.search.save_dialog.saving_topic')
                : t('dashboard.search.save_dialog.save_as_topic')
            }}
          </button>
        </div>
      </div>
    </section>
  </div>
</template>
