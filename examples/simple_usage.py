"""Simple usage examples - how to replace current FlashcardService"""

# OLD WAY (current FlashcardService)
# from flashcards import FlashcardService, create_flashcard_service
# service = create_flashcard_service()

# NEW WAY (improved orchestrator)
from flashcards.services.improved_flashcard_service import create_flashcard_orchestrator

def basic_flashcard_operations():
    """Basic operations - simple drop-in replacement"""
    
    # Initialize service
    orchestrator = create_flashcard_orchestrator(
        db_path="database/flashcards",
        enable_anki=True
    )
    
    user_id = "user123"
    
    # 1. Create a flashcard
    print("1. Creating flashcard...")
    card_result = orchestrator.create_card(
        user_id=user_id,
        front="What is Python?",
        back="A high-level programming language",
        domains=["programming", "python"],
        algorithm="sm2"
    )
    
    if card_result.success:
        card = card_result.data
        print(f"✅ Created card: {card.id}")
        print(f"   Front: {card.front}")
        print(f"   Next review: {card.scheduling.next_review_date}")
    else:
        print(f"❌ Error: {card_result.error}")
        return
    
    # 2. Create a deck
    print("\n2. Creating deck...")
    deck_result = orchestrator.create_deck(
        user_id=user_id,
        name="Python Basics",
        description="Fundamental Python concepts"
    )
    
    if deck_result.success:
        deck = deck_result.data
        print(f"✅ Created deck: {deck.name}")
    else:
        print(f"❌ Error: {deck_result.error}")
    
    # 3. Get cards due for review
    print("\n3. Getting due cards...")
    due_result = orchestrator.get_due_cards(user_id, limit=5)
    
    if due_result.success:
        due_cards = due_result.data
        print(f"✅ Found {len(due_cards)} cards due for review")
        
        if due_cards:
            # 4. Review the first card
            print("\n4. Reviewing first card...")
            first_card = due_cards[0]
            
            review_result = orchestrator.review_card(
                card_id=first_card.id,
                quality=4,  # Good recall
                response_time=3.5
            )
            
            if review_result.success:
                review = review_result.data
                print(f"✅ Card reviewed with quality {review.quality}")
                print(f"   Next review: {first_card.scheduling.next_review_date}")
            else:
                print(f"❌ Review error: {review_result.error}")
    
    # 5. Get user statistics
    print("\n5. Getting user stats...")
    stats_result = orchestrator.get_user_stats(user_id)
    
    if stats_result.success:
        stats = stats_result.data
        print(f"✅ User stats:")
        print(f"   Total cards: {stats['total_cards']}")
        print(f"   Cards due: {stats['cards_due']}")
        print(f"   Average ease: {stats['average_ease_factor']:.2f}")
    
    # 6. Sync with Anki (if available)
    print("\n6. Syncing with Anki...")
    sync_result = orchestrator.sync_with_anki(user_id)
    
    if sync_result.success:
        sync_data = sync_result.data
        print(f"✅ Anki sync: {sync_data}")
    else:
        print(f"ℹ️ Anki sync: {sync_result.error}")


def error_handling_example():
    """Demonstrates consistent error handling"""
    
    orchestrator = create_flashcard_orchestrator()
    
    # Try to get a non-existent card
    result = orchestrator.get_card("non_existent_id")
    
    if result.success:
        print(f"Card found: {result.data}")
    else:
        print(f"Expected error: {result.error}")  # "Card not found"
    
    # Try to review with invalid quality
    card_result = orchestrator.create_card(
        user_id="test_user",
        front="Test",
        back="Test answer"
    )
    
    if card_result.success:
        review_result = orchestrator.review_card(
            card_id=card_result.data.id,
            quality=10  # Invalid quality (should be 1-5)
        )
        
        if not review_result.success:
            print(f"Expected validation error: {review_result.error}")


def performance_comparison():
    """Show performance improvements"""
    import time
    
    orchestrator = create_flashcard_orchestrator()
    user_id = "perf_test_user"
    
    # Create test cards
    print("Creating test cards...")
    for i in range(100):
        orchestrator.create_card(
            user_id=user_id,
            front=f"Question {i}",
            back=f"Answer {i}",
            domains=["test"]
        )
    
    # Test due cards performance
    print("Testing due cards query performance...")
    
    start_time = time.time()
    due_result = orchestrator.get_due_cards(user_id, limit=10)
    end_time = time.time()
    
    if due_result.success:
        print(f"✅ Got {len(due_result.data)} due cards in {end_time - start_time:.3f}s")
    
    # Test stats performance
    start_time = time.time()
    stats_result = orchestrator.get_user_stats(user_id)
    end_time = time.time()
    
    if stats_result.success:
        print(f"✅ Got user stats in {end_time - start_time:.3f}s")


def main():
    """Run all examples"""
    print("=== Basic Flashcard Operations ===")
    basic_flashcard_operations()
    
    print("\n=== Error Handling Example ===")
    error_handling_example()
    
    print("\n=== Performance Test ===")
    performance_comparison()


if __name__ == "__main__":
    main()
