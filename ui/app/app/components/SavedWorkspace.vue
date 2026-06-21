<script setup lang="ts">
import type { SavedFolder } from 'types/search-agent'

const authStore = useAuthStore()
const dashboardStore = useDashboardStore()
const savedStore = useSavedWorkspaceStore()
const { t } = useI18n()

const confirmDeleteFolderId = ref<number | null>(null)
const movingResultId = ref<number | null>(null)
const moveTargetFolderId = ref<number | null>(null)
const moveNewFolderName = ref('')

const allSavedCount = computed(() => savedStore.folders.reduce((s, f) => s + f.result_count, 0))

const selectFolder = (id: number | 'unfiled' | null) => {
  savedStore.loadFolderResults(id)
}

const submitCreateFolder = async () => {
  if (!savedStore.newFolderName.trim()) return
  const folder = await savedStore.createFolder(savedStore.newFolderName)
  if (folder) {
    savedStore.newFolderName = ''
    savedStore.isCreatingFolder = false
  }
}

const submitRenameFolder = async (folder: SavedFolder) => {
  await savedStore.renameFolder(folder.id, savedStore.editingFolderName)
}

const confirmDelete = async (id: number) => {
  await savedStore.deleteFolder(id)
  confirmDeleteFolderId.value = null
}

const startMove = (resultId: number) => {
  movingResultId.value = resultId
  moveTargetFolderId.value = null
  moveNewFolderName.value = ''
}

const submitMove = async () => {
  if (movingResultId.value === null) return
  await savedStore.moveResult(
    movingResultId.value,
    moveTargetFolderId.value,
    moveNewFolderName.value,
  )
  movingResultId.value = null
  if (savedStore.selectedFolderId !== null) {
    await savedStore.loadFolderResults(savedStore.selectedFolderId)
  }
}
</script>

<template>
  <section
    v-if="authStore.isAuthenticated && dashboardStore.activeWorkspace === 'saved'"
    class="grid gap-3 sm:gap-5 xl:grid-cols-[0.7fr_1.5fr]"
  >
    <!-- Folder panel -->
    <div class="min-w-0">
      <section class="terminal-panel relative overflow-hidden rounded-[1.2rem] p-3 sm:rounded-3xl sm:p-5">
        <div class="relative z-10 space-y-3">
          <p class="mono-heading text-sm tracking-[0.22em] text-white uppercase sm:text-lg">
            {{ t('saved.folders.title') }}
          </p>

          <nav class="space-y-1">
            <!-- All saved -->
            <button
              class="flex w-full items-center justify-between gap-2 rounded-xl px-3 py-2 text-left text-sm transition-colors"
              :class="
                savedStore.selectedFolderId === null
                  ? 'bg-[var(--accent-soft)] text-[var(--accent)]'
                  : 'text-[var(--muted)] hover:bg-black/30 hover:text-white'
              "
              @click="selectFolder(null)"
            >
              <span class="flex items-center gap-2">
                <UIcon name="i-heroicons-bookmark" class="size-4 shrink-0" />
                {{ t('saved.folders.all_saved') }}
              </span>
              <span class="text-xs">{{ allSavedCount }}</span>
            </button>

            <!-- Unfiled -->
            <button
              class="flex w-full items-center justify-between gap-2 rounded-xl px-3 py-2 text-left text-sm transition-colors"
              :class="
                savedStore.selectedFolderId === 'unfiled'
                  ? 'bg-[var(--accent-soft)] text-[var(--accent)]'
                  : 'text-[var(--muted)] hover:bg-black/30 hover:text-white'
              "
              @click="selectFolder('unfiled')"
            >
              <span class="flex items-center gap-2">
                <UIcon name="i-heroicons-inbox" class="size-4 shrink-0" />
                {{ t('saved.folders.unfiled') }}
              </span>
            </button>

            <div class="my-2 border-t border-[var(--line)]" />

            <!-- Folder list -->
            <div v-for="folder in savedStore.folders" :key="folder.id">
              <!-- Rename mode -->
              <div
                v-if="savedStore.editingFolderId === folder.id"
                class="flex items-center gap-2 px-2 py-1"
              >
                <input
                  v-model="savedStore.editingFolderName"
                  class="terminal-input flex-1 text-sm"
                  @keyup.enter="submitRenameFolder(folder)"
                  @keyup.escape="savedStore.cancelEditFolder()"
                />
                <button class="terminal-button terminal-button-primary text-xs" @click="submitRenameFolder(folder)">
                  {{ t('dashboard.common.buttons.save') }}
                </button>
                <button class="terminal-button terminal-button-secondary text-xs" @click="savedStore.cancelEditFolder()">
                  ✕
                </button>
              </div>

              <!-- Delete confirm -->
              <div
                v-else-if="confirmDeleteFolderId === folder.id"
                class="flex items-center gap-2 rounded-xl border border-[rgba(255,125,125,0.35)] bg-[rgba(64,7,7,0.4)] px-3 py-2"
              >
                <span class="min-w-0 flex-1 text-xs text-[#ffd8d8]">{{ t('saved.folders.confirm_delete', { name: folder.name }) }}</span>
                <button class="terminal-button terminal-button-danger text-xs" @click="confirmDelete(folder.id)">{{ t('dashboard.common.buttons.delete') }}</button>
                <button class="terminal-button terminal-button-secondary text-xs" @click="confirmDeleteFolderId = null">✕</button>
              </div>

              <!-- Normal row -->
              <div
                v-else
                class="group flex items-center gap-1 rounded-xl px-1 py-0.5 transition-colors"
                :class="
                  savedStore.selectedFolderId === folder.id
                    ? 'bg-[var(--accent-soft)]'
                    : 'hover:bg-black/30'
                "
              >
                <button
                  class="flex flex-1 items-center justify-between gap-2 px-2 py-1.5 text-left text-sm"
                  :class="savedStore.selectedFolderId === folder.id ? 'text-[var(--accent)]' : 'text-[var(--muted)] hover:text-white'"
                  @click="selectFolder(folder.id)"
                >
                  <span class="flex min-w-0 items-center gap-2">
                    <UIcon name="i-heroicons-folder" class="size-4 shrink-0" />
                    <span class="truncate">{{ folder.name }}</span>
                  </span>
                  <span class="shrink-0 text-xs">{{ folder.result_count }}</span>
                </button>
                <div class="flex shrink-0 gap-0.5 opacity-0 transition-opacity group-hover:opacity-100">
                  <button
                    class="rounded-lg p-1 text-[var(--muted)] hover:text-white transition-colors"
                    :title="t('saved.folders.rename')"
                    @click="savedStore.startEditFolder(folder)"
                  >
                    <UIcon name="i-heroicons-pencil" class="size-3.5" />
                  </button>
                  <button
                    class="rounded-lg p-1 text-[var(--muted)] hover:text-[var(--danger)] transition-colors"
                    :title="t('saved.folders.delete')"
                    @click="confirmDeleteFolderId = folder.id"
                  >
                    <UIcon name="i-heroicons-trash" class="size-3.5" />
                  </button>
                </div>
              </div>
            </div>
          </nav>

          <!-- New folder -->
          <div v-if="savedStore.isCreatingFolder" class="flex items-center gap-2">
            <input
              v-model="savedStore.newFolderName"
              class="terminal-input flex-1 text-sm"
              :placeholder="t('saved.folders.new_folder_placeholder')"
              @keyup.enter="submitCreateFolder"
              @keyup.escape="savedStore.isCreatingFolder = false"
            />
            <button class="terminal-button terminal-button-primary text-xs" @click="submitCreateFolder">
              {{ t('dashboard.common.buttons.save') }}
            </button>
          </div>
          <button
            v-else
            class="terminal-button terminal-button-secondary w-full text-sm"
            @click="savedStore.isCreatingFolder = true; savedStore.newFolderName = ''"
          >
            <UIcon name="i-heroicons-plus" class="size-3.5" />
            {{ t('saved.folders.new_folder') }}
          </button>
        </div>
      </section>
    </div>

    <!-- Results panel -->
    <div class="min-w-0">
      <section class="terminal-panel relative overflow-hidden rounded-[1.2rem] p-3 sm:rounded-3xl sm:p-5">
        <div class="relative z-10 space-y-3">
          <p class="mono-heading text-sm tracking-[0.22em] text-white uppercase sm:text-lg">
            {{
              savedStore.selectedFolder
                ? savedStore.selectedFolder.name
                : savedStore.selectedFolderId === 'unfiled'
                  ? t('saved.folders.unfiled')
                  : t('saved.results.all_title')
            }}
          </p>

          <div v-if="savedStore.isLoadingResults" class="flex justify-center py-8">
            <XunoLoadingMark class="xuno-loading-mark--sm" />
          </div>

          <div v-else-if="savedStore.folderResultsPage === null" class="py-8 text-center text-sm text-[var(--muted)]">
            {{ t('saved.results.select_folder_prompt') }}
          </div>

          <div v-else-if="savedStore.folderResults.length === 0" class="py-6 text-sm text-[var(--muted)]">
            {{ t('saved.results.empty') }}
          </div>

          <div v-else class="space-y-2">
            <article
              v-for="result in savedStore.folderResults"
              :key="result.id"
              class="rounded-xl border border-[var(--line)] bg-black/25 p-3"
            >
              <div class="flex items-start justify-between gap-3">
                <div class="min-w-0 flex-1 space-y-1">
                  <p v-if="result.folder_name" class="text-[10px] tracking-[0.18em] text-[var(--muted)] uppercase">
                    {{ result.folder_name }}
                  </p>
                  <a
                    :href="result.url"
                    target="_blank"
                    rel="noreferrer"
                    class="block break-words text-sm font-medium text-white hover:text-[var(--accent)]"
                  >
                    {{ result.saved_title || result.title }}
                  </a>
                  <p class="text-xs text-[var(--muted)]">{{ result.domain }}</p>
                </div>
                <div class="flex shrink-0 gap-1.5">
                  <button
                    class="terminal-button terminal-button-secondary text-xs"
                    :title="t('saved.results.move')"
                    @click="startMove(result.id)"
                  >
                    <UIcon name="i-heroicons-arrow-right-circle" class="size-3.5" />
                    {{ t('saved.results.move') }}
                  </button>
                  <button
                    class="terminal-button terminal-button-danger text-xs"
                    :title="t('saved.results.remove')"
                    @click="savedStore.unsaveResult(result.id)"
                  >
                    <UIcon name="i-heroicons-trash" class="size-3.5" />
                  </button>
                </div>
              </div>

              <!-- Move form -->
              <div
                v-if="movingResultId === result.id"
                class="mt-2 space-y-2 rounded-xl border border-[var(--line)] bg-black/30 p-3"
              >
                <p class="text-xs tracking-[0.18em] text-[var(--muted)] uppercase">{{ t('saved.results.move_to') }}</p>
                <select v-model="moveTargetFolderId" class="terminal-select text-sm">
                  <option :value="null">{{ t('saved.folders.unfiled') }}</option>
                  <option v-for="f in savedStore.folders" :key="f.id" :value="f.id">{{ f.name }}</option>
                  <option :value="-1">{{ t('saved.folders.new_folder_option') }}</option>
                </select>
                <input
                  v-if="moveTargetFolderId === -1"
                  v-model="moveNewFolderName"
                  class="terminal-input text-sm"
                  :placeholder="t('saved.folders.new_folder_placeholder')"
                />
                <div class="flex gap-2">
                  <button class="terminal-button terminal-button-primary text-xs" @click="submitMove">
                    {{ t('saved.results.confirm_move') }}
                  </button>
                  <button class="terminal-button terminal-button-secondary text-xs" @click="movingResultId = null">
                    {{ t('dashboard.common.buttons.cancel') }}
                  </button>
                </div>
              </div>
            </article>
          </div>

          <p v-if="savedStore.folderResultsPage" class="text-xs text-[var(--muted)]">
            {{
              t('saved.results.showing', {
                shown: savedStore.folderResults.length,
                total: savedStore.folderResultsPage.count,
              })
            }}
          </p>
        </div>
      </section>
    </div>
  </section>
</template>
