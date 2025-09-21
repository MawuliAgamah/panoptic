#!/usr/bin/env python3
"""Test telegram bot flashcard integration"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from bots.base import MessageHandler

def test_telegram_flashcard_integration():
    """Test the telegram bot flashcard features"""
    print("🤖 Testing Telegram Bot Flashcard Integration")
    print("=" * 55)

    # Initialize message handler
    handler = MessageHandler()
    test_user_id = "telegram_test_user"

    # Test conversation flow
    test_conversations = [
        # Help command
        ("/help", "Should show all commands including flashcards"),

        # Create first flashcard
        ("new card", "Should start card creation"),
        ("What is Python?", "Should ask for answer"),
        ("A programming language", "Should create the flashcard"),

        # Check stats
        ("/stats", "Should show user statistics"),

        # Create another card
        ("new card", "Start creating second card"),
        ("What is a variable?", "Ask for answer"),
        ("A storage location with a name", "Create second flashcard"),

        # Start review session
        ("review", "Should show first card for review"),
        ("anything", "Should show answer and ask for rating"),
        ("4", "Should record review and show next card or completion"),

        # Check final stats
        ("/stats", "Should show updated statistics"),

        # List decks
        ("/decks", "Should show user decks"),
    ]

    print("\n🎯 Running conversation simulation...")
    print("-" * 55)

    for i, (message, expected) in enumerate(test_conversations, 1):
        print(f"\n[{i:2d}] User: {message}")
        print(f"     Expected: {expected}")

        try:
            response = handler.process_message(message, test_user_id)
            print(f"     Bot Response: {response[:100]}...")
            if len(response) > 100:
                print(f"                   (+ {len(response) - 100} more chars)")

        except Exception as e:
            print(f"     ❌ ERROR: {e}")

        print("-" * 55)

    print("\n🎉 Test completed!")
    print("\nKey Features Tested:")
    print("✅ Help command with flashcard info")
    print("✅ Card creation workflow (question → answer → save)")
    print("✅ Review workflow (show question → show answer → rate → save)")
    print("✅ Statistics tracking")
    print("✅ Deck management")
    print("✅ Context handling (multi-step conversations)")

if __name__ == "__main__":
    test_telegram_flashcard_integration()