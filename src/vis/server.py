#!/usr/bin/env python3
"""
Simple HTTP server to serve the knowledge graph visualization.
Run this script and open http://localhost:8000 in your browser.
"""

import http.server
import socketserver
import os
import webbrowser
from pathlib import Path

# Find an available port
import socket
def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port

PORT = find_free_port()

# Change to the project root directory so we can serve both vis files and database
vis_dir = Path(__file__).parent
project_root = vis_dir.parent.parent  # Go up two levels from src/vis to project root
os.chdir(project_root)

class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200, "OK")
        self.end_headers()

def start_server():
    """Start the HTTP server and open the browser."""

    print(f"🌐 Starting Knowledge Graph Visualization Server...")
    print(f"📁 Serving from: {project_root.absolute()}")
    print(f"🔗 Open your browser to: http://localhost:{PORT}")
    print(f"📄 Direct link to visualization: http://localhost:{PORT}/src/vis/index.html")
    print()
    print("Press Ctrl+C to stop the server")
    print("-" * 50)

    # Create server
    with socketserver.TCPServer(("", PORT), CORSRequestHandler) as httpd:
        try:
            # Try to open browser automatically
            webbrowser.open(f'http://localhost:{PORT}/src/vis/index.html')
        except Exception as e:
            print(f"Could not open browser automatically: {e}")

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print(f"\n🛑 Server stopped")

if __name__ == "__main__":
    start_server()