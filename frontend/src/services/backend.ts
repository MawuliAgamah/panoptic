import type { DocumentItem, GraphEdge, GraphSnapshot, Triple } from '@/types/graph'

const API_BASE_URL = import.meta.env.VITE_BACKEND_URL ?? 'http://127.0.0.1:8001'
const USE_MOCK_API = import.meta.env.VITE_USE_MOCK_BACKEND === 'true'
const USE_MOCK_EXTRACTION = import.meta.env.VITE_USE_MOCK_EXTRACTION === 'true'

const MOCK_GRAPH: GraphSnapshot = {
  nodes: [],
  edges: [],
  documents: []
}

export async function fetchGraphSnapshot(): Promise<GraphSnapshot> {
  if (USE_MOCK_API) {
    return structuredClone(MOCK_GRAPH)
  }

  try {
    const response = await fetch(`${API_BASE_URL}/api/graph`)
    if (!response.ok) {
      throw new Error(`Failed to fetch graph: ${response.statusText}`)
    }
    const payload = (await response.json()) as GraphSnapshot
    return payload
  } catch (error) {
    console.warn('[backend] Falling back to mock graph snapshot.', error)
    return structuredClone(MOCK_GRAPH)
  }
}

export async function saveGraphSnapshot(snapshot: GraphSnapshot): Promise<void> {
  if (USE_MOCK_API) {
    return
  }

  try {
    const response = await fetch(`${API_BASE_URL}/api/graph/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(snapshot)
    })

    if (!response.ok) {
      throw new Error(`Failed to save graph snapshot: ${response.status} ${response.statusText}`)
    }
  } catch (error) {
    console.warn('[backend] Graph save endpoint unavailable. Ignoring for now.', error)
  }
}

export interface UploadDocumentOptions {
  documentId?: string
  domain?: string
  tags?: string[]
}

export interface UploadDocumentResponse {
  success: boolean
  document_id: string
  message?: string
  graph?: GraphSnapshot
  entity_count?: number
  relation_count?: number
  kg_data?: {
    entities: string[]
    relations: string[][]
  }
  [key: string]: unknown
}

export async function uploadLocalDocument(
  file: File,
  options: UploadDocumentOptions = {}
): Promise<UploadDocumentResponse> {
  if (USE_MOCK_API) {
    await delay(350)
    return {
      success: true,
      document_id: options.documentId ?? `mock-doc-${Date.now()}`,
      message: 'Mock upload complete'
    }
  }

  const formData = new FormData()
  formData.append('file', file, file.name)
  formData.append('domain', options.domain ?? 'general')
  formData.append('tags', JSON.stringify(options.tags ?? []))
  if (options.documentId) {
    formData.append('document_id', options.documentId)
  }

  const response = await fetch(`${API_BASE_URL}/api/extract-kg`, {
    method: 'POST',
    body: formData
  })

  if (!response.ok) {
    throw new Error(`Failed to upload document: ${response.status} ${response.statusText}`)
  }

  return (await response.json()) as UploadDocumentResponse
}

export async function deleteDocument(documentId: string): Promise<void> {
  if (USE_MOCK_API) {
    await delay(150)
    return
  }

  const response = await fetch(`${API_BASE_URL}/api/documents/${encodeURIComponent(documentId)}`, {
    method: 'DELETE'
  })

  if (!response.ok) {
    throw new Error(`Failed to delete document: ${response.status} ${response.statusText}`)
  }
}

export interface RemoteDocumentRegistration {
  documentId: string
  title: string
  source: DocumentItem['source']
  mimeType?: string
  externalId?: string
  url?: string
  author?: string
}

export async function registerRemoteDocument(
  payload: RemoteDocumentRegistration
): Promise<unknown> {
  if (USE_MOCK_API) {
    await delay(250)
    return { success: true, document_id: payload.documentId }
  }

  const response = await fetch(`${API_BASE_URL}/api/documents/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      document_id: payload.documentId,
      title: payload.title,
      source: payload.source,
      mime_type: payload.mimeType,
      external_id: payload.externalId,
      url: payload.url,
      author: payload.author
    })
  })

  if (!response.ok) {
    throw new Error(`Failed to register remote document: ${response.status} ${response.statusText}`)
  }

  return response.json()
}

interface ExtractionResult {
  triples: Triple[]
  edges: GraphEdge[]
}

export async function triggerExtractionForNode(
  nodeId: string,
  documentId: string
): Promise<ExtractionResult> {
  if (!USE_MOCK_EXTRACTION) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/extract-node`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ node_id: nodeId, document_id: documentId })
      })
      if (response.ok) {
        return (await response.json()) as ExtractionResult
      }
    } catch (error) {
      console.warn('[backend] Node extraction endpoint unavailable. Falling back to mock.', error)
    }
  }

  await delay(650)

  const newTriple: Triple = {
    id: `triple-${nodeId}-${documentId}-${Date.now()}`,
    subject: `Node ${nodeId}`,
    predicate: 'related_to',
    object: `Entity from ${documentId}`,
    confidence: 0.72,
    sourceDocumentId: documentId,
    snippet: 'Example snippet returned from simulated extraction.'
  }

  const newEdge: GraphEdge = {
    id: `edge-${nodeId}-${documentId}-${Date.now()}`,
    source: nodeId,
    target: `${nodeId}-related-entity`,
    predicate: newTriple.predicate,
    description: 'Simulated relation',
    confidence: newTriple.confidence,
    sourceDocumentId: documentId,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString()
  }

  return {
    triples: [newTriple],
    edges: [newEdge]
  }
}

function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}
