"""
Example usage of the FlashcardClient API

This demonstrates how to use the new FlashcardClient as your primary interface.
"""

from flashcards import FlashcardClient, create_flashcard_client


def demonstrate_flashcard_client():
    """Demonstrate basic FlashcardClient usage"""
    
    print("=== FlashcardClient Demo ===\n")
    
    # 1. Initialize client
    print("1. Initializing FlashcardClient...")
    client = create_flashcard_client(
        db_path="database/flashcards",
        enable_anki=True
    )
    
    # 2. Health check
    print("2. Checking system health...")
    health = client.health_check()
    if health.success:
        print(f"✅ System healthy: {health.data['status']}")
        print(f"   Anki: {health.data['services']['anki_integration']}")
    else:
        print(f"❌ Health check failed: {health.error}")
        return
    
    user_id = "demo_user"
    
    # 3. Create a deck
    print(f"\n3. Creating deck for user {user_id}...")
    deck_result = client.create_deck(
        user_id=user_id,
        name="Python Fundamentals",
        description="Basic Python programming concepts",
        algorithm="sm2"
    )
    
    if deck_result.success:
        deck = deck_result.data
        print(f"✅ Created deck: {deck['name']} (ID: {deck['id'][:8]}...)")
    else:
        print(f"❌ Failed to create deck: {deck_result.error}")
    
    # 4. Create flashcards
    print("\n4. Creating flashcards...")
    
    cards_to_create = [
        {
            "front": "What is a Python list?",
            "back": "A Python list is an ordered, mutable collection that can hold multiple items of different data types",
            "domains": ["python", "data_structures"]
        },
        {
            "front": "What is the difference between == and is in Python?",
            "back": "== compares values for equality, while 'is' compares object identity (whether two variables point to the same object)",
            "domains": ["python", "operators"]
        },
        {
            "front": "What is a Python dictionary?",
            "back": "A dictionary is an unordered, mutable collection of key-value pairs where keys must be unique and immutable",
            "domains": ["python", "data_structures"]
        }
    ]
    
    created_cards = []
    for card_data in cards_to_create:
        result = client.create_card(
            user_id=user_id,
            front=card_data["front"],
            back=card_data["back"],
            domains=card_data["domains"],
            algorithm="sm2"
        )
        
        if result.success:
            card = result.data
            created_cards.append(card)
            print(f"✅ Created card: {card['front'][:30]}... (ID: {card['id'][:8]}...)")
        else:
            print(f"❌ Failed to create card: {result.error}")
    
    # 5. Get user stats
    print(f"\n5. Getting stats for user {user_id}...")
    stats_result = client.get_user_stats(user_id)
    
    if stats_result.success:
        stats = stats_result.data
        print(f"✅ User stats:")
        print(f"   Total cards: {stats['total_cards']}")
        print(f"   Cards due: {stats['cards_due']}")
        print(f"   Average ease factor: {stats['average_ease_factor']:.2f}")
    else:
        print(f"❌ Failed to get stats: {stats_result.error}")
    
    # 6. Start study session
    print(f"\n6. Starting study session for user {user_id}...")
    session_result = client.start_study_session(
        user_id=user_id,
        max_cards=5,
        domains=["python"]  # Filter to Python cards only
    )
    
    if session_result.success:
        session = session_result.data
        print(f"✅ Study session started: {session['session_id']}")
        print(f"   Cards in session: {session['session_info']['total_cards']}")
        print(f"   Session started at: {session['session_info']['started_at']}")
        
        # 7. Review first card in session
        if session['cards']:
            print(f"\n7. Reviewing first card...")
            first_card = session['cards'][0]
            
            print(f"   Question: {first_card['front']}")
            print(f"   Answer: {first_card['back']}")
            
            # Simulate user reviewing the card
            review_result = client.review_card(
                card_id=first_card['id'],
                quality=4,  # Good recall
                response_time_seconds=3.5,
                user_id=user_id
            )
            
            if review_result.success:
                review = review_result.data
                print(f"✅ Card reviewed with quality {review['review']['quality']}")
                print(f"   Next review: {review['next_review_date']}")
                print(f"   Updated ease factor: {review['updated_card']['scheduling']['ease_factor']:.2f}")
            else:
                print(f"❌ Failed to review card: {review_result.error}")
    else:
        print(f"❌ Failed to start study session: {session_result.error}")
    
    # 8. Get updated stats
    print(f"\n8. Getting updated stats...")
    updated_stats_result = client.get_user_stats(user_id)
    
    if updated_stats_result.success:
        updated_stats = updated_stats_result.data
        print(f"✅ Updated stats:")
        print(f"   Cards reviewed today: {updated_stats['cards_reviewed_today']}")
    
    # 9. Try Anki sync
    print(f"\n9. Attempting Anki sync...")
    sync_result = client.sync_with_anki(user_id)
    
    if sync_result.success:
        sync_data = sync_result.data
        print(f"✅ Anki sync completed: {sync_data}")
    else:
        print(f"ℹ️ Anki sync: {sync_result.error}")
    
    print("\n=== Demo Complete ===")


def demonstrate_error_handling():
    """Demonstrate error handling and validation"""
    
    print("\n=== Error Handling Demo ===\n")
    
    client = create_flashcard_client()
    
    # Test various error conditions
    error_tests = [
        {
            "name": "Empty user_id",
            "action": lambda: client.create_card("", "front", "back")
        },
        {
            "name": "Empty front text",
            "action": lambda: client.create_card("user123", "", "back")
        },
        {
            "name": "Front text too long",
            "action": lambda: client.create_card("user123", "x" * 600, "back")
        },
        {
            "name": "Invalid quality score",
            "action": lambda: client.review_card("fake_card_id", 10)  # Quality must be 1-5
        },
        {
            "name": "Non-existent card",
            "action": lambda: client.get_card("non_existent_card_id")
        },
        {
            "name": "Invalid limit",
            "action": lambda: client.get_due_cards("user123", limit=200)  # Max 100
        }
    ]
    
    for test in error_tests:
        print(f"Testing: {test['name']}")
        result = test['action']()
        
        if not result.success:
            print(f"  ✅ Expected error: {result.error} (Code: {result.error_code})")
        else:
            print(f"  ❌ Expected error but got success")
        print()


def demonstrate_api_consistency():
    """Demonstrate consistent API responses"""
    
    print("\n=== API Consistency Demo ===\n")
    
    client = create_flashcard_client()
    
    # All API methods return FlashcardResult with consistent structure
    operations = [
        ("Health Check", lambda: client.health_check()),
        ("Create Card", lambda: client.create_card("test_user", "Q", "A")),
        ("Get Stats", lambda: client.get_user_stats("test_user")),
        ("Get Due Cards", lambda: client.get_due_cards("test_user")),
    ]
    
    for name, operation in operations:
        print(f"{name}:")
        result = operation()
        
        print(f"  Success: {result.success}")
        print(f"  Error: {result.error}")
        print(f"  Error Code: {result.error_code}")
        print(f"  Has Data: {result.data is not None}")
        print(f"  Has Metadata: {result.metadata is not None}")
        print(f"  JSON Serializable: {bool(result.to_dict())}")
        print()


if __name__ == "__main__":
    # Run all demonstrations
    demonstrate_flashcard_client()
    demonstrate_error_handling()
    demonstrate_api_consistency()
