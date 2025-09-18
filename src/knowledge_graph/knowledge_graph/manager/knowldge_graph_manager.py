

class KnowledgeGraphManager:
    """Manager for knowledge graph operations"""
    def __init__(self, db_client, llm_service):
        self.db_client = db_client
        self.llm_service = llm_service
        
    
    def save_document_ontology(self, document_id, ontology):
        """Save ontology to document"""
        self.db_client.save_document_ontology(document_id, ontology)



