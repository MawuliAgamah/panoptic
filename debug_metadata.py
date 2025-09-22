#!/usr/bin/env python3
"""
Debug script to check what metadata is being stored in entities.
"""

import sys
import os
from pathlib import Path

# Add src to path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

from services.knowledge_store import JsonKnowledgeStore

def debug_metadata():
    """Debug what metadata is being stored."""
    
    print("🔍 Debugging Entity Metadata Storage")
    print("=" * 40)
    
    # Create a test knowledge store
    store = JsonKnowledgeStore("debug_knowledge_store.json")
    
    # Test metadata
    test_metadata = {
        'title': 'Test Document',
        'tags': ['AI', 'Machine Learning'],
        'categories': ['Computer Science', 'Technology'],
        'domains': ['Machine Learning', 'AI']
    }
    
    print(f"📋 Test metadata: {test_metadata}")
    
    # Add an entity with metadata
    result = store.add_entity(
        name="Test Entity",
        entity_type="concept",
        document_id="test_doc",
        metadata=test_metadata
    )
    
    print(f"✅ Entity added: {result}")
    
    # Get all entities
    entities = store.get_entities()
    print(f"📊 Total entities: {len(entities)}")
    
    for entity in entities:
        print(f"🔍 Entity: {entity['name']}")
        print(f"   Metadata: {entity.get('metadata', {})}")
        print(f"   Document IDs: {entity.get('document_ids', [])}")
        print()
    
    # Test domain extraction
    print("🏷️ Testing domain extraction:")
    domains = set()
    for entity in entities:
        metadata = entity.get('metadata', {})
        if 'domains' in metadata:
            domains.update(metadata['domains'])
        if 'categories' in metadata:
            domains.update(metadata['categories'])
        if 'tags' in metadata:
            domains.update(metadata['tags'])
    
    print(f"📊 Extracted domains: {sorted(list(domains))}")
    
    # Cleanup
    if os.path.exists("debug_knowledge_store.json"):
        os.remove("debug_knowledge_store.json")

if __name__ == "__main__":
    debug_metadata()
