<template>
  <aside class="sidebar">
    <section class="sidebar__section">
      <header class="sidebar__header">
        <h2 class="sidebar__title">Visible Documents</h2>
        <p class="sidebar__subtitle">Toggle which documents appear in the graph.</p>
      </header>
      <div class="visibility-controls" v-if="documents.length">
        <div class="visibility-actions">
          <button class="visibility-btn" type="button" @click="selectAll">Select all</button>
          <button class="visibility-btn" type="button" @click="clearAll">Clear</button>
        </div>
        <ul class="visibility-list">
          <li v-for="doc in documents" :key="doc.id" class="visibility-item">
            <label>
              <input type="checkbox" :checked="isVisible(doc.id)" @change="toggle(doc.id)" />
              <span class="doc-label">{{ doc.title }}</span>
            </label>
          </li>
        </ul>
      </div>
      <div v-else class="sidebar__empty">No documents to filter.</div>
    </section>
    <section class="sidebar__section">
      <header class="sidebar__header">
        <h2 class="sidebar__title">Document Library</h2>
        <p class="sidebar__subtitle">
          Manage Google Drive imports and local uploads. Link documents to nodes via the context menu or details panel.
        </p>
      </header>
      <div v-if="documents.length === 0" class="sidebar__empty">
        No documents yet. Import files to begin building your graph.
      </div>
      <ul v-else class="doc-list">
        <li v-for="doc in documents" :key="doc.id" class="doc-list__item">
          <div class="doc-list__meta">
            <span class="doc-list__title">{{ doc.title }}</span>
            <span class="doc-list__info">
              {{ doc.source === 'google' ? 'Google Drive' : 'Local file' }}
              <span v-if="doc.mimeType"> · {{ doc.mimeType }}</span>
            </span>
            <span v-if="doc.description" class="doc-list__description">{{ doc.description }}</span>
          </div>
          <div class="doc-list__actions">
            <span class="doc-list__status" :data-status="doc.status">
              {{ doc.status }}
            </span>
            <button class="doc-list__delete" type="button" @click="handleDeleteDocument(doc.id)">
              Delete
            </button>
          </div>
        </li>
      </ul>
    </section>

    <section class="sidebar__section">
      <header class="sidebar__header">
        <h2 class="sidebar__title">Network Analytics</h2>
        <p class="sidebar__subtitle">
          Metrics refresh automatically as you edit the graph.
        </p>
      </header>

      <article class="metric-card">
        <h3 class="metric-card__label">Totals</h3>
        <ul class="metric-card__list">
          <li>Nodes: <strong>{{ metrics.totals.nodes }}</strong></li>
          <li>Edges: <strong>{{ metrics.totals.edges }}</strong></li>
          <li>Documents: <strong>{{ metrics.totals.documents }}</strong></li>
        </ul>
      </article>

      <article class="metric-card">
        <h3 class="metric-card__label">Connectivity</h3>
        <ul class="metric-card__list">
          <li>Components: <strong>{{ metrics.connectivity.components }}</strong></li>
          <li>Avg. degree: <strong>{{ metrics.connectivity.averageDegree }}</strong></li>
          <li>Density: <strong>{{ metrics.connectivity.density }}</strong></li>
        </ul>
        <p v-if="metrics.connectivity.isolates.length" class="metric-card__note">
          Isolated: {{ metrics.connectivity.isolates.join(', ') }}
        </p>
      </article>

      <article class="metric-card">
        <h3 class="metric-card__label">Influence</h3>
        <ul v-if="metrics.influence.topDegree.length" class="metric-card__list">
          <li v-for="node in metrics.influence.topDegree" :key="node.nodeId">
            {{ node.label }} ({{ node.degree }})
          </li>
        </ul>
        <p v-else class="metric-card__note">
          Add more relationships to surface key entities.
        </p>
      </article>

      <article class="metric-card">
        <h3 class="metric-card__label">Communities</h3>
        <ul v-if="metrics.communities.clusters.length" class="metric-card__list">
          <li v-for="cluster in metrics.communities.clusters" :key="cluster.id">
            {{ cluster.label }} · {{ cluster.nodeIds.length }} nodes
          </li>
        </ul>
        <p v-else class="metric-card__note">No clusters detected yet.</p>
        <div class="community-toggle">
          <label>
            <input type="checkbox" :checked="showCommunities" @change="toggleCommunities" />
            Show communities (color by cluster)
          </label>
        </div>
      </article>
    </section>
  </aside>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { useGraphStore } from '@/stores/graphStore'

const graphStore = useGraphStore()
const { documents, metrics, visibleDocumentIds, showCommunities } = storeToRefs(graphStore)

function isVisible(id: string) {
  return visibleDocumentIds.value.has(id)
}
function toggle(id: string) {
  graphStore.toggleDocumentVisibility(id)
}
function selectAll() {
  graphStore.selectAllDocuments()
}
function clearAll() {
  graphStore.clearVisibleDocuments()
}

function toggleCommunities() {
  graphStore.toggleShowCommunities()
}

function handleDeleteDocument(documentId: string) {
  graphStore.deleteDocument(documentId).catch((error) => {
    console.error('Failed to delete document', error)
  })
}
</script>

<style scoped>
.sidebar {
  width: 320px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 16px 16px 24px 16px;
  background: #ffffff;
  border-right: 1px solid rgba(15, 49, 103, 0.12);
  box-shadow: inset -1px 0 0 rgba(15, 49, 103, 0.04);
  overflow-y: auto;
  height: 100%;
  min-height: 0; /* allow internal scrolling in grid */
}

.sidebar__section {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 12px;
  background: #fafcff;
  border-radius: 12px;
  border: 1px solid rgba(15, 49, 103, 0.08);
}

.visibility-controls {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.visibility-actions {
  display: flex;
  gap: 8px;
}

.visibility-btn {
  border: 1px solid rgba(15, 49, 103, 0.15);
  background: rgba(255, 255, 255, 0.92);
  color: #0f3167;
  font-size: 12px;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 6px;
  cursor: pointer;
}

.visibility-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 180px;
  overflow-y: auto;
}

.visibility-item label {
  display: flex;
  align-items: center;
  gap: 8px;
}

.doc-label {
  color: #0f3167;
  font-size: 13px;
}

.sidebar__header {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.sidebar__title {
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.01em;
  color: #0f3167;
}

.sidebar__subtitle {
  font-size: 12px;
  color: rgba(18, 20, 23, 0.62);
}

.sidebar__empty {
  min-height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 12px;
  border: 1px dashed rgba(15, 49, 103, 0.12);
  border-radius: 10px;
  color: rgba(18, 20, 23, 0.65);
  font-size: 13px;
}

.doc-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.doc-list__item {
  padding: 12px;
  border-radius: 12px;
  border: 1px solid rgba(15, 49, 103, 0.08);
  background: #fff;
  display: flex;
  align-items: center;
  gap: 12px;
}

.doc-list__meta {
  display: flex;
  flex: 1;
  min-width: 0;
  flex-direction: column;
  gap: 4px;
}

.doc-list__title {
  font-weight: 600;
  color: #0f3167;
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.doc-list__info {
  font-size: 12px;
  color: rgba(18, 20, 23, 0.6);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.doc-list__description {
  font-size: 11px;
  color: rgba(18, 20, 23, 0.55);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.doc-list__actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
  flex-shrink: 0;
  min-width: 72px;
}

.doc-list__status {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 600;
  color: #0f3167;
}

.doc-list__status[data-status='processing'] {
  color: #ff9800;
}

.doc-list__status[data-status='ready'] {
  color: #1b7b4a;
}

.doc-list__status[data-status='error'] {
  color: #c62828;
}

.doc-list__delete {
  border: 1px solid rgba(198, 40, 40, 0.2);
  background: #fff5f5;
  color: #c62828;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: background 0.2s ease, color 0.2s ease, border-color 0.2s ease;
}

.doc-list__delete:hover {
  background: rgba(198, 40, 40, 0.1);
  border-color: rgba(198, 40, 40, 0.35);
}

.metric-card {
  padding: 12px 14px;
  background: #fff;
  border-radius: 14px;
  border: 1px solid rgba(15, 49, 103, 0.08);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.metric-card__label {
  font-size: 14px;
  font-weight: 600;
  color: #0f3167;
}

.metric-card__list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
  color: rgba(18, 20, 23, 0.75);
}

.metric-card__note {
  font-size: 12px;
  color: rgba(18, 20, 23, 0.55);
}

.community-toggle {
  margin-top: 8px;
  font-size: 13px;
  color: #0f3167;
}

@media (max-width: 1200px) {
  .sidebar {
    width: 280px;
  }
}
</style>
