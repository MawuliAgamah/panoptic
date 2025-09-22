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
        """Send startup message with help and due flashcards"""
        try:
            # Use the chat_id as the user_id for flashcard service
            user_id = self.chat_id

            # First, send the help message to show what the bot can do
            help_message = self.message_handler._get_help_message()
            await self.send_message(help_message)

            # Then check for due cards and provide personalized info
            flashcard_client = self.message_handler.flashcard_client
            due_cards_result = flashcard_client.get_due_cards(user_id, limit=1)
            stats_result = flashcard_client.get_user_stats(user_id)
            
            if not due_cards_result.success or not stats_result.success:
                # Fallback if we can't get flashcard data
                fallback_message = (
                    f"\n\n🎯 **Quick Start:**\n"
                    f"• Type `/new_card` to create your first flashcard\n"
                    f"• Type `review` to start studying\n"
                    f"• Type `stats` to see your progress"
                )
                await self.send_message(fallback_message)
                return
                
            due_cards = due_cards_result.data
            stats = stats_result.data

            # Send personalized status message
            if due_cards:
                status_message = (
                    f"📚 **Your Study Status:**\n\n"
                    f"🔄 **{len(due_cards)} cards due for review!**\n"
                    f"📊 **Total cards:** {stats['total_cards']}\n"
                    f"📅 **Reviewed today:** {stats['cards_reviewed_today']}\n\n"
                    f"💡 **Ready to study?** Type `review` to start your review session!"
                )
            elif stats['total_cards'] > 0:
                status_message = (
                    f"📚 **Your Study Status:**\n\n"
                    f"🎉 **All caught up!** No cards due for review right now.\n"
                    f"📊 **Total cards:** {stats['total_cards']}\n"
                    f"📅 **Reviewed today:** {stats['cards_reviewed_today']}\n\n"
                    f"💡 **What's next?** Type `/new_card` to create more flashcards!"
                )
            else:
                status_message = (
                    f"📚 **Your Study Status:**\n\n"
                    f"🆕 **Welcome!** You don't have any flashcards yet.\n\n"
                    f"💡 **Get started:** Type `/new_card` to create your first flashcard!"
                )

            await self.send_message(status_message)

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