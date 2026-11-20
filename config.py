"""Configuration management for the Telegram AI Userbot."""

import os
import sys
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration."""

    def __init__(self):
        """Initialize configuration from environment variables."""
        self.telegram_api_id: Optional[int] = self._get_int('TELEGRAM_API_ID')
        self.telegram_api_hash: Optional[str] = os.getenv('TELEGRAM_API_HASH')
        self.telegram_session: Optional[str] = os.getenv('TELEGRAM_SESSION')

        self.openrouter_api_key: Optional[str] = os.getenv('OPENROUTER_API_KEY')
        self.openrouter_model: str = os.getenv('OPENROUTER_MODEL', 'anthropic/claude-3.5-sonnet')

        self.ai_system_prompt: str = os.getenv(
            'AI_SYSTEM_PROMPT',
            "You are an AI assistant replying on behalf of the Telegram account owner. "
            "Write naturally, casually and conversationally. "
            "Use the language of the incoming message. "
            "Keep replies concise and relevant. "
            "Avoid robotic expressions. "
            "Do not invent personal facts, promises, decisions or experiences. "
            "If you do not know something about the account owner, do not pretend that you do. "
            "Do not send sensitive information or make commitments on behalf of the owner."
        )
        self.ai_temperature: float = float(os.getenv('AI_TEMPERATURE', '0.7'))
        self.ai_max_tokens: int = int(os.getenv('AI_MAX_TOKENS', '500'))

        self.conversation_history_limit: int = int(os.getenv('CONVERSATION_HISTORY_LIMIT', '20'))
        self.response_cooldown_seconds: int = int(os.getenv('RESPONSE_COOLDOWN_SECONDS', '5'))

        self.database_path: str = os.getenv('DATABASE_PATH', '/var/data/database.sqlite3')
        self.session_path: str = os.getenv('SESSION_PATH', '/var/data/telegram.session')
        self.log_level: str = os.getenv('LOG_LEVEL', 'INFO')

        self.ai_enabled: bool = True

    def _get_int(self, key: str) -> Optional[int]:
        """Get integer value from environment variable."""
        value = os.getenv(key)
        if value:
            try:
                return int(value)
            except ValueError:
                return None
        return None

    def validate(self) -> tuple[bool, list[str]]:
        """
        Validate required configuration.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        if not self.telegram_api_id:
            errors.append("TELEGRAM_API_ID is required")

        if not self.telegram_api_hash:
            errors.append("TELEGRAM_API_HASH is required")

        if not self.telegram_session:
            errors.append("TELEGRAM_SESSION is required")

        if not self.openrouter_api_key:
            errors.append("OPENROUTER_API_KEY is required")

        if not self.openrouter_model:
            errors.append("OPENROUTER_MODEL is required")

        if self.ai_temperature < 0 or self.ai_temperature > 2:
            errors.append("AI_TEMPERATURE must be between 0 and 2")

        if self.ai_max_tokens < 1:
            errors.append("AI_MAX_TOKENS must be positive")

        if self.conversation_history_limit < 1:
            errors.append("CONVERSATION_HISTORY_LIMIT must be positive")

        return len(errors) == 0, errors

    def ensure_data_directories(self) -> None:
        """Ensure data directories exist."""
        for path in [self.database_path, self.session_path]:
            directory = Path(path).parent
            directory.mkdir(parents=True, exist_ok=True)


config = Config()
