<template>
  <aside class="sidebar">
    <section class="sidebar__section">
      <header class="sidebar__header">
        <h2 class="sidebar__title">Visible Documents</h2>
        <div class="sidebar__header-actions">
          <button class="header-toggle" type="button" @click="collapsedFilters = !collapsedFilters">
            {{ collapsedFilters ? 'Expand' : 'Collapse' }}
          </button>
        </div>
        <p class="sidebar__subtitle">Toggle which documents appear in the graph.</p>
      </header>
      <div v-if="!collapsedFilters && documents.length" class="visibility-controls">
        <div class="visibility-actions">
          <button class="visibility-btn" type="button" @click="selectAll">Select all</button>
          <button class="visibility-btn" type="button" @click="clearAll">Clear</button>
        </div>
        <ul class="visibility-list">
          <li v-for="doc in documentsForFilter" :key="doc.id" class="visibility-item">
            <label>
              <input type="checkbox" :checked="isVisible(doc.id)" @change="toggle(doc.id)" />
              <span class="doc-label">{{ doc.title }}</span>
            </label>
          </li>
        </ul>
        <div v-if="documents.length > filterLimit" class="list-footer">
          <button class="link-btn" type="button" @click="showAllFilters = !showAllFilters">
            {{ showAllFilters ? 'Show less' : `Show all (${documents.length})` }}
          </button>
        </div>
      </div>
      <div v-else-if="!collapsedFilters" class="sidebar__empty">No documents to filter.</div>
    </section>
    <section class="sidebar__section">
      <header class="sidebar__header">
        <h2 class="sidebar__title">Document Library</h2>
        <div class="sidebar__header-actions">
          <button class="header-toggle" type="button" @click="collapsedLibrary = !collapsedLibrary">
            {{ collapsedLibrary ? 'Expand' : 'Collapse' }}
          </button>
        </div>
        <p class="sidebar__subtitle">
          Manage Google Drive imports and local uploads. Link documents to nodes via the context menu or details panel.
        </p>
      </header>
      <div v-if="collapsedLibrary"></div>
      <div v-else-if="documents.length === 0" class="sidebar__empty">
        No documents yet. Import files to begin building your graph.
      </div>
      <ul v-else class="doc-list">
        <li v-for="doc in documentsPreview" :key="doc.id" class="doc-list__item">
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
      <div v-if="!collapsedLibrary && documents.length > libraryLimit" class="list-footer">
        <button class="link-btn" type="button" @click="showAllLibrary = !showAllLibrary">
          {{ showAllLibrary ? 'Show less' : `Show all (${documents.length})` }}
        </button>
      </div>
    </section>

    <section class="sidebar__section">
      <header class="sidebar__header">
        <h2 class="sidebar__title">Network Analytics</h2>
        <div class="sidebar__header-actions">
          <button class="header-toggle" type="button" @click="collapsedMetrics = !collapsedMetrics">
            {{ collapsedMetrics ? 'Expand' : 'Collapse' }}
          </button>
        </div>
        <p class="sidebar__subtitle">
          Metrics refresh automatically as you edit the graph.
        </p>
      </header>
      <template v-if="!collapsedMetrics">
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
        <p v-if="metrics.connectivity.isolates.length" class="metric-card__note isolates-line">
          <span>Isolated:</span>
          <span class="isolates-text">
            <template v-if="!showAllIsolates && metrics.connectivity.isolates.length > isolatesLimit">
              {{ metrics.connectivity.isolates.slice(0, isolatesLimit).join(', ') }}
              <span class="isolates-extra"> (+{{ metrics.connectivity.isolates.length - isolatesLimit }} more)</span>
            </template>
            <template v-else>
              {{ metrics.connectivity.isolates.join(', ') }}
            </template>
          </span>
          <button
            v-if="metrics.connectivity.isolates.length > isolatesLimit"
            class="link-btn"
            type="button"
            @click="showAllIsolates = !showAllIsolates"
          >{{ showAllIsolates ? 'Show less' : 'Show all' }}</button>
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
        <div class="metric-card__header-row">
          <h3 class="metric-card__label">Communities</h3>
          <label class="community-toggle">
            <input type="checkbox" :checked="showCommunities" @change="toggleCommunities" />
            Show communities
          </label>
        </div>
        <p class="metric-card__note" v-if="metrics.communities.clusters.length">Total: {{ metrics.communities.clusters.length }}</p>
        <ul v-if="metrics.communities.clusters.length" class="metric-card__list metric-card__list--scroll">
          <li v-for="cluster in communitiesForDisplay" :key="cluster.id">
            {{ cluster.label }} · {{ cluster.nodeIds.length }} nodes
          </li>
        </ul>
        <p v-else class="metric-card__note">No clusters detected yet.</p>
        <div v-if="metrics.communities.clusters.length > communitiesLimit" class="list-footer">
          <button class="link-btn" type="button" @click="showAllCommunities = !showAllCommunities">
            {{ showAllCommunities ? 'Show less' : `Show all (${metrics.communities.clusters.length})` }}
          </button>
        </div>
      </article>
      </template>
    </section>
  </aside>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useGraphStore } from '@/stores/graphStore'

const graphStore = useGraphStore()
const { documents, metrics, visibleDocumentIds, showCommunities } = storeToRefs(graphStore)

// Collapsible sections
const collapsedFilters = ref(false)
const collapsedLibrary = ref(true)
const collapsedMetrics = ref(false)

// List limiting to avoid scroll while fitting viewport
const filterLimit = 6
const libraryLimit = 5
const showAllFilters = ref(false)
const showAllLibrary = ref(false)
const documentsForFilter = computed(() => (showAllFilters.value ? documents.value : documents.value.slice(0, filterLimit)))
const documentsPreview = computed(() => (showAllLibrary.value ? documents.value : documents.value.slice(0, libraryLimit)))

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

// UI controls for analytics limits
const isolatesLimit = 10
const showAllIsolates = ref(false)

const communitiesLimit = 8
const showAllCommunities = ref(false)
const communitiesForDisplay = computed(() => {
  const clusters = metrics.value.communities.clusters || []
  return showAllCommunities.value ? clusters : clusters.slice(0, communitiesLimit)
})
</script>

<style scoped>
.sidebar {
  width: 320px;
  display: flex;
  flex-direction: column;
  gap: var(--space-14);
  padding: var(--space-14) var(--space-14) 18px var(--space-14);
  background: var(--surface-1);
  border-right: 1px solid var(--border);
  box-shadow: inset -1px 0 0 var(--border-subtle);
  /* Avoid internal scrolling; content is constrained via limits */
  height: 100%;
  min-height: 0; /* allow internal scrolling in grid */
}

.sidebar__section {
  display: flex;
  flex-direction: column;
  gap: var(--space-10);
  padding: var(--space-10);
  background: var(--surface-muted);
  border-radius: var(--radius-12);
  border: 1px solid var(--border);
}

.visibility-controls {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.visibility-actions {
  display: flex;
  gap: var(--space-8);
}

.visibility-btn { border: 1px solid var(--action-bg); background: var(--action-bg); color: var(--action-fg); font-size: var(--font-size-12); font-weight: var(--font-weight-bold); padding: 4px 10px; border-radius: var(--radius-6); cursor: pointer; }

.visibility-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.visibility-item { background: var(--surface-1); border: 1px solid var(--border); border-radius: var(--radius-8); padding: 6px 8px; }
.visibility-item label { display: flex; align-items: center; gap: 8px; width: 100%; overflow: hidden; }
.visibility-item input { flex: 0 0 auto; }

.doc-label {
  color: var(--color-brand-700);
  font-size: var(--font-size-13);
  flex: 1 1 auto;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar__header {
  display: flex;
  flex-direction: column;
  gap: 6px;
  position: relative;
}

.sidebar__title {
  font-size: var(--font-size-14);
  font-weight: var(--font-weight-bold);
  letter-spacing: 0.01em;
  color: var(--color-brand-700);
}

.sidebar__subtitle {
  font-size: var(--font-size-12);
  color: var(--text-muted);
}

.sidebar__empty {
  min-height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 12px;
  border: 1px dashed var(--border-strong);
  border-radius: var(--radius-10);
  color: var(--text-muted);
  font-size: var(--font-size-13);
}

.doc-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.doc-list__item { padding: 12px; border-radius: 12px; border: 1px solid var(--border); background: var(--surface-1); display: flex; align-items: center; gap: 12px; transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease; }
.doc-list__item:hover { border-color: var(--border-strong); box-shadow: var(--shadow-1); transform: translateY(-1px); }

.doc-list__meta {
  display: flex;
  flex: 1;
  min-width: 0;
  flex-direction: column;
  gap: 4px;
}

.doc-list__title {
  font-weight: var(--font-weight-bold);
  color: var(--color-brand-700);
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.doc-list__info {
  font-size: var(--font-size-12);
  color: var(--text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.doc-list__description {
  font-size: var(--font-size-11);
  color: var(--text-subtle);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.doc-list__actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: var(--space-6);
  flex-shrink: 0;
  min-width: 72px;
}

.doc-list__status { font-size: var(--font-size-11); text-transform: uppercase; letter-spacing: 0.05em; font-weight: var(--font-weight-bold); padding: 4px 10px; border-radius: var(--radius-pill); background: var(--pill-bg); color: var(--pill-fg); border: 1px solid var(--pill-border); }
.doc-list__status[data-status='processing'] { background: var(--status-processing-bg); color: var(--status-processing-fg); }
.doc-list__status[data-status='ready'] { background: var(--status-ready-bg); color: var(--status-ready-fg); }
.doc-list__status[data-status='error'] { background: var(--status-error-bg); color: var(--status-error-fg); }

.doc-list__delete { border: 1px solid color-mix(in srgb, var(--color-danger-600) 45%, white); background: var(--surface-1); color: var(--color-danger-600); font-size: var(--font-size-11); text-transform: uppercase; letter-spacing: 0.05em; font-weight: var(--font-weight-bold); cursor: pointer; padding: 4px 10px; border-radius: var(--radius-pill); }
.doc-list__delete:hover { background: var(--status-error-bg); border-color: color-mix(in srgb, var(--color-danger-600) 70%, white); }

.metric-card { padding: 12px 14px; background: var(--surface-1); border-radius: var(--radius-14); border: 1px solid var(--border); display: flex; flex-direction: column; gap: var(--space-8); }

.metric-card__label { font-size: var(--font-size-14); font-weight: var(--font-weight-bold); color: var(--color-brand-700); }

.metric-card__list { list-style: none; display: flex; flex-direction: column; gap: 4px; font-size: var(--font-size-13); color: var(--text); }
.metric-card__list--scroll { max-height: 180px; overflow: auto; }

.metric-card__note { font-size: var(--font-size-12); color: var(--text-muted); }

.community-toggle { margin-top: var(--space-8); font-size: var(--font-size-13); color: var(--color-brand-700); }
.metric-card__header-row { display: flex; align-items: center; justify-content: space-between; }
.isolates-line { display: flex; flex-wrap: wrap; gap: 6px; }
.isolates-text { flex: 1 1 auto; }
.isolates-extra { color: var(--text-subtle); }

.sidebar__header-actions { position: absolute; top: 0; right: 0; }
.header-toggle { border: 1px solid var(--border-strong); background: var(--surface-1); color: var(--color-brand-700); border-radius: var(--radius-8); font-size: var(--font-size-11); font-weight: var(--font-weight-bold); padding: 4px 8px; cursor: pointer; }

.link-btn { background: transparent; border: none; color: var(--color-brand-700); font-weight: var(--font-weight-bold); cursor: pointer; padding: 0; text-decoration: underline; }
.list-footer { display: flex; justify-content: flex-end; margin-top: 6px; }

@media (max-width: 1200px) {
  .sidebar {
    width: 280px;
  }
}
</style>
