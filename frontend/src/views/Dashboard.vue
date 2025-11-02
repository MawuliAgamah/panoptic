<template>
  <DashboardShell>
    <template #default>
      <div class="graph-mode-toolbar">
        <label>
          View:
          <select v-model="mode">
            <option value="2d">2D</option>
            <option value="3d">3D</option>
          </select>
        </label>
      </div>

      <GraphCanvas
        v-if="mode === '2d'"
        @request-node-create="handleNodeCreateRequest"
        @request-node-context="handleNodeContextRequest"
      />
      <GraphCanvas3D
        v-else
        @request-node-context="handleNodeContextRequest"
      />
    </template>
  </DashboardShell>

  <NodeFormDialog
    :visible="isNodeDialogOpen"
    @close="closeNodeDialog"
    @submit="handleNodeCreateSubmit"
  />

  <NodeContextMenu
    :visible="contextMenu.visible"
    :position="contextMenu.position"
    :node-label="contextMenu.nodeLabel"
    @action="handleContextMenuAction"
  />

  <DetailsDrawer />
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import DashboardShell from '@/components/layout/DashboardShell.vue'
import GraphCanvas from '@/components/graph/GraphCanvas.vue'
import GraphCanvas3D from '@/components/graph/GraphCanvas3D.vue'
import NodeFormDialog from '@/components/graph/NodeFormDialog.vue'
import NodeContextMenu from '@/components/graph/NodeContextMenu.vue'
import { useGraphStore } from '@/stores/graphStore'
import DetailsDrawer from '@/components/layout/DetailsDrawer.vue'
import { useUiStore } from '@/stores/uiStore'

const graphStore = useGraphStore()
const { nodes, selection } = storeToRefs(graphStore)
const ui = useUiStore()

const isNodeDialogOpen = ref(false)
const pendingPosition = ref<{ x: number; y: number } | null>(null)
const mode = ref<'2d' | '3d'>('3d')

const contextMenu = reactive({
  visible: false,
  nodeId: '',
  nodeLabel: '',
  position: null as { x: number; y: number } | null
})

function handleNodeCreateRequest(event: { position: { x: number; y: number } }) {
  pendingPosition.value = event.position
  isNodeDialogOpen.value = true
  hideContextMenu()
}

function handleNodeCreateSubmit(payload: { label: string; type: string; description?: string }) {
  graphStore.addNode({
    label: payload.label,
    type: payload.type as any,
    description: payload.description,
    position: pendingPosition.value ?? undefined
  })
  pendingPosition.value = null
  isNodeDialogOpen.value = false
}

function closeNodeDialog() {
  isNodeDialogOpen.value = false
  pendingPosition.value = null
}

function handleNodeContextRequest(payload: {
  nodeId: string
  renderedPosition: { x: number; y: number }
  containerRect?: { top: number; left: number }
}) {
  const node = nodes.value.find((n) => n.id === payload.nodeId)
  contextMenu.nodeId = payload.nodeId
  contextMenu.nodeLabel = node?.label ?? 'Node'
  contextMenu.position = payload.containerRect
    ? {
        x: payload.containerRect.left + payload.renderedPosition.x,
        y: payload.containerRect.top + payload.renderedPosition.y
      }
    : {
        x: payload.renderedPosition.x,
        y: payload.renderedPosition.y
      }
  contextMenu.visible = true
}

function handleContextMenuAction(action: 'link' | 'extract' | 'merge') {
  const nodeId = contextMenu.nodeId
  if (!nodeId) return

  graphStore.setSelection({ nodeId, edgeId: null })

  switch (action) {
    case 'link':
      // Focus details panel for linking.
      break
    case 'extract': {
      const node = nodes.value.find((candidate) => candidate.id === nodeId)
      const docId = node?.documents[0]
      if (node && docId) {
        graphStore.triggerExtraction(nodeId, docId).catch((error) => {
          console.error('Extraction failed', error)
        })
      }
      break
    }
    case 'merge':
      console.info('Merge action selected. Implement merge workflow as a next iteration.')
      break
  }

  hideContextMenu()
}

function hideContextMenu() {
  contextMenu.visible = false
  contextMenu.position = null
}

function handleGlobalClick(event: MouseEvent) {
  if (!(event.target as HTMLElement).closest('.context-menu')) {
    hideContextMenu()
  }
}

onMounted(() => {
  window.addEventListener('click', handleGlobalClick)
  graphStore.loadGraph().catch((error) => {
    console.error('Failed to load graph snapshot', error)
  })
})

onUnmounted(() => {
  window.removeEventListener('click', handleGlobalClick)
})

// Open drawer when a node/edge is selected; close when nothing selected
watch(selection, (sel) => {
  if (sel.nodeId || sel.edgeId) ui.openDetails()
  else ui.closeDetails()
}, { deep: true })
</script>

<style scoped>
.graph-mode-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 8px;
}

.graph-mode-toolbar select {
  border: 1px solid rgba(15, 49, 103, 0.15);
  background: rgba(255, 255, 255, 0.92);
  color: #0f3167;
  font-size: 12px;
  font-weight: 600;
  padding: 6px 10px;
  border-radius: 8px;
}
</style>
