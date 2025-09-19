# Knowledge Graph Visualization

This folder contains a D3.js-based interactive visualization of your knowledge graph data.

## Features

- **Interactive Force-Directed Graph**: Nodes and edges with physics simulation
- **Node Interaction**: Click and drag nodes, hover for details
- **Zoom and Pan**: Mouse wheel to zoom, drag to pan
- **Document Filtering**: Filter by specific documents
- **Real-time Controls**: Adjust layout forces and node sizes
- **Statistics**: Live count of entities, relationships, and documents
- **Responsive Design**: Clean, modern interface

## Quick Start

### Option 1: Using Python Server (Recommended)

```bash
# From the aiModule directory
cd src/vis
python3 server.py
```

This will:
- Start a local server on port 8000
- Automatically open your browser to http://localhost:8000
- Load the knowledge graph data from ../../database/knowledge_store.json

### Option 2: Direct File Access

If you can't run the Python server, you can try opening `index.html` directly in your browser, but this may have CORS issues loading the JSON data.

## Usage

1. **Load Data**: Click "Load Knowledge Graph" to load your current knowledge store
2. **Explore**:
   - Hover over nodes to see entity details
   - Hover over edges to see relationship details
   - Click nodes to highlight connected entities
3. **Control Layout**:
   - Adjust "Layout Strength" to change node repulsion
   - Adjust "Node Size" to change node radius
4. **Filter**: Use the document dropdown to show only entities from specific documents
5. **Navigate**: Use mouse wheel to zoom, drag to pan, "Reset Zoom" to center

## Graph Structure

Your knowledge graph is visualized as:

- **Nodes**: Circles representing entities (Python, TensorFlow, etc.)
- **Edges**: Arrows showing relationships with labels ("created by", "used for", etc.)
- **Colors**: Blue for normal nodes, red for highlighted/connected nodes

## Data Source

The visualization loads data from:
```
../../database/knowledge_store.json
```

This should contain your entities and relationships in the format:
```json
{
  "entities": [...],
  "relationships": [...],
  "metadata": {...}
}
```

## Customization

You can modify:
- **Colors**: Edit the CSS in `index.html`
- **Layout**: Adjust D3.js force parameters in `graph-viz.js`
- **Styling**: Modify the visual appearance in the CSS section
- **Interactions**: Add new features in the JavaScript file

## Troubleshooting

- **No data showing**: Make sure the knowledge_store.json file exists and has been populated
- **CORS errors**: Use the Python server instead of opening HTML directly
- **Performance issues**: For large graphs (>100 nodes), consider adjusting force parameters

## Technology Stack

- **D3.js v7**: Data visualization and DOM manipulation
- **Vanilla JavaScript**: Core functionality
- **CSS3**: Modern styling and layout
- **Python HTTP Server**: Local development server