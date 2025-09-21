from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import sys
import os

# Add the src directory to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
sys.path.insert(0, src_dir)

from services.knowledge_store import JsonKnowledgeStore
from flashcards import create_flashcard_service


class MessageHandler:
    def __init__(self):
        self.knowledge_store = JsonKnowledgeStore()
        self.flashcard_service = create_flashcard_service(enable_anki=False)
        self.user_contexts = {}  # Track user conversation states

    def process_message(self, message: str, user_id: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        print(f"User {user_id}: '{message}' (length: {len(message)})")

        # Strip any whitespace
        message = message.strip()
        print(f"After strip: '{message}'")

        # Check if user is in a flashcard context
        user_context = self.user_contexts.get(user_id, {})

        # Handle flashcard creation context
        if user_context.get('state') == 'creating_card':
            return self._handle_card_creation(message, user_id, user_context)

        # Handle flashcard review context
        if user_context.get('state') == 'reviewing':
            return self._handle_card_review(message, user_id, user_context)

        # Regular command processing
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

        # Flashcard commands
        elif message.lower() in ['new card', '/newcard', '/new_card']:
            return self._start_card_creation(user_id)

        elif message.lower() in ['review', '/review', 'study', '/study']:
            return self._start_review_session(user_id)

        elif message.startswith('/create_deck '):
            deck_name = message[13:]  # Remove '/create_deck '
            return self._create_deck(user_id, deck_name)

        elif message == '/flashcard_stats' or message == '/stats':
            return self._get_flashcard_stats(user_id)

        elif message == '/decks':
            return self._list_decks(user_id)

        elif message.lower() in ['cancel', '/cancel']:
            return self._cancel_context(user_id)

        elif message == '/help':
            print("Processing help command")
            return self._get_help_message()

        else:
            print("No command matched, returning echo")
            return f"You said: {message}\nType /help for available commands"

    def _start_card_creation(self, user_id: str) -> str:
        """Start the card creation process"""
        # Check if user has any decks
        decks = self.flashcard_service.get_user_decks(user_id)

        if not decks:
            # Create a default deck
            deck = self.flashcard_service.create_deck(user_id, "My Flashcards", "Personal flashcard collection")
            if not deck:
                return "❌ Failed to create default deck. Please try again."

        self.user_contexts[user_id] = {
            'state': 'creating_card',
            'step': 'question'
        }

        return ("📝 **Create New Flashcard**\n\n"
                "Please enter the **question** or **front** of the card:")

    def _handle_card_creation(self, message: str, user_id: str, context: Dict[str, Any]) -> str:
        """Handle the card creation process"""
        step = context.get('step')

        if step == 'question':
            # Store the question and ask for answer
            self.user_contexts[user_id].update({
                'step': 'answer',
                'question': message
            })
            return f"✅ Question: {message}\n\nNow enter the **answer** or **back** of the card:"

        elif step == 'answer':
            # Create the flashcard
            question = context['question']
            answer = message

            # Get user's first deck (or create default)
            decks = self.flashcard_service.get_user_decks(user_id)
            if not decks:
                deck = self.flashcard_service.create_deck(user_id, "My Flashcards")
                if not deck:
                    self._cancel_context(user_id)
                    return "❌ Failed to create deck. Please try again."
                deck_id = deck.deck_id
            else:
                deck_id = decks[0].deck_id

            # Create the card
            card = self.flashcard_service.create_card(
                deck_id=deck_id,
                user_id=user_id,
                front=question,
                back=answer,
                tags=["telegram"]
            )

            # Clear context
            self._cancel_context(user_id)

            if card:
                return (f"🎉 **Flashcard Created!**\n\n"
                       f"📝 **Q:** {question}\n"
                       f"💡 **A:** {answer}\n"
                       f"🔄 **Algorithm:** {card.scheduling.algorithm_name}\n\n"
                       f"Type 'new card' to create another or 'review' to start studying!")
            else:
                return "❌ Failed to create flashcard. Please try again."

        return "❌ Something went wrong. Please try 'new card' again."

    def _start_review_session(self, user_id: str) -> str:
        """Start a review session"""
        due_cards = self.flashcard_service.get_due_cards(user_id, limit=1)

        if not due_cards:
            stats = self.flashcard_service.get_user_stats(user_id)
            total_cards = stats['total_cards']
            if total_cards == 0:
                return ("📚 **No flashcards to review!**\n\n"
                       "You don't have any flashcards yet.\n"
                       "Type 'new card' to create your first flashcard!")
            else:
                return (f"🎉 **All caught up!**\n\n"
                       f"You have {total_cards} flashcards but none are due for review right now.\n"
                       f"Great job staying on top of your studies! 🌟")

        card = due_cards[0]
        self.user_contexts[user_id] = {
            'state': 'reviewing',
            'card_id': card.card_id,
            'step': 'show_question'
        }

        # Get quality scale for this card's algorithm
        quality_scale = card.get_quality_scale()
        scale_text = "\n".join([f"**{k}**: {v}" for k, v in quality_scale.items()])

        return (f"📚 **Review Time!**\n\n"
               f"**Question:**\n{card.front}\n\n"
               f"Think about the answer, then reply with any message to see the answer.\n\n"
               f"Algorithm: {card.scheduling.algorithm_name}")

    def _handle_card_review(self, message: str, user_id: str, context: Dict[str, Any]) -> str:
        """Handle the card review process"""
        card_id = context['card_id']
        step = context.get('step')

        card = self.flashcard_service.get_card(card_id)
        if not card:
            self._cancel_context(user_id)
            return "❌ Card not found. Please try 'review' again."

        if step == 'show_question':
            # Show the answer and ask for quality rating
            quality_scale = card.get_quality_scale()
            scale_text = "\n".join([f"**{k}**: {v}" for k, v in quality_scale.items()])

            self.user_contexts[user_id]['step'] = 'rate_quality'

            return (f"💡 **Answer:**\n{card.back}\n\n"
                   f"**How well did you know this?**\n{scale_text}\n\n"
                   f"Reply with a number ({min(quality_scale.keys())}-{max(quality_scale.keys())}):")

        elif step == 'rate_quality':
            # Process the quality rating
            try:
                quality = int(message.strip())
                quality_scale = card.get_quality_scale()

                if quality not in quality_scale:
                    return f"❌ Please enter a valid rating ({min(quality_scale.keys())}-{max(quality_scale.keys())}):"

                # Process the review
                review = self.flashcard_service.review_card(card_id, quality)
                if not review:
                    self._cancel_context(user_id)
                    return "❌ Failed to record review. Please try again."

                # Get updated card info
                updated_card = self.flashcard_service.get_card(card_id)
                next_review_date = updated_card.scheduling.next_review_date

                # Clear context
                self._cancel_context(user_id)

                # Check for more due cards
                remaining_due = self.flashcard_service.get_due_cards(user_id)
                more_cards_msg = ""
                if remaining_due:
                    more_cards_msg = f"\n\n🔄 **{len(remaining_due)} more cards due!** Type 'review' to continue."
                else:
                    more_cards_msg = "\n\n🎉 **All caught up!** Great job studying!"

                return (f"✅ **Review recorded!**\n\n"
                       f"**Rating:** {quality} - {quality_scale[quality]}\n"
                       f"**Next review:** {next_review_date.strftime('%Y-%m-%d %H:%M')}\n"
                       f"**Algorithm:** {updated_card.scheduling.algorithm_name}"
                       f"{more_cards_msg}")

            except ValueError:
                return "❌ Please enter a valid number for your rating:"

        return "❌ Something went wrong. Please try 'review' again."

    def _create_deck(self, user_id: str, deck_name: str) -> str:
        """Create a new deck"""
        deck = self.flashcard_service.create_deck(
            user_id=user_id,
            name=deck_name,
            description=f"Deck created via Telegram",
            algorithm="sm2"
        )

        if deck:
            return (f"🗂️ **Deck Created!**\n\n"
                   f"**Name:** {deck.name}\n"
                   f"**Algorithm:** {deck.default_algorithm}\n"
                   f"**ID:** {deck.deck_id[:8]}...\n\n"
                   f"Type 'new card' to add flashcards to this deck!")
        else:
            return f"❌ Failed to create deck '{deck_name}'. Please try again."

    def _list_decks(self, user_id: str) -> str:
        """List all user decks"""
        decks = self.flashcard_service.get_user_decks(user_id)

        if not decks:
            return ("📚 **No decks found**\n\n"
                   "You don't have any flashcard decks yet.\n"
                   "Type '/create_deck <name>' to create your first deck!")

        deck_list = []
        for deck in decks:
            deck_stats = self.flashcard_service.get_deck_stats(deck.deck_id)
            deck_list.append(
                f"🗂️ **{deck.name}**\n"
                f"   📊 {deck_stats['total_cards']} cards ({deck_stats['cards_due']} due)\n"
                f"   🧠 Algorithm: {deck.default_algorithm}"
            )

        return "📚 **Your Decks:**\n\n" + "\n\n".join(deck_list)

    def _get_flashcard_stats(self, user_id: str) -> str:
        """Get user flashcard statistics"""
        stats = self.flashcard_service.get_user_stats(user_id)

        if stats['total_cards'] == 0:
            return ("📊 **Your Flashcard Stats**\n\n"
                   "No flashcards yet! Type 'new card' to get started.")

        return (f"📊 **Your Flashcard Stats**\n\n"
               f"📝 **Total Cards:** {stats['total_cards']}\n"
               f"🔄 **Due for Review:** {stats['cards_due']}\n"
               f"📈 **Total Reviews:** {stats['total_reviews']}\n"
               f"🔥 **Current Streak:** {stats['current_streak']}\n"
               f"⚠️ **Overdue:** {stats['overdue_cards']}\n\n"
               f"**Difficulty Breakdown:**\n"
               f"🟢 Easy: {stats['difficulty_breakdown']['Easy']}\n"
               f"🟡 Medium: {stats['difficulty_breakdown']['Medium']}\n"
               f"🔴 Hard: {stats['difficulty_breakdown']['Hard']}\n\n"
               f"**Algorithms Used:**\n" +
               "\n".join([f"🧠 {algo}: {count} cards" for algo, count in stats['algorithm_breakdown'].items()]))

    def _cancel_context(self, user_id: str) -> str:
        """Cancel any active context"""
        if user_id in self.user_contexts:
            del self.user_contexts[user_id]
        return "❌ **Cancelled**\n\nType /help to see available commands."

    def _get_help_message(self) -> str:
        """Get the help message with all available commands"""
        return ("🤖 **Available Commands:**\n\n"
               "**📚 Flashcards:**\n"
               "• `new card` - Create a new flashcard\n"
               "• `review` or `study` - Start reviewing due cards\n"
               "• `/create_deck <name>` - Create a new deck\n"
               "• `/decks` - List your decks\n"
               "• `/stats` - Show your flashcard statistics\n"
               "• `cancel` - Cancel current operation\n\n"
               "**🔍 Knowledge Base:**\n"
               "• `/search <query>` - Search knowledge base\n"
               "• `/add <fact>` - Add a new fact\n\n"
               "**💡 Tips:**\n"
               "• Just say 'new card' to create flashcards quickly\n"
               "• Say 'review' anytime to study your due cards\n"
               "• The system uses spaced repetition for optimal learning!")


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