from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import sys
import os

# Add the src directory to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
sys.path.insert(0, src_dir)

from services.knowledge_store import JsonKnowledgeStore
from knowledge_graph import create_json_client
from flashcards import create_flashcard_client


class MessageHandler:
    def __init__(self):
        self.knowledge_store = JsonKnowledgeStore()
        self.kg_client = create_json_client()
        self.flashcard_client = create_flashcard_client(enable_anki=False)
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

        # Flashcard commands (case-insensitive and with/without slash)
        elif message.lower() in ['/new_card', 'new_card', 'new card', '/newcard', 'newcard']:
            return self._start_card_creation(user_id)

        elif message.lower() in ['review', '/review', 'study', '/study']:
            return self._start_review_session(user_id)

        elif message.lower().startswith('/create_deck ') or message.lower().startswith('create_deck '):
            # Handle both /create_deck and create_deck
            if message.lower().startswith('/create_deck '):
                deck_name = message[13:]  # Remove '/create_deck '
            else:
                deck_name = message[12:]  # Remove 'create_deck '
            return self._create_deck(user_id, deck_name)

        elif message.lower() in ['/flashcard_stats', '/stats', 'flashcard_stats', 'stats']:
            return self._get_flashcard_stats(user_id)

        elif message.lower() in ['/decks', 'decks']:
            return self._list_decks(user_id)

        elif message.lower() in ['cancel', '/cancel']:
            return self._cancel_context(user_id)

        elif message.lower() in ['/exit_review', 'exit_review', 'exit review']:
            return self._exit_review_session(user_id)

        elif message.lower() in ['/help', 'help']:
            print("Processing help command")
            return self._get_help_message()
        elif message.lower() in ['/kg_info', 'kg_info', 'kg info']:
            return self._get_knowledge_graph_info()

        else:
            print("No command matched, returning echo")
            return f"You said: {message}\nType /help for available commands"

    def _start_card_creation(self, user_id: str) -> str:
        """Start the card creation process"""
        # Check if user has any decks
        decks_result = self.flashcard_client.get_user_decks(user_id)
        
        if not decks_result.success:
            return f"❌ Failed to check decks: {decks_result.error}"

        if not decks_result.data:
            # Create a default deck
            deck_result = self.flashcard_client.create_deck(user_id, "My Flashcards", "Personal flashcard collection")
            if not deck_result.success:
                return f"❌ Failed to create default deck: {deck_result.error}"

        self.user_contexts[user_id] = {
            'state': 'creating_card',
            'step': 'question'
        }

        return ("📝 **Create New Flashcard**\n\n"
                "**Step 1/3: Question**\n"
                "Please enter the **question** or **front** of the card:\n\n"
                "💡 **Tip:** Make your question clear and specific!")

    def _handle_card_creation(self, message: str, user_id: str, context: Dict[str, Any]) -> str:
        """Handle the card creation process"""
        step = context.get('step')

        if step == 'question':
            # Store the question and ask for answer
            self.user_contexts[user_id].update({
                'step': 'answer',
                'question': message
            })
            return (f"✅ **Step 1/3 Complete!**\n"
                   f"**Question:** {message}\n\n"
                   f"**Step 2/3: Answer**\n"
                   f"Now enter the **answer** or **back** of the card:\n\n"
                   f"💡 **Tip:** Make your answer clear and comprehensive!")

        elif step == 'answer':
            # Store the answer and ask for domains
            self.user_contexts[user_id].update({
                'step': 'domains',
                'answer': message
            })
            return (f"✅ **Step 2/3 Complete!**\n"
                   f"**Answer:** {message}\n\n"
                   f"**Step 3/3: Topic/Domain**\n"
                   f"Choose a topic for this card:\n\n"
                   f"**Quick Options:**\n"
                   f"• Type `1` for **Programming** (python, javascript, etc.)\n"
                   f"• Type `2` for **General Knowledge** (facts, trivia, etc.)\n"
                   f"• Type `3` for **Language Learning** (vocabulary, grammar, etc.)\n"
                   f"• Type `4` for **Science** (biology, physics, chemistry, etc.)\n"
                   f"• Type `5` for **History** (events, dates, people, etc.)\n"
                   f"• Type `6` for **Mathematics** (formulas, concepts, etc.)\n\n"
                   f"**Custom:** Or type your own topics (comma-separated)\n"
                   f"Example: `python, algorithms, data-structures`")

        elif step == 'domains':
            # Create the flashcard
            question = context['question']
            answer = context['answer']
            
            # Parse domains based on user input
            domains = self._parse_domain_input(message)

            # Create the card
            card_result = self.flashcard_client.create_card(
                user_id=user_id,
                front=question,
                back=answer,
                domains=domains
            )

            # Clear context
            self._cancel_context(user_id)

            if card_result.success:
                card_data = card_result.data
                return (f"🎉 **Flashcard Created Successfully!**\n\n"
                       f"📝 **Question:** {question}\n"
                       f"💡 **Answer:** {answer}\n"
                       f"🏷️ **Topics:** {', '.join(domains)}\n"
                       f"🔄 **Algorithm:** {card_data['algorithm']}\n"
                       f"⚡ **Ease Factor:** {card_data['ease_factor']}\n\n"
                       f"**What's next?**\n"
                       f"• Type `/new_card` to create another card\n"
                       f"• Type `review` to start studying\n"
                       f"• Type `stats` to see your progress!")
            else:
                return f"❌ Failed to create flashcard: {card_result.error}"

        return "❌ Something went wrong. Please try 'new card' again."

    def _parse_domain_input(self, message: str) -> list:
        """Parse domain input from user message"""
        message = message.strip()
        
        # Handle quick options (1-6)
        quick_options = {
            '1': ['programming', 'python', 'javascript', 'coding'],
            '2': ['general-knowledge', 'facts', 'trivia', 'general'],
            '3': ['language-learning', 'vocabulary', 'grammar', 'languages'],
            '4': ['science', 'biology', 'physics', 'chemistry'],
            '5': ['history', 'events', 'dates', 'historical'],
            '6': ['mathematics', 'math', 'formulas', 'calculus']
        }
        
        if message in quick_options:
            return quick_options[message]
        
        # Handle custom input (comma-separated)
        if ',' in message:
            domains = [d.strip().lower() for d in message.split(',') if d.strip()]
            return domains if domains else ['general']
        
        # Handle single word/phrase
        if message:
            return [message.strip().lower()]
        
        # Default fallback
        return ['general', 'telegram']

    def _start_review_session(self, user_id: str) -> str:
        """Start a review session"""
        due_cards_result = self.flashcard_client.get_due_cards(user_id, limit=10)  # Get more cards for session
        
        if not due_cards_result.success:
            return f"❌ Failed to get due cards: {due_cards_result.error}"

        due_cards = due_cards_result.data
        if not due_cards:
            stats_result = self.flashcard_client.get_user_stats(user_id)
            if not stats_result.success:
                return f"❌ Failed to get stats: {stats_result.error}"
                
            stats = stats_result.data
            total_cards = stats['total_cards']
            if total_cards == 0:
                return ("📚 **No flashcards to review!**\n\n"
                       "You don't have any flashcards yet.\n"
                       "Type 'new card' to create your first flashcard!")
            else:
                return (f"🎉 **All caught up!**\n\n"
                       f"You have {total_cards} flashcards but none are due for review right now.\n"
                       f"Great job staying on top of your studies! 🌟")

        # Set up review session context with all due cards
        self.user_contexts[user_id] = {
            'state': 'reviewing',
            'due_cards': due_cards,
            'current_card_index': 0,
            'step': 'show_question'
        }
        
        # Get the first card
        card = due_cards[0]

        return (f"📚 **Review Session Started!**\n\n"
               f"**Cards to review:** {len(due_cards)}\n"
               f"**Current card:** 1/{len(due_cards)}\n\n"
               f"**Question:**\n{card['front']}\n\n"
               f"Think about the answer, then reply with any message to see the answer.\n\n"
               f"🔄 **Algorithm:** {card.get('algorithm', 'sm2')}\n"
               f"⚡ **Ease Factor:** {card.get('ease_factor', 2.5)}\n\n"
               f"💡 **Tip:** Type '/exit_review' anytime to stop reviewing.")

    def _handle_card_review(self, message: str, user_id: str, context: Dict[str, Any]) -> str:
        """Handle the card review process"""
        step = context.get('step')
        due_cards = context.get('due_cards', [])
        current_index = context.get('current_card_index', 0)
        
        if current_index >= len(due_cards):
            self._cancel_context(user_id)
            return "🎉 **Review session complete!** All cards have been reviewed."

        current_card = due_cards[current_index]
        card_id = current_card['id']

        if step == 'show_question':
            # Show the answer and ask for quality rating
            quality_scale = {
                1: "Complete blackout",
                2: "Incorrect but remembered something", 
                3: "Correct with serious difficulty",
                4: "Correct after hesitation",
                5: "Perfect recall"
            }
            scale_text = "\n".join([f"**{k}**: {v}" for k, v in quality_scale.items()])

            self.user_contexts[user_id]['step'] = 'rate_quality'

            return (f"💡 **Answer:**\n{current_card['back']}\n\n"
                   f"**How well did you know this?**\n{scale_text}\n\n"
                   f"Reply with a number (1-5):")

        elif step == 'rate_quality':
            # Process the quality rating
            try:
                quality = int(message.strip())

                if not (1 <= quality <= 5):
                    return "❌ Please enter a valid rating (1-5):"

                # Process the review
                review_result = self.flashcard_client.review_card(card_id, quality, user_id=user_id)
                if not review_result.success:
                    return f"❌ Failed to record review: {review_result.error}"

                # Get next review date from result
                next_review_date = review_result.data.get('next_review_date', 'Unknown')

                quality_labels = {
                    1: "Complete blackout",
                    2: "Incorrect but remembered", 
                    3: "Correct with difficulty",
                    4: "Correct after hesitation",
                    5: "Perfect recall"
                }

                # Move to next card
                next_index = current_index + 1
                self.user_contexts[user_id]['current_card_index'] = next_index
                self.user_contexts[user_id]['step'] = 'show_question'

                if next_index >= len(due_cards):
                    # Session complete
                    self._cancel_context(user_id)
                    return (f"✅ **Review recorded!**\n\n"
                           f"**Rating:** {quality} - {quality_labels.get(quality, 'Unknown')}\n"
                           f"**Next review:** {next_review_date}\n\n"
                           f"🎉 **Review session complete!** All {len(due_cards)} cards reviewed!")
                else:
                    # Show next card
                    next_card = due_cards[next_index]
                    return (f"✅ **Review recorded!**\n\n"
                           f"**Rating:** {quality} - {quality_labels.get(quality, 'Unknown')}\n"
                           f"**Next review:** {next_review_date}\n\n"
                           f"📚 **Next Card:** {next_index + 1}/{len(due_cards)}\n\n"
                           f"**Question:**\n{next_card['front']}\n\n"
                           f"Think about the answer, then reply with any message to see the answer.\n\n"
                           f"🔄 **Algorithm:** {next_card.get('algorithm', 'sm2')}\n"
                           f"⚡ **Ease Factor:** {next_card.get('ease_factor', 2.5)}")

            except ValueError:
                return "❌ Please enter a valid number for your rating:"

        return "❌ Something went wrong. Please try 'review' again."

    def _create_deck(self, user_id: str, deck_name: str) -> str:
        """Create a new deck"""
        deck_result = self.flashcard_client.create_deck(
            user_id=user_id,
            name=deck_name,
            description="Deck created via Telegram",
            algorithm="sm2"
        )

        if deck_result.success:
            deck_data = deck_result.data
            return (f"🗂️ **Deck Created!**\n\n"
                   f"**Name:** {deck_data['name']}\n"
                   f"**Algorithm:** {deck_data['default_algorithm']}\n"
                   f"**ID:** {deck_data['id'][:8]}...\n\n"
                   f"Type 'new card' to add flashcards to this deck!")
        else:
            return f"❌ Failed to create deck '{deck_name}': {deck_result.error}"

    def _list_decks(self, user_id: str) -> str:
        """List all user decks"""
        decks_result = self.flashcard_client.get_user_decks(user_id)
        
        if not decks_result.success:
            return f"❌ Failed to get decks: {decks_result.error}"

        decks = decks_result.data
        if not decks:
            return ("📚 **No decks found**\n\n"
                   "You don't have any flashcard decks yet.\n"
                   "Type '/create_deck <name>' to create your first deck!")

        deck_list = []
        for deck in decks:
            # Note: The new API doesn't have get_deck_stats, so we'll show basic info
            deck_list.append(
                f"🗂️ **{deck['name']}**\n"
                f"   🧠 Algorithm: {deck['default_algorithm']}\n"
                f"   📅 Created: {deck['created_at'][:10]}"  # Just the date
            )

        return "📚 **Your Decks:**\n\n" + "\n\n".join(deck_list)

    def _get_flashcard_stats(self, user_id: str) -> str:
        """Get user flashcard statistics"""
        stats_result = self.flashcard_client.get_user_stats(user_id)
        
        if not stats_result.success:
            return f"❌ Failed to get stats: {stats_result.error}"

        stats = stats_result.data
        if stats['total_cards'] == 0:
            return ("📊 **Your Flashcard Stats**\n\n"
                   "No flashcards yet! Type 'new card' to get started.")

        return (f"📊 **Your Flashcard Stats**\n\n"
               f"📝 **Total Cards:** {stats['total_cards']}\n"
               f"🔄 **Due for Review:** {stats['cards_due']}\n"
               f"📚 **Reviewed Today:** {stats['cards_reviewed_today']}\n"
               f"⚡ **Average Ease Factor:** {stats['average_ease_factor']:.2f}\n\n"
               f"💡 **Tip:** Type 'review' to start studying your due cards!")
    
    def _get_knowledge_graph_info(self) -> str:
        """Get knowledge graph domains and document information"""
        try:
            # Use the knowledge graph client to get summary information
            summary = self.kg_client.get_knowledge_graph_summary()
            
            if "error" in summary:
                return f"❌ Failed to get knowledge graph info: {summary['error']}"
            
            # Extract information from summary
            stats = summary.get('stats', {})
            domains = summary.get('domains', [])
            documents = summary.get('documents', [])
            
            result = f"🧠 **Knowledge Graph Information**\n\n"
            result += f"📊 **Overview:**\n"
            result += f"• Total Entities: {stats.get('total_entities', 0)}\n"
            result += f"• Total Relationships: {stats.get('total_relationships', 0)}\n"
            result += f"• Total Documents: {len(documents)}\n"
            result += f"• Total Domains: {len(domains)}\n\n"
            
            result += f"🏷️ **Available Domains:**\n"
            if domains:
                for domain in domains:
                    result += f"• {domain}\n"
            else:
                result += "• No domains found in metadata\n"
            
            result += f"\n📚 **Documents:**\n"
            for doc in documents:
                result += f"• **{doc['title']}**\n"
                result += f"  ID: {doc['id']}\n"
                result += f"  Entities: {doc['entity_count']}\n"
                
                # Show domains for this document
                doc_domains = doc.get('domains', [])
                if doc_domains:
                    result += f"  Domains: {', '.join(doc_domains)}\n"
                else:
                    result += f"  Domains: None found\n"
                result += f"\n"
            
            return result
            
        except Exception as e:
            return f"❌ Failed to get knowledge graph info: {str(e)}"

    def _cancel_context(self, user_id: str) -> str:
        """Cancel any active context"""
        if user_id in self.user_contexts:
            del self.user_contexts[user_id]
        return "❌ **Cancelled**\n\nType /help to see available commands."

    def _exit_review_session(self, user_id: str) -> str:
        """Exit review session and return to main menu"""
        if user_id in self.user_contexts:
            context = self.user_contexts[user_id]
            if context.get('state') == 'reviewing':
                current_index = context.get('current_card_index', 0)
                total_cards = len(context.get('due_cards', []))
                del self.user_contexts[user_id]
                return (f"🛑 **Review session ended!**\n\n"
                       f"**Progress:** {current_index}/{total_cards} cards reviewed\n"
                       f"Type 'review' to continue later!")
            else:
                del self.user_contexts[user_id]
                return "✅ You're back to the main menu!"
        return "✅ You're back to the main menu!"

    def _get_help_message(self) -> str:
        """Get the help message with all available commands"""
        return ("🤖 **Available Commands:**\n\n"
               "**📚 Flashcards:**\n"
               "• `/new_card` - Create a new flashcard (3-step process)\n"
               "• `review` or `study` - Start reviewing due cards\n"
               "• `/exit_review` - Exit review session anytime\n"
               "• `decks` or `/decks` - List your decks\n"
               "• `stats` or `/stats` - Show your flashcard statistics\n"
               "• `create_deck <name>` - Create a new deck\n"
               "• `cancel` - Cancel current operation\n\n"
               "**🔍 Knowledge Base:**\n"
               "• `/search <query>` - Search knowledge base\n"
               "• `/add <fact>` - Add a new fact\n"
               "• `/kg_info` - Show knowledge graph domains and documents\n\n"
               "**💡 Tips:**\n"
               "• Use `/new_card` for guided card creation with topics\n"
               "• Choose from 6 quick topic categories or create custom ones\n"
               "• Say 'review' anytime to study your due cards\n"
               "• Use `/exit_review` to stop reviewing and return to main menu\n"
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