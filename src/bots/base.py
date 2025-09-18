from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import sys
import os

# Add the src directory to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
sys.path.insert(0, src_dir)

from services.knowledge_store import JsonKnowledgeStore


class MessageHandler:
    def __init__(self):
        self.knowledge_store = JsonKnowledgeStore()

    def process_message(self, message: str, user_id: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        print(f"User {user_id}: '{message}' (length: {len(message)})")

        # Strip any whitespace
        message = message.strip()
        print(f"After strip: '{message}'")

        if message.startswith('/search '):
            print("Processing search command")
            query = message[8:]  # Remove '/search '
            results = self.knowledge_store.search_facts(query)
            if results:
                return f"Found {len(results)} results:\n" + "\n".join([f"• {fact['content']}" for fact in results[:3]])
            else:
                return f"No results found for: {query}"

        elif message.startswith('/add '):
            print("Processing add command")
            fact_content = message[5:]  # Remove '/add '
            new_fact = self.knowledge_store.add_fact(fact_content)
            return f"Added fact #{new_fact['id']}: {fact_content}"

        elif message == '/help':
            print("Processing help command")
            return ("Available commands:\n"
                   "/search <query> - Search knowledge base\n"
                   "/add <fact> - Add a new fact\n"
                   "/help - Show this help")

        else:
            print("No command matched, returning echo")
            return f"You said: {message}\nType /help for available commands"


class BaseBot(ABC):
    def __init__(self):
        self.message_handler = MessageHandler()
        self.is_running = False

    @abstractmethod
    async def start(self) -> None:
        pass

    @abstractmethod
    async def stop(self) -> None:
        pass

    @abstractmethod
    async def send_message(self, message: str, recipient: str) -> bool:
        pass

    def handle_message(self, message: str, user_id: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        return self.message_handler.process_message(message, user_id, metadata)