// Knowledge Graph D3.js Visualization
class KnowledgeGraphViz {
    constructor() {
        this.svg = d3.select("#graph");
        this.width = +this.svg.attr("width");
        this.height = +this.svg.attr("height");

        this.g = this.svg.append("g");

        // Create zoom behavior
        this.zoom = d3.zoom()
            .scaleExtent([0.1, 4])
            .on("zoom", (event) => {
                this.g.attr("transform", event.transform);
            });

        this.svg.call(this.zoom);

        // Create arrow marker for directed edges
        this.svg.append("defs").selectAll("marker")
            .data(["arrowhead"])
            .enter().append("marker")
            .attr("id", d => d)
            .attr("viewBox", "0 -5 10 10")
            .attr("refX", 25)
            .attr("refY", 0)
            .attr("markerWidth", 6)
            .attr("markerHeight", 6)
            .attr("orient", "auto")
            .append("path")
            .attr("d", "M0,-5L10,0L0,5")
            .attr("fill", "#95a5a6");

        // Initialize tooltip
        this.tooltip = d3.select("body").append("div")
            .attr("class", "tooltip")
            .style("opacity", 0);

        // Initialize simulation
        this.simulation = d3.forceSimulation()
            .force("link", d3.forceLink().id(d => d.id).distance(100))
            .force("charge", d3.forceManyBody().strength(-200))
            .force("center", d3.forceCenter(this.width / 2, this.height / 2))
            .force("collision", d3.forceCollide().radius(25));

        this.data = null;
        this.filteredData = null;
    }

    async loadData() {
        try {
            // Try to load from the knowledge store JSON file
            const response = await fetch('/database/knowledge_store.json');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            this.data = await response.json();
            this.processData();
            this.updateStats();
            this.render();
            this.showError(null); // Clear any previous errors
        } catch (error) {
            console.error('Error loading data:', error);
            this.showError(`Failed to load knowledge graph data: ${error.message}`);

            // Try to load sample data as fallback
            this.loadSampleData();
        }
    }

    loadSampleData() {
        // Fallback sample data based on your actual structure
        this.data = {
            entities: [
                { id: 1, name: "Python", type: "extracted", document_ids: ["test_doc"], metadata: { title: "Test Document" } },
                { id: 2, name: "artificial intelligence", type: "extracted", document_ids: ["test_doc"], metadata: { title: "Test Document" } },
                { id: 3, name: "machine learning", type: "extracted", document_ids: ["test_doc"], metadata: { title: "Test Document" } },
                { id: 4, name: "TensorFlow", type: "extracted", document_ids: ["test_doc"], metadata: { title: "Test Document" } },
                { id: 5, name: "Google", type: "extracted", document_ids: ["test_doc"], metadata: { title: "Test Document" } }
            ],
            relationships: [
                { id: 1, source_entity: "artificial intelligence", relation_type: "is about", target_entity: "machine learning" },
                { id: 2, source_entity: "Python", relation_type: "used for", target_entity: "machine learning" },
                { id: 3, source_entity: "TensorFlow", relation_type: "developed by", target_entity: "Google" }
            ],
            metadata: { total_entities: 5, total_relationships: 3, unique_documents: 1 }
        };

        console.log('Loaded sample data as fallback');
        this.processData();
        this.updateStats();
        this.render();
    }

    processData() {
        if (!this.data) return;

        // Create nodes from entities
        this.nodes = this.data.entities.map(entity => ({
            id: entity.name, // Use name as ID for linking
            label: entity.name,
            type: entity.type,
            document_ids: entity.document_ids,
            metadata: entity.metadata,
            originalId: entity.id
        }));

        // Create links from relationships
        this.links = this.data.relationships.map(rel => ({
            source: rel.source_entity,
            target: rel.target_entity,
            relation: rel.relation_type,
            document_ids: rel.document_ids,
            metadata: rel.metadata,
            id: rel.id
        }));

        this.filteredData = {
            nodes: [...this.nodes],
            links: [...this.links]
        };

        // Update document filter
        this.updateDocumentFilter();
    }

    updateDocumentFilter() {
        const documentSet = new Set();
        this.nodes.forEach(node => {
            if (node.document_ids) {
                node.document_ids.forEach(docId => documentSet.add(docId));
            }
        });

        const select = document.getElementById('document-filter');
        select.innerHTML = '<option value="">All Documents</option>';

        Array.from(documentSet).sort().forEach(docId => {
            const option = document.createElement('option');
            option.value = docId;
            option.textContent = docId.replace(/_/g, ' ').replace(/processed /g, '');
            select.appendChild(option);
        });
    }

    filterByDocument() {
        const selectedDoc = document.getElementById('document-filter').value;

        if (!selectedDoc) {
            this.filteredData = {
                nodes: [...this.nodes],
                links: [...this.links]
            };
        } else {
            // Filter nodes by document
            const filteredNodes = this.nodes.filter(node =>
                node.document_ids && node.document_ids.includes(selectedDoc)
            );

            // Get node names for filtering links
            const nodeNames = new Set(filteredNodes.map(n => n.id));

            // Filter links to only include those between filtered nodes
            const filteredLinks = this.links.filter(link =>
                nodeNames.has(link.source) && nodeNames.has(link.target) ||
                (typeof link.source === 'object' && typeof link.target === 'object' &&
                 nodeNames.has(link.source.id) && nodeNames.has(link.target.id))
            );

            this.filteredData = {
                nodes: filteredNodes,
                links: filteredLinks
            };
        }

        this.render();
    }

    updateStats() {
        if (!this.data) return;

        document.getElementById('entity-count').textContent = this.data.entities.length;
        document.getElementById('relationship-count').textContent = this.data.relationships.length;

        // Count unique documents
        const documentSet = new Set();
        this.data.entities.forEach(entity => {
            if (entity.document_ids) {
                entity.document_ids.forEach(docId => documentSet.add(docId));
            }
        });
        document.getElementById('document-count').textContent = documentSet.size;
    }

    render() {
        if (!this.filteredData) return;

        // Clear previous elements
        this.g.selectAll("*").remove();

        // Update simulation with new data
        this.simulation.nodes(this.filteredData.nodes);
        this.simulation.force("link").links(this.filteredData.links);

        // Create links
        this.link = this.g.append("g")
            .attr("class", "links")
            .selectAll("line")
            .data(this.filteredData.links)
            .enter().append("line")
            .attr("class", "link")
            .on("mouseover", (event, d) => this.showTooltip(event, `${d.source.id || d.source} —[${d.relation}]→ ${d.target.id || d.target}`))
            .on("mouseout", () => this.hideTooltip());

        // Create link labels
        this.linkLabel = this.g.append("g")
            .attr("class", "link-labels")
            .selectAll("text")
            .data(this.filteredData.links)
            .enter().append("text")
            .attr("class", "link-label")
            .text(d => d.relation);

        // Create nodes
        this.node = this.g.append("g")
            .attr("class", "nodes")
            .selectAll("circle")
            .data(this.filteredData.nodes)
            .enter().append("circle")
            .attr("class", "node")
            .attr("r", 10)
            .attr("fill", "#3498db")
            .attr("stroke", "#2980b9")
            .on("mouseover", (event, d) => this.showNodeTooltip(event, d))
            .on("mouseout", () => this.hideTooltip())
            .on("click", (event, d) => this.highlightNode(d))
            .call(d3.drag()
                .on("start", (event, d) => this.dragStarted(event, d))
                .on("drag", (event, d) => this.dragged(event, d))
                .on("end", (event, d) => this.dragEnded(event, d)));

        // Create node labels
        this.nodeLabel = this.g.append("g")
            .attr("class", "node-labels")
            .selectAll("text")
            .data(this.filteredData.nodes)
            .enter().append("text")
            .attr("class", "node-label")
            .text(d => d.label.length > 15 ? d.label.substring(0, 15) + "..." : d.label)
            .attr("dy", -15);

        // Start simulation
        this.simulation.on("tick", () => this.ticked());
        this.simulation.alpha(1).restart();
    }

    ticked() {
        this.link
            .attr("x1", d => d.source.x)
            .attr("y1", d => d.source.y)
            .attr("x2", d => d.target.x)
            .attr("y2", d => d.target.y);

        this.linkLabel
            .attr("x", d => (d.source.x + d.target.x) / 2)
            .attr("y", d => (d.source.y + d.target.y) / 2);

        this.node
            .attr("cx", d => d.x)
            .attr("cy", d => d.y);

        this.nodeLabel
            .attr("x", d => d.x)
            .attr("y", d => d.y);
    }

    showNodeTooltip(event, d) {
        const metadata = d.metadata || {};
        let content = `<strong>${d.label}</strong><br/>`;
        content += `Type: ${d.type}<br/>`;
        if (metadata.title) content += `Document: ${metadata.title}<br/>`;
        if (metadata.file_path) content += `File: ${metadata.file_path}<br/>`;
        if (d.document_ids) content += `Documents: ${d.document_ids.length}`;

        this.showTooltip(event, content);
    }

    showTooltip(event, content) {
        this.tooltip.transition()
            .duration(200)
            .style("opacity", .9);
        this.tooltip.html(content)
            .style("left", (event.pageX + 10) + "px")
            .style("top", (event.pageY - 28) + "px");
    }

    hideTooltip() {
        this.tooltip.transition()
            .duration(500)
            .style("opacity", 0);
    }

    highlightNode(selectedNode) {
        // Reset all nodes
        this.node.attr("fill", "#3498db");

        // Highlight selected node and connected nodes
        const connectedNodes = new Set([selectedNode.id]);

        this.filteredData.links.forEach(link => {
            const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
            const targetId = typeof link.target === 'object' ? link.target.id : link.target;

            if (sourceId === selectedNode.id) {
                connectedNodes.add(targetId);
            } else if (targetId === selectedNode.id) {
                connectedNodes.add(sourceId);
            }
        });

        this.node.attr("fill", d => connectedNodes.has(d.id) ? "#e74c3c" : "#3498db");
    }

    dragStarted(event, d) {
        if (!event.active) this.simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }

    dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }

    dragEnded(event, d) {
        if (!event.active) this.simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }

    updateForces() {
        const strength = +document.getElementById('strength-slider').value;
        this.simulation.force("charge").strength(strength);
        this.simulation.alpha(1).restart();
    }

    updateNodeSize() {
        const size = +document.getElementById('size-slider').value;
        this.node.attr("r", size);
        this.simulation.force("collision").radius(size + 5);
        this.simulation.alpha(1).restart();
    }

    resetZoom() {
        this.svg.transition().duration(750).call(
            this.zoom.transform,
            d3.zoomIdentity
        );
    }

    showError(message) {
        const errorContainer = document.getElementById('error-container');
        if (message) {
            errorContainer.innerHTML = `<div class="error">${message}</div>`;
        } else {
            errorContainer.innerHTML = '';
        }
    }
}

// Initialize the visualization
const viz = new KnowledgeGraphViz();

// Global functions for HTML controls
function loadData() {
    viz.loadData();
}

function resetZoom() {
    viz.resetZoom();
}

function updateForces() {
    viz.updateForces();
}

function updateNodeSize() {
    viz.updateNodeSize();
}

function filterByDocument() {
    viz.filterByDocument();
}

// Auto-load data when page loads
document.addEventListener('DOMContentLoaded', function() {
    viz.loadData();
});