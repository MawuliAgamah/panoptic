<template>
  <header class="top-nav">
    <div class="top-nav__brand">
      <span class="top-nav__logo">KG Extract</span>
      <span class="top-nav__subtitle">Interactive Knowledge Graph Demo</span>
    </div>

    <div class="top-nav__actions">
      <input
        ref="fileInputRef"
        type="file"
        class="top-nav__file-input"
        multiple
        accept=".pdf,.md,.markdown,.doc,.docx,.txt"
        @change="handleLocalFileChange"
      />
      <button class="top-nav__button" type="button" @click="handleLocalImportClick">
        Import Local Document
      </button>
      <button class="top-nav__button top-nav__button--primary" type="button" @click="handleConnectDrive">
        Connect Google Drive
      </button>
      <button class="top-nav__button top-nav__button--ghost" type="button" :disabled="isLoading || isUploading" @click="handleSaveGraph">
        Save Snapshot
      </button>
      <div class="top-nav__status-group">
        <div class="top-nav__status" :class="{ 'top-nav__status--busy': isLoading || isUploading }">
          {{ statusLabel }}
        </div>
        <div class="top-nav__status top-nav__status--muted">
          {{ driveStatus }}
        </div>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useGraphStore } from '@/stores/graphStore'
import {
  ensureAuthenticated,
  fetchDriveDocuments,
  getCurrentGoogleUser,
  toDocumentInput,
  type GoogleUser,
  type GoogleDocMetadata
} from '@/services/googleDrive'
import { registerRemoteDocument, uploadLocalDocument } from '@/services/backend'

const graphStore = useGraphStore()
const { isLoading, lastSavedAt } = storeToRefs(graphStore)

const fileInputRef = ref<HTMLInputElement | null>(null)
const driveUser = ref<GoogleUser | null>(getCurrentGoogleUser())
const driveError = ref<string | null>(null)
const isUploading = ref(false)

function handleLocalImportClick() {
  fileInputRef.value?.click()
}

async function handleLocalFileChange(event: Event) {
  const target = event.target as HTMLInputElement
  const files = target.files
  if (!files || files.length === 0) return

  isUploading.value = true

  for (const file of Array.from(files)) {
    const doc = graphStore.addDocument({
      title: file.name,
      source: 'local',
      mimeType: file.type,
      description: formatFileDescription(file),
      status: 'processing'
    })

    try {
      const result = await uploadLocalDocument(file, { documentId: doc.id })
      if (result.graph) {
        graphStore.applySnapshot(result.graph)
      } else {
        await graphStore.loadGraph()
      }
      graphStore.updateDocument(doc.id, {
        status: 'ready',
        description: formatFileDescription(file)
      })
    } catch (error) {
      console.error('Local upload failed', error)
      graphStore.updateDocument(doc.id, {
        status: 'error',
        description: `${formatFileDescription(file)} · Upload failed`
      })
    }
  }

  isUploading.value = false

  target.value = ''
}

async function handleConnectDrive() {
  try {
    driveError.value = null
    driveUser.value = await ensureAuthenticated()
    const picks = await fetchDriveDocuments()
    await registerDriveDocuments(picks)
  } catch (error) {
    console.error('Google Drive import failed', error)
    driveError.value = error instanceof Error ? error.message : String(error)
  }
}

async function handleSaveGraph() {
  try {
    await graphStore.saveGraph()
  } catch (error) {
    console.error('Failed to save graph snapshot', error)
  }
}

const statusLabel = computed(() => {
  if (isLoading.value) {
    return 'Saving snapshot…'
  }
  if (isUploading.value) {
    return 'Uploading documents…'
  }
  if (lastSavedAt.value) {
    return `Last saved ${formatTimestamp(lastSavedAt.value)}`
  }
  return 'Unsaved changes'
})

const driveStatus = computed(() => {
  if (driveError.value) {
    return `Drive error: ${driveError.value}`
  }
  if (driveUser.value) {
    return `Drive connected: ${driveUser.value.email}`
  }
  return 'Drive disconnected'
})

function formatTimestamp(timestamp: string) {
  const date = new Date(timestamp)
  return `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`
}

function formatFileDescription(file: File) {
  const sizeKb = Math.round(file.size / 1024)
  return `Local file (${file.type || 'unknown type'}) · ${sizeKb}KB`
}

async function registerDriveDocuments(documents: GoogleDocMetadata[]) {
  for (const doc of documents) {
    const mapped = toDocumentInput(doc)
    const created = graphStore.addDocument({
      id: doc.id,
      source: 'google',
      status: 'processing',
      ...mapped
    })

    try {
      await registerRemoteDocument({
        documentId: created.id,
        title: created.title,
        source: created.source,
        mimeType: created.mimeType,
        author: created.author,
        externalId: doc.id,
        url: created.url
      })
      graphStore.updateDocument(created.id, {
        status: 'ready',
        description: mapped.description
      })
    } catch (error) {
      console.error('Failed to register remote document', error)
      graphStore.updateDocument(created.id, {
        status: 'error',
        description: `${mapped.description ?? 'Google Drive document'} · Registration failed`
      })
    }
  }
}
</script>

<style scoped>
.top-nav {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 32px;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(18, 20, 23, 0.08);
  position: sticky;
  top: 0;
  z-index: 10;
}

.top-nav__brand {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.top-nav__logo {
  font-weight: 600;
  font-size: 18px;
  letter-spacing: 0.02em;
  color: #0f3167;
}

.top-nav__subtitle {
  font-size: 13px;
  color: rgba(18, 20, 23, 0.6);
}

.top-nav__actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.top-nav__file-input {
  display: none;
}

.top-nav__button {
  padding: 8px 16px;
  border-radius: 8px;
  border: 1px solid rgba(15, 49, 103, 0.2);
  background: rgba(255, 255, 255, 0.96);
  color: #0f3167;
  font-weight: 500;
  transition: transform 0.12s ease, box-shadow 0.12s ease;
}

.top-nav__button:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 8px 16px rgba(15, 49, 103, 0.12);
}

.top-nav__button:disabled {
  opacity: 0.5;
  cursor: progress;
}

.top-nav__button--primary {
  background: #0f3167;
  color: #fdfdff;
  border-color: #0f3167;
}

.top-nav__button--primary:hover:not(:disabled) {
  box-shadow: 0 12px 20px rgba(15, 49, 103, 0.25);
}

.top-nav__button--ghost {
  background: transparent;
  border-style: dashed;
}

.top-nav__status {
  font-size: 13px;
  color: rgba(18, 20, 23, 0.6);
}

.top-nav__status-group {
  display: flex;
  flex-direction: column;
  gap: 2px;
  text-align: right;
}

.top-nav__status--busy {
  color: #0f3167;
  font-weight: 500;
}

.top-nav__status--muted {
  font-size: 12px;
  color: rgba(18, 20, 23, 0.45);
}

@media (max-width: 1280px) {
  .top-nav {
    padding: 16px;
  }

  .top-nav__actions {
    gap: 8px;
  }

  .top-nav__button {
    padding: 8px 12px;
  }
}
</style>
