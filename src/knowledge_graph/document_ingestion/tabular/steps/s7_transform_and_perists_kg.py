"""Transform CSV data to Knowledge Graph and persist it to the database.

This step takes the mapping_spec created by previous steps and uses it to
transform CSV rows into entities and relationships, then persists them to
the graph repository.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from ...document_pipeline import DocumentPipelineContext, PipelineStep
from ..agents_tools import sniff_csv, read_rows
from knowledge_graph.agent.normalizers import REGISTRY as NORMALIZERS
from knowledge_graph.persistence.sqlite.sql_lite import SqlLite
from knowledge_graph.settings.settings import get_settings

logger = logging.getLogger("knowledgeAgent.pipeline.csv.transform_kg")


def _apply_transform(value: Any, name: Optional[str]) -> str:
    """Apply a normalization transform to a value."""
    if not name:
        return "" if value is None else str(value)
    fn = NORMALIZERS.get(name)
    return fn(value) if fn else ("" if value is None else str(value))


def _compute_entity_id(row: Dict[str, Any], key_spec: Dict[str, Any]) -> str:
    """Compute an entity ID from a row using a key specification.
    
    Supports either {column,prefix,transform} or {template,transforms}.
    """
    template = key_spec.get("template")
    if template:
        transforms = key_spec.get("transforms", {}) or {}
        # Replace {Field} placeholders with normalized values
        def repl(match):
            col = match.group(1)
            xf = transforms.get(col)
            return _apply_transform(row.get(col, ""), xf)
        value = re.sub(r"\{([^}]+)\}", repl, template)
        return value if value else ""
    else:
        prefix = key_spec.get("prefix", "")
        col = key_spec.get("column")
        xform = key_spec.get("transform")
        raw = row.get(col, "")
        norm = _apply_transform(raw, xform)
        return f"{prefix}{norm}" if norm else ""


def _entity_key_spec(entity_spec: Dict[str, Any]) -> Dict[str, Any]:
    """Extract the key specification from an entity spec."""
    key = entity_spec.get("key") or {}
    if not isinstance(key, dict):
        key = {}
    return key


def _resolve_node_id(row: Dict[str, Any], mapping: Dict[str, Any], which: Dict[str, Any]) -> str:
    """Resolve a node ID from a row using mapping and entity specification.
    
    which: {entity: "Person"} or {entity: "Education", by: {prefix, column, transform}}
    """
    entity_name = which.get("entity")
    entities = mapping.get("entities", {})
    e_spec = entities.get(entity_name, {}) if isinstance(entities, dict) else {}
    by = which.get("by")
    if by and isinstance(by, dict):
        key_spec = by
    else:
        key_spec = _entity_key_spec(e_spec)
    return _compute_entity_id(row, key_spec)


def _iter_dict_rows(csv_path: str, limit: Optional[int] = None, *, delimiter: Optional[str] = None) -> List[Dict[str, Any]]:
    """Read CSV rows and convert them to dictionaries.
    
    Returns a list of dictionaries where keys are column headers.
    """
    dialect = sniff_csv(csv_path, delimiter=delimiter)
    rows = read_rows(csv_path, dialect, limit=limit if limit is not None else 1_000_000_000)
    if not rows:
        return []
    headers = rows[0]
    result = []
    for r in rows[1:]:
        # Normalize length
        if len(r) < len(headers):
            r = r + [""] * (len(headers) - len(r))
        elif len(r) > len(headers):
            r = r[: len(headers)]
        result.append({h: v for h, v in zip(headers, r)})
    return result


class TransformAndPersistKGStep(PipelineStep):
    name = "transform_and_persist_kg"
    
    def run(self, context: DocumentPipelineContext) -> DocumentPipelineContext:
        document = context.ensure_document()
        mapping_spec = getattr(context, "mapping_spec", None)
        csv_profile = getattr(context, "csv_profile", None)
        ontology_spec = getattr(context, "ontology_specification", None)
        
        if not mapping_spec or not csv_profile:
            logger.warning("Missing mapping_spec or csv_profile, skipping KG transformation")
            return context
        
        logger.info(f"🔄 [STEP 7] Starting KG transformation for document_id={document.id}")
        
        # Transform CSV to KG (inline implementation)
        csv_path = document.file_path
        mapping = mapping_spec
        delimiter = csv_profile.delimiter
        
        # Build a map of entity names to their ontology definitions for label inference
        ontology_entities_map = {}
        if ontology_spec:
            # Handle both list and dict formats for entities
            entities_list = ontology_spec.get("entities", [])
            if isinstance(entities_list, list):
                for entity in entities_list:
                    if isinstance(entity, dict):
                        entity_name = entity.get("name", "")
                        if entity_name:
                            ontology_entities_map[entity_name] = entity
            elif isinstance(entities_list, dict):
                ontology_entities_map = entities_list
        
        logger.info(f"[transform] start path={csv_path}")
        
        # Store entities with their data: entity_id -> {entity_name, row_data}
        entities_data: Dict[str, Dict[str, Any]] = {}
        relations: Set[Tuple[str, str, str]] = set()
        
        ent_map: Dict[str, Any] = mapping.get("entities", {}) if isinstance(mapping.get("entities"), dict) else {}
        edges = mapping.get("edges", []) or []
        null_policy = (mapping.get("options", {}) or {}).get("null_policy", "skip")
        
        # Debug: Log mapping spec structure
        logger.info(f"🔍 [DEBUG] Mapping spec entities: {list(ent_map.keys())}")
        for e_name, e_spec in ent_map.items():
            logger.info(f"🔍 [DEBUG] Entity '{e_name}': key={e_spec.get('key')}, attributes={e_spec.get('attributes', [])}")
        
        row_count = 0
        for row in _iter_dict_rows(csv_path, limit=None, delimiter=delimiter):
            row_count += 1
            # Create nodes for each entity spec (if key is resolvable from row)
            for e_name, e_spec in ent_map.items():
                node_id = _compute_entity_id(row, _entity_key_spec(e_spec))
                if node_id:
                    # Store entity with its name and row data for later label/property extraction
                    if node_id not in entities_data:
                        entities_data[node_id] = {
                            "entity_name": e_name,
                            "row_data": row.copy()  # Store a copy of the row
                        }
                    else:
                        # If entity already exists, merge row data (keep first non-empty values)
                        existing = entities_data[node_id]["row_data"]
                        for key, value in row.items():
                            if key not in existing or not existing[key]:
                                existing[key] = value
            
            # Create edges
            for e in edges:
                pred = e.get("predicate") or e.get("label") or e.get("relation")
                if not pred:
                    continue
                src = e.get("source") or {}
                tgt = e.get("target") or {}
                src_id = _resolve_node_id(row, mapping, src)
                tgt_id = _resolve_node_id(row, mapping, tgt)
                if not src_id or not tgt_id:
                    if null_policy != "keep":
                        continue
                else:
                    # Ensure referenced nodes exist (create placeholder entries if needed)
                    if src_id and src_id not in entities_data:
                        entities_data[src_id] = {
                            "entity_name": src.get("entity", "Entity"),
                            "row_data": row.copy()
                        }
                    if tgt_id and tgt_id not in entities_data:
                        entities_data[tgt_id] = {
                            "entity_name": tgt.get("entity", "Entity"),
                            "row_data": row.copy()
                        }
                    relations.add((src_id, pred, tgt_id))
        
        logger.info(
            "[transform] done rows=%d entities=%d relations=%d",
            row_count,
            len(entities_data),
            len(relations),
        )
        
        # Convert to format expected by save_knowledge_graph
        # Extract labels and properties from CSV columns using attributes mapping
        entity_list = []
        for entity_id, entity_info in sorted(entities_data.items()):
            entity_name = entity_info["entity_name"]
            row_data = entity_info["row_data"]
            
            # Get entity spec to access attributes mapping
            e_spec = ent_map.get(entity_name, {})
            attributes = e_spec.get("attributes", []) or []
            
            # Debug: Log entity processing
            logger.debug(f"🔍 [DEBUG] Processing entity: {entity_name} (id={entity_id})")
            logger.debug(f"🔍 [DEBUG] Row data keys: {list(row_data.keys())}")
            logger.debug(f"🔍 [DEBUG] Attributes mapped: {[a.get('name') if isinstance(a, dict) else str(a) for a in attributes]}")
            
            # Extract label from CSV using ontology-defined attributes
            # Strategy: Use heuristics based on attribute names and types from ontology
            label = entity_id  # Default to ID
            
            # Get ontology entity definition if available
            ontology_entity = ontology_entities_map.get(entity_name, {})
            ontology_attrs = ontology_entity.get("attributes", []) or []
            
            # Build a map of attribute names to their ontology definitions
            ontology_attr_map = {}
            for oa in ontology_attrs:
                if isinstance(oa, dict):
                    attr_name = oa.get("name", "")
                    if attr_name:
                        ontology_attr_map[attr_name.lower()] = oa
            
            # Extract label using ontology-driven heuristics
            # Priority: Use ontology attribute types and descriptions to infer the best label
            label_candidates = []
            for attr in attributes:
                if isinstance(attr, dict):
                    mapped_attr_name = attr.get("name", "").lower()
                    column = attr.get("column")
                    
                    if not column:
                        continue
                    
                    # Get ontology definition for this attribute if available
                    oa_def = ontology_attr_map.get(mapped_attr_name, {})
                    attr_type = oa_def.get("type", "").lower() if oa_def else ""
                    attr_description = oa_def.get("description", "").lower() if oa_def else ""
                    
                    # Calculate priority based on ontology metadata and attribute name
                    priority = 999  # Lower is better
                    
                    # Priority 1: Attribute name contains label indicators (from ontology naming)
                    if any(kw in mapped_attr_name for kw in ["name", "title", "label"]):
                        priority = 1
                    # Priority 2: Description mentions label/display/name (from ontology)
                    elif any(kw in attr_description for kw in ["name", "label", "display", "title", "identifier"]):
                        priority = 2
                    # Priority 3: Attribute name suggests display/description
                    elif any(kw in mapped_attr_name for kw in ["display", "description", "full_name"]):
                        priority = 3
                    # Priority 4: String type from ontology (not ID, not date, not numeric)
                    elif attr_type == "string" and not mapped_attr_name.endswith("_id") and "date" not in mapped_attr_name:
                        priority = 4
                    # Priority 5: Any non-ID, non-numeric, non-date attribute
                    elif not mapped_attr_name.endswith("_id") and attr_type not in ["integer", "float", "date", "datetime"]:
                        priority = 5
                    
                    if priority < 999:
                        label_candidates.append((priority, attr, column, mapped_attr_name))
            
            # Sort by priority and use the best candidate
            if label_candidates:
                label_candidates.sort(key=lambda x: x[0])
                _, best_attr, best_column, best_attr_name = label_candidates[0]
                if best_column in row_data:
                    label_value = row_data.get(best_column, "").strip()
                    if label_value:
                        label = label_value
                        oa_def = ontology_attr_map.get(best_attr_name, {})
                        logger.debug(f"✅ [DEBUG] Entity {entity_id}: Using label '{label}' from column '{best_column}' (attribute: {best_attr.get('name')}, type: {oa_def.get('type', 'unknown')})")
            
            # If no label found from candidates, try to find a non-ID attribute
            if label == entity_id and attributes:
                # Skip ID columns (those ending in "_ID" or "_id") and try other attributes
                for attr in attributes:
                    if isinstance(attr, dict):
                        attr_name = attr.get("name", "").lower()
                        column = attr.get("column")
                        # Skip ID columns
                        if not attr_name.endswith("_id") and column and column in row_data:
                            label_value = row_data.get(column, "").strip()
                            if label_value:
                                label = label_value
                                logger.debug(f"✅ [DEBUG] Entity {entity_id}: Using label '{label}' from non-ID attribute column '{column}' (attribute: {attr.get('name')})")
                                break
                
                # If still no label, use first attribute (even if it's an ID)
                if label == entity_id and attributes:
                    first_attr = attributes[0]
                    if isinstance(first_attr, dict):
                        column = first_attr.get("column")
                        if column and column in row_data:
                            label_value = row_data.get(column, "").strip()
                            if label_value:
                                label = label_value
                                logger.debug(f"✅ [DEBUG] Entity {entity_id}: Using label '{label}' from first attribute column '{column}' (fallback)")
            
            # Warn if no label found
            if label == entity_id:
                logger.warning(f"⚠️ [DEBUG] Entity {entity_id}: No label found, using ID. Attributes: {[a.get('name') if isinstance(a, dict) else str(a) for a in attributes]}")
                logger.warning(f"⚠️ [DEBUG] Available row columns: {list(row_data.keys())}")
            
            # Extract properties from all mapped attributes
            properties = {}
            for attr in attributes:
                if isinstance(attr, dict):
                    attr_name = attr.get("name", "")
                    column = attr.get("column")
                    if column and column in row_data:
                        value = row_data.get(column, "")
                        if value:  # Only include non-empty values
                            properties[attr_name] = value
            
            # Debug: Log properties extraction
            if properties:
                logger.debug(f"🔍 [DEBUG] Entity {entity_id}: Properties extracted: {list(properties.keys())}")
            else:
                logger.warning(f"⚠️ [DEBUG] Entity {entity_id}: No properties extracted. Attributes: {[a.get('name') if isinstance(a, dict) else str(a) for a in attributes]}")
            
            # Determine entity type from entity name (could be enhanced)
            entity_type = entity_name.lower() if entity_name else "concept"
            
            entity_list.append({
                "id": entity_id,
                "type": entity_type,
                "label": label,
                "properties": properties
            })
        
        # Relationships: from list of tuples to list of dicts
        relationship_list = [
            {
                "source": src_id,
                "target": tgt_id,
                "predicate": pred,
                "properties": {}
            }
            for src_id, pred, tgt_id in sorted(relations)
        ]
        
        kg_data = {
            "entities": entity_list,
            "relationships": relationship_list
        }
        
        # Persist to database
        sqlite = SqlLite(settings=get_settings())
        graph_repo = sqlite.graph_repository()
        
        logger.info(f"💾 [STEP 7] Persisting KG: {len(entity_list)} entities, {len(relationship_list)} relationships")
        success = graph_repo.save_to_knowledge_graph(
            document_id=str(document.id),
            kg_data=kg_data,
            kb_id=str(context.params.kb_id) if context.params.kb_id else None
        )
        
        if success:
            logger.info(f"✅ [STEP 7] KG persisted successfully: {len(entity_list)} entities, {len(relationship_list)} relationships")
            context.results[self.name] = {
                "entities_count": len(entity_list),
                "relationships_count": len(relationship_list),
                "rows_processed": row_count
            }
        else:
            logger.error("❌ [STEP 7] Failed to persist KG")
            context.results[self.name] = {"error": "Failed to persist KG"}
        
        return context