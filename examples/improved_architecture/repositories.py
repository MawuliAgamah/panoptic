"""Improved repository pattern with better abstraction and no storage-specific leakage"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Protocol, TypeVar
from dataclasses import dataclass
from datetime import datetime
import logging

# Domain models (these would be your actual models)
from ..models.Card import Card
from ..models.flashcard import Deck, FlashcardReview


T = TypeVar('T')


class Entity(Protocol):
    """Protocol for entities that can be stored"""
    id: str


@dataclass
class QueryFilter:
    """Generic query filter for repositories"""
    field: str
    operator: str  # eq, ne, gt, lt, gte, lte, in, like
    value: Any


@dataclass
class QueryOptions:
    """Query options for repositories"""
    filters: List[QueryFilter] = None
    order_by: Optional[str] = None
    order_desc: bool = False
    limit: Optional[int] = None
    offset: int = 0

    def __post_init__(self):
        if self.filters is None:
            self.filters = []


class Repository(ABC, Protocol[T]):
    """
    Base repository interface - completely storage-agnostic
    No implementation details should leak into this interface
    """

    @abstractmethod
    def save(self, entity: T) -> T:
        """Save or update an entity"""
        pass

    @abstractmethod
    def find_by_id(self, entity_id: str) -> Optional[T]:
        """Find entity by ID"""
        pass

    @abstractmethod
    def find_all(self, options: Optional[QueryOptions] = None) -> List[T]:
        """Find all entities matching criteria"""
        pass

    @abstractmethod
    def delete(self, entity_id: str) -> bool:
        """Delete entity by ID"""
        pass

    @abstractmethod
    def exists(self, entity_id: str) -> bool:
        """Check if entity exists"""
        pass

    @abstractmethod
    def count(self, options: Optional[QueryOptions] = None) -> int:
        """Count entities matching criteria"""
        pass


class CardRepository(Repository[Card]):
    """Card-specific repository interface"""

    @abstractmethod
    def find_by_user_id(self, user_id: str) -> List[Card]:
        """Find all cards for a user"""
        pass

    @abstractmethod
    def find_due_cards(self, user_id: str, limit: Optional[int] = None) -> List[Card]:
        """Find cards due for review - optimized query"""
        pass

    @abstractmethod
    def find_by_domains(self, user_id: str, domains: List[str]) -> List[Card]:
        """Find cards by domains"""
        pass

    @abstractmethod
    def find_reviewed_today(self, user_id: str) -> List[Card]:
        """Find cards reviewed today"""
        pass


class DeckRepository(Repository[Deck]):
    """Deck-specific repository interface"""

    @abstractmethod
    def find_by_user_id(self, user_id: str) -> List[Deck]:
        """Find all decks for a user"""
        pass

    @abstractmethod
    def find_by_name(self, user_id: str, name: str) -> Optional[Deck]:
        """Find deck by name for a user"""
        pass


class ReviewRepository(Repository[FlashcardReview]):
    """Review-specific repository interface"""

    @abstractmethod
    def find_by_card_id(self, card_id: str) -> List[FlashcardReview]:
        """Find all reviews for a card"""
        pass

    @abstractmethod
    def find_by_user_id(self, user_id: str, limit: Optional[int] = None) -> List[FlashcardReview]:
        """Find reviews by user"""
        pass

    @abstractmethod
    def find_recent_reviews(self, user_id: str, days: int = 7) -> List[FlashcardReview]:
        """Find recent reviews"""
        pass


class StorageAdapter(ABC):
    """
    Abstract storage adapter - handles the actual storage operations
    This separates storage concerns from repository logic
    """

    @abstractmethod
    def save_entity(self, entity_type: str, entity_id: str, data: Dict[str, Any]) -> None:
        """Save entity data"""
        pass

    @abstractmethod
    def load_entity(self, entity_type: str, entity_id: str) -> Optional[Dict[str, Any]]:
        """Load entity data"""
        pass

    @abstractmethod
    def load_entities(self, entity_type: str, options: Optional[QueryOptions] = None) -> List[Dict[str, Any]]:
        """Load multiple entities"""
        pass

    @abstractmethod
    def delete_entity(self, entity_type: str, entity_id: str) -> bool:
        """Delete entity"""
        pass

    @abstractmethod
    def exists_entity(self, entity_type: str, entity_id: str) -> bool:
        """Check if entity exists"""
        pass

    @abstractmethod
    def count_entities(self, entity_type: str, options: Optional[QueryOptions] = None) -> int:
        """Count entities"""
        pass


class EntityMapper(ABC, Protocol[T]):
    """Maps between domain objects and storage format"""

    @abstractmethod
    def to_dict(self, entity: T) -> Dict[str, Any]:
        """Convert entity to storage format"""
        pass

    @abstractmethod
    def from_dict(self, data: Dict[str, Any]) -> T:
        """Convert from storage format to entity"""
        pass

    @abstractmethod
    def get_entity_type(self) -> str:
        """Get entity type identifier"""
        pass


# Base repository implementation using adapter pattern
class BaseRepository(Repository[T]):
    """
    Base repository implementation using storage adapter
    Completely storage-agnostic - all storage logic is in the adapter
    """

    def __init__(self, storage_adapter: StorageAdapter, mapper: EntityMapper[T]):
        self.storage = storage_adapter
        self.mapper = mapper
        self.logger = logging.getLogger(f"repository.{mapper.get_entity_type()}")

    def save(self, entity: T) -> T:
        """Save or update an entity"""
        try:
            data = self.mapper.to_dict(entity)
            entity_type = self.mapper.get_entity_type()
            self.storage.save_entity(entity_type, entity.id, data)
            self.logger.debug(f"Saved {entity_type} with ID: {entity.id}")
            return entity
        except Exception as e:
            self.logger.error(f"Failed to save {entity.id}: {e}")
            raise

    def find_by_id(self, entity_id: str) -> Optional[T]:
        """Find entity by ID"""
        try:
            entity_type = self.mapper.get_entity_type()
            data = self.storage.load_entity(entity_type, entity_id)

            if data is None:
                return None

            return self.mapper.from_dict(data)
        except Exception as e:
            self.logger.error(f"Failed to find {entity_id}: {e}")
            raise

    def find_all(self, options: Optional[QueryOptions] = None) -> List[T]:
        """Find all entities matching criteria"""
        try:
            entity_type = self.mapper.get_entity_type()
            data_list = self.storage.load_entities(entity_type, options)
            return [self.mapper.from_dict(data) for data in data_list]
        except Exception as e:
            self.logger.error(f"Failed to find entities: {e}")
            raise

    def delete(self, entity_id: str) -> bool:
        """Delete entity by ID"""
        try:
            entity_type = self.mapper.get_entity_type()
            result = self.storage.delete_entity(entity_type, entity_id)
            if result:
                self.logger.debug(f"Deleted {entity_type} with ID: {entity_id}")
            return result
        except Exception as e:
            self.logger.error(f"Failed to delete {entity_id}: {e}")
            raise

    def exists(self, entity_id: str) -> bool:
        """Check if entity exists"""
        try:
            entity_type = self.mapper.get_entity_type()
            return self.storage.exists_entity(entity_type, entity_id)
        except Exception as e:
            self.logger.error(f"Failed to check existence of {entity_id}: {e}")
            raise

    def count(self, options: Optional[QueryOptions] = None) -> int:
        """Count entities matching criteria"""
        try:
            entity_type = self.mapper.get_entity_type()
            return self.storage.count_entities(entity_type, options)
        except Exception as e:
            self.logger.error(f"Failed to count entities: {e}")
            raise


# Concrete implementations for specific entities
class CardRepositoryImpl(BaseRepository[Card], CardRepository):
    """Card repository implementation"""

    def __init__(self, storage_adapter: StorageAdapter, mapper: EntityMapper[Card]):
        super().__init__(storage_adapter, mapper)

    def find_by_user_id(self, user_id: str) -> List[Card]:
        """Find all cards for a user"""
        options = QueryOptions(filters=[
            QueryFilter("user_id", "eq", user_id)
        ])
        return self.find_all(options)

    def find_due_cards(self, user_id: str, limit: Optional[int] = None) -> List[Card]:
        """Find cards due for review"""
        now = datetime.now().isoformat()
        options = QueryOptions(
            filters=[
                QueryFilter("user_id", "eq", user_id),
                QueryFilter("scheduling.next_review_date", "lte", now)
            ],
            order_by="scheduling.next_review_date",
            limit=limit
        )
        return self.find_all(options)

    def find_by_domains(self, user_id: str, domains: List[str]) -> List[Card]:
        """Find cards by domains"""
        options = QueryOptions(filters=[
            QueryFilter("user_id", "eq", user_id),
            QueryFilter("Domains", "in", domains)
        ])
        return self.find_all(options)

    def find_reviewed_today(self, user_id: str) -> List[Card]:
        """Find cards reviewed today"""
        today = datetime.now().date().isoformat()
        options = QueryOptions(filters=[
            QueryFilter("user_id", "eq", user_id),
            QueryFilter("reviewed_at", "gte", today)
        ])
        return self.find_all(options)


class DeckRepositoryImpl(BaseRepository[Deck], DeckRepository):
    """Deck repository implementation"""

    def __init__(self, storage_adapter: StorageAdapter, mapper: EntityMapper[Deck]):
        super().__init__(storage_adapter, mapper)

    def find_by_user_id(self, user_id: str) -> List[Deck]:
        """Find all decks for a user"""
        options = QueryOptions(filters=[
            QueryFilter("user_id", "eq", user_id)
        ])
        return self.find_all(options)

    def find_by_name(self, user_id: str, name: str) -> Optional[Deck]:
        """Find deck by name for a user"""
        options = QueryOptions(filters=[
            QueryFilter("user_id", "eq", user_id),
            QueryFilter("name", "eq", name)
        ], limit=1)
        results = self.find_all(options)
        return results[0] if results else None


class ReviewRepositoryImpl(BaseRepository[FlashcardReview], ReviewRepository):
    """Review repository implementation"""

    def __init__(self, storage_adapter: StorageAdapter, mapper: EntityMapper[FlashcardReview]):
        super().__init__(storage_adapter, mapper)

    def find_by_card_id(self, card_id: str) -> List[FlashcardReview]:
        """Find all reviews for a card"""
        options = QueryOptions(
            filters=[QueryFilter("card_id", "eq", card_id)],
            order_by="reviewed_at",
            order_desc=True
        )
        return self.find_all(options)

    def find_by_user_id(self, user_id: str, limit: Optional[int] = None) -> List[FlashcardReview]:
        """Find reviews by user"""
        options = QueryOptions(
            filters=[QueryFilter("user_id", "eq", user_id)],
            order_by="reviewed_at",
            order_desc=True,
            limit=limit
        )
        return self.find_all(options)

    def find_recent_reviews(self, user_id: str, days: int = 7) -> List[FlashcardReview]:
        """Find recent reviews"""
        cutoff_date = (datetime.now().date() - datetime.timedelta(days=days)).isoformat()
        options = QueryOptions(filters=[
            QueryFilter("user_id", "eq", user_id),
            QueryFilter("reviewed_at", "gte", cutoff_date)
        ])
        return self.find_all(options)


# Entity mappers
class CardMapper(EntityMapper[Card]):
    """Maps Card entities to/from storage"""

    def to_dict(self, entity: Card) -> Dict[str, Any]:
        """Convert Card to storage format"""
        return entity.to_dict()  # Assuming Card has this method

    def from_dict(self, data: Dict[str, Any]) -> Card:
        """Convert from storage format to Card"""
        return Card.from_dict(data)  # Assuming Card has this method

    def get_entity_type(self) -> str:
        """Get entity type identifier"""
        return "card"


class DeckMapper(EntityMapper[Deck]):
    """Maps Deck entities to/from storage"""

    def to_dict(self, entity: Deck) -> Dict[str, Any]:
        return entity.to_dict()

    def from_dict(self, data: Dict[str, Any]) -> Deck:
        return Deck.from_dict(data)

    def get_entity_type(self) -> str:
        return "deck"


class ReviewMapper(EntityMapper[FlashcardReview]):
    """Maps FlashcardReview entities to/from storage"""

    def to_dict(self, entity: FlashcardReview) -> Dict[str, Any]:
        return entity.to_dict()

    def from_dict(self, data: Dict[str, Any]) -> FlashcardReview:
        return FlashcardReview.from_dict(data)

    def get_entity_type(self) -> str:
        return "review"


# Repository factory for dependency injection
class RepositoryFactory:
    """Factory for creating repositories with proper dependencies"""

    def __init__(self, storage_adapter: StorageAdapter):
        self.storage_adapter = storage_adapter

    def create_card_repository(self) -> CardRepository:
        """Create card repository"""
        mapper = CardMapper()
        return CardRepositoryImpl(self.storage_adapter, mapper)

    def create_deck_repository(self) -> DeckRepository:
        """Create deck repository"""
        mapper = DeckMapper()
        return DeckRepositoryImpl(self.storage_adapter, mapper)

    def create_review_repository(self) -> ReviewRepository:
        """Create review repository"""
        mapper = ReviewMapper()
        return ReviewRepositoryImpl(self.storage_adapter, mapper)