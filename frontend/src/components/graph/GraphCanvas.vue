<template>
  <section class="graph-canvas" role="presentation" aria-label="Knowledge graph canvas">
    <div class="graph-canvas__controls">
      <select class="layout-select" v-model="layoutChoice" @change="runAutoLayout" :disabled="!hasGraph">
        <option value="auto">Auto</option>
        <option value="fcose" :disabled="!availableLayouts.fcose">Force (fCoSE)</option>
        <option value="cose-bilkent" :disabled="!availableLayouts.coseBilkent">Force (CoSE Bilkent)</option>
        <option value="dagre" :disabled="!availableLayouts.dagre">Hierarchy (Dagre)</option>
        <option value="breadthfirst">Hierarchy (Breadthfirst)</option>
        <option value="grid">Grid</option>
      </select>
      <button type="button" class="graph-control" @click="runAutoLayout" :disabled="!hasGraph">
        Layout
      </button>
      <button type="button" class="graph-control" @click="fitToView" :disabled="!hasGraph">
        Fit
      </button>
      <button type="button" class="graph-control" @click="zoomIn" :disabled="!hasGraph">
        +
      </button>
      <button type="button" class="graph-control" @click="zoomOut" :disabled="!hasGraph">
        -
      </button>
    </div>
    <div ref="containerRef" class="graph-canvas__surface" />
    <div v-if="showPlaceholder" class="graph-canvas__placeholder">
      <h2>Knowledge Graph Workspace</h2>
      <p>
        Double-click the canvas to add a node. Right-click nodes to manage documents or trigger
        extraction.
      </p>
    </div>
  </section>
</template>

<script setup lang="ts">
import cytoscape, { type Core, type EventObject, type NodeSingular } from 'cytoscape'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useGraphStore } from '@/stores/graphStore'
import type { GraphNode } from '@/types/graph'

const emit = defineEmits<{
  (event: 'request-node-create', payload: { position: { x: number; y: number } }): void
  (
    event: 'request-node-context',
    payload: {
      nodeId: string
      renderedPosition: { x: number; y: number }
      position: { x: number; y: number }
      containerRect?: { top: number; left: number }
    }
  ): void
}>()

const graphStore = useGraphStore()
const { visibleNodes: nodes, visibleEdges: edges, selection, showCommunities, communityAssignments, focusTarget } = storeToRefs(graphStore)

const containerRef = ref<HTMLDivElement | null>(null)
let cy: Core | null = null

const showPlaceholder = computed(() => nodes.value.length === 0)
const hasGraph = computed(() => nodes.value.length > 0 || edges.value.length > 0)

onMounted(async () => {
  if (!containerRef.value) return
  await registerLayouts()
  cy = cytoscape({
    container: containerRef.value,
    boxSelectionEnabled: false,
    autounselectify: false,
    style: graphStyles(),
    layout: { name: 'preset' },
    wheelSensitivity: 0.2
  })

  bindGraphEvents()
  syncNodes(nodes.value)
  syncEdges(edges.value)
})

onBeforeUnmount(() => {
  cy?.destroy()
  cy = null
})

watch(
  nodes,
  (newNodes, oldNodes) => {
    if (!cy) return
    syncNodes(newNodes)
    if (oldNodes.length === 0 && newNodes.length > 0) {
      runLayout()
    }
  },
  { deep: true }
)

watch(
  edges,
  (newEdges) => {
    if (!cy) return
    syncEdges(newEdges)
  },
  { deep: true }
)

watch(showCommunities, () => {
  if (!cy) return
  cy.style().update()
})

watch(communityAssignments, () => {
  if (!cy) return
  cy.style().update()
})

watch(
  selection,
  (selectionState) => {
    const instance = cy
    if (!instance) return
    instance.batch(() => {
      instance.nodes().unselect()
      instance.edges().unselect()
      if (selectionState.nodeId) {
        instance.$id(selectionState.nodeId).select()
      } else if (selectionState.edgeId) {
        instance.$id(selectionState.edgeId).select()
      }
    })
  },
  { deep: true }
)

// Pan/zoom to requested focus target (node or edge) from store, then clear
watch(
  focusTarget,
  (target) => {
    if (!cy || !target) return
    const ele = cy.$id(target.id)
    if (ele && ele.length > 0) {
      try {
        cy.fit(ele, 60)
      } catch (e) {
        // ignore fit errors
      }
    }
    graphStore.clearFocusTarget()
  },
  { deep: true }
)

function bindGraphEvents() {
  if (!cy) return
  cy.on('tap', (event: EventObject) => {
    if (event.target === cy) {
      graphStore.setSelection({ nodeId: null, edgeId: null })
    }
  })

  cy.on('tap', 'node', (event) => {
    graphStore.setSelection({ nodeId: event.target.id(), edgeId: null })
  })

  cy.on('tap', 'edge', (event) => {
    graphStore.setSelection({ nodeId: null, edgeId: event.target.id() })
  })

  cy.on('cxttap', 'node', (event) => {
    const rect = containerRef.value?.getBoundingClientRect()
    emit('request-node-context', {
      nodeId: event.target.id(),
      renderedPosition: event.renderedPosition,
      position: event.position,
      containerRect: rect
    })
  })

  cy.on('dragfree', 'node', (event) => {
    const position = event.target.position()
    graphStore.updateNode(event.target.id(), { position })
  })

  cy.on('dbltap', (event) => {
    if (event.target === cy) {
      emit('request-node-create', { position: event.position })
    }
  })
}

function syncNodes(graphNodes: GraphNode[]) {
  if (!cy) return
  const existingIds = new Set<string>()
  cy.nodes().forEach((element) => {
    const stillExists = graphNodes.some((node) => node.id === element.id())
    if (!stillExists) {
      element.remove()
    } else {
      existingIds.add(element.id())
    }
  })

  graphNodes.forEach((node) => {
    const element = cy!.$id(node.id)
    const position = node.position ?? generateFallbackPosition()
    if (element.length === 0) {
      cy!.add({
        group: 'nodes',
        data: {
          id: node.id,
          label: node.label,
          nodeType: node.type
        },
        position
      })
    } else {
      element.data({
        label: node.label,
        nodeType: node.type
      })
      if (node.position) {
        element.position(node.position)
      }
    }
  })
}

function syncEdges(graphEdges: typeof edges.value) {
  if (!cy) return
  cy.edges().forEach((edge) => {
    const exists = graphEdges.some((candidate) => candidate.id === edge.id())
    if (!exists) {
      edge.remove()
    }
  })

  graphEdges.forEach((edge) => {
    const element = cy!.$id(edge.id)
    if (element.length === 0) {
      cy!.add({
        group: 'edges',
        data: {
          id: edge.id,
          source: edge.source,
          target: edge.target,
          label: edge.predicate
        }
      })
    } else {
      element.data('label', edge.predicate)
    }
  })
}

const availableLayouts = ref({ fcose: false, coseBilkent: false, dagre: false })
const layoutChoice = ref<'auto' | 'fcose' | 'cose-bilkent' | 'dagre' | 'breadthfirst' | 'grid'>('breadthfirst')

async function registerLayouts() {
  try {
    const mod = await import(/* @vite-ignore */ 'cytoscape-fcose')
    // @ts-ignore - plugin default export varies
    cytoscape.use(mod.default || mod)
    availableLayouts.value.fcose = true
  } catch (e) {
    console.warn('[graph] fcose not available, will fallback')
  }
  try {
    const mod = await import(/* @vite-ignore */ 'cytoscape-cose-bilkent')
    // @ts-ignore
    cytoscape.use(mod.default || mod)
    availableLayouts.value.coseBilkent = true
  } catch (e) {
    console.warn('[graph] cose-bilkent not available, will fallback')
  }
  try {
    const mod = await import(/* @vite-ignore */ 'cytoscape-dagre')
    // @ts-ignore
    cytoscape.use(mod.default || mod)
    availableLayouts.value.dagre = true
  } catch (e) {
    console.warn('[graph] dagre not available, will fallback')
  }
}

function runLayout() {
  if (!cy) return
  let name: string
  let options: any = { animate: false }
  const nodeCount = cy.nodes().length
  const edgeCount = cy.edges().length

  const pickAuto = () => {
    if (availableLayouts.value.fcose) return 'fcose'
    if (availableLayouts.value.coseBilkent) return 'cose-bilkent'
    return 'cose'
  }

  switch (layoutChoice.value) {
    case 'fcose':
      name = availableLayouts.value.fcose ? 'fcose' : pickAuto()
      options = {
        name,
        animate: false,
        quality: 'default',
        randomize: true,
        idealEdgeLength: 150,
        nodeRepulsion: 4500,
        gravity: 0.25,
        componentSpacing: 120
      }
      break
    case 'cose-bilkent':
      name = availableLayouts.value.coseBilkent ? 'cose-bilkent' : pickAuto()
      options = {
        name,
        animate: false,
        randomize: true,
        idealEdgeLength: 150,
        nodeRepulsion: 4500,
        gravity: 0.25,
        nodeDimensionsIncludeLabels: true
      }
      break
    case 'dagre':
      name = availableLayouts.value.dagre ? 'dagre' : pickAuto()
      options = {
        name,
        animate: false,
        rankDir: 'LR',
        nodeSep: 60,
        edgeSep: 30,
        rankSep: 120
      }
      break
    case 'breadthfirst':
      name = 'breadthfirst'
      options = {
        name,
        animate: false,
        directed: false,
        circle: false,
        grid: false,
        spacingFactor: 1.1,
        padding: 20
      }
      break
    case 'grid':
      name = 'grid'
      options = { name, fit: false, avoidOverlap: true }
      break
    case 'auto':
    default:
      name = pickAuto()
      options = { name, animate: false, idealEdgeLength: 140 }
  }

  cy.layout(options).run()
}

function runAutoLayout() {
  runLayout()
  fitToView()
}

function fitToView() {
  if (!cy) return
  cy.fit(undefined, 60)
}

function zoomIn() {
  if (!cy) return
  const current = cy.zoom()
  cy.zoom({
    level: Math.min(current + 0.2, 2.5),
    renderedPosition: cy.renderedCenter()
  })
}

function zoomOut() {
  if (!cy) return
  const current = cy.zoom()
  cy.zoom({
    level: Math.max(current - 0.2, 0.2),
    renderedPosition: cy.renderedCenter()
  })
}

function generateFallbackPosition() {
  return {
    x: Math.random() * 500 + 200,
    y: Math.random() * 400 + 200
  }
}

function graphStyles() {
  return [
    {
      selector: 'core',
      style: {
        'active-bg-color': '#0F3167',
        'active-bg-opacity': 0.1
      }
    },
    {
      selector: '.faded',
      style: {
        opacity: 0.15
      }
    },
    {
      selector: 'node',
      style: {
        label: 'data(label)',
        'font-size': 12,
        'text-valign': 'center',
        'text-halign': 'center',
        color: '#0f3167',
        'background-color': (ele: NodeSingular) => nodeFill(ele),
        'border-width': 2,
        'border-color': '#ffffff',
        'border-opacity': 0.9,
        'text-outline-width': 2,
        'text-outline-color': '#ffffff',
        'overlay-opacity': 0
      }
    },
    {
      selector: 'node:selected',
      style: {
        'border-color': '#0f3167',
        'border-width': 3,
        'background-color': '#0f3167',
        color: '#ffffff',
        'text-outline-color': '#0f3167'
      }
    },
    {
      selector: 'edge',
      style: {
        label: 'data(label)',
        'curve-style': 'bezier',
        'target-arrow-shape': 'triangle',
        width: 2,
        'line-color': '#6080b3',
        'target-arrow-color': '#6080b3',
        'font-size': 10,
        color: '#4a5d80',
        'text-background-opacity': 0.8,
        'text-background-color': '#fff',
        'text-background-padding': 2
      }
    },
    {
      selector: 'edge:selected',
      style: {
        'line-color': '#0f3167',
        'target-arrow-color': '#0f3167',
        width: 3
      }
    }
  ] as any
}

function nodeTypeColor(nodeType: GraphNode['type']) {
  switch (nodeType) {
    case 'person':
      return '#99c1ff'
    case 'organization':
      return '#f7b267'
    case 'concept':
      return '#9dbf9e'
    case 'event':
      return '#f48498'
    case 'location':
      return '#d6a2e8'
    default:
      return '#cfd8dc'
  }
}

const COMMUNITY_PALETTE = ['#6e40aa', '#ff6e54', '#2a9d8f', '#e76f51', '#457b9d', '#f4a261', '#8ab17d', '#e9c46a', '#118ab2', '#ef476f']

function nodeFill(ele: NodeSingular) {
  if (showCommunities.value) {
    const id = ele.id()
    const communityId = communityAssignments.value[id]
    const color = COMMUNITY_PALETTE[communityId % COMMUNITY_PALETTE.length] || '#cfd8dc'
    return color
  }
  return nodeTypeColor(ele.data('nodeType'))
}
</script>

<style scoped>
.graph-canvas {
  flex: 1;
  min-height: 0;
  position: relative;
  border-radius: 24px;
  border: 1px solid rgba(15, 49, 103, 0.08);
  background:
    linear-gradient(rgba(15, 49, 103, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(15, 49, 103, 0.05) 1px, transparent 1px),
    radial-gradient(circle at 20% 20%, rgba(15, 49, 103, 0.08), transparent 35%),
    rgba(255, 255, 255, 0.92);
  background-size: 32px 32px, 32px 32px, 100% 100%, 100% 100%;
  overflow: hidden;
}

.graph-canvas__surface {
  width: 100%;
  height: 100%;
}

.graph-canvas__controls {
  position: absolute;
  top: 16px;
  right: 16px;
  display: flex;
  gap: 8px;
  z-index: 2;
}

.layout-select {
  border: 1px solid rgba(15, 49, 103, 0.15);
  background: rgba(255, 255, 255, 0.92);
  color: #0f3167;
  font-size: 12px;
  font-weight: 600;
  padding: 6px 10px;
  border-radius: 8px;
}

.graph-control {
  border: 1px solid rgba(15, 49, 103, 0.15);
  background: rgba(255, 255, 255, 0.92);
  color: #0f3167;
  font-size: 12px;
  font-weight: 600;
  padding: 6px 10px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease, color 0.2s ease;
}

.graph-control:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.graph-control:not(:disabled):hover {
  background: rgba(15, 49, 103, 0.08);
  border-color: rgba(15, 49, 103, 0.25);
}

.graph-canvas__placeholder {
  position: absolute;
  inset: 40px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  gap: 12px;
  background: rgba(255, 255, 255, 0.92);
  border-radius: 20px;
  border: 1px dashed rgba(15, 49, 103, 0.18);
  pointer-events: none;
}

.graph-canvas__placeholder h2 {
  font-size: 20px;
  font-weight: 600;
  color: #0f3167;
}

.graph-canvas__placeholder p {
  max-width: 420px;
  font-size: 14px;
  color: rgba(18, 20, 23, 0.7);
}
</style>
