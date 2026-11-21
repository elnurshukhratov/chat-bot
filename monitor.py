"""Telegram heartbeat monitoring for userbot status."""

import asyncio
import time
from datetime import timedelta
from typing import Optional
from telethon.errors import FloodWaitError, MessageIdInvalidError, MessageNotModifiedError
from logging_config import get_logger

logger = get_logger(__name__)


class HeartbeatMonitor:
    """Monitor userbot health and send periodic status updates to Telegram."""

    def __init__(self, userbot, database, config):
        """
        Initialize heartbeat monitor.

        Args:
            userbot: TelegramUserbot instance
            database: Database instance
            config: Config instance
        """
        self.userbot = userbot
        self.database = database
        self.config = config
        self.monitor_enabled = False
        self.monitor_task: Optional[asyncio.Task] = None
        self.monitor_chat_id: Optional[int] = None
        self.monitor_message_id: Optional[int] = None
        self.interval_seconds = 180  # Default 3 minutes

    async def initialize(self) -> None:
        """Load monitoring settings from database."""
        enabled = await self.database.get_setting('monitor_enabled')
        self.monitor_enabled = enabled == '1' if enabled else False

        chat_id = await self.database.get_setting('monitor_chat_id')
        self.monitor_chat_id = int(chat_id) if chat_id else None

        msg_id = await self.database.get_setting('monitor_message_id')
        self.monitor_message_id = int(msg_id) if msg_id else None

        interval = await self.database.get_setting('monitor_interval')
        self.interval_seconds = int(interval) if interval else 180

        logger.info(
            f"Monitor initialized: enabled={self.monitor_enabled}, "
            f"chat_id={self.monitor_chat_id}, "
            f"interval={self.interval_seconds}s"
        )

    async def start_monitoring(self, chat_id: int) -> str:
        """
        Start heartbeat monitoring.

        Args:
            chat_id: Chat ID to send status messages

        Returns:
            Status message in Uzbek
        """
        if self.monitor_task and not self.monitor_task.done():
            return "⚠️ **Monitor allaqachon ishlayapti**"

        self.monitor_chat_id = chat_id
        self.monitor_enabled = True

        # Save settings
        await self.database.set_setting('monitor_enabled', '1')
        await self.database.set_setting('monitor_chat_id', str(chat_id))
        await self.database.set_setting('monitor_interval', str(self.interval_seconds))

        # Send initial status
        await self._send_status_update(initial=True)

        # Start background task
        self.monitor_task = asyncio.create_task(self._monitoring_loop())

        logger.info(f"Monitoring started for chat {chat_id}")
        return f"✅ **Monitor yoqildi**\n\n📍 Chat: `{chat_id}`\n⏱️ Interval: {self.interval_seconds}s"

    async def stop_monitoring(self) -> str:
        """
        Stop heartbeat monitoring.

        Returns:
            Status message in Uzbek
        """
        if not self.monitor_enabled:
            return "ℹ️ **Monitor ishlamayapti**"

        self.monitor_enabled = False
        await self.database.set_setting('monitor_enabled', '0')

        if self.monitor_task and not self.monitor_task.done():
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass

        logger.info("Monitoring stopped")
        return "⏸️ **Monitor to'xtatildi**"

    async def get_status(self) -> str:
        """
        Get monitoring status.

        Returns:
            Status message in Uzbek
        """
        if not self.monitor_enabled:
            return "ℹ️ **Monitor o'chirilgan**\n\nYoqish: `/monitor_on`"

        status = (
            f"✅ **Monitor ishlayapti**\n\n"
            f"📍 Chat ID: `{self.monitor_chat_id}`\n"
            f"⏱️ Interval: {self.interval_seconds}s\n"
        )

        if self.monitor_message_id:
            status += f"📨 Message ID: `{self.monitor_message_id}`\n"

        status += f"\nO'chirish: `/monitor_off`"
        return status

    async def set_interval(self, seconds: int) -> str:
        """
        Set monitoring interval.

        Args:
            seconds: Interval in seconds (minimum 60)

        Returns:
            Status message in Uzbek
        """
        if seconds < 60:
            return "❌ **Interval kamida 60 soniya bo'lishi kerak**"

        self.interval_seconds = seconds
        await self.database.set_setting('monitor_interval', str(seconds))

        logger.info(f"Monitor interval set to {seconds}s")
        return f"✅ **Interval o'zgartirildi:** {seconds}s"

    def _format_status_message(self) -> str:
        """
        Format current status message.

        Returns:
            Formatted status message
        """
        # AI status
        ai_status = "✅ Yoqilgan" if self.config.ai_enabled else "⏸️ O'chirilgan"

        # Telegram connection
        client_ok = self.userbot.client and self.userbot.client.is_connected()
        telegram_status = "✅ Ulangan" if client_ok else "❌ Uzilgan"

        # Database status
        db_ok = self.database.db is not None
        db_status = "✅ Ishlayapti" if db_ok else "❌ Xato"

        # Uptime
        uptime_sec = int(time.time() - self.config.start_time) if self.config.start_time > 0 else 0
        uptime_str = str(timedelta(seconds=uptime_sec))

        # Current time
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")

        status_msg = (
            f"🤖 **Telegram AI Userbot**\n\n"
            f"**Holat:** 🟢 Onlayn\n"
            f"**AI:** {ai_status}\n"
            f"**Telegram:** {telegram_status}\n"
            f"**Database:** {db_status}\n"
            f"**Model:** {self.config.openrouter_model}\n\n"
            f"**⏱️ Ishlash vaqti:** {uptime_str}\n"
            f"**🕒 Tekshirildi:** {current_time}"
        )

        return status_msg

    async def _send_status_update(self, initial: bool = False) -> None:
        """
        Send or update status message.

        Args:
            initial: Whether this is the first message
        """
        if not self.monitor_chat_id:
            logger.warning("No monitor chat ID configured")
            return

        try:
            status_text = self._format_status_message()

            # Try to edit existing message
            if not initial and self.monitor_message_id:
                try:
                    await self.userbot.client.edit_message(
                        self.monitor_chat_id,
                        self.monitor_message_id,
                        status_text
                    )
                    logger.debug(f"Status message updated: {self.monitor_message_id}")
                    return
                except (MessageIdInvalidError, MessageNotModifiedError) as e:
                    logger.info(f"Cannot edit message, sending new one: {e}")
                    self.monitor_message_id = None

            # Send new message
            sent_msg = await self.userbot.client.send_message(
                self.monitor_chat_id,
                status_text
            )
            self.monitor_message_id = sent_msg.id
            await self.database.set_setting('monitor_message_id', str(sent_msg.id))
            logger.info(f"New status message sent: {sent_msg.id}")

        except FloodWaitError as e:
            logger.warning(f"FloodWait error: must wait {e.seconds}s")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            logger.error(f"Failed to send status update: {e}", exc_info=True)

    async def _monitoring_loop(self) -> None:
        """Background task that sends periodic status updates."""
        logger.info("Monitoring loop started")

        try:
            while self.monitor_enabled:
                await asyncio.sleep(self.interval_seconds)

                if not self.monitor_enabled:
                    break

                await self._send_status_update(initial=False)

        except asyncio.CancelledError:
            logger.info("Monitoring loop cancelled")
            raise
        except Exception as e:
            logger.error(f"Monitoring loop error: {e}", exc_info=True)
            self.monitor_enabled = False
            await self.database.set_setting('monitor_enabled', '0')
