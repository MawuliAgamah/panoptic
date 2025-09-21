"""Knowledge Graph models for flashcard mapping"""

from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any, Set
from datetime import datetime
import uuid


@dataclass
class KGEntity:
    """Individual entity from knowledge graph"""
    entity_id: str
    name: str
    entity_type: str  # e.g., "concept", "person", "technology", "method"
    confidence: float = 1.0  # How confident we are in this entity extraction (0.0-1.0)
    aliases: List[str] = None  # Alternative names for this entity

    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KGEntity':
        return cls(**data)


@dataclass
class KGTopic:
    """Topic/Domain classification"""
    topic_id: str
    name: str
    category: str  # e.g., "programming", "mathematics", "science"
    confidence: float = 1.0  # Confidence in topic classification
    parent_topic: Optional[str] = None  # For hierarchical topics
    subtopics: List[str] = None  # Child topics

    def __post_init__(self):
        if self.subtopics is None:
            self.subtopics = []

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KGTopic':
        return cls(**data)


@dataclass
class KGDocument:
    """Source document information"""
    document_id: str
    title: str
    document_type: str  # e.g., "pdf", "markdown", "text", "webpage"
    file_path: Optional[str] = None
    content_hash: Optional[str] = None  # For change detection
    processed_date: Optional[datetime] = None
    metadata: Dict[str, Any] = None  # Additional document metadata

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if self.processed_date:
            data['processed_date'] = self.processed_date.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KGDocument':
        data = data.copy()
        if data.get('processed_date'):
            data['processed_date'] = datetime.fromisoformat(data['processed_date'])
        return cls(**data)


@dataclass
class KGRelationship:
    """Relationship between entities"""
    relationship_id: str
    source_entity_id: str
    target_entity_id: str
    relationship_type: str  # e.g., "is_a", "part_of", "used_for", "similar_to"
    confidence: float = 1.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KGRelationship':
        return cls(**data)


@dataclass
class KGMapping:
    """Complete knowledge graph mapping for a flashcard"""

    # Core identification
    mapping_id: str
    created_at: datetime
    updated_at: datetime

    # Entity-based mapping
    primary_entities: List[KGEntity]  # Main entities this flashcard tests
    secondary_entities: List[KGEntity]  # Supporting/context entities

    # Topic/Domain mapping
    primary_topics: List[KGTopic]  # Main topics/domains
    secondary_topics: List[KGTopic]  # Related topics

    # Document linking
    source_document: Optional[KGDocument]  # Primary source document
    related_documents: List[KGDocument]  # Additional relevant documents

    # Relationships
    tested_relationships: List[KGRelationship]  # Entity relationships this card tests

    # Content extraction metadata
    extraction_method: str = "manual"  # "manual", "ai_extracted", "imported"
    extraction_confidence: float = 1.0  # Overall confidence in the mapping
    content_chunks: List[str] = None  # Specific text chunks from documents

    # Performance tracking metadata
    difficulty_indicators: Dict[str, Any] = None  # Factors that might affect difficulty
    learning_objectives: List[str] = None  # What this flashcard should teach

    def __post_init__(self):
        if self.content_chunks is None:
            self.content_chunks = []
        if self.difficulty_indicators is None:
            self.difficulty_indicators = {}
        if self.learning_objectives is None:
            self.learning_objectives = []

    @classmethod
    def create_new(
        cls,
        primary_entities: List[KGEntity] = None,
        primary_topics: List[KGTopic] = None,
        source_document: Optional[KGDocument] = None,
        extraction_method: str = "manual"
    ) -> 'KGMapping':
        """Create a new KG mapping"""
        now = datetime.now()
        return cls(
            mapping_id=str(uuid.uuid4()),
            created_at=now,
            updated_at=now,
            primary_entities=primary_entities or [],
            secondary_entities=[],
            primary_topics=primary_topics or [],
            secondary_topics=[],
            source_document=source_document,
            related_documents=[],
            tested_relationships=[],
            extraction_method=extraction_method
        )

    def add_entity(self, entity: KGEntity, is_primary: bool = True) -> None:
        """Add an entity to the mapping"""
        if is_primary:
            self.primary_entities.append(entity)
        else:
            self.secondary_entities.append(entity)
        self.updated_at = datetime.now()

    def add_topic(self, topic: KGTopic, is_primary: bool = True) -> None:
        """Add a topic to the mapping"""
        if is_primary:
            self.primary_topics.append(topic)
        else:
            self.secondary_topics.append(topic)
        self.updated_at = datetime.now()

    def add_relationship(self, relationship: KGRelationship) -> None:
        """Add a relationship that this flashcard tests"""
        self.tested_relationships.append(relationship)
        self.updated_at = datetime.now()

    def get_all_entities(self) -> List[KGEntity]:
        """Get all entities (primary + secondary)"""
        return self.primary_entities + self.secondary_entities

    def get_all_topics(self) -> List[KGTopic]:
        """Get all topics (primary + secondary)"""
        return self.primary_topics + self.secondary_topics

    def get_all_documents(self) -> List[KGDocument]:
        """Get all documents (source + related)"""
        documents = self.related_documents.copy()
        if self.source_document:
            documents.insert(0, self.source_document)
        return documents

    def get_entity_names(self) -> Set[str]:
        """Get all entity names for quick lookup"""
        names = set()
        for entity in self.get_all_entities():
            names.add(entity.name.lower())
            names.update(alias.lower() for alias in entity.aliases)
        return names

    def get_topic_names(self) -> Set[str]:
        """Get all topic names for quick lookup"""
        return {topic.name.lower() for topic in self.get_all_topics()}

    def calculate_complexity_score(self) -> float:
        """Calculate a complexity score based on KG connections"""
        # More entities, topics, and relationships = higher complexity
        entity_count = len(self.get_all_entities())
        topic_count = len(self.get_all_topics())
        relationship_count = len(self.tested_relationships)

        # Weighted complexity score
        complexity = (
            entity_count * 0.3 +
            topic_count * 0.2 +
            relationship_count * 0.4 +
            (1.0 - self.extraction_confidence) * 0.1  # Lower confidence = higher complexity
        )

        return min(complexity, 10.0)  # Cap at 10.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON storage"""
        return {
            'mapping_id': self.mapping_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'primary_entities': [entity.to_dict() for entity in self.primary_entities],
            'secondary_entities': [entity.to_dict() for entity in self.secondary_entities],
            'primary_topics': [topic.to_dict() for topic in self.primary_topics],
            'secondary_topics': [topic.to_dict() for topic in self.secondary_topics],
            'source_document': self.source_document.to_dict() if self.source_document else None,
            'related_documents': [doc.to_dict() for doc in self.related_documents],
            'tested_relationships': [rel.to_dict() for rel in self.tested_relationships],
            'extraction_method': self.extraction_method,
            'extraction_confidence': self.extraction_confidence,
            'content_chunks': self.content_chunks,
            'difficulty_indicators': self.difficulty_indicators,
            'learning_objectives': self.learning_objectives
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KGMapping':
        """Create from dictionary"""
        data = data.copy()

        # Parse datetimes
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['updated_at'] = datetime.fromisoformat(data['updated_at'])

        # Parse entities
        data['primary_entities'] = [KGEntity.from_dict(e) for e in data['primary_entities']]
        data['secondary_entities'] = [KGEntity.from_dict(e) for e in data['secondary_entities']]

        # Parse topics
        data['primary_topics'] = [KGTopic.from_dict(t) for t in data['primary_topics']]
        data['secondary_topics'] = [KGTopic.from_dict(t) for t in data['secondary_topics']]

        # Parse documents
        if data['source_document']:
            data['source_document'] = KGDocument.from_dict(data['source_document'])
        data['related_documents'] = [KGDocument.from_dict(d) for d in data['related_documents']]

        # Parse relationships
        data['tested_relationships'] = [KGRelationship.from_dict(r) for r in data['tested_relationships']]

        return cls(**data)


# Utility functions for creating common KG mappings

def create_simple_entity_mapping(entity_name: str, entity_type: str = "concept") -> KGMapping:
    """Create a simple mapping with one entity"""
    entity = KGEntity(
        entity_id=str(uuid.uuid4()),
        name=entity_name,
        entity_type=entity_type
    )

    return KGMapping.create_new(primary_entities=[entity])


def create_topic_mapping(topic_name: str, category: str = "general") -> KGMapping:
    """Create a simple mapping with one topic"""
    topic = KGTopic(
        topic_id=str(uuid.uuid4()),
        name=topic_name,
        category=category
    )

    return KGMapping.create_new(primary_topics=[topic])


def create_document_mapping(document_title: str, document_type: str = "text") -> KGMapping:
    """Create a mapping linked to a document"""
    document = KGDocument(
        document_id=str(uuid.uuid4()),
        title=document_title,
        document_type=document_type,
        processed_date=datetime.now()
    )

    return KGMapping.create_new(source_document=document)