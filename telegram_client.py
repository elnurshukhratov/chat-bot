"""Telegram client initialization and management."""

import base64
from telethon import TelegramClient
from telethon.sessions import StringSession
from typing import Optional
from logging_config import get_logger

logger = get_logger(__name__)


class TelegramUserbot:
    """Telegram userbot client manager."""

    def __init__(
        self,
        api_id: int,
        api_hash: str,
        session_string: str
    ):
        """
        Initialize Telegram userbot.

        Args:
            api_id: Telegram API ID
            api_hash: Telegram API hash
            session_string: Base64-encoded session string
        """
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_string = session_string
        self.client: Optional[TelegramClient] = None
        self.me = None

    async def start(self) -> bool:
        """
        Start the Telegram client.

        Returns:
            True if started successfully, False otherwise
        """
        try:
            session = StringSession(self.session_string)
            self.client = TelegramClient(
                session,
                self.api_id,
                self.api_hash,
                connection_retries=5,
                retry_delay=3
            )

            await self.client.connect()

            if not await self.client.is_user_authorized():
                logger.error("Session is not authorized. Please generate a new session.")
                return False

            self.me = await self.client.get_me()
            logger.info(f"Telegram client started: @{self.me.username} (ID: {self.me.id})")
            return True

        except Exception as e:
            logger.error(f"Failed to start Telegram client: {e}")
            return False

    async def stop(self) -> None:
        """Stop the Telegram client."""
        if self.client:
            await self.client.disconnect()
            logger.info("Telegram client stopped")

    def get_client(self) -> TelegramClient:
        """Get the Telegram client instance."""
        return self.client

    def is_me(self, user_id: int) -> bool:
        """
        Check if a user ID belongs to the bot owner.

        Args:
            user_id: User ID to check

        Returns:
            True if the user is the bot owner
        """
        return self.me and user_id == self.me.id


async def create_new_session(api_id: int, api_hash: str, phone: str) -> Optional[str]:
    """
    Create a new Telegram session (for local use only).

    Args:
        api_id: Telegram API ID
        api_hash: Telegram API hash
        phone: Phone number with country code

    Returns:
        Base64-encoded session string or None
    """
    try:
        client = TelegramClient(StringSession(), api_id, api_hash)
        await client.connect()

        if not await client.is_user_authorized():
            await client.send_code_request(phone)
            code = input('Enter the code you received: ')

            try:
                await client.sign_in(phone, code)
            except Exception:
                password = input('Two-factor authentication enabled. Enter your password: ')
                await client.sign_in(password=password)

        session_string = client.session.save()
        await client.disconnect()

        return session_string

    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        return None
