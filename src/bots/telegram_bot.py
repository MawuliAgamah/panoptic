import os
import asyncio
import logging
from typing import Optional
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

from .base import BaseBot

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class TelegramBot(BaseBot):
    def __init__(self):
        super().__init__()
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.bot_number = os.getenv("TELEGRAM_BOT_NUMBER")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")

        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set")
        if not self.bot_number:
            raise ValueError("TELEGRAM_BOT_NUMBER environment variable is not set")
        if not self.chat_id:
            raise ValueError("TELEGRAM_CHAT_ID environment variable is not set")

        self.application: Optional[Application] = None

    async def start(self) -> None:
        self.application = Application.builder().token(self.token).build()

        message_handler = MessageHandler(filters.TEXT, self._handle_telegram_message)
        self.application.add_handler(message_handler)

        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()

        self.is_running = True
        logger.info("Telegram bot started successfully")

        # Send startup message with due flashcards
        await self._send_startup_message()

    async def stop(self) -> None:
        if self.application:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()

        self.is_running = False
        logger.info("Telegram bot stopped")

    async def send_message(self, message: str, recipient: str = None) -> bool:
        if not self.application:
            logger.error("Bot not started")
            return False

        try:
            chat_id = recipient or self.chat_id
            await self.application.bot.send_message(chat_id=chat_id, text=message)
            logger.info(f"Message sent to {chat_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False

    async def _handle_telegram_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.message.text:
            return

        user_id = str(update.effective_user.id)
        message_text = update.message.text

        response = self.handle_message(message_text, user_id)

        await update.message.reply_text(response)
        logger.info(f"Responded to user {user_id} with: {response}")

    async def _send_startup_message(self) -> None:
        """Send startup message with due flashcards"""
        try:
            # Use the chat_id as the user_id for flashcard service
            user_id = self.chat_id

            # Get flashcard service from message handler
            flashcard_service = self.message_handler.flashcard_service

            # Check for due cards
            due_cards = flashcard_service.get_due_cards(user_id, limit=1)
            stats = flashcard_service.get_user_stats(user_id)

            if due_cards:
                # Start review session automatically
                card = due_cards[0]

                startup_message = (
                    f"🤖 **Bot Started!**\n\n"
                    f"📚 **Time to study!** You have {len(flashcard_service.get_due_cards(user_id))} cards due for review.\n\n"
                    f"**Here's your first card:**\n\n"
                    f"**Question:**\n{card.front}\n\n"
                    f"Think about the answer, then reply with any message to see the answer.\n\n"
                    f"Algorithm: {card.scheduling.algorithm_name}"
                )

                # Set up review context for this user
                self.message_handler.user_contexts[user_id] = {
                    'state': 'reviewing',
                    'card_id': card.card_id,
                    'step': 'show_question'
                }

            elif stats['total_cards'] > 0:
                # User has cards but none due
                startup_message = (
                    f"🤖 **Bot Started!**\n\n"
                    f"🎉 **All caught up!** You have {stats['total_cards']} flashcards but none are due for review right now.\n"
                    f"Great job staying on top of your studies! 🌟\n\n"
                    f"💡 Type 'new card' to create more flashcards or 'review' to study."
                )
            else:
                # No cards at all
                startup_message = (
                    f"🤖 **Bot Started!**\n\n"
                    f"📚 **Welcome to your Flashcard Learning Bot!**\n\n"
                    f"You don't have any flashcards yet. Let's get started!\n\n"
                    f"💡 Type 'new card' to create your first flashcard, or '/help' to see all commands."
                )

            await self.send_message(startup_message)

        except Exception as e:
            logger.error(f"Failed to send startup message: {e}")
            # Send basic startup message as fallback
            fallback_message = (
                f"🤖 **Bot Started!**\n\n"
                f"Ready for flashcard learning! Type '/help' to see available commands."
            )
            await self.send_message(fallback_message)

    async def run_forever(self) -> None:
        await self.start()
        try:
            while self.is_running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            await self.stop()


async def main():
    bot = TelegramBot()
    await bot.run_forever()


if __name__ == '__main__':
    asyncio.run(main())