"""Message event handler for AI responses."""

import asyncio
from datetime import datetime, timedelta
from telethon import events
from telethon.tl.types import User, Chat, Channel, PeerUser, PeerChat, PeerChannel
from logging_config import get_logger

logger = get_logger(__name__)


class MessageHandler:
    """Handle incoming Telegram messages and generate AI responses."""

    def __init__(self, userbot, database, openrouter_client, config):
        """
        Initialize message handler.

        Args:
            userbot: TelegramUserbot instance
            database: Database instance
            openrouter_client: OpenRouterClient instance
            config: Config instance
        """
        self.userbot = userbot
        self.database = database
        self.openrouter = openrouter_client
        self.config = config
        self.processing_lock = asyncio.Lock()

    async def should_respond(
        self,
        event: events.NewMessage.Event
    ) -> tuple[bool, str]:
        """
        Determine if the bot should respond to a message.

        Args:
            event: Telegram message event

        Returns:
            Tuple of (should_respond, reason)
        """
        # Check if message is a command (starts with /)
        if event.raw_text and event.raw_text.strip().startswith('/'):
            return False, "command message"

        if not self.config.ai_enabled:
            return False, "AI globally disabled"

        if event.out:
            return False, "outgoing message"

        if self.userbot.is_me(event.sender_id):
            return False, "message from self"

        if await self.database.is_message_processed(event.id, event.chat_id):
            return False, "already processed"

        sender = await event.get_sender()
        if sender and getattr(sender, 'bot', False):
            return False, "sender is bot"

        # Check per-chat AI settings
        chat_settings = await self.database.get_chat_settings(event.chat_id)
        if not chat_settings['ai_enabled']:
            return False, "AI disabled for this chat"

        if chat_settings['paused']:
            return False, "AI paused for this chat"

        user_prefs = await self.database.get_user_preferences(event.sender_id)
        if user_prefs['blocklisted']:
            return False, "user blocklisted"

        if user_prefs['last_response_at']:
            last_response = datetime.fromisoformat(user_prefs['last_response_at'])
            cooldown = timedelta(seconds=self.config.response_cooldown_seconds)
            if datetime.now() - last_response < cooldown:
                return False, "cooldown active"

        chat = await event.get_chat()

        if isinstance(chat, User):
            return True, "private chat"

        if isinstance(chat, (Chat, Channel)):
            if not event.mentioned and not event.is_reply:
                return False, "not mentioned or replied to"

            if event.is_reply:
                reply_msg = await event.get_reply_message()
                if reply_msg and not self.userbot.is_me(reply_msg.sender_id):
                    return False, "reply to someone else"

            return True, "mentioned or replied to in group"

        return False, "unknown chat type"

    async def handle_message(self, event: events.NewMessage.Event) -> None:
        """
        Handle incoming message and generate AI response.

        Args:
            event: Telegram message event
        """
        try:
            should_respond, reason = await self.should_respond(event)

            if not should_respond:
                logger.debug(f"Skipping message {event.id} in chat {event.chat_id}: {reason}")
                return

            logger.info(f"Processing message {event.id} from user {event.sender_id} in chat {event.chat_id}: {reason}")

            await self.database.mark_message_processed(event.id, event.chat_id)

            message_text = event.raw_text
            if not message_text or not message_text.strip():
                logger.debug("Empty message text, skipping")
                return

            chat = await event.get_chat()
            chat_type = self._get_chat_type(chat)

            conversation_id = await self.database.get_or_create_conversation(
                event.chat_id,
                chat_type
            )

            sender = await event.get_sender()
            sender_username = getattr(sender, 'username', None)

            await self.database.add_message(
                conversation_id=conversation_id,
                message_id=event.id,
                sender_id=event.sender_id,
                sender_username=sender_username,
                role='user',
                content=message_text
            )

            history = await self.database.get_conversation_history(
                conversation_id,
                self.config.conversation_history_limit
            )

            formatted_messages = self._build_context_aware_messages(
                history,
                message_text,
                sender_username or f"User{event.sender_id}"
            )

            async with self.processing_lock:
                response = await self.openrouter.generate_response(formatted_messages)

            if not response:
                logger.error(f"Failed to generate response for message {event.id}")
                return

            sent_message = await event.reply(response)

            await self.database.add_message(
                conversation_id=conversation_id,
                message_id=sent_message.id,
                sender_id=self.userbot.me.id,
                sender_username=self.userbot.me.username,
                role='assistant',
                content=response
            )

            await self.database.update_last_response_time(event.sender_id)

            logger.info(f"Sent AI response to message {event.id} in chat {event.chat_id}")

        except Exception as e:
            logger.error(f"Error handling message {event.id}: {e}", exc_info=True)

    def _build_context_aware_messages(
        self,
        history: list,
        current_message: str,
        current_sender: str
    ) -> list:
        """
        Build context-aware message list for AI with conversation understanding.

        Args:
            history: List of previous messages with sender info
            current_message: The current incoming message text
            current_sender: Username of current sender

        Returns:
            List of formatted messages for OpenRouter API
        """
        formatted_messages = []

        if len(history) > 1:
            context_summary = self._summarize_recent_context(history)
            if context_summary:
                formatted_messages.append({
                    'role': 'system',
                    'content': f"Recent conversation context: {context_summary}"
                })

        for msg in history:
            content = msg['content']

            if msg['role'] == 'user':
                sender_label = msg.get('sender_username') or f"User{msg.get('sender_id', '')}"
                formatted_messages.append({
                    'role': 'user',
                    'content': f"[{sender_label}]: {content}"
                })
            else:
                formatted_messages.append({
                    'role': 'assistant',
                    'content': content
                })

        formatted_messages.append({
            'role': 'user',
            'content': f"[{current_sender}]: {current_message}"
        })

        return formatted_messages

    def _summarize_recent_context(self, history: list) -> str:
        """
        Summarize recent conversation context to help AI understand the flow.

        Args:
            history: List of previous messages

        Returns:
            Context summary string or empty string
        """
        if len(history) < 2:
            return ""

        recent_messages = history[-5:] if len(history) > 5 else history

        topics = []
        has_questions = False
        has_agreements = False

        for msg in recent_messages:
            content = msg['content'].lower()

            if any(word in content for word in ['?', 'nima', 'qachon', 'qayer', 'kim', 'nega']):
                has_questions = True

            if any(word in content for word in ['ha', "yo'q", 'yaxshi', 'mayli', 'kelishdik', 'ok', "zo'r", 'rostan']):
                has_agreements = True

        context_parts = []
        if has_questions:
            context_parts.append("qoshimcha ma'lumot so'ralgan")
        if has_agreements:
            context_parts.append("kelishuvlar/tasdiqlar mavjud")

        if context_parts:
            return f"Suhbatda {', '.join(context_parts)}. Qisqa javoblarni suhbat kontekstida tushuning."

        return "Davomiy suhbat. Oldingi xabarlarni hisobga oling."

    def _get_chat_type(self, chat) -> str:
        """
        Determine chat type from chat object.

        Args:
            chat: Telegram chat object

        Returns:
            Chat type string
        """
        if isinstance(chat, User):
            return 'private'
        elif isinstance(chat, Chat):
            return 'group'
        elif isinstance(chat, Channel):
            return 'supergroup' if chat.megagroup else 'channel'
        else:
            return 'unknown'

    def register_handler(self, client) -> None:
        """
        Register message handler with Telegram client.

        Args:
            client: TelegramClient instance
        """
        client.add_event_handler(
            self.handle_message,
            events.NewMessage(incoming=True)
        )
        logger.info("Message handler registered")
