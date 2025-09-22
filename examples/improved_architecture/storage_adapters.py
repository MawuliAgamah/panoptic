"""Storage adapter implementations - completely separate from business logic"""

import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import sqlite3
from .repositories import StorageAdapter, QueryOptions, QueryFilter


class JSONStorageAdapter(StorageAdapter):
    """JSON file storage adapter - no business logic, just storage operations"""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_entity_file(self, entity_type: str) -> Path:
        """Get file path for entity type"""
        return self.base_path / f"{entity_type}.json"

    def _load_entity_data(self, entity_type: str) -> Dict[str, Dict[str, Any]]:
        """Load all entities of a type from file"""
        file_path = self._get_entity_file(entity_type)

        if not file_path.exists():
            return {}

        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def _save_entity_data(self, entity_type: str, data: Dict[str, Dict[str, Any]]) -> None:
        """Save all entities of a type to file"""
        file_path = self._get_entity_file(entity_type)

        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)

    def save_entity(self, entity_type: str, entity_id: str, data: Dict[str, Any]) -> None:
        """Save entity data"""
        all_entities = self._load_entity_data(entity_type)
        all_entities[entity_id] = data
        self._save_entity_data(entity_type, all_entities)

    def load_entity(self, entity_type: str, entity_id: str) -> Optional[Dict[str, Any]]:
        """Load entity data"""
        all_entities = self._load_entity_data(entity_type)
        return all_entities.get(entity_id)

    def load_entities(self, entity_type: str, options: Optional[QueryOptions] = None) -> List[Dict[str, Any]]:
        """Load multiple entities"""
        all_entities = self._load_entity_data(entity_type)
        entities = list(all_entities.values())

        if not options:
            return entities

        # Apply filters
        if options.filters:
            entities = self._apply_filters(entities, options.filters)

        # Apply sorting
        if options.order_by:
            entities = self._apply_sorting(entities, options.order_by, options.order_desc)

        # Apply pagination
        if options.offset > 0:
            entities = entities[options.offset:]

        if options.limit:
            entities = entities[:options.limit]

        return entities

    def delete_entity(self, entity_type: str, entity_id: str) -> bool:
        """Delete entity"""
        all_entities = self._load_entity_data(entity_type)

        if entity_id not in all_entities:
            return False

        del all_entities[entity_id]
        self._save_entity_data(entity_type, all_entities)
        return True

    def exists_entity(self, entity_type: str, entity_id: str) -> bool:
        """Check if entity exists"""
        all_entities = self._load_entity_data(entity_type)
        return entity_id in all_entities

    def count_entities(self, entity_type: str, options: Optional[QueryOptions] = None) -> int:
        """Count entities"""
        entities = self.load_entities(entity_type, options)
        return len(entities)

    def _apply_filters(self, entities: List[Dict[str, Any]], filters: List[QueryFilter]) -> List[Dict[str, Any]]:
        """Apply filters to entities"""
        filtered = []

        for entity in entities:
            matches = True

            for filter_rule in filters:
                field_value = self._get_nested_field(entity, filter_rule.field)

                if not self._check_filter(field_value, filter_rule.operator, filter_rule.value):
                    matches = False
                    break

            if matches:
                filtered.append(entity)

        return filtered

    def _get_nested_field(self, data: Dict[str, Any], field_path: str) -> Any:
        """Get nested field value using dot notation"""
        fields = field_path.split('.')
        value = data

        for field in fields:
            if isinstance(value, dict) and field in value:
                value = value[field]
            else:
                return None

        return value

    def _check_filter(self, field_value: Any, operator: str, filter_value: Any) -> bool:
        """Check if field value matches filter"""
        if field_value is None:
            return operator == "eq" and filter_value is None

        if operator == "eq":
            return field_value == filter_value
        elif operator == "ne":
            return field_value != filter_value
        elif operator == "gt":
            return field_value > filter_value
        elif operator == "gte":
            return field_value >= filter_value
        elif operator == "lt":
            return field_value < filter_value
        elif operator == "lte":
            return field_value <= filter_value
        elif operator == "in":
            if isinstance(field_value, list):
                return any(item in filter_value for item in field_value)
            return field_value in filter_value
        elif operator == "like":
            return str(filter_value).lower() in str(field_value).lower()

        return False

    def _apply_sorting(self, entities: List[Dict[str, Any]], order_by: str, desc: bool = False) -> List[Dict[str, Any]]:
        """Apply sorting to entities"""
        def sort_key(entity):
            value = self._get_nested_field(entity, order_by)
            # Handle None values by putting them at the end
            if value is None:
                return "" if not desc else "~"  # ASCII tilde is high value
            return value

        return sorted(entities, key=sort_key, reverse=desc)


class SQLiteStorageAdapter(StorageAdapter):
    """SQLite storage adapter for better performance and querying"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_db_directory()
        self._initialize_database()

    def _ensure_db_directory(self):
        """Ensure database directory exists"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    def _initialize_database(self):
        """Initialize database with tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS entities (
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (entity_type, entity_id)
                )
            ''')

            # Create indexes for better performance
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_entity_type
                ON entities(entity_type)
            ''')

            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_updated_at
                ON entities(updated_at)
            ''')

    def save_entity(self, entity_type: str, entity_id: str, data: Dict[str, Any]) -> None:
        """Save entity data"""
        json_data = json.dumps(data, default=str)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO entities
                (entity_type, entity_id, data, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (entity_type, entity_id, json_data))

    def load_entity(self, entity_type: str, entity_id: str) -> Optional[Dict[str, Any]]:
        """Load entity data"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT data FROM entities
                WHERE entity_type = ? AND entity_id = ?
            ''', (entity_type, entity_id))

            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
            return None

    def load_entities(self, entity_type: str, options: Optional[QueryOptions] = None) -> List[Dict[str, Any]]:
        """Load multiple entities"""
        query = "SELECT data FROM entities WHERE entity_type = ?"
        params = [entity_type]

        # Note: For full SQLite implementation, you'd want to properly translate
        # QueryOptions to SQL WHERE clauses, ORDER BY, LIMIT, etc.
        # This is a simplified version

        if options and options.limit:
            query += " LIMIT ?"
            params.append(options.limit)

        if options and options.offset:
            query += " OFFSET ?"
            params.append(options.offset)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

            entities = [json.loads(row[0]) for row in rows]

            # Apply filters in Python (for simplicity)
            # In production, you'd want to translate filters to SQL WHERE clauses
            if options and options.filters:
                entities = self._apply_python_filters(entities, options.filters)

            return entities

    def delete_entity(self, entity_type: str, entity_id: str) -> bool:
        """Delete entity"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                DELETE FROM entities
                WHERE entity_type = ? AND entity_id = ?
            ''', (entity_type, entity_id))

            return cursor.rowcount > 0

    def exists_entity(self, entity_type: str, entity_id: str) -> bool:
        """Check if entity exists"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT 1 FROM entities
                WHERE entity_type = ? AND entity_id = ?
                LIMIT 1
            ''', (entity_type, entity_id))

            return cursor.fetchone() is not None

    def count_entities(self, entity_type: str, options: Optional[QueryOptions] = None) -> int:
        """Count entities"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT COUNT(*) FROM entities
                WHERE entity_type = ?
            ''', (entity_type,))

            return cursor.fetchone()[0]

    def _apply_python_filters(self, entities: List[Dict[str, Any]], filters: List[QueryFilter]) -> List[Dict[str, Any]]:
        """Apply filters in Python (fallback for complex queries)"""
        # Same logic as JSON adapter
        filtered = []

        for entity in entities:
            matches = True

            for filter_rule in filters:
                field_value = self._get_nested_field(entity, filter_rule.field)

                if not self._check_filter(field_value, filter_rule.operator, filter_rule.value):
                    matches = False
                    break

            if matches:
                filtered.append(entity)

        return filtered

    def _get_nested_field(self, data: Dict[str, Any], field_path: str) -> Any:
        """Get nested field value using dot notation"""
        fields = field_path.split('.')
        value = data

        for field in fields:
            if isinstance(value, dict) and field in value:
                value = value[field]
            else:
                return None

        return value

    def _check_filter(self, field_value: Any, operator: str, filter_value: Any) -> bool:
        """Check if field value matches filter"""
        if field_value is None:
            return operator == "eq" and filter_value is None

        if operator == "eq":
            return field_value == filter_value
        elif operator == "ne":
            return field_value != filter_value
        elif operator == "gt":
            return field_value > filter_value
        elif operator == "gte":
            return field_value >= filter_value
        elif operator == "lt":
            return field_value < filter_value
        elif operator == "lte":
            return field_value <= filter_value
        elif operator == "in":
            if isinstance(field_value, list):
                return any(item in filter_value for item in field_value)
            return field_value in filter_value
        elif operator == "like":
            return str(filter_value).lower() in str(field_value).lower()

        return False


# Factory for creating storage adapters based on configuration
def create_storage_adapter(provider: str, **config) -> StorageAdapter:
    """Factory function to create storage adapter based on provider"""

    if provider == "json":
        path = config.get("path", "database/flashcards")
        return JSONStorageAdapter(path)

    elif provider == "sqlite":
        db_path = config.get("db_path", "database/flashcards.db")
        return SQLiteStorageAdapter(db_path)

    else:
        raise ValueError(f"Unsupported storage provider: {provider}")