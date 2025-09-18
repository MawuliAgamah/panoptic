from langchain_core.prompts import ChatPromptTemplate
from langchain_core import prompts, output_parsers

TOPICS_EXTRACTION_PROMPT = prompts.ChatPromptTemplate.from_messages([
    ("system", """Analyze this text chunk from a larger document and identify the 3 most significant topics.
     There must be 3 topics.
    
    A good topic should:
    - Represent a major theme or subject matter discussed
    - Be broad enough to encompass multiple related points
    - Be specific enough to distinguish from other topics
    - Be expressed in 1-3 words when possible
    
    
    {format_instructions}"""),
    ("human", "{chunk}")
])

KEYWORD_EXTRACTION_PROMPT = prompts.ChatPromptTemplate.from_messages([
    ("system", """Analyze this text chunk from a larger document and identify the 2-3 most important keywords.
     There must be 3 keywords.
    A good keyword should:
    - Represent a specific concept, term, or entity mentioned
    - Be consistently prominent or crucial to understanding the text
    - Typically be a noun, proper noun, or technical term
    - Be expressed in 1-2 words when possible
    
    Format each keyword with a '#' prefix (e.g., #artificial_intelligence).
    For multi-word keywords, use underscores between words.
    
    {format_instructions}"""),
    ("human", "{chunk}")
])


ONTOLOGY_EXTRACTION_PROMPT = prompts.ChatPromptTemplate.from_messages([
    ("system", """
     You are a knowledge graph extraction system designed to process informal, markdown-formatted notes. 
     These notes reflect personal thinking, so expect incomplete thoughts, implicit ideas, and unstructured logic.
     This is important as you may be required to infer relationships between entities that are not explicitly stated in the text.
     Your task is to analyze text and identify entities and relationships to build a knowledge graph.


The rules for entities you must extract are as follows:
They can either be named entities or concepts/ideas.
They must fit into one of the categories below.
     
## Named Entities:
- people: Individuals mentioned by name
- organizations: Companies, institutions, groups, etc.
- locations: Physical places and geographic locations
- products: Named goods and services
- events: Specific occurrences with dates/times
- other: Other named entities not fitting above categories

## Concepts/Ideas:
- concepts: General notions or mental constructs
- ideas: Thoughts or suggestions
- theories: Systems of ideas explaining something
- abstract notions: Non-concrete concepts
- philosophical concepts: Ideas related to philosophy
- scientific concepts: Ideas related to science

# INSTRUCTIONS:
1. Carefully analyze the text and identify at max 3 entities which capture the spirit of the text.
2. Focus on salient entities that reflect the core of the chunk
2. For each entity, determine its type (Named Entity or Concept/Idea) and appropriate category.
3. Look for implicit relationships between these entities. Do not just copy verbatim the relationships from the text.
4. Extract relationships in the format: Entity A → Relationship → Entity B

# IMPORTANT GUIDELINES:
- Even abstract texts contain entities (concepts, ideas, theories)
- Texts about principles or thoughts should produce concept/idea entities
- Include relationships that are implicit in the text
- If there are multiple relationships between the same entities, include them all
- EVERY entity mentioned must be included
- Write concise but specific relationship descriptions


# FORMAT REQUIREMENTS:
{format_instructions}

Analyze the following text chunk:
"""),
    ("human", "{chunk}")
])

