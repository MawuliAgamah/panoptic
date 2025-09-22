"""Example: How to use improved flashcard service in Telegram bot"""

import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from flashcards.services.improved_flashcard_service import create_flashcard_orchestrator


class FlashcardTelegramBot:
    def __init__(self):
        self.flashcard_orchestrator = create_flashcard_orchestrator(enable_anki=True)
    
    async def handle_flashcard_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /flashcards command"""
        user_id = str(update.effective_user.id)
        
        # Get due cards for user
        session_result = await self._get_study_session(user_id)
        
        if not session_result["success"]:
            await update.message.reply_text(f"Error: {session_result['error']}")
            return
        
        cards = session_result["cards"]
        
        if not cards:
            await update.message.reply_text(
                "🎉 No cards due for review! Great job staying on top of your studies."
            )
            return
        
        # Start study session
        context.user_data['study_session'] = {
            'cards': cards,
            'current_index': 0,
            'session_start': asyncio.get_event_loop().time()
        }
        
        await self._show_current_card(update, context)
    
    async def handle_add_flashcard(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /add command: /add front | back"""
        user_id = str(update.effective_user.id)
        
        # Parse command
        command_text = update.message.text
        if '|' not in command_text:
            await update.message.reply_text(
                "Format: /add What is Python? | A programming language"
            )
            return
        
        try:
            _, content = command_text.split(' ', 1)
            front, back = content.split('|', 1)
            front = front.strip()
            back = back.strip()
        except ValueError:
            await update.message.reply_text("Invalid format. Use: /add question | answer")
            return
        
        # Create flashcard
        result = self.flashcard_orchestrator.create_card(
            user_id=user_id,
            front=front,
            back=back,
            domains=["telegram", "manual"],
            algorithm="sm2"
        )
        
        if result.success:
            card = result.data
            await update.message.reply_text(
                f"✅ Flashcard created!\n\n"
                f"📝 Front: {front}\n"
                f"💡 Back: {back}\n\n"
                f"Card ID: {card.id[:8]}..."
            )
            
            # Optional: Show sync status
            anki_status = "🔄 Syncing to Anki..." if self.flashcard_orchestrator.anki_service else ""
            if anki_status:
                await update.message.reply_text(anki_status)
        else:
            await update.message.reply_text(f"❌ Failed to create flashcard: {result.error}")
    
    async def handle_document_upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle document upload for flashcard generation"""
        user_id = str(update.effective_user.id)
        
        if not update.message.document:
            return
        
        # Download document
        file = await context.bot.get_file(update.message.document.file_id)
        file_path = f"temp/{user_id}_{update.message.document.file_name}"
        await file.download_to_drive(file_path)
        
        await update.message.reply_text("📄 Processing document and generating flashcards...")
        
        # Use your main app logic here
        from examples.main_app_usage import AIModuleApp
        app = AIModuleApp()
        
        result = await app.process_document_with_flashcards(
            document_path=file_path,
            user_id=user_id,
            generate_flashcards=True
        )
        
        if result["success"]:
            await update.message.reply_text(
                f"✅ Document processed!\n"
                f"📚 Created {result['flashcards_created']} flashcards\n"
                f"📝 Type /flashcards to start studying"
            )
        else:
            await update.message.reply_text(f"❌ Processing failed: {result['error']}")
        
        # Clean up temp file
        os.remove(file_path)
    
    async def _show_current_card(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show current card in study session"""
        session = context.user_data.get('study_session')
        if not session:
            return
        
        cards = session['cards']
        current_index = session['current_index']
        
        if current_index >= len(cards):
            await self._end_study_session(update, context)
            return
        
        card = cards[current_index]
        
        # Create inline keyboard for interaction
        keyboard = [
            [InlineKeyboardButton("Show Answer", callback_data=f"show_answer_{card.id}")],
            [InlineKeyboardButton("Skip Card", callback_data=f"skip_card_{card.id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"📚 Card {current_index + 1}/{len(cards)}\n\n"
            f"❓ {card.front}\n\n"
            f"💭 Think about the answer, then click 'Show Answer'",
            reply_markup=reply_markup
        )
    
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button presses during study session"""
        query = update.callback_query
        user_id = str(query.from_user.id)
        
        await query.answer()
        
        if query.data.startswith("show_answer_"):
            card_id = query.data.split("_", 2)[2]
            await self._show_answer(query, context, card_id)
        
        elif query.data.startswith("rate_"):
            # Parse: rate_cardid_quality
            _, card_id, quality = query.data.split("_", 2)
            await self._process_review(query, context, card_id, int(quality))
    
    async def _show_answer(self, query, context: ContextTypes.DEFAULT_TYPE, card_id: str):
        """Show answer and rating buttons"""
        session = context.user_data.get('study_session')
        if not session:
            return
        
        # Find current card
        current_card = None
        for card in session['cards']:
            if card.id == card_id:
                current_card = card
                break
        
        if not current_card:
            return
        
        # Show answer with rating buttons
        keyboard = [
            [
                InlineKeyboardButton("😰 Hard (1)", callback_data=f"rate_{card_id}_1"),
                InlineKeyboardButton("😐 OK (3)", callback_data=f"rate_{card_id}_3"),
                InlineKeyboardButton("😊 Easy (5)", callback_data=f"rate_{card_id}_5")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"❓ {current_card.front}\n\n"
            f"💡 {current_card.back}\n\n"
            f"How well did you know this?",
            reply_markup=reply_markup
        )
    
    async def _process_review(self, query, context: ContextTypes.DEFAULT_TYPE, 
                            card_id: str, quality: int):
        """Process card review and move to next card"""
        user_id = str(query.from_user.id)
        session = context.user_data.get('study_session')
        
        # Calculate response time
        current_time = asyncio.get_event_loop().time()
        response_time = current_time - session.get('card_start_time', current_time)
        
        # Process review
        review_result = self.flashcard_orchestrator.review_card(
            card_id=card_id,
            quality=quality,
            response_time=response_time
        )
        
        if review_result.success:
            # Show feedback
            quality_text = {1: "😰 Hard", 3: "😐 OK", 5: "😊 Easy"}[quality]
            await query.edit_message_text(f"✅ Reviewed as: {quality_text}")
            
            # Move to next card
            session['current_index'] += 1
            context.user_data['study_session'] = session
            
            # Small delay then show next card
            await asyncio.sleep(1)
            
            if session['current_index'] < len(session['cards']):
                await self._show_current_card_callback(query, context)
            else:
                await self._end_study_session_callback(query, context)
        else:
            await query.edit_message_text(f"❌ Review failed: {review_result.error}")
    
    async def _end_study_session(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """End study session and show stats"""
        session = context.user_data.get('study_session', {})
        cards_reviewed = session.get('current_index', 0)
        
        # Get updated stats
        user_id = str(update.effective_user.id)
        stats_result = self.flashcard_orchestrator.get_user_stats(user_id)
        
        if stats_result.success:
            stats = stats_result.data
            await update.message.reply_text(
                f"🎉 Study session complete!\n\n"
                f"📊 Session Stats:\n"
                f"• Cards reviewed: {cards_reviewed}\n"
                f"• Total cards: {stats['total_cards']}\n"
                f"• Cards due: {stats['cards_due']}\n"
                f"• Average ease: {stats['average_ease_factor']:.2f}\n\n"
                f"Great job! 🌟"
            )
        else:
            await update.message.reply_text(f"🎉 Reviewed {cards_reviewed} cards!")
        
        # Clear session
        context.user_data.pop('study_session', None)


# Usage in your telegram bot setup
def setup_flashcard_handlers(application):
    """Add flashcard handlers to your telegram bot"""
    bot_handler = FlashcardTelegramBot()
    
    # Add command handlers
    application.add_handler(CommandHandler("flashcards", bot_handler.handle_flashcard_command))
    application.add_handler(CommandHandler("add", bot_handler.handle_add_flashcard))
    
    # Add document handler
    application.add_handler(MessageHandler(filters.Document.ALL, bot_handler.handle_document_upload))
    
    # Add callback handler for buttons
    application.add_handler(CallbackQueryHandler(bot_handler.handle_callback_query))

    return bot_handler
