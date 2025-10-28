<template>
  <aside class="details-panel">
    <header class="details-panel__header">
      <h2 class="details-panel__title">Details</h2>
      <p class="details-panel__subtitle">
        Select a node or relationship to inspect metadata, manage documents, or run extraction.
      </p>
    </header>

    <section v-if="selectedNode" class="details-card">
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
          <h4>Linked Documents</h4>
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
          >
            Link
          </button>
        </div>
      </section>

      <section class="details-card__section">
        <header class="details-card__section-header">
          <h4>Knowledge Triples</h4>
          <button
            v-if="selectedNode.documents.length"
            class="details-card__button details-card__button--ghost"
            type="button"
            :disabled="isLoading"
            @click="triggerExtraction"
          >
            Extract from linked docs
          </button>
        </header>

        <div v-if="selectedNode.triples.length === 0" class="details-card__empty">
          Extraction results will appear here once you process linked documents.
        </div>

        <ul v-else class="triples">
          <li v-for="triple in selectedNode.triples" :key="triple.id" class="triple-row">
            <span class="triple-row__subject">{{ triple.subject }}</span>
            <span class="triple-row__predicate">{{ triple.predicate }}</span>
            <span class="triple-row__object">{{ triple.object }}</span>
          </li>
        </ul>
      </section>
    </section>

    <section v-else-if="selectedEdge" class="details-card">
      <div class="details-card__header">
        <h3>{{ selectedEdge.predicate }}</h3>
        <p class="details-card__caption">
          {{ selectedEdge.source }} → {{ selectedEdge.target }}
        </p>
      </div>
      <p class="details-card__muted">
        Edge editing UI will live here. For now, selections show metadata only.
      </p>
    </section>

    <section v-else class="details-card details-card--empty">
      <p>No selection yet.</p>
      <p class="details-card__hint">
        Double-click the canvas to create a node, right-click to manage documents, and use the sidebar
        to monitor analysis metrics.
      </p>
    </section>
  </aside>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useGraphStore } from '@/stores/graphStore'
import type { NodeType } from '@/types/graph'

const NODE_TYPES: NodeType[] = ['person', 'organization', 'concept', 'event', 'location', 'other']

const graphStore = useGraphStore()
const { selectedNode, selectedEdge, documents, isLoading } = storeToRefs(graphStore)

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
</script>

<style scoped>
.details-panel {
  width: 340px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 24px 20px;
  background: rgba(255, 255, 255, 0.92);
  border-left: 1px solid rgba(18, 20, 23, 0.06);
  overflow-y: auto;
}

.details-panel__header {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.details-panel__title {
  font-size: 16px;
  font-weight: 600;
  color: #0f3167;
}

.details-panel__subtitle {
  font-size: 13px;
  color: rgba(18, 20, 23, 0.6);
}

.details-card {
  padding: 18px;
  border-radius: 16px;
  border: 1px solid rgba(15, 49, 103, 0.08);
  background: rgba(246, 248, 253, 0.92);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.details-card--empty {
  text-align: center;
  gap: 8px;
  color: rgba(18, 20, 23, 0.7);
}

.details-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.details-card__caption {
  font-size: 13px;
  color: rgba(18, 20, 23, 0.65);
}

.badge {
  font-size: 12px;
  padding: 4px 10px;
  background: rgba(15, 49, 103, 0.15);
  color: #0f3167;
  border-radius: 999px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group--inline {
  flex-direction: row;
  align-items: center;
}

.form-group__label {
  font-size: 12px;
  font-weight: 600;
  color: rgba(18, 20, 23, 0.7);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.form-group__input {
  width: 100%;
  padding: 8px 12px;
  border-radius: 10px;
  border: 1px solid rgba(15, 49, 103, 0.18);
  background: rgba(255, 255, 255, 0.96);
  font-size: 14px;
  color: #121417;
}

.form-group__input:focus {
  outline: none;
  border-color: #0f3167;
  box-shadow: 0 0 0 2px rgba(15, 49, 103, 0.15);
}

.details-card__button {
  align-self: flex-start;
  padding: 8px 16px;
  border-radius: 10px;
  border: none;
  background: #0f3167;
  color: #fff;
  font-weight: 600;
  transition: transform 0.12s ease, box-shadow 0.12s ease;
}

.details-card__button--ghost {
  background: transparent;
  border: 1px dashed rgba(15, 49, 103, 0.25);
  color: #0f3167;
}

.details-card__button--light {
  background: rgba(15, 49, 103, 0.12);
  color: #0f3167;
}

.details-card__button:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 10px 16px rgba(15, 49, 103, 0.12);
}

.details-card__button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.details-card__section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.details-card__section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.details-card__empty {
  padding: 12px;
  border-radius: 12px;
  border: 1px dashed rgba(15, 49, 103, 0.12);
  background: rgba(255, 255, 255, 0.9);
  font-size: 13px;
  color: rgba(18, 20, 23, 0.65);
}

.details-card__hint {
  font-size: 12px;
  color: rgba(18, 20, 23, 0.55);
}

.details-card__muted {
  font-size: 13px;
  color: rgba(18, 20, 23, 0.65);
}

.pill-list {
  list-style: none;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(15, 49, 103, 0.12);
  color: #0f3167;
  font-size: 12px;
}

.pill button {
  border: none;
  background: transparent;
  color: inherit;
  font-size: 14px;
  cursor: pointer;
  line-height: 1;
}

.triples {
  display: flex;
  flex-direction: column;
  gap: 10px;
  list-style: none;
}

.triple-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  font-size: 13px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 12px;
  padding: 10px 12px;
  border: 1px solid rgba(15, 49, 103, 0.08);
}

.triple-row__predicate {
  text-align: center;
  font-weight: 600;
  color: #0f3167;
}

.triple-row__object {
  text-align: right;
}

@media (max-width: 1200px) {
  .details-panel {
    width: 300px;
  }
}
</style>
