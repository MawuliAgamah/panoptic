// Minimal CSV → KG visualizer (agent pilot)

// Sample data (matches people.mapping.json and people.csv)
const SAMPLE_MAPPING = {
  entities: {
    Person: { key: { prefix: 'person:', column: 'person_id' } },
    Education: { key: { prefix: 'education:', column: 'education', transform: 'slug' } },
    Region: { key: { prefix: 'region:', column: 'region', transform: 'slug' } }
  },
  edges: [
    { predicate: 'has Education', source: { entity: 'Person' }, target: { entity: 'Education' } },
    { predicate: 'resides in', source: { entity: 'Person' }, target: { entity: 'Region' } }
  ],
  options: { dedupe: true, null_policy: 'skip' }
}

const SAMPLE_CSV = `person_id,education,region
1001,Bachelors,Northeast
1002,Masters,South
1003,High School,Midwest
1004,PhD,West
1005,Bachelors,South`;

// Normalizers (mirror of Python)
const normalizers = {
  trim: (x) => (x == null ? '' : String(x)).trim(),
  lower: (x) => (x == null ? '' : String(x)).trim().toLowerCase(),
  upper: (x) => (x == null ? '' : String(x)).trim().toUpperCase(),
  title_case: (x) => {
    const s = (x == null ? '' : String(x)).trim().toLowerCase()
    return s.replace(/\b\w/g, (m) => m.toUpperCase())
  },
  slug: (x) => {
    const s = (x == null ? '' : String(x)).trim().toLowerCase()
    return s.replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '')
  },
  identity: (x) => (x == null ? '' : String(x))
}

function applyTransform(val, name) {
  if (!name) return val == null ? '' : String(val)
  const fn = normalizers[name] || normalizers.identity
  return fn(val)
}

function computeEntityId(row, keySpec) {
  const prefix = (keySpec && keySpec.prefix) || ''
  const col = keySpec && keySpec.column
  const xf = keySpec && keySpec.transform
  const raw = row[col]
  const norm = applyTransform(raw, xf)
  return norm ? prefix + norm : ''
}

function entityKeySpec(entitySpec) {
  const key = (entitySpec && entitySpec.key) || {}
  return typeof key === 'object' ? key : {}
}

function resolveNodeId(row, mapping, which) {
  const entities = mapping.entities || {}
  const eName = which.entity
  const eSpec = entities[eName] || {}
  const by = which.by
  const keySpec = by && typeof by === 'object' ? by : entityKeySpec(eSpec)
  return computeEntityId(row, keySpec)
}

function buildKgFromRows(rows, mapping) {
  const entities = new Set()
  const rels = new Set()

  const entMap = mapping.entities || {}
  const edges = mapping.edges || []
  const nullPolicy = (mapping.options && mapping.options.null_policy) || 'skip'

  for (const row of rows) {
    for (const [name, eSpec] of Object.entries(entMap)) {
      const id = computeEntityId(row, entityKeySpec(eSpec))
      if (id) entities.add(id)
    }
    for (const e of edges) {
      const pred = e.predicate || e.label || e.relation
      if (!pred) continue
      const srcId = resolveNodeId(row, mapping, e.source || {})
      const tgtId = resolveNodeId(row, mapping, e.target || {})
      if (!srcId || !tgtId) {
        if (nullPolicy !== 'keep') continue
      } else {
        entities.add(srcId)
        entities.add(tgtId)
        rels.add(`${srcId}|${pred}|${tgtId}`)
      }
    }
  }

  const nodes = [...entities].map((id) => ({ data: { id, label: id } }))
  const edgesCy = [...rels].map((k, i) => {
    const [s, p, t] = k.split('|')
    return { data: { id: `e${i}`, source: s, target: t, label: p } }
  })

  return { nodes, edges: edgesCy, stats: { nodes: entities.size, edges: rels.size } }
}

function renderGraph(container, graph) {
  const isLarge = (graph.nodes?.length || 0) > 400 || (graph.edges?.length || 0) > 800

  const baseNodeStyle = {
    'background-color': '#5B8FF9',
    'font-size': 10,
    'text-valign': 'center',
    'color': '#072'
  }
  // For large graphs, hide labels by default for speed
  const nodeLabelStyle = isLarge ? '' : 'data(label)'

  const edgeBaseStyle = {
    'target-arrow-shape': 'triangle',
    'line-color': '#A3B1FF',
    'target-arrow-color': '#A3B1FF',
    'width': 2
  }
  // Use faster curve style and hide labels on large graphs
  const edgeCurve = isLarge ? 'haystack' : 'bezier'
  const edgeLabel = isLarge ? '' : 'data(label)'

  const cy = cytoscape({
    container,
    elements: { nodes: graph.nodes, edges: graph.edges },
    pixelRatio: 1, // speed over fidelity
    textureOnViewport: true,
    wheelSensitivity: 0.2,
    style: [
      { selector: 'node', style: { ...baseNodeStyle, label: nodeLabelStyle } },
      { selector: 'edge', style: { 'curve-style': edgeCurve, ...edgeBaseStyle, label: edgeLabel } },
      // Show labels when selected even in large graphs
      { selector: 'node:selected', style: { label: 'data(label)' } },
      { selector: 'edge:selected', style: { 'line-color': '#0f62fe', 'target-arrow-color': '#0f62fe', label: 'data(label)', 'text-background-opacity': 1, 'text-background-color': '#fff', 'text-background-padding': 2 } }
    ],
    // Use a faster layout by default; 'concentric' is generally quicker than force-based
    layout: { name: isLarge ? 'concentric' : 'concentric', animate: false, fit: true, padding: 20 }
  })
  return cy
}

function enableBuildButton() {
  const csvOk = Boolean(window.__csvRows && window.__csvRows.length)
  const mapOk = Boolean(window.__mapping && window.__mapping.entities)
  document.getElementById('btnBuild').disabled = !(csvOk && mapOk)
}

async function readFileAsText(file) {
  return new Promise((resolve, reject) => {
    const fr = new FileReader()
    fr.onload = () => resolve(fr.result)
    fr.onerror = reject
    fr.readAsText(file)
  })
}

function setStats(text) {
  document.getElementById('stats').textContent = text
}

(function main() {
  const csvInput = document.getElementById('csvInput')
  const mapInput = document.getElementById('mapInput')
  const kgInput = document.getElementById('kgInput')
  const btnBuild = document.getElementById('btnBuild')
  const btnExport = document.getElementById('btnExport')
  const btnRenderKG = document.getElementById('btnRenderKG')
  const btnRenderKG3D = document.getElementById('btnRenderKG3D')
  const btnUseSample = document.getElementById('btnUseSample')
  const mapPreview = document.getElementById('mapPreview')
  const cyContainer = document.getElementById('cy')
  const sampleNodesInput = document.getElementById('sampleNodes')
  const chkResolve = document.getElementById('chkResolve')
  const chkPrune = document.getElementById('chkPrune')
  const btnPageRank = document.getElementById('btnPageRank')
  const btnCommunities = document.getElementById('btnCommunities')
  const btnResetStyles = document.getElementById('btnResetStyles')
  const topNInput = document.getElementById('topN')

  window.__mapping = null
  window.__csvRows = null
  window.__kgPayload = null
  window.__fg = null
  let cy = null

  csvInput.addEventListener('change', async (e) => {
    const file = e.target.files && e.target.files[0]
    if (!file) return
    const text = await readFileAsText(file)
    const parsed = Papa.parse(text, { header: true, skipEmptyLines: true })
    window.__csvRows = parsed.data || []
    setStats(`CSV loaded: rows=${window.__csvRows.length}, columns=${parsed.meta.fields?.length || 0}`)
    enableBuildButton()
  })

  mapInput.addEventListener('change', async (e) => {
    const file = e.target.files && e.target.files[0]
    if (!file) return
    const text = await readFileAsText(file)
    try {
      window.__mapping = JSON.parse(text)
      mapPreview.value = JSON.stringify(window.__mapping, null, 2)
    } catch (err) {
      mapPreview.value = `Error parsing JSON: ${err}`
      window.__mapping = null
    }
    enableBuildButton()
  })

  kgInput.addEventListener('change', async (e) => {
    const file = e.target.files && e.target.files[0]
    if (!file) return
    try {
      const text = await readFileAsText(file)
      const payload = JSON.parse(text)
      if (!payload || !Array.isArray(payload.entities) || !Array.isArray(payload.relations)) {
        setStats('Invalid KG JSON: expected {entities:[], relations:[]}')
        window.__kgPayload = null
        btnRenderKG.disabled = true
        return
      }
      window.__kgPayload = payload
      setStats(`KG JSON loaded: entities=${payload.entities.length}, relations=${payload.relations.length}`)
      btnRenderKG.disabled = false
      btnRenderKG3D.disabled = false
    } catch (err) {
      setStats(`Error reading KG JSON: ${err}`)
      window.__kgPayload = null
      btnRenderKG.disabled = true
      btnRenderKG3D.disabled = true
    }
  })

  btnUseSample.addEventListener('click', () => {
    window.__mapping = SAMPLE_MAPPING
    mapPreview.value = JSON.stringify(SAMPLE_MAPPING, null, 2)
    const parsed = Papa.parse(SAMPLE_CSV, { header: true, skipEmptyLines: true })
    window.__csvRows = parsed.data || []
    setStats(`Sample loaded: rows=${window.__csvRows.length}, columns=${parsed.meta.fields?.length || 0}`)
    enableBuildButton()
  })

  btnBuild.addEventListener('click', () => {
    if (!window.__mapping || !window.__csvRows) return
    const graph = buildKgFromRows(window.__csvRows, window.__mapping)
    // Convert to payload for optional resolve/export
    let payload = {
      entities: graph.nodes.map((n) => n.data.id),
      relations: graph.edges.map((e) => [e.data.source, e.data.label, e.data.target])
    }
    if (chkResolve.checked) {
      payload = resolveKgSimple(payload, chkPrune.checked)
      // Recompute graph elements from resolved payload
      const uniq = new Set(payload.entities || [])
      graph.nodes = [...uniq].map((id) => ({ data: { id, label: id } }))
      graph.edges = (payload.relations || []).map((tr, i) => {
        const [s, p, t] = tr
        return { data: { id: `e${i}`, source: String(s), target: String(t), label: String(p) } }
      })
      graph.stats.nodes = graph.nodes.length
      graph.stats.edges = graph.edges.length
    }
    setStats(`Graph: nodes=${graph.stats.nodes}, edges=${graph.stats.edges}`)
    if (cy) cy.destroy()
    cy = renderGraph(cyContainer, graph)
    enableAnalyticsButtons()
    // Save for export (prefer resolved payload if applied)
    window.__kgPayload = payload
    btnExport.disabled = false
  })

  btnRenderKG.addEventListener('click', () => {
    let payload = window.__kgPayload
    if (!payload) return
    if (chkResolve.checked) {
      payload = resolveKgSimple(payload, chkPrune.checked)
      window.__kgPayload = payload
    }
    // Convert payload to Cytoscape elements after optional resolution
    const uniq = new Set(payload.entities || [])
    const nodes = [...uniq].map((id) => ({ data: { id, label: id } }))
    const edges = (payload.relations || []).map((tr, i) => {
      const [s, p, t] = tr
      return { data: { id: `e${i}`, source: String(s), target: String(t), label: String(p) } }
    })
    const graph = { nodes, edges, stats: { nodes: nodes.length, edges: edges.length } }
    setStats(`Graph: nodes=${graph.stats.nodes}, edges=${graph.stats.edges}`)
    if (cy) cy.destroy()
    cy = renderGraph(cyContainer, graph)
    enableAnalyticsButtons()
  })

  function sampleKgPayload(payload, maxNodes) {
    const entities = payload.entities || []
    const relations = payload.relations || []
    if (entities.length <= maxNodes) return payload
    // Degree-based sampling
    const deg = new Map()
    for (const [s, , t] of relations) {
      deg.set(s, (deg.get(s) || 0) + 1)
      deg.set(t, (deg.get(t) || 0) + 1)
    }
    const ranked = entities
      .map((id) => ({ id, d: deg.get(id) || 0 }))
      .sort((a, b) => b.d - a.d)
    const chosen = new Set(ranked.slice(0, maxNodes).map((x) => x.id))
    const filteredRelations = relations.filter(([s, , t]) => chosen.has(s) && chosen.has(t))
    const finalNodes = Array.from(chosen)
    return { entities: finalNodes, relations: filteredRelations }
  }

  function render3DGraph(container, payload, sampleN) {
    // Destroy 2D graph if present
    if (cy) { try { cy.destroy() } catch(_){} cy = null }
    // Destroy existing 3D if present
    if (window.__fg && window.__fg._destructor) { try { window.__fg._destructor() } catch(_){} }
    container.innerHTML = ''

    const sampled = sampleKgPayload(payload, sampleN)
    const groupOf = (id) => (id.split(':')[0] || 'node')
    const nodes = sampled.entities.map((id) => ({ id, group: groupOf(id) }))
    const links = sampled.relations.map(([s, p, t]) => ({ source: s, target: t, name: p }))

    const colorByGroup = (g) => {
      const palette = ['#5B8FF9','#61DDAA','#65789B','#F6BD16','#7262fd','#78D3F8','#9661BC','#F6903D','#E86452','#6DC8EC']
      let idx = 0
      for (let i = 0; i < g.length; i++) idx = (idx * 31 + g.charCodeAt(i)) >>> 0
      return palette[idx % palette.length]
    }

    const FG = ForceGraph3D()(container)
      .graphData({ nodes, links })
      .nodeAutoColorBy('group')
      .nodeColor((n) => n._compColor || (n._highlight ? '#f39c12' : colorByGroup(n.group)))
      .nodeVal((n) => n._size || 3)
      .linkColor(() => 'rgba(160,160,160,0.7)')
      .linkOpacity(0.6)
      .linkDirectionalParticles(0)
      .backgroundColor('#ffffff')
      .nodeLabel((n) => n.id)
      .linkLabel((l) => l.name || '')
      .numDimensions(3)
      .d3AlphaDecay(0.02)

    // Save reference
    window.__fg = FG
    window.__fgData = { nodes, links }
    window.__fgColorByGroup = colorByGroup
    setStats(`3D Graph: nodes=${nodes.length}, edges=${links.length}`)
    enableAnalyticsButtons()
  }

  btnRenderKG3D.addEventListener('click', () => {
    const payload = window.__kgPayload
    if (!payload) return
    const sampleN = Math.max(100, Math.min(10000, parseInt(sampleNodesInput.value || '1500', 10)))
    let pl = payload
    if (chkResolve.checked) {
      pl = resolveKgSimple(payload, chkPrune.checked)
    }
    render3DGraph(cyContainer, pl, sampleN)
  })

  // Simple client-side ER (JS equivalent of server's simple resolver)
  function resolveKgSimple(payload, pruneIsolates = false, ignorePrefix = true) {
    const entities = payload.entities || []
    const relations = payload.relations || []
    const buckets = new Map() // norm -> canonical id
    const oldToNew = new Map()

    const normalizeKey = (id) => {
      let s = String(id || '')
      if (ignorePrefix) {
        const idx = s.indexOf(':')
        if (idx >= 0) s = s.slice(idx + 1)
      }
      s = (s || '').trim().toLowerCase().replace(/\s+/g, ' ')
      s = s.replace(/[^a-z0-9]+/g, '')
      return s
    }

    for (const eid of entities) {
      const key = normalizeKey(eid)
      if (!key) {
        oldToNew.set(String(eid), String(eid))
        continue
      }
      if (buckets.has(key)) {
        oldToNew.set(String(eid), buckets.get(key))
      } else {
        buckets.set(key, String(eid))
        oldToNew.set(String(eid), String(eid))
      }
    }

    const newRelations = []
    for (const tr of relations) {
      const [s, p, t] = tr
      const s2 = oldToNew.get(String(s)) || String(s)
      const t2 = oldToNew.get(String(t)) || String(t)
      newRelations.push([s2, String(p), t2])
    }
    // Dedup edges
    const relSet = new Set()
    const dedupRel = []
    for (const [s, p, t] of newRelations) {
      const k = `${s}|${p}|${t}`
      if (relSet.has(k)) continue
      relSet.add(k)
      dedupRel.push([s, p, t])
    }

    const referenced = new Set()
    for (const [s, , t] of dedupRel) {
      referenced.add(s); referenced.add(t)
    }
    const canonSet = new Set(buckets.values())
    const finalNodes = pruneIsolates ? Array.from(referenced) : Array.from(new Set([...referenced, ...canonSet]))

    return { entities: finalNodes, relations: dedupRel }
  }

  function enableAnalyticsButtons() {
    const enabled = !!cy || !!window.__fg
    btnPageRank.disabled = !enabled
    btnCommunities.disabled = !enabled
    btnResetStyles.disabled = !enabled
  }

  // Analytics: PageRank
  btnPageRank.addEventListener('click', () => {
    const topN = Math.max(1, Math.min(200, parseInt(topNInput.value || '20', 10)))
    if (cy) {
      let pr
      try { pr = cy.elements().pageRank() } catch (e) { pr = { rank: (n) => n.degree() } }
      const scores = cy.nodes().map((n) => ({ n, s: pr.rank(n) }))
      scores.sort((a, b) => b.s - a.s)
      const max = scores[0]?.s || 1
      const min = scores[Math.min(scores.length - 1, topN - 1)]?.s || 0
      const top = scores.slice(0, topN)
      cy.nodes().forEach((n) => { n.style('width', 8); n.style('height', 8); n.style('background-color', '#5B8FF9'); n.removeClass('ranked') })
      top.forEach(({ n, s }) => {
        const size = 12 + 28 * ((s - min) / Math.max(1e-9, (max - min)))
        n.style('width', size); n.style('height', size); n.style('background-color', '#f39c12'); n.addClass('ranked')
      })
      const names = top.slice(0, 10).map(({ n }) => n.id())
      setStats(`Top PageRank (${topN}): ${names.join(', ')}`)
      return
    }
    if (window.__fg && window.__fgData) {
      // Compute PageRank on current 3D data
      const { nodes, links } = window.__fgData
      const idx = new Map(nodes.map((n, i) => [n.id, i]))
      const N = nodes.length
      const outdeg = new Array(N).fill(0)
      const incoming = Array.from({ length: N }, () => [])
      links.forEach((e) => {
        const s = idx.get(e.source) ?? idx.get(e.source.id)
        const t = idx.get(e.target) ?? idx.get(e.target.id)
        if (s == null || t == null) return
        outdeg[s] += 1
        incoming[t].push(s)
      })
      const d = 0.85
      let rank = new Array(N).fill(1 / Math.max(1, N))
      for (let it = 0; it < 30; it++) {
        const newRank = new Array(N).fill((1 - d) / Math.max(1, N))
        let dangling = 0
        for (let i = 0; i < N; i++) if (outdeg[i] === 0) dangling += rank[i]
        const danglingShare = d * dangling / Math.max(1, N)
        for (let i = 0; i < N; i++) {
          let sum = 0
          for (const s of incoming[i]) sum += rank[s] / Math.max(1, outdeg[s])
          newRank[i] += d * sum + danglingShare
        }
        rank = newRank
      }
      const scores = nodes.map((n, i) => ({ n, s: rank[i] }))
      scores.sort((a, b) => b.s - a.s)
      const top = scores.slice(0, topN)
      const max = top[0]?.s || 1
      const min = top[top.length - 1]?.s || 0
      // Reset sizes/highlights
      nodes.forEach((n) => { n._highlight = false; n._size = 3 })
      top.forEach(({ n, s }) => {
        n._highlight = true
        n._size = 4 + 12 * ((s - min) / Math.max(1e-9, (max - min)))
      })
      window.__fg.nodeVal((n) => n._size || 3).nodeColor((n) => n._compColor || (n._highlight ? '#f39c12' : (window.__fgColorByGroup ? window.__fgColorByGroup(n.group) : '#5B8FF9')))
      const names = top.slice(0, 10).map(({ n }) => n.id)
      setStats(`Top PageRank (3D, ${topN}): ${names.join(', ')}`)
    }
  })

  // Analytics: Color by communities (connected components)
  btnCommunities.addEventListener('click', () => {
    if (cy) {
      let comps
      try { comps = cy.elements().components() } catch (e) {
        // Fallback BFS
        const visited = new Set(); comps = []
        cy.nodes().forEach((start) => {
          if (visited.has(start.id())) return
          const queue = [start]; const comp = []
          visited.add(start.id())
          while (queue.length) {
            const v = queue.shift(); comp.push(v)
            v.connectedEdges().connectedNodes().forEach((w) => {
              if (!visited.has(w.id())) { visited.add(w.id()); queue.push(w) }
            })
          }
          comps.push(comp)
        })
      }
      const palette = ['#5B8FF9','#61DDAA','#65789B','#F6BD16','#7262fd','#78D3F8','#9661BC','#F6903D','#E86452','#6DC8EC']
      comps.forEach((c, idx) => {
        const color = palette[idx % palette.length]
        const nodes = Array.isArray(c) ? c : c.nodes()
        nodes.forEach((n) => { const node = n.isNode ? n : n; node.style('background-color', color) })
      })
      setStats(`Components (2D): ${comps.length}`)
      return
    }
    if (window.__fg && window.__fgData) {
      const { nodes, links } = window.__fgData
      const idx = new Map(nodes.map((n, i) => [n.id, i]))
      const N = nodes.length
      const adj = Array.from({ length: N }, () => [])
      links.forEach((e) => {
        const s = idx.get(e.source) ?? idx.get(e.source.id)
        const t = idx.get(e.target) ?? idx.get(e.target.id)
        if (s == null || t == null) return
        adj[s].push(t); adj[t].push(s)
      })
      const visited = new Array(N).fill(false)
      let compId = 0
      for (let i = 0; i < N; i++) {
        if (visited[i]) continue
        const queue = [i]; visited[i] = true
        while (queue.length) {
          const v = queue.shift()
          nodes[v]._comp = compId
          queue.push.apply(queue, adj[v].filter((w) => !visited[w]).map((w) => (visited[w] = true, w)))
        }
        compId++
      }
      const palette = ['#5B8FF9','#61DDAA','#65789B','#F6BD16','#7262fd','#78D3F8','#9661BC','#F6903D','#E86452','#6DC8EC']
      nodes.forEach((n) => { n._compColor = palette[(n._comp || 0) % palette.length] })
      window.__fg.nodeColor((n) => n._compColor || (window.__fgColorByGroup ? window.__fgColorByGroup(n.group) : '#5B8FF9'))
      setStats(`Components (3D): ${compId}`)
    }
  })

  // Reset styling
  btnResetStyles.addEventListener('click', () => {
    if (cy) {
      cy.nodes().forEach((n) => n.removeStyle())
      cy.edges().forEach((e) => e.removeStyle())
      setStats('Styles reset (2D)')
      return
    }
    if (window.__fg && window.__fgData) {
      const { nodes } = window.__fgData
      nodes.forEach((n) => { n._highlight = false; n._size = 3; n._comp = undefined; n._compColor = undefined })
      window.__fg.nodeVal((n) => n._size || 3).nodeColor((n) => (window.__fgColorByGroup ? window.__fgColorByGroup(n.group) : '#5B8FF9'))
      setStats('Styles reset (3D)')
    }
  })

  btnExport.addEventListener('click', () => {
    if (!window.__kgPayload) return
    const blob = new Blob([JSON.stringify(window.__kgPayload, null, 2)], { type: 'application/json' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = 'kg_payload.json'
    document.body.appendChild(a)
    a.click()
    a.remove()
  })
})()
