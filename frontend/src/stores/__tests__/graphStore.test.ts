import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useGraphStore } from '../graphStore'

vi.mock('@/services/backend', () => ({
  fetchGraphSnapshot: vi.fn().mockResolvedValue({ nodes: [], edges: [], documents: [] }),
  saveGraphSnapshot: vi.fn().mockResolvedValue(undefined),
  triggerExtractionForNode: vi.fn().mockResolvedValue({
    triples: [],
    edges: []
  })
}))

describe('graphStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('adds nodes and updates selection + metrics', () => {
    const store = useGraphStore()
    const node = store.addNode({ label: 'Machine Learning', type: 'concept' })

    expect(node.label).toBe('Machine Learning')
    expect(store.selection.nodeId).toBe(node.id)
    expect(store.metrics.totals.nodes).toBe(1)
  })

  it('links a document to a node', () => {
    const store = useGraphStore()
    const node = store.addNode({ label: 'Data Pipeline', type: 'concept' })
    const doc = store.addDocument({ title: 'Pipeline Design.pdf', source: 'local' })

    store.linkDocumentToNode(node.id, doc.id)

    const updatedNode = store.nodes.find((candidate) => candidate.id === node.id)
    expect(updatedNode?.documents).toContain(doc.id)
  })

  it('merges duplicate nodes and keeps document + triple associations', () => {
    const store = useGraphStore()
    const primary = store.addNode({ label: 'Graph DB', type: 'concept' })
    const duplicate = store.addNode({ label: 'Graph Database', type: 'concept' })

    const doc = store.addDocument({ title: 'Neo4j Playbook', source: 'google' })
    store.linkDocumentToNode(primary.id, doc.id)
    store.linkDocumentToNode(duplicate.id, doc.id)

    store.mergeNodes(primary.id, duplicate.id)

    expect(store.nodes.length).toBe(1)
    const merged = store.nodes[0]
    expect(merged.documents).toContain(doc.id)
  })
})
