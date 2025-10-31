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

// ---------- Per-node analytics ----------

export interface NodeMetrics {
  degree: number
  pagerank: number
  closeness: number
}

export function computeNodeMetrics(
  nodes: GraphNode[],
  edges: GraphEdge[]
): Record<string, NodeMetrics> {
  const n = nodes.length
  if (n === 0) return {}

  const idIndex = new Map<string, number>()
  nodes.forEach((node, i) => idIndex.set(node.id, i))

  const outNeighbors: number[][] = Array.from({ length: n }, () => [])
  const inNeighbors: number[][] = Array.from({ length: n }, () => [])
  const degree = new Array<number>(n).fill(0)

  edges.forEach((e) => {
    const s = idIndex.get(e.source)
    const t = idIndex.get(e.target)
    if (s === undefined || t === undefined) return
    outNeighbors[s].push(t)
    inNeighbors[t].push(s)
    degree[s] += 1
    degree[t] += 1
  })

  // PageRank (simple, unweighted)
  const d = 0.85
  const pr = new Array<number>(n).fill(1 / n)
  const maxIters = 50
  const eps = 1e-6
  for (let iter = 0; iter < maxIters; iter++) {
    const next = new Array<number>(n).fill((1 - d) / n)
    // handle sinks (nodes with no outlinks)
    let sinkSum = 0
    for (let i = 0; i < n; i++) {
      if (outNeighbors[i].length === 0) sinkSum += pr[i]
    }
    const sinkContribution = (d * sinkSum) / n
    for (let i = 0; i < n; i++) next[i] += sinkContribution
    // distribute PR
    for (let i = 0; i < n; i++) {
      const out = outNeighbors[i]
      if (out.length === 0) continue
      const share = (d * pr[i]) / out.length
      for (const j of out) next[j] += share
    }
    // check convergence
    let diff = 0
    for (let i = 0; i < n; i++) diff += Math.abs(next[i] - pr[i])
    pr.splice(0, n, ...next)
    if (diff < eps) break
  }

  // Closeness centrality: 1 / average shortest path length to others (reachable)
  const adjacency: number[][] = Array.from({ length: n }, () => [])
  for (let i = 0; i < n; i++) {
    // treat as undirected for closeness
    const undirected = new Set<number>([...outNeighbors[i], ...inNeighbors[i]])
    adjacency[i] = [...undirected]
  }
  const closeness = new Array<number>(n).fill(0)
  const bfs = (src: number) => {
    const dist = new Array<number>(n).fill(-1)
    const q: number[] = []
    dist[src] = 0
    q.push(src)
    while (q.length) {
      const u = q.shift() as number
      for (const v of adjacency[u]) {
        if (dist[v] === -1) {
          dist[v] = dist[u] + 1
          q.push(v)
        }
      }
    }
    let sum = 0
    let reach = 0
    for (let i = 0; i < n; i++) {
      if (i === src) continue
      if (dist[i] > 0) {
        sum += dist[i]
        reach += 1
      }
    }
    if (sum > 0 && reach > 0) return reach / sum
    return 0
  }
  for (let i = 0; i < n; i++) closeness[i] = bfs(i)

  const result: Record<string, NodeMetrics> = {}
  nodes.forEach((node, i) => {
    result[node.id] = {
      degree: degree[i],
      pagerank: pr[i],
      closeness: closeness[i]
    }
  })
  return result
}

// Community detection via Label Propagation (LPA) for unweighted graphs
export function detectCommunitiesLPA(
  nodes: GraphNode[],
  edges: GraphEdge[],
  maxIters = 20
): Record<string, number> {
  const n = nodes.length
  const idIndex = new Map<string, number>()
  nodes.forEach((node, i) => idIndex.set(node.id, i))

  const neighbors: number[][] = Array.from({ length: n }, () => [])
  edges.forEach((e) => {
    const s = idIndex.get(e.source)
    const t = idIndex.get(e.target)
    if (s === undefined || t === undefined) return
    neighbors[s].push(t)
    neighbors[t].push(s)
  })

  const labels = new Array<number>(n)
  for (let i = 0; i < n; i++) labels[i] = i

  const order = [...Array(n).keys()]
  for (let iter = 0; iter < maxIters; iter++) {
    // Shuffle order to avoid bias
    for (let i = order.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1))
      ;[order[i], order[j]] = [order[j], order[i]]
    }
    let changes = 0
    for (const u of order) {
      const counts = new Map<number, number>()
      for (const v of neighbors[u]) {
        const lab = labels[v]
        counts.set(lab, (counts.get(lab) ?? 0) + 1)
      }
      if (counts.size === 0) continue
      let bestLabel = labels[u]
      let bestCount = -1
      counts.forEach((cnt, lab) => {
        if (cnt > bestCount || (cnt === bestCount && lab < bestLabel)) {
          bestCount = cnt
          bestLabel = lab
        }
      })
      if (bestLabel !== labels[u]) {
        labels[u] = bestLabel
        changes++
      }
    }
    if (changes === 0) break
  }

  // Normalize labels to contiguous group indices
  const unique = Array.from(new Set(labels)).sort((a, b) => a - b)
  const mapOldToNew = new Map<number, number>()
  unique.forEach((lab, idx) => mapOldToNew.set(lab, idx))
  const assignment: Record<string, number> = {}
  nodes.forEach((node, i) => {
    assignment[node.id] = mapOldToNew.get(labels[i]) ?? 0
  })
  return assignment
}
