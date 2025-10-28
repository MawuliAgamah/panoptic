<template>
  <DashboardShell>
    <template #default>
      <GraphCanvas
        @request-node-create="handleNodeCreateRequest"
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
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, reactive, ref } from 'vue'
import { storeToRefs } from 'pinia'
import DashboardShell from '@/components/layout/DashboardShell.vue'
import GraphCanvas from '@/components/graph/GraphCanvas.vue'
import NodeFormDialog from '@/components/graph/NodeFormDialog.vue'
import NodeContextMenu from '@/components/graph/NodeContextMenu.vue'
import { useGraphStore } from '@/stores/graphStore'

const graphStore = useGraphStore()
const { nodes } = storeToRefs(graphStore)

const isNodeDialogOpen = ref(false)
const pendingPosition = ref<{ x: number; y: number } | null>(null)

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
})

onUnmounted(() => {
  window.removeEventListener('click', handleGlobalClick)
})
</script>
