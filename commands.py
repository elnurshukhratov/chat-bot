"""Command handlers for the userbot."""

from telethon.events import NewMessage
from logging_config import get_logger

logger = get_logger(__name__)


class CommandHandler:
    """Handle userbot commands."""

    def __init__(self, userbot, database, config):
        """
        Initialize command handler.

        Args:
            userbot: TelegramUserbot instance
            database: Database instance
            config: Config instance
        """
        self.userbot = userbot
        self.database = database
        self.config = config

    async def handle_ai_on(self, event: NewMessage.Event) -> None:
        """Enable automatic AI replies."""
        if not self.userbot.is_me(event.sender_id):
            return

        self.config.ai_enabled = True
        await event.reply("✅ AI automatic replies enabled")
        logger.info("AI replies enabled via command")

    async def handle_ai_off(self, event: NewMessage.Event) -> None:
        """Disable automatic AI replies."""
        if not self.userbot.is_me(event.sender_id):
            return

        self.config.ai_enabled = False
        await event.reply("⏸️ AI automatic replies disabled")
        logger.info("AI replies disabled via command")

    async def handle_status(self, event: NewMessage.Event) -> None:
        """Show current status."""
        if not self.userbot.is_me(event.sender_id):
            return

        status = "✅ Enabled" if self.config.ai_enabled else "⏸️ Disabled"
        me = self.userbot.me

        status_message = (
            f"**Telegram AI Userbot Status**\n\n"
            f"Account: @{me.username} (ID: {me.id})\n"
            f"AI Replies: {status}\n"
            f"Model: {self.config.openrouter_model}\n"
            f"History Limit: {self.config.conversation_history_limit} messages\n"
            f"Cooldown: {self.config.response_cooldown_seconds}s"
        )

        await event.reply(status_message)

    async def handle_clear(self, event: NewMessage.Event) -> None:
        """Clear conversation history for current chat."""
        if not self.userbot.is_me(event.sender_id):
            return

        chat_id = event.chat_id
        cleared = await self.database.clear_conversation(chat_id)

        if cleared:
            await event.reply("🗑️ Conversation history cleared")
            logger.info(f"Cleared conversation history for chat {chat_id}")
        else:
            await event.reply("No conversation history found")

    async def handle_help(self, event: NewMessage.Event) -> None:
        """Show help message."""
        if not self.userbot.is_me(event.sender_id):
            return

        help_message = (
            "**Telegram AI Userbot Commands**\n\n"
            "/ai_on - Enable automatic AI replies\n"
            "/ai_off - Disable automatic AI replies\n"
            "/status - Show current status\n"
            "/clear - Clear current conversation history\n"
            "/help - Show this help message\n\n"
            "**How it works:**\n"
            "• Private chats: Responds to all incoming messages\n"
            "• Groups: Responds when mentioned or replied to\n"
            "• Only you can use these commands"
        )

        await event.reply(help_message)

    def register_handlers(self, client) -> None:
        """
        Register command handlers with the Telegram client.

        Args:
            client: TelegramClient instance
        """
        client.add_event_handler(
            self.handle_ai_on,
            NewMessage(pattern=r'^/ai_on$', outgoing=True)
        )

        client.add_event_handler(
            self.handle_ai_off,
            NewMessage(pattern=r'^/ai_off$', outgoing=True)
        )

        client.add_event_handler(
            self.handle_status,
            NewMessage(pattern=r'^/status$', outgoing=True)
        )

        client.add_event_handler(
            self.handle_clear,
            NewMessage(pattern=r'^/clear$', outgoing=True)
        )

        client.add_event_handler(
            self.handle_help,
            NewMessage(pattern=r'^/help$', outgoing=True)
        )

        logger.info("Command handlers registered (outgoing=True for userbot)")
