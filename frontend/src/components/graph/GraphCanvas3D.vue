<template>
  <section class="graph-canvas" role="presentation" aria-label="Knowledge graph 3D">
    <div class="graph-canvas__controls">
      <button type="button" class="graph-control" @click="fit" :disabled="!hasGraph">
        Fit
      </button>
      <button type="button" class="graph-control" @click="zoom(+1)" :disabled="!hasGraph">
        +
      </button>
      <button type="button" class="graph-control" @click="zoom(-1)" :disabled="!hasGraph">
        -
      </button>
    </div>
    <div ref="containerRef" class="graph-canvas__surface" />
    <div v-if="showPlaceholder" class="graph-canvas__placeholder">
      <h2>Knowledge Graph Workspace (3D)</h2>
      <p>Click nodes/edges to select. Right-click a node for actions.</p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useGraphStore } from '@/stores/graphStore'
import type { GraphNode } from '@/types/graph'

const emit = defineEmits<{
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
const { visibleNodes: nodes, visibleEdges: edges, selection, showCommunities, communityAssignments } = storeToRefs(graphStore)

const containerRef = ref<HTMLDivElement | null>(null)
let fg: any = null
const cleanupHandlers = ref<Array<() => void>>([])

const showPlaceholder = computed(() => nodes.value.length === 0)
const hasGraph = computed(() => nodes.value.length > 0 || edges.value.length > 0)

onMounted(async () => {
  if (!containerRef.value) return
  const ForceGraph3D = (await import('3d-force-graph')).default
  // const { default: SpriteText } = await import('three-spritetext')
  const THREE = await import('three')

  fg = ForceGraph3D()(containerRef.value)
    .nodeId('id')
    .nodeLabel('label')
    .nodeColor((n: any) => nodeFill(n))
    .linkColor(() => '#6080b3')
    .linkWidth((l: any) => (selection.value.edgeId === l.id ? 3 : 1.5))
    // Enable if you want edge labels now; commented to keep performance high by default
    // .linkThreeObject((link: any) => {
    //   const sprite = new SpriteText(link.predicate || '')
    //   sprite.color = '#4a5d80'
    //   sprite.textHeight = 2
    //   return sprite
    // })
    // .linkThreeObjectExtend(true)
    .onNodeClick((n: any) => {
      graphStore.setSelection({ nodeId: n.id, edgeId: null })
    })
    .onLinkClick((l: any) => {
      graphStore.setSelection({ nodeId: null, edgeId: l.id })
    })
    .onNodeRightClick((n: any, ev: MouseEvent) => {
      if (!containerRef.value) return
      const rect = containerRef.value.getBoundingClientRect()
      emit('request-node-context', {
        nodeId: n.id,
        renderedPosition: { x: ev.clientX - rect.left, y: ev.clientY - rect.top },
        position: { x: n.x ?? 0, y: n.y ?? 0 },
        containerRect: rect
      })
    })
    .onNodeDragEnd((n: any) => {
      // freeze the node's position after dragging
      n.fx = n.x
      n.fy = n.y
      n.fz = n.z
      graphStore.updateNode(n.id, { position: { x: n.x, y: n.y, z: n.z } })
    })

  // enable intuitive camera panning/controls
  try {
    const controls: any = fg.controls()
    if (controls) {
      controls.enablePan = true
      controls.screenSpacePanning = true
      controls.enableDamping = true
      controls.dampingFactor = 0.08
      controls.update?.()
    }
  } catch {}

  // initial data
  syncData()
  // let bounds settle
  setTimeout(() => fit(), 0)

  // Allow Command (Meta) + left-drag to pan
  const setPanMode = (active: boolean) => {
    try {
      const controls: any = fg?.controls()
      if (!controls) return
      controls.mouseButtons = controls.mouseButtons || {}
      controls.mouseButtons.LEFT = active ? THREE.MOUSE.PAN : THREE.MOUSE.ROTATE
      controls.update?.()
    } catch {}
  }

  const handlePointerDown = (e: PointerEvent) => {
    if (e.metaKey) setPanMode(true)
  }
  const handlePointerUp = () => setPanMode(false)
  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Meta') setPanMode(true)
  }
  const handleKeyUp = (e: KeyboardEvent) => {
    if (e.key === 'Meta') setPanMode(false)
  }

  containerRef.value.addEventListener('pointerdown', handlePointerDown)
  window.addEventListener('pointerup', handlePointerUp)
  window.addEventListener('keydown', handleKeyDown)
  window.addEventListener('keyup', handleKeyUp)

  // store cleanup on component instance for removal
  ;(cleanupHandlers as any).value = [
    () => containerRef.value?.removeEventListener('pointerdown', handlePointerDown),
    () => window.removeEventListener('pointerup', handlePointerUp),
    () => window.removeEventListener('keydown', handleKeyDown),
    () => window.removeEventListener('keyup', handleKeyUp)
  ]
})

onBeforeUnmount(() => {
  try {
    ;(cleanupHandlers.value || []).forEach((fn) => fn())
  } catch {}
  fg = null
})

watch([nodes, edges], () => {
  syncData()
}, { deep: true })

watch([showCommunities, communityAssignments], () => {
  if (!fg) return
  fg.nodeColor((n: any) => nodeFill(n))
})

watch(selection, () => {
  if (!fg) return
  fg.linkWidth((l: any) => (selection.value.edgeId === l.id ? 3 : 1.5))
  fg.nodeColor((n: any) => nodeFill(n))
}, { deep: true })

function syncData() {
  if (!fg) return
  const g = {
    nodes: nodes.value.map((n) => ({ id: n.id, label: n.label, type: n.type, ...n.position })),
    links: edges.value.map((e) => ({ id: e.id, source: e.source, target: e.target, predicate: e.predicate }))
  }
  fg.graphData(g)
}

const COMMUNITY_PALETTE = ['#6e40aa', '#ff6e54', '#2a9d8f', '#e76f51', '#457b9d', '#f4a261', '#8ab17d', '#e9c46a', '#118ab2', '#ef476f']

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

function nodeFill(n: any) {
  if (showCommunities.value) {
    const cid = communityAssignments.value[n.id]
    return COMMUNITY_PALETTE[cid % COMMUNITY_PALETTE.length] || '#cfd8dc'
  }
  return nodeTypeColor(n.type)
}

function fit() {
  if (!fg) return
  fg.zoomToFit(400, 60)
}

function zoom(dir: 1 | -1) {
  if (!fg) return
  const cam = fg.camera()
  const { x, y, z } = cam.position
  const factor = dir > 0 ? 0.8 : 1.25
  fg.cameraPosition({ x: x * factor, y: y * factor, z: z * factor }, undefined, 300)
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
