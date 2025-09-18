from typing import Literal, Union, List
from pydantic import BaseModel, Field, field_validator

# Define valid entity types
ENTITY_TYPES = Literal["Named Entity", "Concept/Idea"]

# Define valid categories for each entity type
NAMED_ENTITY_CATEGORIES = Literal[
    "people", "organizations", "locations", "products", 
    "events", "other"
]

CONCEPT_IDEA_CATEGORIES = Literal[
    "concepts", "ideas", "theories", "abstract notions", 
    "philosophical concepts", "scientific concepts"
]

class Entity(BaseModel):
    """An entity extracted from text"""
    name: str = Field(description="Name of the entity")
    type: ENTITY_TYPES = Field(description="Type of entity (Named Entity or Concept/Idea)")
    category: Union[NAMED_ENTITY_CATEGORIES, CONCEPT_IDEA_CATEGORIES] = Field(
        description="Specific category the entity belongs to"
    )

    @field_validator('category')
    def validate_category_for_type(cls, v, info):
        """Validate that the category is valid for the given entity type"""
        values = info.data
        if 'type' not in values:
            raise ValueError('Entity type must be provided before category')
            
        entity_type = values['type']
        
        if entity_type == "Named Entity":
            if v not in ["people", "organizations", "locations", "products", 
                         "events", "other"]:
                raise ValueError(f"Invalid category '{v}' for Named Entity type")
        elif entity_type == "Concept/Idea":
            if v not in ["concepts", "ideas", "theories", "abstract notions", 
                         "philosophical concepts", "scientific concepts"]:
                raise ValueError(f"Invalid category '{v}' for Concept/Idea type")
        
        return v


class Relationship(BaseModel):
    """A relationship between two entities"""
    source: str = Field(description="Name of the source entity,these must exist in the list of entities")
    target: str = Field(description="Name of the target entity,these must exist in the list of entities")
    relation: str = Field(description="The relationship between the source and target entity")
    context: str = Field(description="Text snippet where this relationship was found")


class ChunkKnowledgeGraphExtraction(BaseModel):
    """Knowledge graph components extracted from text"""
    entities: List[Entity] = Field(description="List of entities found in the text", default_factory=list)
    relationships: List[Relationship] = Field(description="List of relationships between entities", default_factory=list)


