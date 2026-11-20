"""Database management for conversation history and settings."""

import aiosqlite
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from logging_config import get_logger

logger = get_logger(__name__)


class Database:
    """SQLite database manager for the userbot."""

    def __init__(self, db_path: str):
        """
        Initialize database manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.db: Optional[aiosqlite.Connection] = None

    async def connect(self) -> None:
        """Connect to the database and initialize schema."""
        self.db = await aiosqlite.connect(self.db_path)
        self.db.row_factory = aiosqlite.Row
        await self._initialize_schema()
        logger.info(f"Database connected: {self.db_path}")

    async def close(self) -> None:
        """Close database connection."""
        if self.db:
            await self.db.close()
            logger.info("Database connection closed")

    async def _initialize_schema(self) -> None:
        """Create database tables if they don't exist."""
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL UNIQUE,
                chat_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                sender_id INTEGER NOT NULL,
                sender_username TEXT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
            )
        """)

        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS processed_messages (
                message_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (message_id, chat_id)
            )
        """)

        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id INTEGER PRIMARY KEY,
                allowlisted BOOLEAN DEFAULT 0,
                blocklisted BOOLEAN DEFAULT 0,
                last_response_at TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_conversation
            ON messages (conversation_id, created_at DESC)
        """)

        await self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_processed_messages_chat
            ON processed_messages (chat_id, message_id)
        """)

        await self.db.commit()
        logger.info("Database schema initialized")

    async def get_or_create_conversation(self, chat_id: int, chat_type: str) -> int:
        """
        Get existing conversation or create new one.

        Args:
            chat_id: Telegram chat ID
            chat_type: Type of chat (private, group, supergroup, channel)

        Returns:
            Conversation ID
        """
        cursor = await self.db.execute(
            "SELECT id FROM conversations WHERE chat_id = ?",
            (chat_id,)
        )
        row = await cursor.fetchone()

        if row:
            return row['id']

        cursor = await self.db.execute(
            "INSERT INTO conversations (chat_id, chat_type) VALUES (?, ?)",
            (chat_id, chat_type)
        )
        await self.db.commit()
        return cursor.lastrowid

    async def add_message(
        self,
        conversation_id: int,
        message_id: int,
        sender_id: int,
        sender_username: Optional[str],
        role: str,
        content: str
    ) -> None:
        """
        Add a message to conversation history.

        Args:
            conversation_id: Database conversation ID
            message_id: Telegram message ID
            sender_id: Sender's user ID
            sender_username: Sender's username (optional)
            role: Message role (user or assistant)
            content: Message content
        """
        await self.db.execute(
            """
            INSERT INTO messages
            (conversation_id, message_id, sender_id, sender_username, role, content)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (conversation_id, message_id, sender_id, sender_username, role, content)
        )
        await self.db.execute(
            "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (conversation_id,)
        )
        await self.db.commit()

    async def get_conversation_history(
        self,
        conversation_id: int,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get recent conversation history.

        Args:
            conversation_id: Database conversation ID
            limit: Maximum number of messages to retrieve

        Returns:
            List of messages with role and content
        """
        cursor = await self.db.execute(
            """
            SELECT role, content, created_at
            FROM messages
            WHERE conversation_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (conversation_id, limit)
        )
        rows = await cursor.fetchall()

        messages = [
            {
                'role': row['role'],
                'content': row['content'],
                'created_at': row['created_at']
            }
            for row in reversed(rows)
        ]

        return messages

    async def clear_conversation(self, chat_id: int) -> bool:
        """
        Clear conversation history for a chat.

        Args:
            chat_id: Telegram chat ID

        Returns:
            True if conversation was cleared, False if not found
        """
        cursor = await self.db.execute(
            "SELECT id FROM conversations WHERE chat_id = ?",
            (chat_id,)
        )
        row = await cursor.fetchone()

        if not row:
            return False

        await self.db.execute(
            "DELETE FROM messages WHERE conversation_id = ?",
            (row['id'],)
        )
        await self.db.commit()
        return True

    async def is_message_processed(self, message_id: int, chat_id: int) -> bool:
        """
        Check if a message has already been processed.

        Args:
            message_id: Telegram message ID
            chat_id: Telegram chat ID

        Returns:
            True if message was already processed
        """
        cursor = await self.db.execute(
            "SELECT 1 FROM processed_messages WHERE message_id = ? AND chat_id = ?",
            (message_id, chat_id)
        )
        row = await cursor.fetchone()
        return row is not None

    async def mark_message_processed(self, message_id: int, chat_id: int) -> None:
        """
        Mark a message as processed.

        Args:
            message_id: Telegram message ID
            chat_id: Telegram chat ID
        """
        await self.db.execute(
            "INSERT OR IGNORE INTO processed_messages (message_id, chat_id) VALUES (?, ?)",
            (message_id, chat_id)
        )
        await self.db.commit()

    async def cleanup_old_processed_messages(self, days: int = 7) -> None:
        """
        Remove old processed message records.

        Args:
            days: Number of days to keep records
        """
        await self.db.execute(
            "DELETE FROM processed_messages WHERE processed_at < datetime('now', ? || ' days')",
            (f'-{days}',)
        )
        await self.db.commit()

    async def get_user_preferences(self, user_id: int) -> Dict[str, Any]:
        """
        Get user preferences.

        Args:
            user_id: Telegram user ID

        Returns:
            Dictionary with user preferences
        """
        cursor = await self.db.execute(
            "SELECT * FROM user_preferences WHERE user_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()

        if row:
            return {
                'allowlisted': bool(row['allowlisted']),
                'blocklisted': bool(row['blocklisted']),
                'last_response_at': row['last_response_at']
            }

        return {
            'allowlisted': False,
            'blocklisted': False,
            'last_response_at': None
        }

    async def update_last_response_time(self, user_id: int) -> None:
        """
        Update last response timestamp for a user.

        Args:
            user_id: Telegram user ID
        """
        await self.db.execute(
            """
            INSERT INTO user_preferences (user_id, last_response_at)
            VALUES (?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                last_response_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id,)
        )
        await self.db.commit()

    async def set_user_blocklist(self, user_id: int, blocked: bool) -> None:
        """
        Block or unblock a user.

        Args:
            user_id: Telegram user ID
            blocked: True to block, False to unblock
        """
        await self.db.execute(
            """
            INSERT INTO user_preferences (user_id, blocklisted)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                blocklisted = ?,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, int(blocked), int(blocked))
        )
        await self.db.commit()

    async def get_setting(self, key: str) -> Optional[str]:
        """
        Get a setting value.

        Args:
            key: Setting key

        Returns:
            Setting value or None
        """
        cursor = await self.db.execute(
            "SELECT value FROM settings WHERE key = ?",
            (key,)
        )
        row = await cursor.fetchone()
        return row['value'] if row else None

    async def set_setting(self, key: str, value: str) -> None:
        """
        Set a setting value.

        Args:
            key: Setting key
            value: Setting value
        """
        await self.db.execute(
            """
            INSERT INTO settings (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = ?,
                updated_at = CURRENT_TIMESTAMP
            """,
            (key, value, value)
        )
        await self.db.commit()
