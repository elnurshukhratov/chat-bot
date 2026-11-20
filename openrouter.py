"""OpenRouter API integration."""

import aiohttp
import asyncio
from typing import List, Dict, Any, Optional
from logging_config import get_logger

logger = get_logger(__name__)


class OpenRouterClient:
    """Client for OpenRouter Chat Completions API."""

    def __init__(
        self,
        api_key: str,
        model: str,
        system_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 500
    ):
        """
        Initialize OpenRouter client.

        Args:
            api_key: OpenRouter API key
            model: Model identifier
            system_prompt: System prompt for the AI
            temperature: Temperature parameter (0-2)
            max_tokens: Maximum tokens in response
        """
        self.api_key = api_key
        self.model = model
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def create_session(self) -> None:
        """Create aiohttp session."""
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def close_session(self) -> None:
        """Close aiohttp session."""
        if self.session:
            await self.session.close()
            self.session = None

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        retry_count: int = 3
    ) -> Optional[str]:
        """
        Generate AI response using OpenRouter API.

        Args:
            messages: Conversation history with role and content
            retry_count: Number of retries for transient failures

        Returns:
            Generated response or None on failure
        """
        if not self.session:
            await self.create_session()

        formatted_messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        formatted_messages.extend(messages)

        payload = {
            "model": self.model,
            "messages": formatted_messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        for attempt in range(retry_count):
            try:
                async with self.session.post(
                    self.base_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        content = data['choices'][0]['message']['content']
                        logger.info(f"Generated AI response (attempt {attempt + 1})")
                        return content.strip()

                    elif response.status == 429:
                        retry_after = int(response.headers.get('Retry-After', 5))
                        logger.warning(f"Rate limited, retrying after {retry_after}s")
                        if attempt < retry_count - 1:
                            await asyncio.sleep(retry_after)
                            continue
                        return None

                    elif response.status in [500, 502, 503, 504]:
                        logger.warning(f"Server error {response.status}, attempt {attempt + 1}/{retry_count}")
                        if attempt < retry_count - 1:
                            await asyncio.sleep(2 ** attempt)
                            continue
                        return None

                    else:
                        error_text = await response.text()
                        logger.error(f"OpenRouter API error {response.status}: {error_text}")
                        return None

            except asyncio.TimeoutError:
                logger.warning(f"Request timeout, attempt {attempt + 1}/{retry_count}")
                if attempt < retry_count - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return None

            except aiohttp.ClientError as e:
                logger.error(f"HTTP client error: {e}")
                if attempt < retry_count - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return None

            except Exception as e:
                logger.error(f"Unexpected error generating response: {e}")
                return None

        return None
