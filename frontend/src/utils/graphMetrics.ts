import type { DocumentItem, GraphEdge, GraphMetrics, GraphNode } from '@/types/graph'

const CLUSTER_LABELS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

export function calculateGraphMetrics(
  nodes: GraphNode[],
  edges: GraphEdge[],
  documents: DocumentItem[]
): GraphMetrics {
  const nodeCount = nodes.length
  const edgeCount = edges.length
  const documentCount = documents.length

  const adjacency = new Map<string, Set<string>>()
  const degreeMap = new Map<string, number>()

  nodes.forEach((node) => {
    adjacency.set(node.id, new Set())
    degreeMap.set(node.id, 0)
  })

  edges.forEach((edge) => {
    const targets = adjacency.get(edge.source)
    const sources = adjacency.get(edge.target)
    targets?.add(edge.target)
    sources?.add(edge.source)
    degreeMap.set(edge.source, (degreeMap.get(edge.source) ?? 0) + 1)
    degreeMap.set(edge.target, (degreeMap.get(edge.target) ?? 0) + 1)
  })

  const isolates = nodes.filter((node) => (degreeMap.get(node.id) ?? 0) === 0).map((node) => node.label)
  const averageDegree = nodeCount === 0 ? 0 : parseFloat(((edgeCount * 2) / nodeCount).toFixed(2))
  const density =
    nodeCount <= 1 ? 0 : parseFloat((edgeCount / (nodeCount * (nodeCount - 1))).toFixed(4))

  const clusters = collectCommunities(nodes, adjacency)

  const sortedDegrees = [...degreeMap.entries()]
    .sort((a, b) => (b[1] ?? 0) - (a[1] ?? 0))
    .slice(0, 3)
    .map(([nodeId, degree]) => {
      const node = nodes.find((n) => n.id === nodeId)
      return { nodeId, label: node?.label ?? 'Unknown', degree }
    })

  return {
    totals: {
      nodes: nodeCount,
      edges: edgeCount,
      documents: documentCount
    },
    connectivity: {
      components: clusters.length,
      density,
      averageDegree,
      isolates
    },
    influence: {
      topDegree: sortedDegrees
    },
    communities: {
      clusters: clusters.map((group, index) => ({
        id: `cluster-${index}`,
        label: `Cluster ${CLUSTER_LABELS[index] ?? index + 1}`,
        nodeIds: group
      }))
    },
    lastUpdated: new Date().toISOString()
  }
}

function collectCommunities(
  nodes: GraphNode[],
  adjacency: Map<string, Set<string>>
): string[][] {
  const visited = new Set<string>()
  const groups: string[][] = []

  for (const node of nodes) {
    if (visited.has(node.id)) continue
    const queue = [node.id]
    const component: string[] = []

    while (queue.length > 0) {
      const current = queue.shift()!
      if (visited.has(current)) continue
      visited.add(current)
      component.push(current)
      for (const neighbor of adjacency.get(current) ?? []) {
        if (!visited.has(neighbor)) {
          queue.push(neighbor)
        }
      }
    }

    groups.push(component)
  }

  return groups
}
