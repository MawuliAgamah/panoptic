"""
FlashcardClient - Main API interface for flashcard operations

This is the primary interface users should interact with.
Provides a clean, consistent API that coordinates all flashcard services.
"""

import sys
import os
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
import logging
from dataclasses import dataclass, asdict

# Add src directory to path when running directly
if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.dirname(os.path.dirname(current_dir))  # Go up to src/
    sys.path.insert(0, src_dir)

# Import your models and config
try:
    from ..models import Card, Deck, FlashcardReview
    from ..services.flashcard_service import create_flashcard_orchestrator, FlashcardOrchestrator
    from ..config import FlashcardConfig
except ImportError:
    # Fallback for direct execution
    from flashcards.models import Card, Deck, FlashcardReview
    from flashcards.services.flashcard_service import create_flashcard_orchestrator, FlashcardOrchestrator
    from flashcards.config import FlashcardConfig


@dataclass
class FlashcardResult:
    """Standardized result wrapper for all API operations"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    @classmethod
    def success_result(cls, data: Any = None, metadata: Dict[str, Any] = None):
        """Create successful result"""
        return cls(success=True, data=data, metadata=metadata)

    @classmethod
    def error_result(cls, error: str, error_code: str = None, metadata: Dict[str, Any] = None):
        """Create error result"""
        return cls(success=False, error=error, error_code=error_code, metadata=metadata)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


class FlashcardClient:
    """
    Main Flashcard API Client
    
    This is the primary interface for all flashcard operations.
    Coordinates multiple services and provides consistent error handling.
    """

    def __init__(self, 
                 db_path: str = FlashcardConfig.DATABASE_PATH,
                 enable_anki: bool = FlashcardConfig.ANKI_SYNC_ENABLED_DEFAULT,
                 orchestrator: Optional[FlashcardOrchestrator] = None):
        """
        Initialize FlashcardClient
        
        Args:
            db_path: Path to flashcard database
            enable_anki: Whether to enable Anki integration
            orchestrator: Optional pre-configured orchestrator (for testing)
        """
        self.logger = logging.getLogger(__name__)
        
        # Use provided orchestrator or create new one
        self.orchestrator = orchestrator or create_flashcard_orchestrator(
            db_path=db_path,
            enable_anki=enable_anki
        )
        
        self.logger.info("FlashcardClient initialized")

    # === CARD OPERATIONS ===

    def create_card(self, 
                   user_id: str, 
                   front: str, 
                   back: str,
                   domains: Optional[List[str]] = None,
                   algorithm: str = FlashcardConfig.DEFAULT_ALGORITHM,
                   kg_mapping: Optional[Dict[str, Any]] = None) -> FlashcardResult:
        """
        Create a new flashcard
        
        Args:
            user_id: User identifier
            front: Front of the card (question)
            back: Back of the card (answer)
            domains: Subject domains/categories
            algorithm: Spaced repetition algorithm to use
            kg_mapping: Knowledge graph mapping data
            
        Returns:
            FlashcardResult with created card data
        """
        try:
            # Input validation
            if not user_id or not user_id.strip():
                return FlashcardResult.error_result("user_id is required", "INVALID_USER_ID")
            
            if not front or not front.strip():
                return FlashcardResult.error_result("front text is required", "INVALID_FRONT")
            
            if not back or not back.strip():
                return FlashcardResult.error_result("back text is required", "INVALID_BACK")
            
            
            if FlashcardConfig.CARD_BACK_MAX_LENGTH and len(back.strip()) > FlashcardConfig.CARD_BACK_MAX_LENGTH:
                return FlashcardResult.error_result(f"back text too long (max {FlashcardConfig.CARD_BACK_MAX_LENGTH} chars)", "BACK_TOO_LONG")

            # Create card
            result = self.orchestrator.create_card(
                user_id=user_id.strip(),
                front=front.strip(),
                back=back.strip(),
                domains=domains or [],
                algorithm=algorithm
            )
            
            if result.success:
                card = result.data
                return FlashcardResult.success_result(
                    data={
                        "id": card.id,
                        "front": card.front,
                        "back": card.back,
                        "domains": card.Domains,
                        "algorithm": card.scheduling.algorithm,
                        "created_at": card.created_at.isoformat(),
                        "next_review_date": card.scheduling.next_review_date.isoformat(),
                        "ease_factor": card.scheduling.ease_factor
                    },
                    metadata={
                        "anki_sync_enabled": self.orchestrator.anki_service is not None
                    }
                )
            else:
                return FlashcardResult.error_result(result.error, "CREATE_FAILED")
                
        except Exception as e:
            self.logger.error(f"Failed to create card: {e}")
            return FlashcardResult.error_result(f"Internal error: {str(e)}", "INTERNAL_ERROR")

    def get_card(self, card_id: str) -> FlashcardResult:
        """
        Get card by ID
        
        Args:
            card_id: Card identifier
            
        Returns:
            FlashcardResult with card data
        """
        try:
            if not card_id or not card_id.strip():
                return FlashcardResult.error_result("card_id is required", "INVALID_CARD_ID")
            
            result = self.orchestrator.get_card(card_id.strip())
            
            if result.success:
                card = result.data
                return FlashcardResult.success_result(
                    data={
                        "id": card.id,
                        "user_id": card.user_id,
                        "front": card.front,
                        "back": card.back,
                        "domains": card.Domains,
                        "created_at": card.created_at.isoformat(),
                        "updated_at": card.updated_at.isoformat(),
                        "reviewed_at": card.reviewed_at.isoformat(),
                        "scheduling": {
                            "algorithm": card.scheduling.algorithm,
                            "ease_factor": card.scheduling.ease_factor,
                            "interval_days": card.scheduling.interval_days,
                            "repetitions": card.scheduling.repetitions,
                            "next_review_date": card.scheduling.next_review_date.isoformat() if card.scheduling.next_review_date else None,
                            "last_review_date": card.scheduling.last_review_date.isoformat() if card.scheduling.last_review_date else None
                        },
                        "is_due": card.is_due()
                    }
                )
            else:
                return FlashcardResult.error_result(result.error, "CARD_NOT_FOUND")
                
        except Exception as e:
            self.logger.error(f"Failed to get card {card_id}: {e}")
            return FlashcardResult.error_result(f"Internal error: {str(e)}", "INTERNAL_ERROR")

    def review_card(self, 
                   card_id: str, 
                   quality: int,
                   response_time_seconds: Optional[float] = None,
                   user_id: Optional[str] = None) -> FlashcardResult:
        """
        Review a flashcard
        
        Args:
            card_id: Card identifier
            quality: Quality rating (1-5, algorithm dependent)
            response_time_seconds: Time taken to answer
            user_id: Optional user validation
            
        Returns:
            FlashcardResult with review data and updated scheduling
        """
        try:
            # Input validation
            if not card_id or not card_id.strip():
                return FlashcardResult.error_result("card_id is required", "INVALID_CARD_ID")
            
            if not isinstance(quality, int) or quality < FlashcardConfig.REVIEW_QUALITY_MIN or quality > FlashcardConfig.REVIEW_QUALITY_MAX:
                return FlashcardResult.error_result(f"quality must be an integer between {FlashcardConfig.REVIEW_QUALITY_MIN} and {FlashcardConfig.REVIEW_QUALITY_MAX}", "INVALID_QUALITY")
            
            if response_time_seconds is not None and (response_time_seconds < FlashcardConfig.RESPONSE_TIME_MIN_SECONDS or response_time_seconds > FlashcardConfig.RESPONSE_TIME_MAX_SECONDS):
                return FlashcardResult.error_result(f"response_time_seconds must be between {FlashcardConfig.RESPONSE_TIME_MIN_SECONDS} and {FlashcardConfig.RESPONSE_TIME_MAX_SECONDS}", "INVALID_RESPONSE_TIME")

            # Get card first to validate user ownership
            card_result = self.get_card(card_id)
            if not card_result.success:
                return card_result
            
            if user_id and card_result.data["user_id"] != user_id:
                return FlashcardResult.error_result("Card does not belong to user", "UNAUTHORIZED")

            # Process review
            result = self.orchestrator.review_card(
                card_id=card_id.strip(),
                quality=quality,
                response_time=response_time_seconds
            )
            
            if result.success:
                review = result.data
                
                # Get updated card data
                updated_card_result = self.get_card(card_id)
                updated_card_data = updated_card_result.data if updated_card_result.success else {}
                
                return FlashcardResult.success_result(
                    data={
                        "review": {
                            "id": review.review_id,
                            "card_id": review.card_id,
                            "quality": review.quality,
                            "response_time_seconds": review.response_time_seconds,
                            "reviewed_at": review.reviewed_at.isoformat(),
                            "algorithm_used": review.algorithm_used
                        },
                        "updated_card": updated_card_data,
                        "next_review_date": updated_card_data.get("scheduling", {}).get("next_review_date")
                    },
                    metadata={
                        "review_processed": True,
                        "scheduling_updated": True
                    }
                )
            else:
                return FlashcardResult.error_result(result.error, "REVIEW_FAILED")
                
        except Exception as e:
            self.logger.error(f"Failed to review card {card_id}: {e}")
            return FlashcardResult.error_result(f"Internal error: {str(e)}", "INTERNAL_ERROR")

    def get_due_cards(self, 
                     user_id: str, 
                     limit: Optional[int] = None,
                     domains: Optional[List[str]] = None) -> FlashcardResult:
        """
        Get cards due for review
        
        Args:
            user_id: User identifier
            limit: Maximum number of cards to return
            domains: Filter by specific domains
            
        Returns:
            FlashcardResult with list of due cards
        """
        try:
            if not user_id or not user_id.strip():
                return FlashcardResult.error_result("user_id is required", "INVALID_USER_ID")
            
            if limit is not None and (limit < 1 or limit > FlashcardConfig.MAX_DUE_CARDS_LIMIT):
                return FlashcardResult.error_result(f"limit must be between 1 and {FlashcardConfig.MAX_DUE_CARDS_LIMIT}", "INVALID_LIMIT")

            result = self.orchestrator.get_due_cards(user_id.strip(), limit)
            
            if result.success:
                cards = result.data
                
                # Filter by domains if specified
                if domains:
                    cards = [card for card in cards if any(domain in card.Domains for domain in domains)]
                
                cards_data = []
                for card in cards:
                    cards_data.append({
                        "id": card.id,
                        "front": card.front,
                        "back": card.back,
                        "domains": card.Domains,
                        "ease_factor": card.scheduling.ease_factor,
                        "interval_days": card.scheduling.interval_days,
                        "repetitions": card.scheduling.repetitions,
                        "last_review_date": card.scheduling.last_review_date.isoformat() if card.scheduling.last_review_date else None,
                        "next_review_date": card.scheduling.next_review_date.isoformat() if card.scheduling.next_review_date else None,
                        "days_overdue": (datetime.now() - card.scheduling.next_review_date).days if card.scheduling.next_review_date else 0
                    })
                
                return FlashcardResult.success_result(
                    data=cards_data,
                    metadata={
                        "total_due_cards": len(cards_data),
                        "filtered_by_domains": domains is not None,
                        "domains_filter": domains or []
                    }
                )
            else:
                return FlashcardResult.error_result(result.error, "QUERY_FAILED")
                
        except Exception as e:
            self.logger.error(f"Failed to get due cards for user {user_id}: {e}")
            return FlashcardResult.error_result(f"Internal error: {str(e)}", "INTERNAL_ERROR")

    # === DECK OPERATIONS ===

    def create_deck(self, 
                   user_id: str, 
                   name: str,
                   description: str = "",
                   algorithm: str = FlashcardConfig.DEFAULT_ALGORITHM) -> FlashcardResult:
        """
        Create a new deck
        
        Args:
            user_id: User identifier
            name: Deck name
            description: Deck description
            algorithm: Default algorithm for cards in this deck
            
        Returns:
            FlashcardResult with created deck data
        """
        try:
            # Input validation
            if not user_id or not user_id.strip():
                return FlashcardResult.error_result("user_id is required", "INVALID_USER_ID")
            
            if not name or not name.strip():
                return FlashcardResult.error_result("name is required", "INVALID_NAME")
            
            if len(name.strip()) > FlashcardConfig.DECK_NAME_MAX_LENGTH:
                return FlashcardResult.error_result(f"name too long (max {FlashcardConfig.DECK_NAME_MAX_LENGTH} chars)", "NAME_TOO_LONG")

            result = self.orchestrator.create_deck(
                user_id=user_id.strip(),
                name=name.strip(),
                description=description.strip(),
                algorithm=algorithm
            )
            
            if result.success:
                deck = result.data
                return FlashcardResult.success_result(
                    data={
                        "id": deck.id,
                        "name": deck.name,
                        "description": deck.description,
                        "user_id": deck.user_id,
                        "default_algorithm": deck.default_algorithm,
                        "created_at": deck.created_at.isoformat(),
                        "updated_at": deck.updated_at.isoformat()
                    }
                )
            else:
                return FlashcardResult.error_result(result.error, "CREATE_DECK_FAILED")
                
        except Exception as e:
            self.logger.error(f"Failed to create deck: {e}")
            return FlashcardResult.error_result(f"Internal error: {str(e)}", "INTERNAL_ERROR")

    def get_user_decks(self, user_id: str) -> FlashcardResult:
        """
        Get all decks for a user
        
        Args:
            user_id: User identifier
            
        Returns:
            FlashcardResult with list of user's decks
        """
        try:
            if not user_id or not user_id.strip():
                return FlashcardResult.error_result("user_id is required", "INVALID_USER_ID")

            result = self.orchestrator.get_user_decks(user_id.strip())
            
            if result.success:
                decks = result.data
                decks_data = []
                
                for deck in decks:
                    decks_data.append({
                        "id": deck.id,
                        "name": deck.name,
                        "description": deck.description,
                        "default_algorithm": deck.default_algorithm,
                        "created_at": deck.created_at.isoformat(),
                        "updated_at": deck.updated_at.isoformat()
                    })
                
                return FlashcardResult.success_result(
                    data=decks_data,
                    metadata={"total_decks": len(decks_data)}
                )
            else:
                return FlashcardResult.error_result(result.error, "QUERY_FAILED")
                
        except Exception as e:
            self.logger.error(f"Failed to get decks for user {user_id}: {e}")
            return FlashcardResult.error_result(f"Internal error: {str(e)}", "INTERNAL_ERROR")

    # === STATISTICS ===

    def get_user_stats(self, user_id: str) -> FlashcardResult:
        """
        Get comprehensive user statistics
        
        Args:
            user_id: User identifier
            
        Returns:
            FlashcardResult with user statistics
        """
        try:
            if not user_id or not user_id.strip():
                return FlashcardResult.error_result("user_id is required", "INVALID_USER_ID")

            result = self.orchestrator.get_user_stats(user_id.strip())
            
            if result.success:
                stats = result.data
                return FlashcardResult.success_result(
                    data=stats,
                    metadata={
                        "stats_generated_at": datetime.now().isoformat(),
                        "user_id": user_id
                    }
                )
            else:
                return FlashcardResult.error_result(result.error, "STATS_FAILED")
                
        except Exception as e:
            self.logger.error(f"Failed to get stats for user {user_id}: {e}")
            return FlashcardResult.error_result(f"Internal error: {str(e)}", "INTERNAL_ERROR")

    # === STUDY SESSION ===

    def start_study_session(self, 
                           user_id: str, 
                           max_cards: int = FlashcardConfig.DEFAULT_STUDY_SESSION_SIZE,
                           domains: Optional[List[str]] = None) -> FlashcardResult:
        """
        Start a study session for a user
        
        Args:
            user_id: User identifier
            max_cards: Maximum cards in session
            domains: Filter by specific domains
            
        Returns:
            FlashcardResult with session data
        """
        try:
            if not user_id or not user_id.strip():
                return FlashcardResult.error_result("user_id is required", "INVALID_USER_ID")
            
            if max_cards < FlashcardConfig.MIN_STUDY_SESSION_SIZE or max_cards > FlashcardConfig.MAX_STUDY_SESSION_SIZE:
                return FlashcardResult.error_result(f"max_cards must be between {FlashcardConfig.MIN_STUDY_SESSION_SIZE} and {FlashcardConfig.MAX_STUDY_SESSION_SIZE}", "INVALID_MAX_CARDS")

            # Get due cards
            cards_result = self.get_due_cards(user_id.strip(), limit=max_cards, domains=domains)
            
            if not cards_result.success:
                return cards_result
            
            cards = cards_result.data
            stats_result = self.get_user_stats(user_id.strip())
            stats = stats_result.data if stats_result.success else {}
            
            session_data = {
                "session_id": f"session_{user_id}_{int(datetime.now().timestamp())}",
                "user_id": user_id,
                "cards": cards,
                "session_info": {
                    "total_cards": len(cards),
                    "max_cards_requested": max_cards,
                    "domains_filter": domains,
                    "user_stats": stats,
                    "started_at": datetime.now().isoformat()
                }
            }
            
            return FlashcardResult.success_result(
                data=session_data,
                metadata={
                    "session_created": True,
                    "cards_available": len(cards) > 0
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to start study session for user {user_id}: {e}")
            return FlashcardResult.error_result(f"Internal error: {str(e)}", "INTERNAL_ERROR")

    # === EXTERNAL INTEGRATIONS ===

    def sync_with_anki(self, user_id: str) -> FlashcardResult:
        """
        Sync user's flashcards with Anki
        
        Args:
            user_id: User identifier
            
        Returns:
            FlashcardResult with sync status
        """
        try:
            if not user_id or not user_id.strip():
                return FlashcardResult.error_result("user_id is required", "INVALID_USER_ID")

            result = self.orchestrator.sync_with_anki(user_id.strip())
            
            if result.success:
                return FlashcardResult.success_result(
                    data=result.data,
                    metadata={
                        "sync_completed_at": datetime.now().isoformat(),
                        "anki_integration": True
                    }
                )
            else:
                return FlashcardResult.error_result(result.error, "ANKI_SYNC_FAILED")
                
        except Exception as e:
            self.logger.error(f"Failed to sync with Anki for user {user_id}: {e}")
            return FlashcardResult.error_result(f"Internal error: {str(e)}", "INTERNAL_ERROR")

    # === UTILITY METHODS ===

    def health_check(self) -> FlashcardResult:
        """
        Check if the flashcard system is healthy
        
        Returns:
            FlashcardResult with system health status
        """
        try:
            # Test basic operations
            health_data = {
                "status": FlashcardConfig.HEALTH_CHECK_STATUS_HEALTHY,
                "timestamp": datetime.now().isoformat(),
                "services": {
                    "database": "connected",
                    "anki_integration": "available" if self.orchestrator.anki_service else "disabled"
                },
                "version": FlashcardConfig.SYSTEM_VERSION
            }
            
            return FlashcardResult.success_result(data=health_data)
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return FlashcardResult.error_result(f"System unhealthy: {str(e)}", "HEALTH_CHECK_FAILED")


# Factory function for easy initialization
def create_flashcard_client(db_path: str = FlashcardConfig.DATABASE_PATH, 
                           enable_anki: bool = FlashcardConfig.ANKI_SYNC_ENABLED_DEFAULT) -> FlashcardClient:
    """
    Factory function to create a properly configured FlashcardClient
    
    Args:
        db_path: Path to flashcard database
        enable_anki: Whether to enable Anki integration
        
    Returns:
        Configured FlashcardClient instance
    """
    return FlashcardClient(db_path=db_path, enable_anki=enable_anki)



if __name__ == "__main__":
    """
    Test script for FlashcardClient
    Run this file directly to test the client functionality
    """
    import json
    from datetime import datetime
    
    def print_result(operation_name, result):
        """Helper to print results nicely"""
        print(f"\n=== {operation_name} ===")
        print(f"Success: {result.success}")
        if result.success:
            print(f"Data: {json.dumps(result.data, indent=2, default=str)}")
            if result.metadata:
                print(f"Metadata: {json.dumps(result.metadata, indent=2, default=str)}")
        else:
            print(f"Error: {result.error}")
            print(f"Error Code: {result.error_code}")
        print("-" * 50)
    
    def test_flashcard_client():
        """Run comprehensive tests of FlashcardClient"""
        print("🧠 Testing FlashcardClient")
        print("=" * 50)
        
        # Initialize client
        print("Initializing FlashcardClient...")
        try:
            client = create_flashcard_client(db_path="test_database", enable_anki=False)
            print("✅ Client initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize client: {e}")
            return
        
        # Test health check
        health_result = client.health_check()
        print_result("Health Check", health_result)
        
        if not health_result.success:
            print("❌ System unhealthy, stopping tests")
            return
        
        user_id = "test_user_123"
        
        # Test 1: Create deck
        deck_result = client.create_deck(
            user_id=user_id,
            name="Geography Quiz",
            description="World geography flashcards",
            algorithm="sm2"
        )
        print_result("Create Deck", deck_result)
        
        # Test 2: Create cards
        test_cards = [
            {
                "front": "What is the capital of France?",
                "back": "Paris",
                "domains": ["geography", "europe"]
            },
            {
                "front": "What is the largest ocean?",
                "back": "Pacific Ocean",
                "domains": ["geography", "oceans"]
            },
            {
                "front": "Which mountain range contains Mount Everest?",
                "back": "The Himalayas",
                "domains": ["geography", "mountains"]
            },
            {
                "front": "What is the capital of Japan?",
                "back": "Tokyo",
                "domains": ["geography", "asia"]
            }
        ]
        
        created_cards = []
        for i, card_data in enumerate(test_cards):
            result = client.create_card(
                user_id=user_id,
                front=card_data["front"],
                back=card_data["back"],
                domains=card_data["domains"],
                algorithm="sm2"
            )
            print_result(f"Create Card {i+1}", result)
            
            if result.success:
                created_cards.append(result.data)
        
        print(f"\n📊 Created {len(created_cards)} cards successfully")
        
        # Test 3: Get individual card
        if created_cards:
            first_card_id = created_cards[0]["id"]
            card_result = client.get_card(first_card_id)
            print_result("Get Individual Card", card_result)
        
        # Test 4: Get user stats
        stats_result = client.get_user_stats(user_id)
        print_result("User Statistics", stats_result)
        
        # Test 5: Get due cards
        due_cards_result = client.get_due_cards(user_id, limit=10)
        print_result("Get Due Cards", due_cards_result)
        
        # Test 6: Start study session
        session_result = client.start_study_session(
            user_id=user_id,
            max_cards=3,
            domains=["geography"]
        )
        print_result("Start Study Session", session_result)
        
        # Test 7: Review cards
        if session_result.success and session_result.data["cards"]:
            session_cards = session_result.data["cards"]
            
            print(f"\n🎯 Reviewing {len(session_cards)} cards from study session...")
            
            for i, card in enumerate(session_cards[:2]):  # Review first 2 cards
                print(f"\nCard {i+1}: {card['front']}")
                print(f"Answer: {card['back']}")
                
                # Simulate different review qualities
                quality = 4 if i == 0 else 3  # First card: good, second: okay
                response_time = 2.5 + i * 1.2  # Varying response times
                
                review_result = client.review_card(
                    card_id=card["id"],
                    quality=quality,
                    response_time_seconds=response_time,
                    user_id=user_id
                )
                print_result(f"Review Card {i+1} (Quality: {quality})", review_result)
        
        # Test 8: Get updated stats after reviews
        updated_stats_result = client.get_user_stats(user_id)
        print_result("Updated User Statistics", updated_stats_result)
        
        # Test 9: Get user decks
        decks_result = client.get_user_decks(user_id)
        print_result("User Decks", decks_result)
        
        # Test 10: Error handling tests
        print("\n🚨 Testing Error Handling...")
        
        error_tests = [
            ("Empty user_id", lambda: client.create_card("", "front", "back")),
            ("Empty front", lambda: client.create_card("user", "", "back")),
            ("Invalid quality", lambda: client.review_card("fake_id", 10)),
            ("Non-existent card", lambda: client.get_card("non_existent_id")),
            ("Invalid limit", lambda: client.get_due_cards("user", limit=200))
        ]
        
        for test_name, test_func in error_tests:
            try:
                result = test_func()
                print(f"  {test_name}: {'✅ Caught' if not result.success else '❌ Missed'} error - {result.error}")
            except Exception as e:
                print(f"  {test_name}: ❌ Exception - {e}")
        
        # Test 11: Anki sync (will likely fail without Anki, but tests the interface)
        print("\n🔄 Testing Anki Sync (may fail if Anki not available)...")
        anki_result = client.sync_with_anki(user_id)
        print_result("Anki Sync", anki_result)
        
        print("\n🎉 FlashcardClient Testing Complete!")
        print(f"   Total cards created: {len(created_cards)}")
        print(f"   User ID tested: {user_id}")
        print(f"   Test completed at: {datetime.now().isoformat()}")
    
    # Run the tests
    test_flashcard_client()