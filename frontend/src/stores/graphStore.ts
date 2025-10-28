import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import type {
  DocumentItem,
  GraphEdge,
  GraphMetrics,
  GraphNode,
  GraphSelection,
  GraphSnapshot,
  NodeCreationPayload,
  Triple
} from '@/types/graph'
import { calculateGraphMetrics } from '@/utils/graphMetrics'
import {
  fetchGraphSnapshot,
  saveGraphSnapshot,
  triggerExtractionForNode
} from '@/services/backend'

const METRICS_BASELINE: GraphMetrics = {
  totals: { nodes: 0, edges: 0, documents: 0 },
  connectivity: { components: 0, density: 0, averageDegree: 0, isolates: [] },
  influence: { topDegree: [] },
  communities: { clusters: [] },
  lastUpdated: new Date(0).toISOString()
}

export interface DocumentInput {
  id?: string
  title: string
  source: DocumentItem['source']
  mimeType?: string
  description?: string
  author?: string
  status?: DocumentItem['status']
  externalId?: string
  url?: string
}

export interface EdgeCreationPayload {
  source: string
  target: string
  predicate: string
  confidence?: number
  sourceDocumentId?: string
}

export const useGraphStore = defineStore('graph', () => {
  const nodes = ref<GraphNode[]>([])
  const edges = ref<GraphEdge[]>([])
  const documents = ref<DocumentItem[]>([])
  const selection = ref<GraphSelection>({ nodeId: null, edgeId: null })
  const metrics = ref<GraphMetrics>(METRICS_BASELINE)
  const isLoading = ref(false)
  const lastSavedAt = ref<string | null>(null)
  const errorMessage = ref<string | null>(null)

  const selectedNode = computed(() =>
    nodes.value.find((node) => node.id === selection.value.nodeId) ?? null
  )
  const selectedEdge = computed(() =>
    edges.value.find((edge) => edge.id === selection.value.edgeId) ?? null
  )

  function recomputeMetrics() {
    metrics.value = calculateGraphMetrics(nodes.value, edges.value, documents.value)
  }

  function setSelection(newSelection: GraphSelection) {
    selection.value = newSelection
  }

  function addNode(payload: NodeCreationPayload): GraphNode {
    const timestamp = new Date().toISOString()
    const node: GraphNode = {
      id: createGraphId('node'),
      label: payload.label,
      type: payload.type,
      description: payload.description,
      provenance: payload.provenance,
      position: payload.position,
      documents: [],
      triples: [],
      createdAt: timestamp,
      updatedAt: timestamp
    }

    nodes.value.push(node)
    selection.value = { nodeId: node.id, edgeId: null }
    recomputeMetrics()
    return node
  }

  function updateNode(nodeId: string, updates: Partial<Omit<GraphNode, 'id'>>) {
    const target = nodes.value.find((node) => node.id === nodeId)
    if (!target) return
    Object.assign(target, updates, { updatedAt: new Date().toISOString() })
    recomputeMetrics()
  }

  function removeNode(nodeId: string) {
    nodes.value = nodes.value.filter((node) => node.id !== nodeId)
    edges.value = edges.value.filter(
      (edge) => edge.source !== nodeId && edge.target !== nodeId
    )
    if (selection.value.nodeId === nodeId) {
      selection.value = { nodeId: null, edgeId: null }
    }
    recomputeMetrics()
  }

  function addEdge(payload: EdgeCreationPayload): GraphEdge {
    const timestamp = new Date().toISOString()
    const edge: GraphEdge = {
      id: createGraphId('edge'),
      source: payload.source,
      target: payload.target,
      predicate: payload.predicate,
      confidence: payload.confidence,
      sourceDocumentId: payload.sourceDocumentId,
      createdAt: timestamp,
      updatedAt: timestamp
    }

    edges.value.push(edge)
    selection.value = { nodeId: null, edgeId: edge.id }
    recomputeMetrics()
    return edge
  }

  function updateEdge(edgeId: string, updates: Partial<Omit<GraphEdge, 'id'>>) {
    const target = edges.value.find((edge) => edge.id === edgeId)
    if (!target) return
    Object.assign(target, updates, { updatedAt: new Date().toISOString() })
    recomputeMetrics()
  }

  function removeEdge(edgeId: string) {
    edges.value = edges.value.filter((edge) => edge.id !== edgeId)
    if (selection.value.edgeId === edgeId) {
      selection.value = { nodeId: null, edgeId: null }
    }
    recomputeMetrics()
  }

  function mergeNodes(primaryId: string, duplicateId: string) {
    if (primaryId === duplicateId) {
      return
    }
    const primary = nodes.value.find((node) => node.id === primaryId)
    const duplicate = nodes.value.find((node) => node.id === duplicateId)
    if (!primary || !duplicate) return

    const mergedDocs = new Set([...primary.documents, ...duplicate.documents])
    const mergedTriples: Triple[] = [...primary.triples]
    duplicate.triples.forEach((triple) => {
      if (!mergedTriples.some((existing) => existing.id === triple.id)) {
        mergedTriples.push(triple)
      }
    })

    updateEdgeReferences(duplicateId, primaryId)

    Object.assign(primary, {
      documents: Array.from(mergedDocs),
      triples: mergedTriples,
      updatedAt: new Date().toISOString()
    })

    removeNode(duplicateId)
    selection.value = { nodeId: primaryId, edgeId: null }
    recomputeMetrics()
  }

  function updateEdgeReferences(fromNodeId: string, toNodeId: string) {
    edges.value = edges.value.map((edge) => {
      if (edge.source === fromNodeId || edge.target === fromNodeId) {
        return {
          ...edge,
          source: edge.source === fromNodeId ? toNodeId : edge.source,
          target: edge.target === fromNodeId ? toNodeId : edge.target,
          updatedAt: new Date().toISOString()
        }
      }
      return edge
    })
  }

  function addDocument(payload: DocumentInput): DocumentItem {
    const existing = documents.value.find(
      (doc) =>
        (payload.id && doc.id === payload.id) ||
        (payload.externalId && doc.externalId === payload.externalId)
    )
    const timestamp = new Date().toISOString()
    if (existing) {
      Object.assign(existing, {
        title: payload.title ?? existing.title,
        source: payload.source ?? existing.source,
        mimeType: payload.mimeType ?? existing.mimeType,
        description: payload.description ?? existing.description,
        author: payload.author ?? existing.author,
        status: payload.status ?? existing.status,
        externalId: payload.externalId ?? existing.externalId,
        url: payload.url ?? existing.url,
        updatedAt: timestamp
      })
      recomputeMetrics()
      return existing
    }
    const doc: DocumentItem = {
      id: payload.id ?? createGraphId('doc'),
      title: payload.title,
      source: payload.source,
      mimeType: payload.mimeType,
      status: payload.status ?? 'idle',
      description: payload.description,
      author: payload.author,
      externalId: payload.externalId,
      url: payload.url,
      createdAt: timestamp,
      updatedAt: timestamp
    }
    documents.value.push(doc)
    recomputeMetrics()
    return doc
  }

  function updateDocument(docId: string, updates: Partial<Omit<DocumentItem, 'id'>>) {
    const doc = documents.value.find((document) => document.id === docId)
    if (!doc) return
    Object.assign(doc, updates, { updatedAt: new Date().toISOString() })
  }

  function linkDocumentToNode(nodeId: string, docId: string) {
    const node = nodes.value.find((item) => item.id === nodeId)
    if (!node) return
    if (!node.documents.includes(docId)) {
      node.documents.push(docId)
      node.updatedAt = new Date().toISOString()
      recomputeMetrics()
    }
  }

  function unlinkDocumentFromNode(nodeId: string, docId: string) {
    const node = nodes.value.find((item) => item.id === nodeId)
    if (!node) return
    node.documents = node.documents.filter((existingId) => existingId !== docId)
    node.updatedAt = new Date().toISOString()
    recomputeMetrics()
  }

  async function saveGraph() {
    isLoading.value = true
    errorMessage.value = null
    try {
      const snapshot: GraphSnapshot = {
        nodes: nodes.value,
        edges: edges.value,
        documents: documents.value
      }
      await saveGraphSnapshot(snapshot)
      lastSavedAt.value = new Date().toISOString()
    } catch (error) {
      errorMessage.value = (error as Error).message
      throw error
    } finally {
      isLoading.value = false
    }
  }

  async function loadGraph() {
    isLoading.value = true
    errorMessage.value = null
    try {
      const snapshot = await fetchGraphSnapshot()
      nodes.value = snapshot.nodes
      edges.value = snapshot.edges
      documents.value = snapshot.documents
      recomputeMetrics()
    } catch (error) {
      errorMessage.value = (error as Error).message
      throw error
    } finally {
      isLoading.value = false
    }
  }

  async function triggerExtraction(nodeId: string, documentId: string) {
    isLoading.value = true
    errorMessage.value = null
    try {
      const result = await triggerExtractionForNode(nodeId, documentId)
      const node = nodes.value.find((item) => item.id === nodeId)
      if (!node) return

      result.triples.forEach((triple) => {
        if (!node.triples.some((existing) => existing.id === triple.id)) {
          node.triples.push(triple)
        }
      })
      result.edges.forEach((edge) => {
        if (!edges.value.some((existing) => existing.id === edge.id)) {
          edges.value.push(edge)
        }
      })

      node.updatedAt = new Date().toISOString()
      recomputeMetrics()
    } catch (error) {
      errorMessage.value = (error as Error).message
      throw error
    } finally {
      isLoading.value = false
    }
  }

  return {
    nodes,
    edges,
    documents,
    selection,
    metrics,
    isLoading,
    lastSavedAt,
    errorMessage,
    selectedNode,
    selectedEdge,
    addNode,
    updateNode,
    removeNode,
    addEdge,
    updateEdge,
    removeEdge,
    mergeNodes,
    addDocument,
    updateDocument,
    linkDocumentToNode,
    unlinkDocumentFromNode,
    saveGraph,
    loadGraph,
    triggerExtraction,
    setSelection
  }
})

function createGraphId(prefix: string) {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return `${prefix}-${crypto.randomUUID()}`
  }
  return `${prefix}-${Math.random().toString(36).slice(2, 10)}`
}
