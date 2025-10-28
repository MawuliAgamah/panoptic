export type NodeType =
  | 'person'
  | 'organization'
  | 'concept'
  | 'event'
  | 'location'
  | 'other'

export interface Triple {
  id: string
  subject: string
  predicate: string
  object: string
  confidence?: number
  sourceDocumentId?: string
  snippet?: string
}

export interface GraphNode {
  id: string
  label: string
  type: NodeType
  description?: string
  provenance?: string
  position?: { x: number; y: number }
  documents: string[]
  triples: Triple[]
  createdAt: string
  updatedAt: string
}

export interface GraphEdge {
  id: string
  source: string
  target: string
  predicate: string
  description?: string
  confidence?: number
  sourceDocumentId?: string
  createdAt: string
  updatedAt: string
}

export type DocumentSource = 'local' | 'google'

export interface DocumentItem {
  id: string
  title: string
  source: DocumentSource
  mimeType?: string
  status: 'idle' | 'processing' | 'ready' | 'error'
  createdAt: string
  updatedAt: string
  description?: string
  author?: string
  externalId?: string
  url?: string
}

export interface GraphSnapshot {
  nodes: GraphNode[]
  edges: GraphEdge[]
  documents: DocumentItem[]
}

export interface GraphSelection {
  nodeId: string | null
  edgeId: string | null
}

export interface GraphMetrics {
  totals: {
    nodes: number
    edges: number
    documents: number
  }
  connectivity: {
    components: number
    density: number
    averageDegree: number
    isolates: string[]
  }
  influence: {
    topDegree: Array<{ nodeId: string; label: string; degree: number }>
  }
  communities: {
    clusters: Array<{ id: string; label: string; nodeIds: string[] }>
  }
  lastUpdated: string
}

export interface NodeCreationPayload {
  label: string
  type: NodeType
  description?: string
  provenance?: string
  position?: { x: number; y: number }
}
