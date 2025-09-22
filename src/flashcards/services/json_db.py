"""JSON-based database for flashcards"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import shutil
from threading import Lock


class JSONFlashcardDB:
    """JSON-based database for flashcard storage"""

    def __init__(self, db_path: str = "database/flashcards"):
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)

        # File paths
        self.decks_file = self.db_path / "decks.json"
        self.cards_file = self.db_path / "cards.json"
        self.reviews_file = self.db_path / "reviews.json"
        self.users_file = self.db_path / "users.json"

        # Thread safety
        self._lock = Lock()

        # Logger
        self.logger = logging.getLogger(__name__)

        # Initialize files
        self._init_db_files()

    def _init_db_files(self):
        """Initialize database files if they don't exist"""
        default_structures = {
            self.decks_file: {},
            self.cards_file: {},
            self.reviews_file: {},
            self.users_file: {}
        }

        for file_path, default_data in default_structures.items():
            if not file_path.exists():
                self._write_json_file(file_path, default_data)
                self.logger.info(f"Initialized {file_path.name}")

    def _read_json_file(self, file_path: Path) -> Dict[str, Any]:
        """Safely read JSON file"""
        try:
            with file_path.open('r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.logger.error(f"Error reading {file_path}: {e}")
            return {}

    def _write_json_file(self, file_path: Path, data: Dict[str, Any]):
        """Safely write JSON file with backup"""
        backup_path = file_path.with_suffix(f"{file_path.suffix}.bak")

        try:
            # Create backup if file exists
            if file_path.exists():
                shutil.copy2(file_path, backup_path)

            # Write new data
            with file_path.open('w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)

            # Remove backup on success
            if backup_path.exists():
                backup_path.unlink()

        except Exception as e:
            self.logger.error(f"Error writing {file_path}: {e}")

            # Restore backup if write failed
            if backup_path.exists() and not file_path.exists():
                shutil.copy2(backup_path, file_path)
                backup_path.unlink()
            raise

    # === DECK OPERATIONS ===

    def create_deck(self, deck_data: Dict[str, Any]) -> bool:
        """Create a new deck"""
        with self._lock:
            decks = self._read_json_file(self.decks_file)
            # Handle both old 'deck_id' and new 'id' field names
            deck_id = deck_data.get('id') or deck_data.get('deck_id')

            if deck_id in decks:
                self.logger.warning(f"Deck {deck_id} already exists")
                return False

            decks[deck_id] = deck_data
            self._write_json_file(self.decks_file, decks)
            self.logger.info(f"Created deck: {deck_data.get('name', deck_id)}")
            return True

    def get_deck(self, deck_id: str) -> Optional[Dict[str, Any]]:
        """Get deck by ID"""
        decks = self._read_json_file(self.decks_file)
        return decks.get(deck_id)

    def update_deck(self, deck_id: str, deck_data: Dict[str, Any]) -> bool:
        """Update existing deck"""
        with self._lock:
            decks = self._read_json_file(self.decks_file)

            if deck_id not in decks:
                self.logger.error(f"Deck {deck_id} not found for update")
                return False

            decks[deck_id] = deck_data
            self._write_json_file(self.decks_file, decks)
            self.logger.info(f"Updated deck: {deck_id}")
            return True

    def delete_deck(self, deck_id: str) -> bool:
        """Delete deck and all its cards"""
        with self._lock:
            # Remove deck
            decks = self._read_json_file(self.decks_file)
            if deck_id not in decks:
                return False

            del decks[deck_id]
            self._write_json_file(self.decks_file, decks)

            # Remove all cards in deck
            cards = self._read_json_file(self.cards_file)
            cards_to_remove = [card_id for card_id, card_data in cards.items()
                             if card_data.get('deck_id') == deck_id]

            for card_id in cards_to_remove:
                del cards[card_id]

            self._write_json_file(self.cards_file, cards)
            self.logger.info(f"Deleted deck {deck_id} and {len(cards_to_remove)} cards")
            return True

    def get_user_decks(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all decks for a user"""
        decks = self._read_json_file(self.decks_file)
        return [deck_data for deck_data in decks.values()
                if deck_data.get('user_id') == user_id]

    # === CARD OPERATIONS ===

    def create_card(self, card_data: Dict[str, Any]) -> bool:
        """Create a new card"""
        with self._lock:
            cards = self._read_json_file(self.cards_file)
            # Handle both old 'card_id' and new 'id' field names
            card_id = card_data.get('id') or card_data.get('card_id')

            if card_id in cards:
                self.logger.warning(f"Card {card_id} already exists")
                return False

            cards[card_id] = card_data
            self._write_json_file(self.cards_file, cards)
            self.logger.info(f"Created card: {card_id}")
            return True

    def get_card(self, card_id: str) -> Optional[Dict[str, Any]]:
        """Get card by ID"""
        cards = self._read_json_file(self.cards_file)
        return cards.get(card_id)

    def update_card(self, card_id: str, card_data: Dict[str, Any]) -> bool:
        """Update existing card"""
        with self._lock:
            cards = self._read_json_file(self.cards_file)

            if card_id not in cards:
                self.logger.error(f"Card {card_id} not found for update")
                return False

            cards[card_id] = card_data
            self._write_json_file(self.cards_file, cards)
            return True

    def delete_card(self, card_id: str) -> bool:
        """Delete card"""
        with self._lock:
            cards = self._read_json_file(self.cards_file)

            if card_id not in cards:
                return False

            del cards[card_id]
            self._write_json_file(self.cards_file, cards)
            self.logger.info(f"Deleted card: {card_id}")
            return True

    def get_deck_cards(self, deck_id: str) -> List[Dict[str, Any]]:
        """Get all cards in a deck"""
        cards = self._read_json_file(self.cards_file)
        return [card_data for card_data in cards.values()
                if card_data.get('deck_id') == deck_id]

    def get_user_cards(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all cards for a user"""
        cards = self._read_json_file(self.cards_file)
        return [card_data for card_data in cards.values()
                if card_data.get('user_id') == user_id]

    def get_due_cards(self, user_id: str, current_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get cards due for review"""
        current_time = current_time or datetime.now()
        cards = self._read_json_file(self.cards_file)

        due_cards = []
        for card_data in cards.values():
            if card_data.get('user_id') != user_id:
                continue

            scheduling = card_data.get('scheduling', {})
            next_review = scheduling.get('next_review_date')

            if next_review is None:
                # New card
                due_cards.append(card_data)
            else:
                # Parse date and check if due
                try:
                    next_review_dt = datetime.fromisoformat(next_review)
                    if current_time >= next_review_dt:
                        due_cards.append(card_data)
                except (ValueError, TypeError):
                    # Invalid date, treat as due
                    due_cards.append(card_data)

        return due_cards

    # === REVIEW OPERATIONS ===

    def save_review(self, review_data: Dict[str, Any]) -> bool:
        """Save a review record"""
        with self._lock:
            reviews = self._read_json_file(self.reviews_file)
            review_id = review_data['review_id']

            reviews[review_id] = review_data
            self._write_json_file(self.reviews_file, reviews)
            return True

    def get_card_reviews(self, card_id: str) -> List[Dict[str, Any]]:
        """Get all reviews for a card"""
        reviews = self._read_json_file(self.reviews_file)
        return [review_data for review_data in reviews.values()
                if review_data.get('card_id') == card_id]

    def get_user_reviews(self, user_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get reviews for a user"""
        reviews = self._read_json_file(self.reviews_file)
        user_reviews = [review_data for review_data in reviews.values()
                       if review_data.get('user_id') == user_id]

        # Sort by review date (newest first)
        user_reviews.sort(key=lambda x: x.get('reviewed_at', ''), reverse=True)

        if limit:
            return user_reviews[:limit]

        return user_reviews

    # === USER OPERATIONS ===

    def create_user(self, user_data: Dict[str, Any]) -> bool:
        """Create user profile"""
        with self._lock:
            users = self._read_json_file(self.users_file)
            user_id = user_data['user_id']

            users[user_id] = user_data
            self._write_json_file(self.users_file, users)
            self.logger.info(f"Created user: {user_id}")
            return True

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile"""
        users = self._read_json_file(self.users_file)
        return users.get(user_id)

    def update_user(self, user_id: str, user_data: Dict[str, Any]) -> bool:
        """Update user profile"""
        with self._lock:
            users = self._read_json_file(self.users_file)
            users[user_id] = user_data
            self._write_json_file(self.users_file, users)
            return True

    # === STATISTICS & UTILITIES ===

    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get user statistics"""
        cards = self.get_user_cards(user_id)
        reviews = self.get_user_reviews(user_id)
        due_cards = self.get_due_cards(user_id)

        total_cards = len(cards)
        total_reviews = len(reviews)
        cards_due = len(due_cards)

        # Algorithm breakdown
        algorithm_counts = {}
        for card in cards:
            algo = card.get('scheduling', {}).get('algorithm_name', 'unknown')
            algorithm_counts[algo] = algorithm_counts.get(algo, 0) + 1

        return {
            'user_id': user_id,
            'total_cards': total_cards,
            'total_reviews': total_reviews,
            'cards_due': cards_due,
            'cards_not_due': total_cards - cards_due,
            'algorithm_breakdown': algorithm_counts,
            'last_review': reviews[0].get('reviewed_at') if reviews else None
        }

    def backup_database(self, backup_path: str) -> bool:
        """Create full database backup"""
        try:
            backup_dir = Path(backup_path)
            backup_dir.mkdir(parents=True, exist_ok=True)

            # Copy all database files
            for db_file in [self.decks_file, self.cards_file, self.reviews_file, self.users_file]:
                if db_file.exists():
                    shutil.copy2(db_file, backup_dir / db_file.name)

            self.logger.info(f"Database backed up to {backup_path}")
            return True
        except Exception as e:
            self.logger.error(f"Backup failed: {e}")
            return False

    def get_database_info(self) -> Dict[str, Any]:
        """Get database information"""
        info = {
            'db_path': str(self.db_path),
            'files': {},
            'total_size_bytes': 0
        }

        for db_file in [self.decks_file, self.cards_file, self.reviews_file, self.users_file]:
            if db_file.exists():
                size = db_file.stat().st_size
                info['files'][db_file.name] = {
                    'size_bytes': size,
                    'last_modified': datetime.fromtimestamp(db_file.stat().st_mtime).isoformat()
                }
                info['total_size_bytes'] += size
            else:
                info['files'][db_file.name] = {'exists': False}

        return info