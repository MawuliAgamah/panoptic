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

    def _update_metadata(self) -> None:
        self.data["metadata"] = {
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "total_facts": len(self.data.get("facts", [])),
            "total_entities": len(self.data.get("entities", [])),
            "total_relationships": len(self.data.get("relationships", []))
        }