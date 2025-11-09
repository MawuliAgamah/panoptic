<template>
  <Teleport to="body">
    <!-- Toggle button shown when drawer is closed -->
    <button
      v-if="!dataDrawerOpen"
      class="dataset-toggle"
      type="button"
      @click="openDataDrawer"
      aria-label="Open dataset drawer"
    >
      Dataset
    </button>

    <!-- Bottom drawer -->
    <section v-if="dataDrawerOpen" class="dataset-drawer" role="dialog" aria-modal="true">
      <header class="dataset-header">
        <div class="dataset-header__left">
          <h2 class="dataset-title">Relations</h2>
          <span class="dataset-count">{{ sortedRows.length }} items</span>
        </div>
        <div class="dataset-header__right">
          <button class="dataset-action" type="button" @click="closeDataDrawer">Close</button>
        </div>
      </header>

      <div class="dataset-body">
        <div v-if="sortedRows.length === 0" class="dataset-empty">
          No relations to show. Import documents or adjust filters.
        </div>
        <table v-else class="dataset-table">
          <thead>
            <tr>
              <th @click="toggleSort('docTitle')">
                Document
                <span class="sort-indicator" :data-active="sortKey==='docTitle'" :data-dir="sortDir"></span>
              </th>
              <th @click="toggleSort('sourceLabel')">
                Source
                <span class="sort-indicator" :data-active="sortKey==='sourceLabel'" :data-dir="sortDir"></span>
              </th>
              <th @click="toggleSort('predicate')">
                Relationship
                <span class="sort-indicator" :data-active="sortKey==='predicate'" :data-dir="sortDir"></span>
              </th>
              <th @click="toggleSort('targetLabel')">
                Target
                <span class="sort-indicator" :data-active="sortKey==='targetLabel'" :data-dir="sortDir"></span>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in sortedRows"
              :key="row.edgeId"
              @click="handleRowClick(row)"
              class="dataset-row"
            >
              <td>{{ row.docTitle }}</td>
              <td>{{ row.sourceLabel }}</td>
              <td>{{ row.predicate }}</td>
              <td>{{ row.targetLabel }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </Teleport>
  
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useGraphStore } from '@/stores/graphStore'
import { useUiStore } from '@/stores/uiStore'

const ui = useUiStore()
const { dataDrawerOpen } = storeToRefs(ui)
const { openDataDrawer, closeDataDrawer } = ui

const graphStore = useGraphStore()
const { visibleEdges, nodes, documents } = storeToRefs(graphStore)

type SortKey = 'docTitle' | 'sourceLabel' | 'predicate' | 'targetLabel'
const sortKey = ref<SortKey>('docTitle')
const sortDir = ref<'asc' | 'desc'>('asc')

function toggleSort(key: SortKey) {
  if (sortKey.value === key) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = key
    sortDir.value = 'asc'
  }
}

const nodeLabelMap = computed(() => {
  const map = new Map<string, string>()
  for (const n of nodes.value) map.set(n.id, n.label)
  return map
})

const docTitleMap = computed(() => {
  const map = new Map<string, string>()
  for (const d of documents.value) map.set(d.id, d.title)
  return map
})

const rows = computed(() => {
  return visibleEdges.value.map((e) => {
    // Resolve document title preference
    let docTitle: string | undefined
    if (e.sourceDocumentId) {
      docTitle = docTitleMap.value.get(e.sourceDocumentId)
    }
    if (!docTitle) {
      // fallback: source node's first linked doc
      const srcDocs = nodes.value.find((n) => n.id === e.source)?.documents ?? []
      docTitle = srcDocs.length ? docTitleMap.value.get(srcDocs[0]) : undefined
    }

    return {
      edgeId: e.id,
      sourceId: e.source,
      targetId: e.target,
      sourceLabel: nodeLabelMap.value.get(e.source) ?? e.source,
      targetLabel: nodeLabelMap.value.get(e.target) ?? e.target,
      predicate: e.predicate,
      docTitle: docTitle ?? '—'
    }
  })
})

const sortedRows = computed(() => {
  const key = sortKey.value
  const dir = sortDir.value === 'asc' ? 1 : -1
  return rows.value.slice().sort((a, b) => {
    const av = String(a[key]).toLocaleLowerCase()
    const bv = String(b[key]).toLocaleLowerCase()
    if (av < bv) return -1 * dir
    if (av > bv) return 1 * dir
    return 0
  })
})

function handleRowClick(row: { edgeId: string; sourceId: string }) {
  // Select the edge and pan/zoom to the source node
  graphStore.setSelection({ nodeId: null, edgeId: row.edgeId })
  graphStore.focusNode(row.sourceId)
}
</script>

<style scoped>
/* Bottom toggle button */
.dataset-toggle {
  position: fixed;
  left: 50%;
  transform: translateX(-50%);
  bottom: 12px;
  z-index: var(--z-drawer);
  border: 1px solid var(--border);
  background: var(--surface-2);
  color: var(--text);
  padding: 8px 14px;
  border-radius: var(--radius-pill);
  box-shadow: var(--shadow-1);
}

/* Drawer container */
.dataset-drawer {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  height: 40vh;
  background: var(--surface-overlay);
  backdrop-filter: blur(10px);
  border-top: 1px solid var(--border);
  box-shadow: 0 -12px 30px rgba(0, 0, 0, 0.35);
  z-index: var(--z-drawer);
  display: flex;
  flex-direction: column;
}

.dataset-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-bottom: 1px solid var(--border);
}
.dataset-header__left { display: flex; align-items: center; gap: 10px; }
.dataset-title { font-size: var(--font-size-14); color: var(--text); }
.dataset-count { font-size: var(--font-size-12); color: var(--text-muted); }
.dataset-header__right { display: flex; gap: 8px; }
.dataset-action { border: 1px solid var(--border); background: var(--surface-1); color: var(--text); padding: 6px 10px; border-radius: var(--radius-8); }

.dataset-body {
  flex: 1;
  overflow: auto;
  padding: 8px 12px 12px 12px;
}

.dataset-empty {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: var(--text-muted);
}

.dataset-table {
  width: 100%;
  border-collapse: collapse;
  background: var(--surface-1);
  border: 1px solid var(--border);
  border-radius: var(--radius-12);
  overflow: hidden;
}
.dataset-table thead tr th {
  text-align: left;
  font-size: var(--font-size-12);
  color: var(--text-muted);
  padding: 10px 12px;
  background: var(--surface-muted);
  border-bottom: 1px solid var(--border);
  cursor: pointer;
}

.dataset-table tbody tr.dataset-row {
  border-bottom: 1px solid var(--border);
}
.dataset-table tbody tr.dataset-row:hover {
  background: var(--surface-muted);
}
.dataset-table td {
  padding: 10px 12px;
  font-size: var(--font-size-13);
  color: var(--text);
}

.sort-indicator {
  display: inline-block;
  width: 8px;
  height: 8px;
  margin-left: 6px;
  border-right: 2px solid var(--text-muted);
  border-bottom: 2px solid var(--text-muted);
  transform: rotate(45deg);
  opacity: 0.35;
}
.sort-indicator[data-active="true"] { opacity: 0.9; }
.sort-indicator[data-dir="desc"][data-active="true"] { transform: rotate(-135deg); }

@media (max-width: 800px) {
  .dataset-drawer { height: 50vh; }
  .dataset-toggle { bottom: 10px; }
}
</style>
