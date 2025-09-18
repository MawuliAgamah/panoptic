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