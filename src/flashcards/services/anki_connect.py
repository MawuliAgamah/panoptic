"""AnkiConnect client for interacting with Anki desktop application"""

import json
import urllib.request
import urllib.parse
from typing import Dict, List, Optional, Any
import logging


class AnkiConnectClient:
    """Client for communicating with AnkiConnect add-on"""

    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.url = f"http://{host}:{port}"
        self.logger = logging.getLogger(__name__)

    def _invoke(self, action: str, params: Optional[Dict] = None, version: int = 6) -> Any:
        """Send request to AnkiConnect"""
        request_data = {
            "action": action,
            "version": version
        }
        if params:
            request_data["params"] = params

        try:
            request_json = json.dumps(request_data).encode('utf-8')
            request = urllib.request.Request(self.url, request_json)
            request.add_header('Content-Type', 'application/json')

            with urllib.request.urlopen(request) as response:
                response_data = json.loads(response.read().decode('utf-8'))

            if len(response_data) != 2:
                raise Exception('Response has unexpected number of fields')
            if 'error' not in response_data:
                raise Exception('Response is missing required error field')
            if 'result' not in response_data:
                raise Exception('Response is missing required result field')
            if response_data['error'] is not None:
                raise Exception(response_data['error'])

            return response_data['result']

        except Exception as e:
            self.logger.error(f"AnkiConnect request failed: {e}")
            raise

    def test_connection(self) -> bool:
        """Test if AnkiConnect is available"""
        try:
            version = self._invoke("version")
            self.logger.info(f"Connected to AnkiConnect version {version}")
            return True
        except Exception as e:
            self.logger.error(f"AnkiConnect not available: {e}")
            return False

    def get_deck_names(self) -> List[str]:
        """Get list of all deck names"""
        return self._invoke("deckNames")

    def create_deck(self, deck_name: str) -> bool:
        """Create a new deck"""
        try:
            self._invoke("createDeck", {"deck": deck_name})
            self.logger.info(f"Created deck: {deck_name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create deck {deck_name}: {e}")
            return False

    def add_note(self, deck_name: str, front: str, back: str, note_type: str = "Basic") -> Optional[int]:
        """Add a flashcard note to Anki"""
        note = {
            "deckName": deck_name,
            "modelName": note_type,
            "fields": {
                "Front": front,
                "Back": back
            },
            "options": {
                "allowDuplicate": False,
                "duplicateScope": "deck"
            }
        }

        try:
            note_id = self._invoke("addNote", {"note": note})
            if note_id:
                self.logger.info(f"Added note to {deck_name}: {front[:50]}...")
                return note_id
            else:
                self.logger.warning(f"Note may be duplicate: {front[:50]}...")
                return None
        except Exception as e:
            self.logger.error(f"Failed to add note: {e}")
            return None

    def add_notes_batch(self, notes: List[Dict]) -> List[Optional[int]]:
        """Add multiple notes at once"""
        try:
            note_ids = self._invoke("addNotes", {"notes": notes})
            successful = sum(1 for note_id in note_ids if note_id is not None)
            self.logger.info(f"Added {successful}/{len(notes)} notes successfully")
            return note_ids
        except Exception as e:
            self.logger.error(f"Batch add failed: {e}")
            return [None] * len(notes)

    def get_due_cards_count(self, deck_name: str) -> int:
        """Get number of cards due for review in deck"""
        try:
            deck_stats = self._invoke("getDeckStats", {"decks": [deck_name]})
            if deck_name in deck_stats:
                return deck_stats[deck_name].get("due_count", 0)
            return 0
        except Exception as e:
            self.logger.error(f"Failed to get due cards for {deck_name}: {e}")
            return 0

    def find_cards(self, query: str) -> List[int]:
        """Find cards matching a query"""
        try:
            return self._invoke("findCards", {"query": query})
        except Exception as e:
            self.logger.error(f"Card search failed: {e}")
            return []

    def get_card_info(self, card_ids: List[int]) -> List[Dict]:
        """Get detailed info for specific cards"""
        try:
            return self._invoke("cardsInfo", {"cards": card_ids})
        except Exception as e:
            self.logger.error(f"Failed to get card info: {e}")
            return []

    def sync(self) -> bool:
        """Trigger Anki sync"""
        try:
            self._invoke("sync")
            self.logger.info("Anki sync triggered")
            return True
        except Exception as e:
            self.logger.error(f"Sync failed: {e}")
            return False


def create_anki_client() -> AnkiConnectClient:
    """Factory function to create AnkiConnect client"""
    client = AnkiConnectClient()

    # Test connection on creation
    if not client.test_connection():
        logging.warning("AnkiConnect not available. Make sure Anki is running with AnkiConnect add-on installed.")

    return client


# Example usage and testing
if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)

    # Test the client
    client = create_anki_client()

    if client.test_connection():
        logging.info("Testing basic functionality...")

        # Get existing decks
        decks = client.get_deck_names()
        logging.info(f"Existing decks: {decks}")

        # Create test deck (if it doesn't exist)
        test_deck = "Telegram Bot Test"
        if test_deck not in decks:
            client.create_deck(test_deck)

        # Add a test card
        note_id = client.add_note(
            deck_name=test_deck,
            front="What is the capital of France?",
            back="Paris"
        )

        if note_id:
            logging.info(f"Test complete! Added note ID: {note_id}")
        else:
            logging.warning("Note may already exist")
    else:
        logging.error("Please install AnkiConnect add-on and restart Anki")