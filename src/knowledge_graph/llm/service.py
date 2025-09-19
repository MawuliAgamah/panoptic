from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain.chains import LLMChain
import os
import logging

from knowledge_graph.llm.models.document_models import TopicModel, KeyWordModel
from knowledge_graph.llm.prompts.templates import TOPICS_EXTRACTION_PROMPT, KEYWORD_EXTRACTION_PROMPT
from knowledge_graph.llm.models.kg_extraction_models import ChunkKnowledgeGraphExtraction
from knowledge_graph.llm.prompts.templates import ONTOLOGY_EXTRACTION_PROMPT


class LLMService:
    """Service for LLM operations"""

    def __init__(self, config=None):
        self.logger = logging.getLogger("knowledgeAgent.llm")
        self.config = config or self._get_default_config()  
        self._initialize_service()  

    def _get_default_config(self):
        """Default configuration for the LLM service"""
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            self.logger.error("OPENAI_API_KEY environment variable is not set")
            raise ValueError("OPENAI_API_KEY environment variable is not set")  
        self.logger.info("Using default LLM configuration")
        return {"model": "gpt-3.5-turbo","temperature": 0.2,"api_key": api_key}

    def _initialize_service(self):
        """Initialize the LLM"""
        # Get API key from config or environment
        api_key = self.config.get("api_key")
        if not api_key:
            self.logger.error("OpenAI API key not found in config or environment variables")
            raise ValueError("OpenAI API key not found in config or environment variables")
            
        # Initialize LLM
        self.logger.info(f"Initializing LLM with model: {self.config.get('model')}")
        self.llm = ChatOpenAI(
            model=self.config.get("model", "gpt-3.5-turbo"),
            temperature=self.config.get("temperature", 0.2),
            api_key=api_key
        )
        self.logger.info("LLM service initialized successfully")

    def extract_topics(self, text):
        """Generate metadata for each chunk"""
        self.logger.info("Extracting topics from text")
        try:
            parser = JsonOutputParser(pydantic_object=TopicModel)
            chain = TOPICS_EXTRACTION_PROMPT | self.llm| parser
            output = chain.invoke(
                {
                    "chunk": text,
                    "format_instructions": parser.get_format_instructions()}
            )
            self.logger.debug(f"Extracted topics: {output}")
            return output
        except Exception as e:
            self.logger.error(f"Error extracting topics: {str(e)}")
            raise
        
    def extract_keywords(self, text):
        """Generate metadata for each chunk"""
        self.logger.info("Extracting keywords from text")
        try:
            parser = JsonOutputParser(pydantic_object=KeyWordModel)
            chain = KEYWORD_EXTRACTION_PROMPT | self.llm | parser
            output = chain.invoke(
                {
                    "chunk": text,
                    "format_instructions": parser.get_format_instructions()}
            )
            self.logger.debug(f"Extracted keywords: {output}")
            return output
        except Exception as e:
            self.logger.error(f"Error extracting keywords: {str(e)}")
            raise


    def extract_ontology(self, text):
        """Extract ontology from text"""
        self.logger.info("Extracting ontology from text")
        try:
            parser = JsonOutputParser(pydantic_object=ChunkKnowledgeGraphExtraction)
            chain = ONTOLOGY_EXTRACTION_PROMPT | self.llm | parser
            output = chain.invoke(
                {
                    "chunk": text,
                    "format_instructions": parser.get_format_instructions()
                }
            )
            self.logger.debug(f"Extracted ontology: {output}")
            return output   
        except Exception as e:
            self.logger.error(f"Error extracting ontology: {str(e)}")
            raise



# if __name__ == "__main__":
#     import os
#     from pathlib import Path
#     import dotenv
#     import logging
#     import sys
    
#     # Configure logging
#     logging.basicConfig(
#         level=logging.INFO,
#         format='\n%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(message)s',
#         datefmt='%Y-%m-%d %H:%M:%S',
#         stream=sys.stdout
#     )
    
#     # Find the project root directory (where .env file is located)
#     project_root = Path(__file__).resolve().parent.parent.parent.parent
#     dotenv.load_dotenv(project_root / ".env")    

#     # Get API key from environment
#     api_key = os.environ.get("OPENAI_API_KEY")
#     if not api_key:
#         raise ValueError("OPENAI_API_KEY environment variable is not set")

#     llm_service = LLMService()
#     print(llm_service.extract_topics("When walking in the park, I like to take a break and rest"))
#     print(llm_service.extract_keywords("it must be a good area like the forest, i like to rest"))