#!/usr/bin/env python3
"""
Main entry point for the AI Module application.
"""
import asyncio
import logging
import sys
from typing import Optional

from bots import get_telegram_bot


async def run_telegram_bot():
    """Run the Telegram bot."""
    try:
        TelegramBot = get_telegram_bot()
        bot = TelegramBot()
        await bot.run_forever()
    except KeyboardInterrupt:
        logging.info("Telegram bot stopped by user")
    except Exception as e:
        logging.error(f"Telegram bot error: {e}")
        raise


async def main():
    """Main application entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    if len(sys.argv) > 1 and sys.argv[1] == "telegram":
        await run_telegram_bot()
    else:
        print("AI Module - Usage:")
        print("  python src/main.py telegram    # Run Telegram bot")
        print("  # Add more options as you build out the application")


if __name__ == "__main__":
    asyncio.run(main())