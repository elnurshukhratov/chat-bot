"""Main entry point for the Telegram AI Userbot."""

import sys
import signal
import asyncio
from config import config
from database import Database
from telegram_client import TelegramUserbot
from openrouter import OpenRouterClient
from message_handler import MessageHandler
from commands import CommandHandler
from logging_config import setup_logging, get_logger

logger = None


async def shutdown(userbot, database, openrouter_client):
    """
    Graceful shutdown handler.

    Args:
        userbot: TelegramUserbot instance
        database: Database instance
        openrouter_client: OpenRouterClient instance
    """
    logger.info("Shutting down...")

    if userbot:
        await userbot.stop()

    if openrouter_client:
        await openrouter_client.close_session()

    if database:
        await database.close()

    logger.info("Shutdown complete")


async def main():
    """Main application entry point."""
    global logger
    logger = setup_logging(config.log_level)

    logger.info("=" * 60)
    logger.info("Telegram AI Userbot Starting")
    logger.info("=" * 60)

    is_valid, errors = config.validate()
    if not is_valid:
        logger.error("Configuration validation failed:")
        for error in errors:
            logger.error(f"  - {error}")
        sys.exit(1)

    logger.info("Configuration validated")

    config.ensure_data_directories()
    logger.info("Data directories ready")

    database = Database(config.database_path)
    await database.connect()

    userbot = TelegramUserbot(
        api_id=config.telegram_api_id,
        api_hash=config.telegram_api_hash,
        session_string=config.telegram_session
    )

    if not await userbot.start():
        logger.error("Failed to start Telegram client. Exiting.")
        await database.close()
        sys.exit(1)

    openrouter_client = OpenRouterClient(
        api_key=config.openrouter_api_key,
        model=config.openrouter_model,
        system_prompt=config.ai_system_prompt,
        temperature=config.ai_temperature,
        max_tokens=config.ai_max_tokens
    )
    await openrouter_client.create_session()

    message_handler = MessageHandler(
        userbot=userbot,
        database=database,
        openrouter_client=openrouter_client,
        config=config
    )

    command_handler = CommandHandler(
        userbot=userbot,
        database=database,
        config=config
    )

    client = userbot.get_client()
    message_handler.register_handler(client)
    command_handler.register_handlers(client)

    logger.info("=" * 60)
    logger.info("Userbot is now running")
    logger.info(f"Account: @{userbot.me.username} (ID: {userbot.me.id})")
    logger.info(f"AI Model: {config.openrouter_model}")
    logger.info(f"AI Status: {'Enabled' if config.ai_enabled else 'Disabled'}")
    logger.info("=" * 60)

    shutdown_event = asyncio.Event()

    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await shutdown_event.wait()
    finally:
        await shutdown(userbot, database, openrouter_client)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        if logger:
            logger.error(f"Fatal error: {e}", exc_info=True)
        else:
            print(f"Fatal error: {e}")
        sys.exit(1)
