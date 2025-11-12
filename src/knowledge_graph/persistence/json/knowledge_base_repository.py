from __future__ import annotations

from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime
import json
import uuid
import logging

from ...ports.knowledge_base import KnowledgeBaseRepository
from ...data_structs.knowledge_base import KnowledgeBase


class JSONKnowledgeBaseRepository(KnowledgeBaseRepository):
    """A JSON-file-backed KnowledgeBase repository for development.

    Stores items in a single file under project_root/database/knowledge_bases.json.
    Idempotent on (owner_id, slug) for create.
    """

    def __init__(self, registry_path: Optional[str] = None) -> None:
        self._path = Path(registry_path) if registry_path else self._default_path()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._write({"items": []})
        self._logger = logging.getLogger("knowledge_graph.persistence.json.kb")

    def create(self, name: str, slug: str, *, owner_id: Optional[str] = None, description: Optional[str] = None) -> KnowledgeBase:
        self._logger.info(f"KB(create) json slug={slug} owner_id={owner_id or '-'}")
        items = self._read_items()
        for it in items:
            if it.get("slug") == slug and it.get("owner_id") == owner_id:
                self._logger.info(f"KB(create) exists kb_id={it.get('id')} slug={slug}")
                return KnowledgeBase(**it)

        now = datetime.utcnow()
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            name=name,
            slug=slug,
            owner_id=owner_id,
            description=description,
            created_at=now,
            updated_at=now,
        )
        items.append(kb.model_dump())
        self._write({"items": items})
        self._logger.info(f"KB(create) upserted kb_id={kb.id} slug={kb.slug}")
        return kb

    def get_by_id(self, kb_id: str) -> Optional[KnowledgeBase]:
        items = self._read_items()
        for it in items:
            if it.get("id") == kb_id:
                return KnowledgeBase(**it)
        return None

    def get_by_slug(self, slug: str, *, owner_id: Optional[str] = None) -> Optional[KnowledgeBase]:
        items = self._read_items()
        for it in items:
            if it.get("slug") == slug and (owner_id is None or it.get("owner_id") == owner_id):
                return KnowledgeBase(**it)
        return None

    def list(self, *, owner_id: Optional[str] = None) -> List[KnowledgeBase]:
        items = self._read_items()
        if owner_id is not None:
            items = [it for it in items if it.get("owner_id") == owner_id]
        self._logger.info(f"KB(list) json owner_id={owner_id or '-'} count={len(items)}")
        return [KnowledgeBase(**it) for it in items]

    # --------------- internal helpers ---------------
    def _default_path(self) -> Path:
        project_root = Path(__file__).resolve().parents[4]
        return project_root / "database" / "knowledge_bases.json"

    def _read(self) -> Dict[str, Any]:
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
        except FileNotFoundError:
            data = {"items": []}
        return data

    def _write(self, data: Dict[str, Any]) -> None:
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    def _read_items(self) -> List[Dict[str, Any]]:
        data = self._read()
        return list(data.get("items") or [])
