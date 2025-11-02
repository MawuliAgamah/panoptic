<template>
  <Teleport to="body">
    <div v-if="detailsOpen" class="drawer-root" @keydown.esc="close" tabindex="-1">
      <div class="drawer-scrim" @click="close" />
      <aside class="drawer-panel">
        <header class="drawer-header">
          <h2>Details</h2>
          <button class="drawer-close" type="button" @click="close">×</button>
        </header>

        <nav class="drawer-tabs">
          <button
            :class="['drawer-tab', activeTab === 'inspector' && 'is-active']"
            @click="setActiveTab('inspector')"
            type="button"
          >Inspector</button>
          <button
            :class="['drawer-tab', activeTab === 'documents' && 'is-active']"
            @click="setActiveTab('documents')"
            type="button"
          >Documents</button>
        </nav>

        <section class="drawer-content">
          <template v-if="selectedNode">
            <div v-if="activeTab === 'inspector'" class="details-card">
              <div class="details-card__header">
                <h3>{{ selectedNode.label }}</h3>
                <span class="badge">{{ selectedNode.type }}</span>
              </div>

              <form class="form-group" @submit.prevent="handleNodeMetadataSave">
                <label class="form-group__label" for="node-label">Label</label>
                <input id="node-label" v-model="editableNode.label" class="form-group__input" />

                <label class="form-group__label" for="node-type">Type</label>
                <select id="node-type" v-model="editableNode.type" class="form-group__input">
                  <option v-for="option in NODE_TYPES" :key="option" :value="option">
                    {{ option }}
                  </option>
                </select>

                <label class="form-group__label" for="node-description">Description</label>
                <textarea
                  id="node-description"
                  v-model="editableNode.description"
                  rows="3"
                  class="form-group__input"
                />

                <button class="details-card__button" type="submit">
                  Update Node
                </button>
              </form>

              <section class="details-card__section">
                <header>
                  <h4>Network Analytics</h4>
                </header>
                <ul class="metric-list">
                  <li>
                    <span>Degree</span>
                    <strong>{{ nodeAnalytics[selectedNode.id]?.degree ?? 0 }}</strong>
                  </li>
                  <li>
                    <span>PageRank</span>
                    <strong>{{ (nodeAnalytics[selectedNode.id]?.pagerank ?? 0).toFixed(4) }}</strong>
                  </li>
                  <li>
                    <span>Closeness</span>
                    <strong>{{ (nodeAnalytics[selectedNode.id]?.closeness ?? 0).toFixed(4) }}</strong>
                  </li>
                  <li>
                    <span>Community</span>
                    <strong>#{{ communityAssignments[selectedNode.id] ?? '-' }}</strong>
                  </li>
                </ul>
              </section>
            </div>

            <div v-else-if="activeTab === 'documents'" class="details-card">
              <header class="details-card__header">
                <h3>Linked Documents</h3>
                <button
                  v-if="selectedNode.documents.length"
                  class="details-card__button details-card__button--ghost"
                  type="button"
                  :disabled="isLoading"
                  @click="triggerExtraction"
                >Extract</button>
              </header>

              <div v-if="selectedNode.documents.length === 0" class="details-card__empty">
                No documents linked. Use the selector below or right-click the node in the canvas.
              </div>
              <ul v-else class="pill-list">
                <li v-for="doc in linkedDocuments" :key="doc.id" class="pill">
                  <span>{{ doc.title }}</span>
                  <button type="button" @click="unlinkDocument(doc.id)">×</button>
                </li>
              </ul>
              <div class="form-group form-group--inline">
                <select v-model="selectedDocId" class="form-group__input">
                  <option disabled value="">Attach existing document</option>
                  <option v-for="doc in availableDocuments" :key="doc.id" :value="doc.id">
                    {{ doc.title }}
                  </option>
                </select>
                <button
                  class="details-card__button details-card__button--light"
                  type="button"
                  :disabled="!selectedDocId"
                  @click="linkDocument"
                >Link</button>
              </div>
            </div>
          </template>

          <template v-else-if="selectedEdge">
            <div class="details-card">
              <div class="details-card__header">
                <h3>{{ selectedEdge.predicate }}</h3>
                <p class="details-card__caption">{{ selectedEdge.source }} → {{ selectedEdge.target }}</p>
              </div>
              <p class="details-card__muted">Edge editing UI will live here.</p>
            </div>
          </template>

          <template v-else>
            <div class="details-card details-card--empty">
              <p>No selection yet.</p>
              <p class="details-card__hint">
                Select a node or edge to inspect details.
              </p>
            </div>
          </template>
        </section>
      </aside>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useGraphStore } from '@/stores/graphStore'
import { useUiStore } from '@/stores/uiStore'
import type { NodeType } from '@/types/graph'

const ui = useUiStore()
const { detailsOpen, activeTab } = storeToRefs(ui)
const { closeDetails, setActiveTab } = ui

const graphStore = useGraphStore()
const { selectedNode, selectedEdge, documents, isLoading, nodeAnalytics, communityAssignments } = storeToRefs(graphStore)

const NODE_TYPES: NodeType[] = ['person', 'organization', 'concept', 'event', 'location', 'other']

const editableNode = reactive({
  id: '',
  label: '',
  type: NODE_TYPES[0],
  description: ''
})

const selectedDocId = ref('')

watch(
  selectedNode,
  (node) => {
    if (!node) {
      editableNode.id = ''
      editableNode.label = ''
      editableNode.type = NODE_TYPES[0]
      editableNode.description = ''
      return
    }
    editableNode.id = node.id
    editableNode.label = node.label
    editableNode.type = node.type
    editableNode.description = node.description ?? ''
  },
  { immediate: true }
)

const linkedDocuments = computed(() => {
  if (!selectedNode.value) return []
  return documents.value.filter((doc) => selectedNode.value?.documents.includes(doc.id))
})

const availableDocuments = computed(() => {
  if (!selectedNode.value) return documents.value
  return documents.value.filter((doc) => !selectedNode.value?.documents.includes(doc.id))
})

function handleNodeMetadataSave() {
  if (!editableNode.id) return
  graphStore.updateNode(editableNode.id, {
    label: editableNode.label,
    type: editableNode.type,
    description: editableNode.description
  })
}

function linkDocument() {
  if (!selectedNode.value || !selectedDocId.value) return
  graphStore.linkDocumentToNode(selectedNode.value.id, selectedDocId.value)
  selectedDocId.value = ''
}

function unlinkDocument(docId: string) {
  const node = selectedNode.value
  if (!node) return
  graphStore.unlinkDocumentFromNode(node.id, docId)
}

async function triggerExtraction() {
  const node = selectedNode.value
  if (!node || node.documents.length === 0) return
  const docId = node.documents[0]
  if (!docId) return
  try {
    await graphStore.triggerExtraction(node.id, docId)
  } catch (error) {
    console.error('Extraction failed', error)
  }
}

function close() {
  closeDetails()
}
</script>

<style scoped>
.drawer-root {
  position: fixed;
  inset: 0;
  z-index: 70;
  display: grid;
  grid-template-columns: 1fr auto;
}

.drawer-scrim {
  background: rgba(18, 20, 23, 0.28);
}

.drawer-panel {
  width: 360px;
  height: 100vh;
  background: #ffffff;
  border-left: 1px solid rgba(15, 49, 103, 0.12);
  box-shadow: -8px 0 24px rgba(15, 49, 103, 0.2);
  display: flex;
  flex-direction: column;
}

.drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid rgba(15, 49, 103, 0.08);
}
.drawer-close {
  border: none;
  background: transparent;
  font-size: 20px;
  line-height: 1;
  color: #0f3167;
  cursor: pointer;
}

.drawer-tabs {
  display: flex;
  gap: 4px;
  padding: 8px 8px 0 8px;
}
.drawer-tab {
  padding: 6px 10px;
  border-radius: 8px;
  border: 1px solid rgba(15, 49, 103, 0.15);
  background: rgba(255, 255, 255, 0.96);
  color: #0f3167;
  font-size: 12px;
  font-weight: 600;
}
.drawer-tab.is-active {
  background: rgba(15, 49, 103, 0.1);
}

.drawer-content {
  padding: 12px 12px 24px 12px;
  overflow-y: auto;
}

/* Reuse DetailsPanel styles for cards and form */
.details-card {
  padding: 14px;
  border-radius: 12px;
  border: 1px solid rgba(15, 49, 103, 0.08);
  background: #fafcff;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.details-card--empty { text-align: center; gap: 8px; color: rgba(18, 20, 23, 0.7); }
.details-card__header { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.details-card__caption { font-size: 13px; color: rgba(18, 20, 23, 0.65); }
.details-card__muted { font-size: 13px; color: rgba(18, 20, 23, 0.65); }
.details-card__hint { font-size: 12px; color: rgba(18, 20, 23, 0.55); }
.details-card__button { align-self: flex-start; padding: 8px 16px; border-radius: 10px; border: none; background: #0f3167; color: #fff; font-weight: 600; }
.details-card__button--ghost { background: transparent; border: 1px dashed rgba(15, 49, 103, 0.25); color: #0f3167; }
.details-card__button--light { background: rgba(15, 49, 103, 0.12); color: #0f3167; }
.details-card__section { display: flex; flex-direction: column; gap: 12px; }
.badge { font-size: 12px; padding: 4px 10px; background: rgba(15, 49, 103, 0.15); color: #0f3167; border-radius: 999px; text-transform: uppercase; letter-spacing: 0.04em; }
.metric-list { list-style: none; display: grid; grid-template-columns: 1fr 1fr; gap: 8px 12px; }
.metric-list li { display: flex; align-items: center; justify-content: space-between; background: #fff; border: 1px solid rgba(15, 49, 103, 0.08); border-radius: 8px; padding: 8px 10px; font-size: 13px; }
.metric-list strong { color: #0f3167; }
.pill-list { list-style: none; display: flex; flex-wrap: wrap; gap: 8px; }
.pill { display: inline-flex; align-items: center; gap: 6px; padding: 6px 10px; border-radius: 999px; background: rgba(15, 49, 103, 0.12); color: #0f3167; font-size: 12px; }
.pill button { border: none; background: transparent; color: inherit; font-size: 14px; cursor: pointer; line-height: 1; }
.form-group { display: flex; flex-direction: column; gap: 8px; }
.form-group--inline { flex-direction: row; align-items: center; gap: 8px; }
.form-group__label { font-size: 12px; color: rgba(18, 20, 23, 0.6); }
.form-group__input { padding: 8px 10px; border: 1px solid rgba(15, 49, 103, 0.15); border-radius: 8px; background: #fff; color: #0f3167; }
.form-group__input:focus { outline: none; box-shadow: 0 0 0 2px rgba(15, 49, 103, 0.15); }

@media (max-width: 420px) {
  .drawer-panel { width: 88vw; }
}
</style>

