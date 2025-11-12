<template>
  <DashboardShell>
    <section class="ontology-creator">
      <header class="oc-header">
        <div class="oc-titles">
          <h1>Ontology Creator</h1>
          <p class="oc-subtitle">Click a square to place a knowledge base block.</p>
        </div>
        <div class="oc-actions">
          <button type="button" class="oc-button" @click="handleClear" :disabled="knowledgeBases.length === 0">
            Clear Blocks
          </button>
          <div class="zoom-controls">
            <button type="button" class="oc-button" @click="zoomOut" :disabled="scale <= minScale">−</button>
            <span class="zoom-label">{{ Math.round(scale * 100) }}%</span>
            <button type="button" class="oc-button" @click="zoomIn" :disabled="scale >= maxScale">+</button>
          </div>
        </div>
      </header>

      <div class="grid-wrapper" ref="wrapperRef" @mousemove="handleMouseMove" @mouseup="handleMouseUp">
        <div class="grid-stage" :style="{ transform: `scale(${scale})` }">
          <!-- Edges overlay -->
          <svg class="edge-layer">
            <g class="edges">
              <path
                v-for="edge in edges"
                :key="edge.id"
                :d="edgePath(edge.a, edge.b)"
              />
            </g>
            <g v-if="pendingFromId && dragPos" class="edges pending">
              <path :d="pendingPath()" />
            </g>
          </svg>
        <div
          class="grid"
          :style="{
            gridTemplateColumns: `repeat(${cols}, 1fr)`,
            gridTemplateRows: `repeat(${rows}, 1fr)`
          }"
        >
          <template v-for="r in rows" :key="`row-${r}`">
            <template v-for="c in cols" :key="`cell-${r}-${c}`">
              <div
                class="grid-cell"
                role="button"
                tabindex="0"
                :class="{ occupied: isOccupied(r - 1, c - 1) }"
                @click="handleCellClick(r - 1, c - 1)"
                @keydown.enter="handleCellClick(r - 1, c - 1)"
                :aria-label="`Grid cell ${r}, ${c}`"
              >
                <div
                  v-if="getBlockAt(r - 1, c - 1)"
                  class="kb-block"
                  @click.stop="handleBlockClick(r - 1, c - 1)"
                  @mouseenter="setHover(r - 1, c - 1)"
                  @mouseleave="clearHover"
                >
                  <div
                    class="kb-cog"
                    role="button"
                    tabindex="0"
                    aria-label="Open block menu"
                    @click="handleCogClickAt(r - 1, c - 1, $event)"
                    @keydown.enter="handleCogClickAt(r - 1, c - 1, $event)"
                    @keydown.space.prevent="handleCogClickAt(r - 1, c - 1, $event)"
                  >
                    <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
                      <path fill="currentColor" d="M12 8.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7Zm8.94 3.25-1.63-.94c.04-.27.06-.54.06-.81 0-.27-.02-.54-.06-.81l1.63-.94a.5.5 0 0 0 .18-.68l-1.5-2.6a.5.5 0 0 0-.65-.2l-1.62.94a6.9 6.9 0 0 0-1.4-.81l-.25-1.86a.5.5 0 0 0-.5-.42h-3a.5.5 0 0 0-.5.42l-.25 1.86c-.5.2-.97.47-1.4.81l-1.62-.94a.5.5 0 0 0-.65.2l-1.5 2.6a.5.5 0 0 0 .18.68l1.63.94c-.04.27-.06.54-.06.81 0 .27.02-.54-.06-.81l-1.63-.94a.5.5 0 0 0-.18.68l1.5 2.6c.14.24.44.32.65.2l1.62-.94c.43.34.9.6 1.4.81l.25 1.86c.04.24.25.42.5.42h3c.25 0 .46-.18.5-.42l.25-1.86c.5-.2.97-.47 1.4-.81l1.62.94c.21.12.51.04.65-.2l1.5-2.6a.5.5 0 0 0-.18-.68ZM12 16a4 4 0 1 1 0-8 4 4 0 0 1 0 8Z"/>
                    </svg>
                  </div>
                  <span class="kb-title">
                    {{ getBlockAt(r - 1, c - 1)?.name }}
                  </span>
                  <span v-if="getBlockAt(r - 1, c - 1)?.description" class="kb-desc">
                    {{ getBlockAt(r - 1, c - 1)?.description }}
                  </span>
                  <div class="kb-nub" title="Connect" @mousedown.stop="startConnection(r - 1, c - 1)"></div>
                  <div v-if="isMenuOpenAt(r - 1, c - 1)" class="kb-menu" @click.stop>
                    <button class="kb-menu-item" type="button" @click="handleRenameAt(r - 1, c - 1)">Rename</button>
                    <button class="kb-menu-item" type="button" @click="handleDescribeAt(r - 1, c - 1)">
                      {{ getBlockAt(r - 1, c - 1)?.description ? 'Edit Description' : 'Add Description' }}
                    </button>
                    <button class="kb-menu-item kb-menu-danger" type="button" @click="handleDeleteAt(r - 1, c - 1)">Delete</button>
                  </div>
                </div>
                <span v-else class="cell-hint">+</span>
              </div>
            </template>
          </template>
        </div>
        </div>
        
        <!-- Contextual popover anchored to selected block (not scaled) -->
        <div
          v-if="openPopoverForId"
          class="kb-popover"
          :style="popoverStyle"
          @click.stop
        >
          <div class="kb-popover__card">
            <header class="kb-popover__header">
              <div class="kb-popover__title">{{ getById(openPopoverForId)?.name ?? 'Knowledge Base' }}</div>
              <button type="button" class="kb-popover__close" aria-label="Close" @click.stop="closePopover">×</button>
            </header>
            <div class="kb-popover__body">
              <button type="button" class="oc-button oc-button--primary" @click.stop="handleAddFileClick" :disabled="uploadingForId === openPopoverForId">
                Add file
              </button>
              <input ref="localFileInputRef" type="file" class="kb-popover__file-input" @change="onLocalFilePicked" />
              <div v-if="uploadingForId === openPopoverForId" class="kb-popover__status">Uploading…</div>
              <div v-else-if="uploadError" class="kb-popover__status kb-popover__status--error">{{ uploadError }}</div>

              <div class="kb-popover__docs">
                <div class="kb-popover__docs-title">Documents</div>
                <div v-if="(getById(openPopoverForId)?.documents?.length ?? 0) === 0" class="kb-popover__empty">No documents yet</div>
                <ul v-else class="kb-popover__doclist">
                  <li v-for="doc in (getById(openPopoverForId)?.documents || [])" :key="doc.id" class="kb-popover__doc">
                    <span class="kb-popover__doc-title">{{ doc.title }}</span>
                    <span class="kb-popover__doc-id">{{ doc.id }}</span>
                  </li>
                </ul>
              </div>
            </div>
          </div>
          <div class="kb-popover__arrow"></div>
        </div>
      </div>
    </section>
  </DashboardShell>
</template>

<script setup lang="ts">
import { reactive, ref, onMounted, onUnmounted, computed } from 'vue'
import DashboardShell from '@/components/layout/DashboardShell.vue'
import { createKnowledgebase, uploadDocument } from '@/api'

type KnowledgeBase = {
  id: string
  name: string
  row: number
  col: number
  description?: string
  documents?: Array<{ id: string; title: string; status?: 'uploading' | 'ready' | 'error' }>
}

const rows = 12
const cols = 18

const counter = ref(0)
const knowledgeBases = reactive<KnowledgeBase[]>([])
const openMenuForId = ref<string | null>(null)
const edges = reactive<{ id: string; a: string; b: string }[]>([])
const pendingFromId = ref<string | null>(null)
const hoverTargetId = ref<string | null>(null)
const dragPos = ref<{ x: number; y: number } | null>(null)
const wrapperRef = ref<HTMLElement | null>(null)
const dims = reactive({ width: 0, height: 0 })
const scale = ref(1)
const minScale = 0.5
const maxScale = 2
const openPopoverForId = ref<string | null>(null)
const localFileInputRef = ref<HTMLInputElement | null>(null)
const uploadingForId = ref<string | null>(null)
const uploadError = ref<string | null>(null)

function isOccupied(row: number, col: number) {
  return knowledgeBases.some((kb) => kb.row === row && kb.col === col)
}

function getBlockAt(row: number, col: number) {
  return knowledgeBases.find((kb) => kb.row === row && kb.col === col)
}

function handleCellClick(row: number, col: number) {
  if (pendingFromId.value) return
  if (isOccupied(row, col)) return
  counter.value += 1
  const draft = {
    id: `kb-${counter.value}`,
    name: `Knowledge Base ${counter.value}`,
    row,
    col,
    description: undefined as string | undefined,
    documents: [] as Array<{ id: string; title: string; status?: 'uploading' | 'ready' | 'error' }>
  }
  knowledgeBases.push(draft)

  // Persist to backend (fire-and-forget; update ID on success)
  createKnowledgebase({ name: draft.name, description: draft.description })
    .then((kb) => {
      const target = knowledgeBases.find((k) => k.id === draft.id)
      if (target) {
        const oldId = target.id
        target.id = kb.id
        target.name = kb.name || target.name
        if (kb.description) target.description = kb.description
        // If popover was open for the draft id, retarget it to the new id
        if (openPopoverForId.value === oldId) {
          openPopoverForId.value = kb.id
        }
      }
    })
    .catch((err) => {
      console.warn('[ontology] Failed to create knowledgebase on backend; keeping local-only block.', err)
    })
}

function handleClear() {
  knowledgeBases.splice(0, knowledgeBases.length)
  counter.value = 0
  edges.splice(0, edges.length)
}

function getIdAt(row: number, col: number) {
  return getBlockAt(row, col)?.id ?? null
}

function isMenuOpenAt(row: number, col: number) {
  const id = getIdAt(row, col)
  return !!id && openMenuForId.value === id
}

function handleCogClickAt(row: number, col: number, event: MouseEvent) {
  event.stopPropagation()
  const id = getIdAt(row, col)
  if (!id) return
  openMenuForId.value = openMenuForId.value === id ? null : id
}

function handleRenameAt(row: number, col: number) {
  const block = getBlockAt(row, col)
  if (!block) return
  const next = window.prompt('Rename knowledge base', block.name)
  if (next && next.trim().length > 0) {
    block.name = next.trim()
  }
  openMenuForId.value = null
}

function handleDescribeAt(row: number, col: number) {
  const block = getBlockAt(row, col)
  if (!block) return
  const current = block.description ?? ''
  const next = window.prompt('Add/Edit description', current)
  if (next !== null) {
    const trimmed = next.trim()
    block.description = trimmed.length > 0 ? trimmed : undefined
  }
  openMenuForId.value = null
}

function handleDeleteAt(row: number, col: number) {
  const block = getBlockAt(row, col)
  if (!block) return
  const ok = window.confirm(`Delete "${block.name}"?`)
  if (!ok) return
  const idx = knowledgeBases.findIndex((kb) => kb.id === block.id)
  if (idx !== -1) knowledgeBases.splice(idx, 1)
  if (openMenuForId.value === block.id) openMenuForId.value = null
}

function closeMenu() {
  openMenuForId.value = null
}

function closePopover() {
  openPopoverForId.value = null
}

onMounted(() => {
  window.addEventListener('click', closeMenu)
  window.addEventListener('click', closePopover)
  updateDims()
  window.addEventListener('resize', updateDims)
})

onUnmounted(() => {
  window.removeEventListener('click', closeMenu)
  window.removeEventListener('click', closePopover)
  window.removeEventListener('resize', updateDims)
})

function updateDims() {
  const el = wrapperRef.value
  if (!el) return
  dims.width = el.clientWidth
  dims.height = el.clientHeight
}

function toXYByRowCol(row: number, col: number) {
  const cw = dims.width / cols
  const ch = dims.height / rows
  return { x: (col + 0.5) * cw, y: (row + 0.5) * ch }
}

function toXYById(id: string) {
  const kb = knowledgeBases.find((k) => k.id === id)
  if (!kb) return { x: 0, y: 0 }
  return toXYByRowCol(kb.row, kb.col)
}

function getById(id: string | null) {
  if (!id) return undefined
  return knowledgeBases.find((k) => k.id === id)
}

function linePath(a: { x: number; y: number }, b: { x: number; y: number }) {
  // Slight curve for nicer aesthetics
  const dx = (b.x - a.x) * 0.4
  const c1x = a.x + dx, c1y = a.y
  const c2x = b.x - dx, c2y = b.y
  return `M ${a.x} ${a.y} C ${c1x} ${c1y}, ${c2x} ${c2y}, ${b.x} ${b.y}`
}

function edgePath(aId: string, bId: string) {
  const a = toXYById(aId)
  const b = toXYById(bId)
  return linePath(a, b)
}

function pendingPath() {
  if (!pendingFromId.value || !dragPos.value) return ''
  const a = toXYById(pendingFromId.value)
  const b = dragPos.value
  return linePath(a, b)
}

function startConnection(row: number, col: number) {
  const id = getIdAt(row, col)
  if (!id) return
  pendingFromId.value = id
}

function completeIfConnecting(row: number, col: number) {
  if (!pendingFromId.value) return
  const targetId = getIdAt(row, col)
  if (!targetId || targetId === pendingFromId.value) {
    pendingFromId.value = null
    dragPos.value = null
    return
  }
  addEdge(pendingFromId.value, targetId)
  pendingFromId.value = null
  dragPos.value = null
}

function handleBlockClick(row: number, col: number) {
  if (pendingFromId.value) {
    completeIfConnecting(row, col)
    return
  }
  const id = getIdAt(row, col)
  if (!id) return
  openPopoverForId.value = openPopoverForId.value === id ? null : id
}

function addEdge(aId: string, bId: string) {
  // Undirected; normalize pair ordering to avoid duplicates
  const [x, y] = aId < bId ? [aId, bId] : [bId, aId]
  const exists = edges.some((e) => (e.a === x && e.b === y))
  if (exists) return
  edges.push({ id: `edge-${edges.length + 1}`, a: x, b: y })
}

function zoomIn() {
  scale.value = Math.min(maxScale, Math.round((scale.value + 0.1) * 10) / 10)
}

function zoomOut() {
  scale.value = Math.max(minScale, Math.round((scale.value - 0.1) * 10) / 10)
}

function handleMouseMove(e: MouseEvent) {
  if (!pendingFromId.value) return
  const el = wrapperRef.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  dragPos.value = { x: (e.clientX - rect.left) / scale.value, y: (e.clientY - rect.top) / scale.value }
}

function handleMouseUp() {
  if (!pendingFromId.value) return
  if (hoverTargetId.value && hoverTargetId.value !== pendingFromId.value) {
    addEdge(pendingFromId.value, hoverTargetId.value)
  }
  pendingFromId.value = null
  dragPos.value = null
}

function setHover(row: number, col: number) {
  const id = getIdAt(row, col)
  hoverTargetId.value = id
}

function clearHover() {
  hoverTargetId.value = null
}

const popoverStyle = computed(() => {
  const id = openPopoverForId.value
  if (!id) return {}
  const { x, y } = toXYById(id)
  return {
    left: `${x * scale.value}px`,
    top: `${y * scale.value}px`
  }
})

function handleAddFileClick() {
  localFileInputRef.value?.click()
}

function onLocalFilePicked(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) {
    const kbId = openPopoverForId.value
    if (!kbId) return
    uploadingForId.value = kbId
    uploadError.value = null
    const documentId = `doc_${Date.now()}`
    uploadDocument(file, { document_id: documentId, knowledgebase_id: kbId })
      .then((result) => {
        console.info('[ontology] Upload success:', result)
        const kb = getById(kbId)
        if (kb) {
          kb.documents = kb.documents || []
          kb.documents.unshift({ id: result.document_id || documentId, title: result.filename || file.name, status: 'ready' })
        }
      })
      .catch((err) => {
        console.error('[ontology] Upload failed:', err)
        uploadError.value = String(err)
      })
      .finally(() => {
        if (uploadingForId.value === kbId) uploadingForId.value = null
      })
  }
  input.value = ''
}
</script>

<style scoped>
.ontology-creator {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.oc-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.oc-titles {
  display: flex;
  flex-direction: column;
}

h1 {
  font-size: 20px;
  color: var(--color-brand-700);
}

.oc-subtitle {
  color: var(--text-muted);
  font-size: 13px;
}

.oc-actions {
  display: flex;
  gap: 8px;
}

.oc-button {
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px dashed var(--border);
  background: var(--surface-1);
  color: var(--color-brand-600);
}

.oc-button:disabled {
  opacity: 0.6;
}

.oc-button--primary {
  background: var(--action-bg);
  color: var(--action-fg);
  border-color: var(--action-bg);
}

.zoom-controls {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.zoom-label {
  min-width: 42px;
  text-align: center;
  color: var(--text-muted);
}

.grid-wrapper {
  width: 100%;
  height: calc(80vh - 120px);
  min-height: 420px;
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  overflow: hidden;
  background: var(--color-white);
  position: relative;
}

.grid-stage {
  width: 100%;
  height: 100%;
  transform-origin: 0 0;
}

.grid {
  display: grid;
  width: 100%;
  height: 100%;
}

.edge-layer {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.edge-layer path {
  stroke: #4b9bff;
  stroke-width: 2;
  fill: none;
  opacity: 0.9;
}

.edge-layer g.pending path {
  stroke-dasharray: 4 4;
  opacity: 0.6;
}

.grid-cell {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  background: repeating-linear-gradient(
      45deg,
      rgba(15, 49, 103, 0.02) 0,
      rgba(15, 49, 103, 0.02) 2px,
      transparent 2px,
      transparent 10px
    );
  border: 1px solid rgba(15, 49, 103, 0.06);
  transition: background-color 0.12s ease;
}

.grid-cell:hover {
  background-color: rgba(15, 49, 103, 0.05);
}

.grid-cell.occupied {
  background: rgba(15, 49, 103, 0.03);
}

.cell-hint {
  opacity: 0.2;
  font-size: 16px;
  color: #0f3167;
}

.kb-block {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  border-radius: 4px;
  background: linear-gradient(
    180deg,
    rgba(56, 127, 245, 0.10) 0%,
    rgba(56, 127, 245, 0.06) 100%
  );
  border: 1px solid rgba(56, 127, 245, 0.35);
  position: relative;
}

.kb-title {
  font-size: 12px;
  font-weight: 600;
  color: #0f3167;
}

.kb-desc {
  margin-top: 2px;
  font-size: 11px;
  color: #2a4a86;
  opacity: 0.9;
  text-align: center;
  padding: 0 6px;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.kb-cog {
  position: absolute;
  top: 6px;
  right: 6px;
  width: 26px;
  height: 26px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(15, 49, 103, 0.15);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.85);
  color: #0f3167;
  cursor: pointer;
}

.kb-cog:hover {
  background: #ffffff;
}

.kb-menu {
  position: absolute;
  top: 36px;
  right: 6px;
  display: flex;
  flex-direction: column;
  background: var(--surface-overlay);
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: var(--shadow-2);
  min-width: 160px;
  overflow: hidden;
  z-index: 2;
}

.kb-menu-item {
  text-align: left;
  background: transparent;
  border: none;
  padding: 8px 10px;
  color: var(--text);
}

.kb-menu-item:hover {
  background: rgba(255, 255, 255, 0.08);
}

.kb-menu-danger {
  color: var(--status-error-fg);
}

.kb-nub {
  position: absolute;
  bottom: 6px;
  left: 50%;
  transform: translateX(-50%);
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #4b9bff;
  box-shadow: 0 0 0 2px #ffffff;
  border: 1px solid rgba(15, 49, 103, 0.25);
}

.kb-nub:hover {
  filter: brightness(1.1);
}

/* Popover styles */
.kb-popover {
  position: absolute;
  z-index: 5;
  transform: translate(-50%, calc(-100% - 12px));
  pointer-events: auto;
}

.kb-popover__card {
  min-width: 220px;
  max-width: 280px;
  background: var(--surface-overlay);
  border: 1px solid var(--border);
  border-radius: 10px;
  box-shadow: var(--shadow-2);
  overflow: hidden;
}

.kb-popover__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-subtle);
}

.kb-popover__title {
  font-size: var(--font-size-14);
  font-weight: var(--font-weight-semibold);
  color: var(--text);
}

.kb-popover__close {
  background: transparent;
  border: none;
  color: var(--text-muted);
  font-size: 18px;
  line-height: 1;
  padding: 0 4px;
}

.kb-popover__body {
  padding: 12px;
}

.kb-popover__file-input { display: none; }

.kb-popover__status {
  margin-top: 8px;
  font-size: var(--font-size-12);
  color: var(--text-muted);
}

.kb-popover__status--error {
  color: var(--status-error-fg);
}

.kb-popover__docs { margin-top: 10px; }
.kb-popover__docs-title {
  font-size: var(--font-size-12);
  color: var(--text-muted);
  margin-bottom: 6px;
}
.kb-popover__empty {
  font-size: var(--font-size-12);
  color: var(--text-subtle);
}
.kb-popover__doclist { list-style: none; display: flex; flex-direction: column; gap: 6px; }
.kb-popover__doc { display: flex; flex-direction: column; gap: 2px; border: 1px solid var(--border-subtle); border-radius: 8px; padding: 6px 8px; }
.kb-popover__doc-title { font-size: var(--font-size-12); color: var(--text); }
.kb-popover__doc-id { font-size: var(--font-size-11); color: var(--text-subtle); }

.kb-popover__arrow {
  position: absolute;
  bottom: -6px;
  left: 50%;
  width: 12px;
  height: 12px;
  background: var(--surface-overlay);
  border-left: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
  transform: translate(-50%, -50%) rotate(45deg);
}
</style>
