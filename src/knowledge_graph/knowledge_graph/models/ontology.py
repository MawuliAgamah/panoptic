

from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class Entity:
    """Entity in the ontology"""
    name: str
    type: str
    category: str

@dataclass
class Relationship:
    """Relationship in the ontology"""
    source: str
    relation: str
    target: str
    context: str
    
@dataclass
class Ontology:
    """Ontology for a document"""
    document_id: str
    entities: List[Entity]
    relationships: List[Relationship]

