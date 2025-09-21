#!/usr/bin/env python3
"""Test script for the flashcard system"""

import logging
from datetime import datetime
from src.flashcards import create_flashcard_service

# Set up logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_flashcard_system():
    """Test the complete flashcard system"""
    print("🧪 Testing Flashcard System")
    print("=" * 50)

    # 1. Initialize service
    print("\n1. Initializing FlashcardService...")
    service = create_flashcard_service(enable_anki=False)  # Disable Anki for testing

    # 2. Test service info
    print("\n2. Service Info:")
    info = service.get_service_info()
    print(f"   Algorithms available: {info['flashcard_service']['algorithms_available']}")
    print(f"   Anki enabled: {info['flashcard_service']['anki_enabled']}")

    # 3. Create a user and deck
    user_id = "test_user_123"
    print(f"\n3. Creating deck for user {user_id}...")

    deck = service.create_deck(
        user_id=user_id,
        name="Python Basics",
        description="Learning Python fundamentals",
        algorithm="sm2"
    )

    if deck:
        print(f"   ✅ Created deck: '{deck.name}' (ID: {deck.deck_id})")
        print(f"   Algorithm: {deck.default_algorithm}")
    else:
        print("   ❌ Failed to create deck")
        return

    # 4. Create some flashcards
    print("\n4. Creating flashcards...")

    cards_data = [
        ("What is a Python list?", "An ordered, mutable collection: [1, 2, 3]"),
        ("How do you define a function in Python?", "def function_name(parameters): return value"),
        ("What is a dictionary in Python?", "A key-value collection: {'key': 'value'}"),
        ("How do you create a for loop?", "for item in iterable: print(item)")
    ]

    cards = []
    for front, back in cards_data:
        card = service.create_card(
            deck_id=deck.deck_id,
            user_id=user_id,
            front=front,
            back=back,
            tags=["python", "basics"]
        )
        if card:
            cards.append(card)
            print(f"   ✅ Created card: {front[:30]}...")

    print(f"   Created {len(cards)} cards")

    # 5. Check due cards (should be all of them since they're new)
    print("\n5. Checking due cards...")
    due_cards = service.get_due_cards(user_id)
    print(f"   Cards due for review: {len(due_cards)}")

    # 6. Review some cards
    print("\n6. Reviewing cards...")

    if due_cards:
        card_to_review = due_cards[0]
        print(f"   Reviewing: {card_to_review.front}")
        print(f"   Algorithm: {card_to_review.scheduling.algorithm_name}")
        print(f"   Quality scale: {card_to_review.get_quality_scale()}")

        # Review with quality 4 (good recall)
        review = service.review_card(card_to_review.card_id, quality=4)

        if review:
            print(f"   ✅ Review completed!")
            print(f"   Next review: {card_to_review.scheduling.next_review_date}")
            print(f"   Ease factor: {card_to_review.scheduling.ease_factor:.2f}")
            print(f"   Interval: {card_to_review.scheduling.interval_days} days")

    # 7. Test algorithm switching
    print("\n7. Testing algorithm switching...")
    if cards:
        test_card = cards[1]
        print(f"   Current algorithm: {test_card.scheduling.algorithm_name}")

        # Switch to SM-15
        success = service.switch_card_algorithm(test_card.card_id, "sm15")
        if success:
            updated_card = service.get_card(test_card.card_id)
            print(f"   ✅ Switched to: {updated_card.scheduling.algorithm_name}")
            print(f"   New quality scale: {updated_card.get_quality_scale()}")
        else:
            print("   ❌ Failed to switch algorithm")

    # 8. Get statistics
    print("\n8. User Statistics:")
    stats = service.get_user_stats(user_id)
    print(f"   Total cards: {stats['total_cards']}")
    print(f"   Cards due: {stats['cards_due']}")
    print(f"   Total reviews: {stats['total_reviews']}")
    print(f"   Algorithm breakdown: {stats['algorithm_breakdown']}")
    print(f"   Difficulty breakdown: {stats['difficulty_breakdown']}")

    # 9. Test different algorithms
    print("\n9. Testing different algorithms...")
    algorithms = service.get_available_algorithms()

    for algo_name, algo_info in algorithms.items():
        print(f"   {algo_name}: {algo_info['description']}")
        print(f"     Quality scale: {algo_info['quality_scale']}")

    # 10. Test deck operations
    print("\n10. Deck operations...")
    user_decks = service.get_user_decks(user_id)
    print(f"   User has {len(user_decks)} deck(s)")

    for user_deck in user_decks:
        deck_stats = service.get_deck_stats(user_deck.deck_id)
        print(f"   Deck '{deck_stats['name']}': {deck_stats['total_cards']} cards")

    print("\n" + "=" * 50)
    print("🎉 Flashcard system test completed!")
    print("Check the database/ folder for created JSON files")

    # Cleanup
    service.close()

def interactive_review_session():
    """Interactive review session"""
    print("\n🎓 Interactive Review Session")
    print("=" * 40)

    service = create_flashcard_service(enable_anki=False)
    user_id = "test_user_123"

    # Get due cards
    due_cards = service.get_due_cards(user_id)

    if not due_cards:
        print("No cards due for review!")
        return

    print(f"You have {len(due_cards)} cards due for review")

    for i, card in enumerate(due_cards[:3]):  # Review first 3 cards
        print(f"\n--- Card {i+1}/{min(3, len(due_cards))} ---")
        print(f"Algorithm: {card.scheduling.algorithm_name}")
        print(f"Question: {card.front}")

        input("Press Enter to see the answer...")
        print(f"Answer: {card.back}")

        # Get quality scale for this card's algorithm
        quality_scale = card.get_quality_scale()
        print("\nHow well did you know this?")
        for quality, description in quality_scale.items():
            print(f"  {quality}: {description}")

        while True:
            try:
                quality = int(input("Enter quality (or 0 to skip): "))
                if quality == 0:
                    break
                if quality in quality_scale:
                    review = service.review_card(card.card_id, quality)
                    if review:
                        updated_card = service.get_card(card.card_id)
                        print(f"✅ Next review: {updated_card.scheduling.next_review_date}")
                    break
                else:
                    print(f"Please enter a valid quality: {list(quality_scale.keys())}")
            except ValueError:
                print("Please enter a number")

    print("\n🎯 Review session completed!")
    service.close()

if __name__ == "__main__":
    # Run basic test
    test_flashcard_system()

    # Ask if user wants interactive session
    print("\n" + "=" * 50)
    response = input("Would you like to try an interactive review session? (y/n): ")
    if response.lower().startswith('y'):
        interactive_review_session()