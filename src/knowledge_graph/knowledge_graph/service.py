from src.knowledgeAgent.knowledge_graph.agent.autogen.autogen_agent import extract_ontology

class KnowledgeGraphService:
    """Service for knowledge graph operations"""
    
    def __init__(self, db_client, llm_service):
        self.llm_service = llm_service
        self.db_client = db_client
        self.agentic_ontology_extraction_agent = extract_ontology

    def extract_ontology(self, document_id):
        """Extract ontology from document"""
        document = self.db_client.get_document(document_id)
        print(f"\n{'='*80}")
        print(f"🔍 EXTRACTING ONTOLOGY FOR DOCUMENT: {document.title}")
        print(f"{'='*80}\n")
        
        chunks = document.textChunks
        print(f"📚 Found {len(chunks)} chunks to process\n")
        
        all_ontologies = []
        
        for i, chunk in enumerate(chunks):
            print(f"\n{'-'*80}")
            print(f"📝 CHUNK #{i+1}/{len(chunks)} (ID: {chunk.id})")
            print(f"{'-'*80}")
            
            # Print chunk content preview
            print(f"\nCONTENT:\n{chunk.content}\n")
            
            # Extract and print ontology
            print(f"ONTOLOGY EXTRACTION:")
            try:
                ontology = self.llm_service.extract_ontology(chunk.content)
                
                # Get entities and relationships, handling different return types
                entities = []
                relationships = []
                
                # Handle both dict and object returns from LLM service
                if isinstance(ontology, dict):
                    entities = ontology.get('entities', [])
                    relationships = ontology.get('relationships', [])
                else:
                    # Pydantic model return
                    entities = ontology.entities if hasattr(ontology, 'entities') else []
                    relationships = ontology.relationships if hasattr(ontology, 'relationships') else []
                
                # Pretty print the ontology
                print(f"\n📊 ENTITIES ({len(entities)}):")
                if entities:
                    for entity in entities:
                        if isinstance(entity, dict):
                            print(f"  • {entity['name']} ({entity['type']}/{entity['category']})")
                        else:
                            print(f"  • {entity.name} ({entity.type}/{entity.category})")
                else:
                    print("  No entities found")
                
                print(f"\n🔗 RELATIONSHIPS ({len(relationships)}):")
                if relationships:
                    for rel in relationships:
                        if isinstance(rel, dict):
                            print(f"  • {rel['source']} → {rel['relation']} → {rel['target']}")
                            print(f"    Context: \"{rel['context']}\"")
                        else:
                            print(f"  • {rel.source} → {rel.relation} → {rel.target}")
                            print(f"    Context: \"{rel.context}\"")
                else:
                    print("  No relationships found")
                
                # Save to database
                chunk_id = int(chunk.id.split('_')[-1]) if '_' in chunk.id else None
                saved = self.db_client.save_entities_and_relationships(document_id, chunk_id, ontology)
                if saved:
                    print("\n💾 Saved ontology to database")
                else:
                    print("\n❌ Failed to save ontology to database")
                          
                all_ontologies.append(ontology)
                
            except Exception as e:
                print(f"\n❌ ERROR: Failed to extract ontology: {str(e)}")
                print("  The LLM may have had difficulty parsing this text.")
            
            print()
            
        print(f"\n{'='*80}")
        print(f"✅ ONTOLOGY EXTRACTION COMPLETE: {len(chunks)} chunks processed")
        print(f"{'='*80}\n")
        
        return all_ontologies
        
    def get_document_ontology(self, document_id):
        """Get all entities and relationships for a document"""
        try:
            ontology = self.db_client.get_document_ontology(document_id)
            
            # Print summary
            entities = ontology.get('entities', [])
            relationships = ontology.get('relationships', [])
            
            print(f"\n{'='*80}")
            print(f"📊 DOCUMENT ONTOLOGY: {document_id}")
            print(f"{'='*80}\n")
            
            print(f"Found {len(entities)} entities and {len(relationships)} relationships\n")
            
            # Print entities grouped by type/category
            entity_groups = {}
            for entity in entities:
                key = f"{entity['type']}/{entity['category']}"
                if key not in entity_groups:
                    entity_groups[key] = []
                entity_groups[key].append(entity['name'])
            
            print("ENTITIES BY TYPE:")
            for group_key, names in entity_groups.items():
                print(f"  • {group_key}: {', '.join(names)}")
            
            # Print relationships
            if relationships:
                print("\nRELATIONSHIPS:")
                for rel in relationships:
                    print(f"  • {rel['source_name']} → {rel['relation']} → {rel['target_name']}")
            
            return ontology
            
        except Exception as e:
            print(f"Error getting document ontology: {str(e)}")
            return {'entities': [], 'relationships': []}

    def agentic_ontology_extraction(self, document_id):
        from src.knowledgeAgent.knowledge_graph.agent.autogen.autogen_agent import extract_ontology
        """Agentic ontology extraction"""
        document = self.db_client.get_document(document_id)
        print(f"\n{'='*80}")
        print(f"🔍 EXTRACTING ONTOLOGY FOR DOCUMENT using agentic approach: {document.title}")
        print(f"{'='*80}\n")

        for chunk in document.textChunks:
            extract_ontology(document=chunk.content)


        
    def save_document_ontology(self, document_id, ontology):
        """Save ontology to document"""
        self.db_client.save_document_ontology(document_id, ontology)

    
