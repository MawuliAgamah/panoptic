import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime


class JsonKnowledgeStore:
    def __init__(self, data_file: str = None):
        if data_file is None:
            # Get the project root directory (two levels up from this file)
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))
            data_file = os.path.join(project_root, "database", "knowledge_store.json")

        self.data_file = data_file
        self.data = self._load_data()
 
    def _load_data(self) -> Dict[str, Any]:
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r') as f:
                return json.load(f)
        return {"facts": [], "entities": [], "relationships": [], "metadata": {}}

    def _save_data(self) -> None:
        with open(self.data_file, 'w') as f:
            json.dump(self.data, f, indent=2)

    def search_facts(self, query: str) -> List[Dict[str, Any]]:
        query_lower = query.lower()
        results = []

        for fact in self.data.get("facts", []):
            if (query_lower in fact["content"].lower() or
                any(query_lower in tag.lower() for tag in fact.get("tags", [])) or
                query_lower in fact.get("category", "").lower()):
                results.append(fact)

        return results

    def add_fact(self, content: str, category: str = "general", tags: List[str] = None) -> Dict[str, Any]:
        if tags is None:
            tags = []

        new_id = max([fact["id"] for fact in self.data.get("facts", [])], default=0) + 1

        new_fact = {
            "id": new_id,
            "content": content,
            "category": category,
            "tags": tags,
            "created_at": datetime.now().isoformat()
        }

        self.data.setdefault("facts", []).append(new_fact)
        self._update_metadata()
        self._save_data()

        return new_fact

    def get_all_facts(self) -> List[Dict[str, Any]]:
        return self.data.get("facts", [])

    def get_entities(self) -> List[Dict[str, Any]]:
        return self.data.get("entities", [])

    def get_relationships(self) -> List[Dict[str, Any]]:
        return self.data.get("relationships", [])

    def add_entity(self, name: str, entity_type: str = "general", document_id: str = None, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Add an entity to the knowledge store."""
        if metadata is None:
            metadata = {}

        # Check if entity already exists
        existing_entity = self._find_entity(name)
        if existing_entity:
            # Update existing entity with new document reference and metadata
            if document_id and document_id not in existing_entity.get("document_ids", []):
                existing_entity.setdefault("document_ids", []).append(document_id)
            
            # Update metadata with new information
            existing_entity["metadata"] = metadata
            existing_entity["last_updated"] = datetime.now().isoformat()
            self._save_data()
            return existing_entity

        # Create new entity
        new_id = max([entity["id"] for entity in self.data.get("entities", [])], default=0) + 1

        new_entity = {
            "id": new_id,
            "name": name,
            "type": entity_type,
            "document_ids": [document_id] if document_id else [],
            "metadata": metadata,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat()
        }

        self.data.setdefault("entities", []).append(new_entity)
        self._update_metadata()
        self._save_data()

        return new_entity

    def add_relationship(self, source_entity: str, relation_type: str, target_entity: str,
                        document_id: str = None, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Add a relationship to the knowledge store."""
        if metadata is None:
            metadata = {}

        # Check if relationship already exists
        existing_rel = self._find_relationship(source_entity, relation_type, target_entity)
        if existing_rel:
            # Update existing relationship with new document reference
            if document_id and document_id not in existing_rel.get("document_ids", []):
                existing_rel.setdefault("document_ids", []).append(document_id)
                existing_rel["last_updated"] = datetime.now().isoformat()
                self._save_data()
            return existing_rel

        # Create new relationship
        new_id = max([rel["id"] for rel in self.data.get("relationships", [])], default=0) + 1

        new_relationship = {
            "id": new_id,
            "source_entity": source_entity,
            "relation_type": relation_type,
            "target_entity": target_entity,
            "document_ids": [document_id] if document_id else [],
            "metadata": metadata,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat()
        }

        self.data.setdefault("relationships", []).append(new_relationship)
        self._update_metadata()
        self._save_data()

        return new_relationship

    def save_knowledge_graph(self, document_id: str, kg_data: Dict[str, Any], document_metadata: Dict[str, Any] = None) -> bool:
        """Save complete knowledge graph data from a document."""
        try:
            entities = kg_data.get('entities', set())
            relations = kg_data.get('relations', [])

            print(f"💾 Saving KG data: {len(entities)} entities, {len(relations)} relations")

            # Add entities
            entities_added = 0
            for entity_name in entities:
                result = self.add_entity(
                    name=entity_name,
                    entity_type="extracted",
                    document_id=document_id,
                    metadata=document_metadata or {}
                )
                if result:
                    entities_added += 1
            print(f"✅ Entities processed: {entities_added}/{len(entities)}")

            # Add relationships
            relations_added = 0
            relations_skipped = 0
            for relation in relations:
                try:
                    print(f"🔗 Processing relation: {relation}")
                    if isinstance(relation, tuple) and len(relation) >= 3:
                        source, rel_type, target = str(relation[0]), str(relation[1]), str(relation[2])
                        print(f"   Source: '{source}', Type: '{rel_type}', Target: '{target}'")

                        result = self.add_relationship(
                            source_entity=source,
                            relation_type=rel_type,
                            target_entity=target,
                            document_id=document_id,
                            metadata=document_metadata or {}
                        )
                        if result:
                            relations_added += 1
                            print(f"   ✅ Relationship added successfully")
                        else:
                            print(f"   ⚠️ Relationship already exists or failed to add")
                    else:
                        print(f"   ❌ Skipping invalid relation format: {relation}")
                        relations_skipped += 1
                except Exception as e:
                    print(f"   ❌ Error processing relation {relation}: {e}")
                    import traceback
                    traceback.print_exc()
                    relations_skipped += 1
                    continue

            print(f"✅ Relationships processed: {relations_added} added, {relations_skipped} skipped")
            return True

        except Exception as e:
            print(f"Error saving knowledge graph: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _find_entity(self, name: str) -> Optional[Dict[str, Any]]:
        """Find an entity by name."""
        for entity in self.data.get("entities", []):
            if entity["name"].lower() == name.lower():
                return entity
        return None

    def _find_relationship(self, source: str, relation_type: str, target: str) -> Optional[Dict[str, Any]]:
        """Find a relationship by its components."""
        for rel in self.data.get("relationships", []):
            # Handle new format with entity names
            if "source_entity" in rel and "target_entity" in rel and "relation_type" in rel:
                if (rel["source_entity"].lower() == source.lower() and
                    rel["relation_type"].lower() == relation_type.lower() and
                    rel["target_entity"].lower() == target.lower()):
                    return rel
            # Skip old format relationships (with entity IDs) - we can't match them by name
            # Old format has: source_entity_id, target_entity_id, relationship_type
        return None

    def search_entities(self, query: str) -> List[Dict[str, Any]]:
        """Search entities by name or metadata."""
        query_lower = query.lower()
        results = []

        for entity in self.data.get("entities", []):
            if (query_lower in entity["name"].lower() or
                query_lower in entity.get("type", "").lower()):
                results.append(entity)

        return results

    def search_relationships(self, query: str) -> List[Dict[str, Any]]:
        """Search relationships by entity names or relation types."""
        query_lower = query.lower()
        results = []

        for rel in self.data.get("relationships", []):
            # Handle both old and new relationship formats
            if "source_entity" in rel:
                # New format
                if (query_lower in rel["source_entity"].lower() or
                    query_lower in rel["target_entity"].lower() or
                    query_lower in rel["relation_type"].lower()):
                    results.append(rel)
            elif "relationship_type" in rel:
                # Old format - skip for now or convert
                if query_lower in rel["relationship_type"].lower():
                    results.append(rel)

        return results

    def get_entity_relationships(self, entity_name: str) -> List[Dict[str, Any]]:
        """Get all relationships involving a specific entity."""
        entity_lower = entity_name.lower()
        results = []

        for rel in self.data.get("relationships", []):
            # Handle both old and new relationship formats
            if "source_entity" in rel:
                # New format
                if (rel["source_entity"].lower() == entity_lower or
                    rel["target_entity"].lower() == entity_lower):
                    results.append(rel)
            # Old format doesn't have entity names stored directly

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge store statistics."""
        return {
            "total_facts": len(self.data.get("facts", [])),
            "total_entities": len(self.data.get("entities", [])),
            "total_relationships": len(self.data.get("relationships", [])),
            "unique_documents": len(set(
                doc_id
                for entity in self.data.get("entities", [])
                for doc_id in entity.get("document_ids", [])
            )),
            "last_updated": self.data.get("metadata", {}).get("last_updated")
        }

    def clear_all_data(self) -> None:
        """Clear all data from the knowledge store."""
        self.data = {
            "facts": [],
            "entities": [],
            "relationships": [],
            "metadata": {
                "version": "1.0",
                "last_updated": datetime.now().isoformat(),
                "total_facts": 0,
                "total_entities": 0,
                "total_relationships": 0
            }
        }
        self._save_data()

    def _update_metadata(self) -> None:
        self.data["metadata"] = {
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "total_facts": len(self.data.get("facts", [])),
            "total_entities": len(self.data.get("entities", [])),
            "total_relationships": len(self.data.get("relationships", []))
        }