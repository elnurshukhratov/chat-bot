"""Command handlers for the userbot - Version 3."""

import time
import asyncio
from datetime import datetime, timedelta
from telethon.events import NewMessage
from telethon import functions
from telethon.tl.types import MessageMediaWebPage
from logging_config import get_logger

logger = get_logger(__name__)


class CommandHandler:
    """Handle userbot commands with Uzbek responses."""

    def __init__(self, userbot, database, openrouter_client, config):
        """
        Initialize command handler.

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
        self.available_models = [
            "anthropic/claude-3.5-sonnet",
            "anthropic/claude-3-opus",
            "anthropic/claude-3-haiku",
            "openai/gpt-4-turbo",
            "openai/gpt-4o",
            "openai/gpt-4o-mini",
            "google/gemini-pro-1.5",
            "meta-llama/llama-3.1-70b-instruct"
        ]

    async def _delete_command_message(self, event: NewMessage.Event) -> None:
        """Safely delete command message if possible."""
        try:
            await asyncio.sleep(0.5)
            await event.delete()
        except Exception as e:
            logger.debug(f"Could not delete command message: {e}")

    # ========== AI MANAGEMENT COMMANDS ==========

    async def handle_ai_on(self, event: NewMessage.Event) -> None:
        """Enable automatic AI replies globally."""
        if not self.userbot.is_me(event.sender_id):
            return
        self.config.ai_enabled = True
        await event.reply("✅ **AI javoblari global yoqildi**")
        logger.info("AI globally enabled")
        await self._delete_command_message(event)

    async def handle_ai_off(self, event: NewMessage.Event) -> None:
        """Disable automatic AI replies globally."""
        if not self.userbot.is_me(event.sender_id):
            return
        self.config.ai_enabled = False
        await event.reply("⏸️ **AI javoblari global o'chirildi**")
        logger.info("AI globally disabled")
        await self._delete_command_message(event)

    async def handle_toggle(self, event: NewMessage.Event) -> None:
        """Toggle AI on/off globally."""
        if not self.userbot.is_me(event.sender_id):
            return
        self.config.ai_enabled = not self.config.ai_enabled
        status = "yoqildi ✅" if self.config.ai_enabled else "o'chirildi ⏸️"
        await event.reply(f"**AI global {status}**")
        await self._delete_command_message(event)

    async def handle_status(self, event: NewMessage.Event) -> None:
        """Show current status."""
        if not self.userbot.is_me(event.sender_id):
            return
        me = self.userbot.me
        status = "✅ Yoqilgan" if self.config.ai_enabled else "⏸️ O'chirilgan"
        uptime_sec = int(time.time() - self.config.start_time) if self.config.start_time > 0 else 0
        uptime_str = str(timedelta(seconds=uptime_sec))
        conv = await self.database.get_conversation_count()
        msgs = await self.database.get_message_count()
        ai_msgs = await self.database.get_ai_message_count()
        status_msg = (
            f"**📊 Telegram AI Userbot V3**\n\n"
            f"**Akkaunt:** @{me.username} (ID: {me.id})\n"
            f"**AI Global:** {status}\n"
            f"**Model:** {self.config.openrouter_model}\n"
            f"**Temperatura:** {self.config.ai_temperature}\n"
            f"**Ishlash vaqti:** {uptime_str}\n\n"
            f"**📈 Statistika:**\n"
            f"Suhbatlar: {conv} | Xabarlar: {msgs} | AI: {ai_msgs}"
        )
        await event.reply(status_msg)
        await self._delete_command_message(event)

    async def handle_model(self, event: NewMessage.Event) -> None:
        """Show current model."""
        if not self.userbot.is_me(event.sender_id):
            return
        await event.reply(f"**Joriy model:** {self.config.openrouter_model}")
        await self._delete_command_message(event)

    async def handle_models(self, event: NewMessage.Event) -> None:
        """List available models."""
        if not self.userbot.is_me(event.sender_id):
            return
        models_text = "**🤖 Mavjud modellar:**\n\n"
        for model in self.available_models:
            marker = "✅" if model == self.config.openrouter_model else "  "
            models_text += f"{marker} `{model}`\n"
        models_text += f"\n**O'zgartirish:** `/setmodel MODEL`"
        await event.reply(models_text)
        await self._delete_command_message(event)

    async def handle_setmodel(self, event: NewMessage.Event) -> None:
        """Set AI model."""
        if not self.userbot.is_me(event.sender_id):
            return
        args = event.raw_text.split(maxsplit=1)
        if len(args) < 2:
            await event.reply("❌ **Model nomini kiriting:** `/setmodel MODEL`")
            await self._delete_command_message(event)
            return
        new_model = args[1].strip()
        self.config.openrouter_model = new_model
        self.openrouter.model = new_model
        await event.reply(f"✅ **Model o'zgartirildi:** `{new_model}`")
        logger.info(f"Model changed to {new_model}")
        await self._delete_command_message(event)

    async def handle_temperature(self, event: NewMessage.Event) -> None:
        """Set or show temperature."""
        if not self.userbot.is_me(event.sender_id):
            return
        args = event.raw_text.split(maxsplit=1)
        if len(args) < 2:
            await event.reply(f"**Joriy temperatura:** {self.config.ai_temperature}\n**O'zgartirish:** `/temperature 0.7`")
            await self._delete_command_message(event)
            return
        try:
            temp = float(args[1].strip())
            if temp < 0 or temp > 2:
                await event.reply("❌ **Temperatura 0.0 va 2.0 orasida bo'lishi kerak**")
            else:
                self.config.ai_temperature = temp
                self.openrouter.temperature = temp
                await event.reply(f"✅ **Temperatura o'zgartirildi:** {temp}")
        except ValueError:
            await event.reply("❌ **Noto'g'ri raqam**")
        await self._delete_command_message(event)

    async def handle_prompt(self, event: NewMessage.Event) -> None:
        """Show current system prompt."""
        if not self.userbot.is_me(event.sender_id):
            return
        preview = self.config.ai_system_prompt[:200]
        if len(self.config.ai_system_prompt) > 200:
            preview += "..."
        await event.reply(f"**💬 System prompt:**\n\n{preview}")
        await self._delete_command_message(event)

    async def handle_setprompt(self, event: NewMessage.Event) -> None:
        """Set system prompt."""
        if not self.userbot.is_me(event.sender_id):
            return
        args = event.raw_text.split(maxsplit=1)
        if len(args) < 2:
            await event.reply("❌ **Promptni kiriting:** `/setprompt MATN`")
            await self._delete_command_message(event)
            return
        new_prompt = args[1].strip()
        self.config.ai_system_prompt = new_prompt
        self.openrouter.system_prompt = new_prompt
        await event.reply(f"✅ **Prompt o'zgartirildi** ({len(new_prompt)} belgi)")
        await self._delete_command_message(event)

    # ========== PER-CHAT AI CONTROL ==========

    async def handle_chat_ai_on(self, event: NewMessage.Event) -> None:
        """Enable AI for current chat."""
        if not self.userbot.is_me(event.sender_id):
            return
        await self.database.set_chat_ai_enabled(event.chat_id, True)
        await event.reply("✅ **Ushbu chat uchun AI yoqildi**")
        await self._delete_command_message(event)

    async def handle_chat_ai_off(self, event: NewMessage.Event) -> None:
        """Disable AI for current chat."""
        if not self.userbot.is_me(event.sender_id):
            return
        await self.database.set_chat_ai_enabled(event.chat_id, False)
        await event.reply("⏸️ **Ushbu chat uchun AI o'chirildi**")
        await self._delete_command_message(event)

    async def handle_chat_ai_toggle(self, event: NewMessage.Event) -> None:
        """Toggle AI for current chat."""
        if not self.userbot.is_me(event.sender_id):
            return
        settings = await self.database.get_chat_settings(event.chat_id)
        new_state = not settings['ai_enabled']
        await self.database.set_chat_ai_enabled(event.chat_id, new_state)
        status = "yoqildi ✅" if new_state else "o'chirildi ⏸️"
        await event.reply(f"**Chat AI {status}**")
        await self._delete_command_message(event)

    async def handle_chat_ai_status(self, event: NewMessage.Event) -> None:
        """Show AI status for current chat."""
        if not self.userbot.is_me(event.sender_id):
            return
        settings = await self.database.get_chat_settings(event.chat_id)
        status = "✅ Yoqilgan" if settings['ai_enabled'] else "⏸️ O'chirilgan"
        paused = "⏸️ Ha" if settings['paused'] else "▶️ Yo'q"
        info = f"**📊 Chat AI Holati**\n\n**Chat ID:** `{event.chat_id}`\n**AI:** {status}\n**Pauza:** {paused}\n"
        if settings['model']:
            info += f"**Model:** `{settings['model']}`\n"
        if settings['temperature'] is not None:
            info += f"**Temperatura:** {settings['temperature']}\n"
        await event.reply(info)
        await self._delete_command_message(event)

    async def handle_chat_info(self, event: NewMessage.Event) -> None:
        """Show chat information."""
        if not self.userbot.is_me(event.sender_id):
            return
        chat = await event.get_chat()
        settings = await self.database.get_chat_settings(event.chat_id)
        chat_name = getattr(chat, 'title', None) or getattr(chat, 'first_name', 'Noma\'lum')
        info = f"**📱 Chat: {chat_name}**\n\n**ID:** `{event.chat_id}`\n**AI:** {'✅ Yoqilgan' if settings['ai_enabled'] else '⏸️ O\'chirilgan'}\n"
        await event.reply(info)
        await self._delete_command_message(event)

    async def handle_chat_clear(self, event: NewMessage.Event) -> None:
        """Clear conversation history for current chat."""
        if not self.userbot.is_me(event.sender_id):
            return
        cleared = await self.database.clear_conversation(event.chat_id)
        msg = "🗑️ **Chat tarixi tozalandi**" if cleared else "ℹ️ **Tarix topilmadi**"
        await event.reply(msg)
        await self._delete_command_message(event)

    # ========== CONVERSATION COMMANDS ==========

    async def handle_clear(self, event: NewMessage.Event) -> None:
        """Clear conversation history."""
        if not self.userbot.is_me(event.sender_id):
            return
        cleared = await self.database.clear_conversation(event.chat_id)
        msg = "🗑️ **Tarix tozalandi**" if cleared else "ℹ️ **Tarix topilmadi**"
        await event.reply(msg)
        await self._delete_command_message(event)

    async def handle_clearall(self, event: NewMessage.Event) -> None:
        """Clear all conversations."""
        if not self.userbot.is_me(event.sender_id):
            return
        count = await self.database.clear_all_conversations()
        await event.reply(f"🗑️ **Barcha tarix tozalandi** ({count} xabar)")
        await self._delete_command_message(event)

    async def handle_history(self, event: NewMessage.Event) -> None:
        """Show conversation history."""
        if not self.userbot.is_me(event.sender_id):
            return
        conv_id = await self.database.get_or_create_conversation(event.chat_id, "unknown")
        history = await self.database.get_conversation_history(conv_id, limit=10)
        if not history:
            await event.reply("ℹ️ **Tarix bo'sh**")
        else:
            text = f"**📜 Oxirgi {len(history)} xabar:**\n\n"
            for msg in history[-5:]:
                icon = "👤" if msg['role'] == 'user' else "🤖"
                preview = msg['content'][:40] + "..." if len(msg['content']) > 40 else msg['content']
                text += f"{icon} {preview}\n"
            await event.reply(text)
        await self._delete_command_message(event)

    async def handle_pause(self, event: NewMessage.Event) -> None:
        """Pause AI for current chat."""
        if not self.userbot.is_me(event.sender_id):
            return
        await self.database.set_chat_paused(event.chat_id, True)
        await event.reply("⏸️ **AI pauza qilindi**")
        await self._delete_command_message(event)

    async def handle_resume(self, event: NewMessage.Event) -> None:
        """Resume AI for current chat."""
        if not self.userbot.is_me(event.sender_id):
            return
        await self.database.set_chat_paused(event.chat_id, False)
        await event.reply("▶️ **AI davom ettirildi**")
        await self._delete_command_message(event)

    # ========== USER MANAGEMENT ==========

    async def handle_block(self, event: NewMessage.Event) -> None:
        """Block a user."""
        if not self.userbot.is_me(event.sender_id):
            return
        args = event.raw_text.split(maxsplit=1)
        if len(args) < 2:
            await event.reply("❌ **User ID:** `/block ID`")
        else:
            try:
                user_id = int(args[1].strip())
                await self.database.set_user_blocklist(user_id, True)
                await event.reply(f"🚫 **Bloklandi:** `{user_id}`")
            except ValueError:
                await event.reply("❌ **Noto'g'ri ID**")
        await self._delete_command_message(event)

    async def handle_unblock(self, event: NewMessage.Event) -> None:
        """Unblock a user."""
        if not self.userbot.is_me(event.sender_id):
            return
        args = event.raw_text.split(maxsplit=1)
        if len(args) < 2:
            await event.reply("❌ **User ID:** `/unblock ID`")
        else:
            try:
                user_id = int(args[1].strip())
                await self.database.set_user_blocklist(user_id, False)
                await event.reply(f"✅ **Blokdan chiqarildi:** `{user_id}`")
            except ValueError:
                await event.reply("❌ **Noto'g'ri ID**")
        await self._delete_command_message(event)

    async def handle_blocked(self, event: NewMessage.Event) -> None:
        """List blocked users."""
        if not self.userbot.is_me(event.sender_id):
            return
        blocked = await self.database.get_all_blocked_users()
        if not blocked:
            await event.reply("ℹ️ **Bloklangan userlar yo'q**")
        else:
            text = f"**🚫 Bloklangan ({len(blocked)}):**\n\n" + "\n".join(f"• `{uid}`" for uid in blocked)
            await event.reply(text)
        await self._delete_command_message(event)

    async def handle_allow(self, event: NewMessage.Event) -> None:
        """Allow a user."""
        if not self.userbot.is_me(event.sender_id):
            return
        args = event.raw_text.split(maxsplit=1)
        if len(args) < 2:
            await event.reply("❌ **User ID:** `/allow ID`")
        else:
            try:
                user_id = int(args[1].strip())
                await self.database.set_user_allowlist(user_id, True)
                await event.reply(f"✅ **Ruxsat berildi:** `{user_id}`")
            except ValueError:
                await event.reply("❌ **Noto'g'ri ID**")
        await self._delete_command_message(event)

    async def handle_deny(self, event: NewMessage.Event) -> None:
        """Deny a user."""
        if not self.userbot.is_me(event.sender_id):
            return
        args = event.raw_text.split(maxsplit=1)
        if len(args) < 2:
            await event.reply("❌ **User ID:** `/deny ID`")
        else:
            try:
                user_id = int(args[1].strip())
                await self.database.set_user_allowlist(user_id, False)
                await event.reply(f"🚫 **Rad etildi:** `{user_id}`")
            except ValueError:
                await event.reply("❌ **Noto'g'ri ID**")
        await self._delete_command_message(event)

    # ========== MONITORING ==========

    async def handle_stats(self, event: NewMessage.Event) -> None:
        """Show statistics."""
        if not self.userbot.is_me(event.sender_id):
            return
        conv = await self.database.get_conversation_count()
        msgs = await self.database.get_message_count()
        ai_msgs = await self.database.get_ai_message_count()
        blocked = len(await self.database.get_all_blocked_users())
        uptime_sec = int(time.time() - self.config.start_time) if self.config.start_time > 0 else 0
        stats = (
            f"**📊 Statistika**\n\n"
            f"**Suhbatlar:** {conv}\n**Xabarlar:** {msgs}\n**AI javoblari:** {ai_msgs}\n"
            f"**Bloklangan:** {blocked}\n**Ishlash vaqti:** {timedelta(seconds=uptime_sec)}"
        )
        await event.reply(stats)
        await self._delete_command_message(event)

    async def handle_uptime(self, event: NewMessage.Event) -> None:
        """Show uptime."""
        if not self.userbot.is_me(event.sender_id):
            return
        uptime_sec = int(time.time() - self.config.start_time) if self.config.start_time > 0 else 0
        await event.reply(f"**⏱️ Ishlash vaqti:** {timedelta(seconds=uptime_sec)}")
        await self._delete_command_message(event)

    async def handle_ping(self, event: NewMessage.Event) -> None:
        """Ping test."""
        if not self.userbot.is_me(event.sender_id):
            return
        start = time.time()
        sent = await event.reply("🏓 Pong!")
        elapsed = (time.time() - start) * 1000
        await sent.edit(f"🏓 **Pong!** `{elapsed:.0f}ms`")
        await self._delete_command_message(event)

    async def handle_health(self, event: NewMessage.Event) -> None:
        """Health check."""
        if not self.userbot.is_me(event.sender_id):
            return
        db_ok = self.database.db is not None
        session_ok = self.openrouter.session is not None
        client_ok = self.userbot.client and self.userbot.client.is_connected()
        health = (
            f"**🏥 Tizim**\n\n**DB:** {'✅' if db_ok else '❌'}\n"
            f"**OpenRouter:** {'✅' if session_ok else '❌'}\n**Telegram:** {'✅' if client_ok else '❌'}"
        )
        await event.reply(health)
        await self._delete_command_message(event)

    # ========== AI TOOLS ==========

    async def handle_ask(self, event: NewMessage.Event) -> None:
        """Ask AI a question."""
        if not self.userbot.is_me(event.sender_id):
            return
        args = event.raw_text.split(maxsplit=1)
        if len(args) < 2:
            await event.reply("❌ **Savol:** `/ask SAVOL`")
        else:
            try:
                response = await self.openrouter.generate_response([{'role': 'user', 'content': args[1].strip()}])
                await event.reply(f"**🤖 AI:**\n\n{response}" if response else "❌ **Xato**")
            except Exception as e:
                await event.reply(f"❌ **Xato:** {str(e)}")
        await self._delete_command_message(event)

    async def handle_language(self, event: NewMessage.Event) -> None:
        """Set language for current chat."""
        if not self.userbot.is_me(event.sender_id):
            return
        args = event.raw_text.split(maxsplit=1)
        if len(args) < 2:
            await event.reply("❌ **Til kodi:** `/language uz`")
        else:
            lang = args[1].strip().lower()
            await self.database.set_chat_language(event.chat_id, lang)
            await event.reply(f"✅ **Til:** `{lang}`")
        await self._delete_command_message(event)

    async def handle_help(self, event: NewMessage.Event) -> None:
        """Show help."""
        if not self.userbot.is_me(event.sender_id):
            return

        # Check if user wants help for a specific command
        args = event.raw_text.split(maxsplit=1)
        if len(args) > 1:
            cmd = args[1].strip().lower().replace('/', '')
            await self._show_command_help(event, cmd)
            await self._delete_command_message(event)
            return

        help_msg = (
            "**🤖 AI Userbot V3**\n\n"
            "**AI Boshqaruv:**\n"
            "/ai_on - AI ni yoqish\n"
            "/ai_off - AI ni o'chirish\n"
            "/toggle - AI holatini o'zgartirish\n"
            "/status - To'liq holat\n"
            "/model - Joriy model\n"
            "/models - Modellar ro'yxati\n"
            "/setmodel - Model o'zgartirish\n"
            "/temperature - Temperatura\n"
            "/prompt - System prompt\n"
            "/setprompt - Promptni o'zgartirish\n\n"
            "**Chat AI:**\n"
            "/chat_ai_on - Chat uchun yoqish\n"
            "/chat_ai_off - Chat uchun o'chirish\n"
            "/chat_ai_toggle - Chat holatini o'zgartirish\n"
            "/chat_ai_status - Chat holati\n"
            "/chat_info - Chat ma'lumotlari\n"
            "/chat_clear - Chat tarixini tozalash\n\n"
            "**Suhbat:**\n"
            "/clear - Tarixni tozalash\n"
            "/clearall - Hammani tozalash\n"
            "/history - Tarix\n"
            "/pause - Pauza\n"
            "/resume - Davom ettirish\n\n"
            "**User Boshqaruv:**\n"
            "/block - Bloklash\n"
            "/unblock - Blokdan chiqarish\n"
            "/blocked - Bloklangan ro'yxat\n"
            "/allow - Ruxsat berish\n"
            "/deny - Rad etish\n\n"
            "**Monitoring:**\n"
            "/stats - Statistika\n"
            "/uptime - Ishlash vaqti\n"
            "/ping - Ping test\n"
            "/health - Tizim holati\n\n"
            "**AI Vositalari:**\n"
            "/ask - AI ga savol\n"
            "/language - Til\n"
            "/reply - AI javob yaratish\n\n"
            "**Tarjima:**\n"
            "/en - Inglizchaga\n"
            "/ru - Ruschaga\n\n"
            "**Matn Tahriri:**\n"
            "/fix - Xatolarni tuzatish\n"
            "/formal - Rasmiy uslub\n"
            "/short - Qisqartirish\n"
            "/pro - Professional\n"
            "/emoji - Emoji qo'shish\n"
            "/clean - Tozalash\n\n"
            "**Telegram:**\n"
            "/copy - Nusxalash\n"
            "/pin - Qadash\n"
            "/del - O'chirish\n"
            "/me - Profilim\n"
            "/id - ID lar\n"
            "/link - Chat havolasi\n"
            "/undo - Oxirgi xabarni qaytarish\n\n"
            "**Batafsil:** `/help BUYRUQ`"
        )
        await event.reply(help_msg)
        await self._delete_command_message(event)

    async def _show_command_help(self, event: NewMessage.Event, cmd: str) -> None:
        """Show detailed help for a specific command."""
        help_texts = {
            'en': '**Tarjima qilish (Inglizcha)**\n\nFoydalanish: `/en MATN` yoki xabarga javob sifatida `/en`\n\nMatnni ingliz tiliga tarjima qilib yuboradi.',
            'ru': '**Tarjima qilish (Ruscha)**\n\nFoydalanish: `/ru MATN` yoki xabarga javob sifatida `/ru`\n\nMatnni rus tiliga tarjima qilib yuboradi.',
            'fix': '**Xatolarni tuzatish**\n\nFoydalanish: `/fix MATN` yoki xabarga javob sifatida `/fix`\n\nImlo va grammatika xatolarini tuzatadi.',
            'formal': '**Rasmiy uslub**\n\nFoydalanish: `/formal MATN` yoki xabarga javob sifatida `/formal`\n\nMatnni rasmiy uslubda qayta yozadi.',
            'short': '**Qisqartirish**\n\nFoydalanish: `/short MATN` yoki xabarga javob sifatida `/short`\n\nMatnni qisqaroq qiladi.',
            'pro': '**Professional**\n\nFoydalanish: `/pro MATN` yoki xabarga javob sifatida `/pro`\n\nMatnni professional uslubda yozadi.',
            'emoji': '**Emoji qo\'shish**\n\nFoydalanish: `/emoji MATN` yoki xabarga javob sifatida `/emoji`\n\nMatnga mos emojilar qo\'shadi.',
            'clean': '**Tozalash**\n\nFoydalanish: `/clean MATN` yoki xabarga javob sifatida `/clean`\n\nKeraksiz belgilarni tozalaydi.',
            'copy': '**Nusxalash**\n\nFoydalanish: Xabarga javob sifatida `/copy`\n\nJavob berilgan xabarni nusxalaydi.',
            'pin': '**Qadash**\n\nFoydalanish: Xabarga javob sifatida `/pin`\n\nXabarni qadar (ruxsat bo\'lsa).',
            'del': '**O\'chirish**\n\nFoydalanish: O\'z xabaringizga javob sifatida `/del`\n\nFaqat sizning xabaringizni o\'chiradi.',
            'me': '**Profilim**\n\nFoydalanish: `/me`\n\nTelegram profilingizni ko\'rsatadi.',
            'id': '**ID lar**\n\nFoydalanish: `/id` yoki xabarga javob sifatida `/id`\n\nChat ID va user ID ni ko\'rsatadi.',
            'link': '**Chat havolasi**\n\nFoydalanish: `/link`\n\nChat invite linkini oladi.',
            'reply': '**AI javob**\n\nFoydalanish: Xabarga javob sifatida `/reply`\n\nAI javob yaratib yuboradi.',
            'undo': '**Qaytarish**\n\nFoydalanish: `/undo`\n\nUserbot yuborgan oxirgi xabarni o\'chiradi.'
        }

        if cmd in help_texts:
            await event.reply(help_texts[cmd])
        else:
            await event.reply(f"❌ **`/{cmd}` buyrug'i topilmadi**\n\n`/help` - barcha buyruqlar")

    # ========== V3 TRANSLATION COMMANDS ==========

    async def handle_translate_en(self, event: NewMessage.Event) -> None:
        """Translate text to English."""
        if not self.userbot.is_me(event.sender_id):
            return

        text = await self._get_text_for_processing(event)
        if not text:
            await event.reply("❌ **Matn kiriting:** `/en MATN` yoki xabarga javob bering")
            await self._delete_command_message(event)
            return

        try:
            prompt = f"Translate the following text to English. Only return the translated text, nothing else:\n\n{text}"
            translated = await self.openrouter.generate_response([{'role': 'user', 'content': prompt}])
            if translated:
                await event.reply(translated)
                logger.info("Translated text to English")
            else:
                await event.reply("❌ **Tarjima xatosi**")
        except Exception as e:
            await event.reply(f"❌ **Xato:** {str(e)}")
            logger.error(f"Translation error: {e}")

        await self._delete_command_message(event)

    async def handle_translate_ru(self, event: NewMessage.Event) -> None:
        """Translate text to Russian."""
        if not self.userbot.is_me(event.sender_id):
            return

        text = await self._get_text_for_processing(event)
        if not text:
            await event.reply("❌ **Matn kiriting:** `/ru MATN` yoki xabarga javob bering")
            await self._delete_command_message(event)
            return

        try:
            prompt = f"Translate the following text to Russian. Only return the translated text, nothing else:\n\n{text}"
            translated = await self.openrouter.generate_response([{'role': 'user', 'content': prompt}])
            if translated:
                await event.reply(translated)
                logger.info("Translated text to Russian")
            else:
                await event.reply("❌ **Tarjima xatosi**")
        except Exception as e:
            await event.reply(f"❌ **Xato:** {str(e)}")
            logger.error(f"Translation error: {e}")

        await self._delete_command_message(event)

    # ========== V3 TEXT IMPROVEMENT COMMANDS ==========

    async def handle_fix(self, event: NewMessage.Event) -> None:
        """Fix spelling and grammar."""
        if not self.userbot.is_me(event.sender_id):
            return

        text = await self._get_text_for_processing(event)
        if not text:
            await event.reply("❌ **Matn kiriting:** `/fix MATN` yoki xabarga javob bering")
            await self._delete_command_message(event)
            return

        try:
            prompt = f"Fix all spelling and grammar errors in this text. Keep the same language and meaning. Only return the corrected text:\n\n{text}"
            fixed = await self.openrouter.generate_response([{'role': 'user', 'content': prompt}])
            if fixed:
                await event.reply(fixed)
            else:
                await event.reply("❌ **Tuzatish xatosi**")
        except Exception as e:
            await event.reply(f"❌ **Xato:** {str(e)}")

        await self._delete_command_message(event)

    async def handle_formal(self, event: NewMessage.Event) -> None:
        """Rewrite in formal style."""
        if not self.userbot.is_me(event.sender_id):
            return

        text = await self._get_text_for_processing(event)
        if not text:
            await event.reply("❌ **Matn kiriting:** `/formal MATN` yoki xabarga javob bering")
            await self._delete_command_message(event)
            return

        try:
            prompt = f"Rewrite this text in a formal, polite style. Keep the same language. Only return the rewritten text:\n\n{text}"
            formal = await self.openrouter.generate_response([{'role': 'user', 'content': prompt}])
            if formal:
                await event.reply(formal)
            else:
                await event.reply("❌ **Qayta yozish xatosi**")
        except Exception as e:
            await event.reply(f"❌ **Xato:** {str(e)}")

        await self._delete_command_message(event)

    async def handle_short(self, event: NewMessage.Event) -> None:
        """Make text shorter."""
        if not self.userbot.is_me(event.sender_id):
            return

        text = await self._get_text_for_processing(event)
        if not text:
            await event.reply("❌ **Matn kiriting:** `/short MATN` yoki xabarga javob bering")
            await self._delete_command_message(event)
            return

        try:
            prompt = f"Make this text shorter while keeping the main message. Keep the same language. Only return the shortened text:\n\n{text}"
            short = await self.openrouter.generate_response([{'role': 'user', 'content': prompt}])
            if short:
                await event.reply(short)
            else:
                await event.reply("❌ **Qisqartirish xatosi**")
        except Exception as e:
            await event.reply(f"❌ **Xato:** {str(e)}")

        await self._delete_command_message(event)

    async def handle_pro(self, event: NewMessage.Event) -> None:
        """Rewrite professionally."""
        if not self.userbot.is_me(event.sender_id):
            return

        text = await self._get_text_for_processing(event)
        if not text:
            await event.reply("❌ **Matn kiriting:** `/pro MATN` yoki xabarga javob bering")
            await self._delete_command_message(event)
            return

        try:
            prompt = f"Rewrite this text in a professional, business style. Keep the same language. Only return the rewritten text:\n\n{text}"
            pro = await self.openrouter.generate_response([{'role': 'user', 'content': prompt}])
            if pro:
                await event.reply(pro)
            else:
                await event.reply("❌ **Qayta yozish xatosi**")
        except Exception as e:
            await event.reply(f"❌ **Xato:** {str(e)}")

        await self._delete_command_message(event)

    async def handle_emoji(self, event: NewMessage.Event) -> None:
        """Add emojis to text."""
        if not self.userbot.is_me(event.sender_id):
            return

        text = await self._get_text_for_processing(event)
        if not text:
            await event.reply("❌ **Matn kiriting:** `/emoji MATN` yoki xabarga javob bering")
            await self._delete_command_message(event)
            return

        try:
            prompt = f"Add appropriate emojis to this text. Keep the same language and don't overdo it. Only return the text with emojis:\n\n{text}"
            with_emoji = await self.openrouter.generate_response([{'role': 'user', 'content': prompt}])
            if with_emoji:
                await event.reply(with_emoji)
            else:
                await event.reply("❌ **Emoji qo'shish xatosi**")
        except Exception as e:
            await event.reply(f"❌ **Xato:** {str(e)}")

        await self._delete_command_message(event)

    async def handle_clean(self, event: NewMessage.Event) -> None:
        """Clean unnecessary symbols."""
        if not self.userbot.is_me(event.sender_id):
            return

        text = await self._get_text_for_processing(event)
        if not text:
            await event.reply("❌ **Matn kiriting:** `/clean MATN` yoki xabarga javob bering")
            await self._delete_command_message(event)
            return

        try:
            prompt = f"Clean this text by removing unnecessary symbols, extra spaces, and weird formatting. Keep the same language and meaning. Only return the cleaned text:\n\n{text}"
            cleaned = await self.openrouter.generate_response([{'role': 'user', 'content': prompt}])
            if cleaned:
                await event.reply(cleaned)
            else:
                await event.reply("❌ **Tozalash xatosi**")
        except Exception as e:
            await event.reply(f"❌ **Xato:** {str(e)}")

        await self._delete_command_message(event)

    # ========== V3 TELEGRAM COMMANDS ==========

    async def handle_copy(self, event: NewMessage.Event) -> None:
        """Copy replied-to message."""
        if not self.userbot.is_me(event.sender_id):
            return

        if not event.is_reply:
            await event.reply("❌ **Xabarga javob bering**")
            await self._delete_command_message(event)
            return

        try:
            reply_msg = await event.get_reply_message()
            if reply_msg.text:
                await event.reply(reply_msg.text)
            elif reply_msg.message:
                await event.reply(reply_msg.message)
            else:
                await event.reply("❌ **Xabarda matn yo'q**")
        except Exception as e:
            await event.reply(f"❌ **Xato:** {str(e)}")

        await self._delete_command_message(event)

    async def handle_pin(self, event: NewMessage.Event) -> None:
        """Pin replied-to message."""
        if not self.userbot.is_me(event.sender_id):
            return

        if not event.is_reply:
            await event.reply("❌ **Xabarga javob bering**")
            await self._delete_command_message(event)
            return

        try:
            reply_msg = await event.get_reply_message()
            await reply_msg.pin()
            await event.reply("📌 **Xabar qadaldi**")
        except Exception as e:
            await event.reply(f"❌ **Qadash xatosi:** {str(e)}")

        await self._delete_command_message(event)

    async def handle_del(self, event: NewMessage.Event) -> None:
        """Delete own replied-to message."""
        if not self.userbot.is_me(event.sender_id):
            return

        if not event.is_reply:
            await event.reply("❌ **O'z xabaringizga javob bering**")
            await self._delete_command_message(event)
            return

        try:
            reply_msg = await event.get_reply_message()
            if reply_msg.sender_id == self.userbot.me.id:
                await reply_msg.delete()
                await event.reply("🗑️ **Xabar o'chirildi**")
            else:
                await event.reply("❌ **Faqat o'z xabarlaringizni o'chirish mumkin**")
        except Exception as e:
            await event.reply(f"❌ **O'chirish xatosi:** {str(e)}")

        await self._delete_command_message(event)

    async def handle_me(self, event: NewMessage.Event) -> None:
        """Show own profile."""
        if not self.userbot.is_me(event.sender_id):
            return

        try:
            me = self.userbot.me
            info = f"**👤 Profil**\n\n"
            info += f"**Ism:** {me.first_name}"
            if me.last_name:
                info += f" {me.last_name}"
            info += f"\n**Username:** @{me.username}" if me.username else ""
            info += f"\n**ID:** `{me.id}`"
            info += f"\n**Phone:** `{me.phone}`" if me.phone else ""
            info += f"\n**Bot:** {'Ha' if me.bot else 'Yo\'q'}"
            await event.reply(info)
        except Exception as e:
            await event.reply(f"❌ **Xato:** {str(e)}")

        await self._delete_command_message(event)

    async def handle_id(self, event: NewMessage.Event) -> None:
        """Show chat and user IDs."""
        if not self.userbot.is_me(event.sender_id):
            return

        try:
            info = f"**🆔 ID Ma'lumotlari**\n\n"
            info += f"**Chat ID:** `{event.chat_id}`\n"

            if event.is_reply:
                reply_msg = await event.get_reply_message()
                sender = await reply_msg.get_sender()
                if sender:
                    info += f"**User ID:** `{sender.id}`\n"
                    if hasattr(sender, 'username') and sender.username:
                        info += f"**Username:** @{sender.username}\n"
                    if hasattr(sender, 'first_name'):
                        info += f"**Ism:** {sender.first_name}"
                        if hasattr(sender, 'last_name') and sender.last_name:
                            info += f" {sender.last_name}"

            await event.reply(info)
        except Exception as e:
            await event.reply(f"❌ **Xato:** {str(e)}")

        await self._delete_command_message(event)

    async def handle_link(self, event: NewMessage.Event) -> None:
        """Get chat invite link."""
        if not self.userbot.is_me(event.sender_id):
            return

        try:
            chat = await event.get_chat()
            if hasattr(chat, 'username') and chat.username:
                link = f"https://t.me/{chat.username}"
                await event.reply(f"**🔗 Chat havolasi:**\n{link}")
            else:
                # Try to get invite link
                result = await self.userbot.client(functions.messages.ExportChatInviteRequest(
                    peer=event.chat_id
                ))
                await event.reply(f"**🔗 Invite link:**\n{result.link}")
        except Exception as e:
            await event.reply(f"❌ **Havola olish xatosi:** {str(e)}")

        await self._delete_command_message(event)

    # ========== V3 AI REPLY COMMANDS ==========

    async def handle_reply(self, event: NewMessage.Event) -> None:
        """Generate AI reply to message."""
        if not self.userbot.is_me(event.sender_id):
            return

        if not event.is_reply:
            await event.reply("❌ **Xabarga javob bering**")
            await self._delete_command_message(event)
            return

        try:
            reply_msg = await event.get_reply_message()
            if not reply_msg.text and not reply_msg.message:
                await event.reply("❌ **Xabarda matn yo'q**")
                await self._delete_command_message(event)
                return

            text = reply_msg.text or reply_msg.message
            response = await self.openrouter.generate_response([{'role': 'user', 'content': text}])

            if response:
                await event.reply(response)
                logger.info("Generated AI reply")
            else:
                await event.reply("❌ **Javob yaratish xatosi**")
        except Exception as e:
            await event.reply(f"❌ **Xato:** {str(e)}")
            logger.error(f"Reply generation error: {e}")

        await self._delete_command_message(event)

    async def handle_undo(self, event: NewMessage.Event) -> None:
        """Delete last userbot message."""
        if not self.userbot.is_me(event.sender_id):
            return

        try:
            # Get recent messages in this chat
            messages = await self.userbot.client.get_messages(event.chat_id, limit=20)

            # Find the last message sent by this userbot (excluding the /undo command itself)
            for msg in messages:
                if msg.id != event.id and msg.sender_id == self.userbot.me.id:
                    await msg.delete()
                    await event.reply("↩️ **Oxirgi xabar o'chirildi**")
                    await self._delete_command_message(event)
                    return

            await event.reply("❌ **O'chiriladigan xabar topilmadi**")
        except Exception as e:
            await event.reply(f"❌ **Xato:** {str(e)}")

        await self._delete_command_message(event)

    # ========== HELPER METHODS ==========

    async def _get_text_for_processing(self, event: NewMessage.Event) -> str:
        """Get text from command argument or replied message."""
        args = event.raw_text.split(maxsplit=1)

        # If text provided in command
        if len(args) > 1:
            return args[1].strip()

        # If replying to a message
        if event.is_reply:
            reply_msg = await event.get_reply_message()
            return reply_msg.text or reply_msg.message or ""

        return ""

    def register_handlers(self, client) -> None:
        """Register all command handlers."""
        # AI Management
        client.add_event_handler(self.handle_ai_on, NewMessage(pattern=r'^/ai_on$', outgoing=True))
        client.add_event_handler(self.handle_ai_off, NewMessage(pattern=r'^/ai_off$', outgoing=True))
        client.add_event_handler(self.handle_toggle, NewMessage(pattern=r'^/toggle$', outgoing=True))
        client.add_event_handler(self.handle_status, NewMessage(pattern=r'^/status$', outgoing=True))
        client.add_event_handler(self.handle_model, NewMessage(pattern=r'^/model$', outgoing=True))
        client.add_event_handler(self.handle_models, NewMessage(pattern=r'^/models$', outgoing=True))
        client.add_event_handler(self.handle_setmodel, NewMessage(pattern=r'^/setmodel(\s|$)', outgoing=True))
        client.add_event_handler(self.handle_temperature, NewMessage(pattern=r'^/temperature', outgoing=True))
        client.add_event_handler(self.handle_prompt, NewMessage(pattern=r'^/prompt$', outgoing=True))
        client.add_event_handler(self.handle_setprompt, NewMessage(pattern=r'^/setprompt(\s|$)', outgoing=True))

        # Per-chat AI
        client.add_event_handler(self.handle_chat_ai_on, NewMessage(pattern=r'^/chat_ai_on$', outgoing=True))
        client.add_event_handler(self.handle_chat_ai_off, NewMessage(pattern=r'^/chat_ai_off$', outgoing=True))
        client.add_event_handler(self.handle_chat_ai_toggle, NewMessage(pattern=r'^/chat_ai_toggle$', outgoing=True))
        client.add_event_handler(self.handle_chat_ai_status, NewMessage(pattern=r'^/chat_ai_status$', outgoing=True))
        client.add_event_handler(self.handle_chat_info, NewMessage(pattern=r'^/chat_info$', outgoing=True))
        client.add_event_handler(self.handle_chat_clear, NewMessage(pattern=r'^/chat_clear$', outgoing=True))

        # Conversation
        client.add_event_handler(self.handle_clear, NewMessage(pattern=r'^/clear$', outgoing=True))
        client.add_event_handler(self.handle_clearall, NewMessage(pattern=r'^/clearall$', outgoing=True))
        client.add_event_handler(self.handle_history, NewMessage(pattern=r'^/history$', outgoing=True))
        client.add_event_handler(self.handle_pause, NewMessage(pattern=r'^/pause$', outgoing=True))
        client.add_event_handler(self.handle_resume, NewMessage(pattern=r'^/resume$', outgoing=True))

        # User Management
        client.add_event_handler(self.handle_block, NewMessage(pattern=r'^/block(\s|$)', outgoing=True))
        client.add_event_handler(self.handle_unblock, NewMessage(pattern=r'^/unblock(\s|$)', outgoing=True))
        client.add_event_handler(self.handle_blocked, NewMessage(pattern=r'^/blocked$', outgoing=True))
        client.add_event_handler(self.handle_allow, NewMessage(pattern=r'^/allow(\s|$)', outgoing=True))
        client.add_event_handler(self.handle_deny, NewMessage(pattern=r'^/deny(\s|$)', outgoing=True))

        # Monitoring
        client.add_event_handler(self.handle_stats, NewMessage(pattern=r'^/stats$', outgoing=True))
        client.add_event_handler(self.handle_uptime, NewMessage(pattern=r'^/uptime$', outgoing=True))
        client.add_event_handler(self.handle_ping, NewMessage(pattern=r'^/ping$', outgoing=True))
        client.add_event_handler(self.handle_health, NewMessage(pattern=r'^/health$', outgoing=True))

        # AI Tools
        client.add_event_handler(self.handle_ask, NewMessage(pattern=r'^/ask(\s|$)', outgoing=True))
        client.add_event_handler(self.handle_language, NewMessage(pattern=r'^/language(\s|$)', outgoing=True))

        # V3: Translation Commands
        client.add_event_handler(self.handle_translate_en, NewMessage(pattern=r'^/en(\s|$)', outgoing=True))
        client.add_event_handler(self.handle_translate_ru, NewMessage(pattern=r'^/ru(\s|$)', outgoing=True))

        # V3: Text Improvement Commands
        client.add_event_handler(self.handle_fix, NewMessage(pattern=r'^/fix(\s|$)', outgoing=True))
        client.add_event_handler(self.handle_formal, NewMessage(pattern=r'^/formal(\s|$)', outgoing=True))
        client.add_event_handler(self.handle_short, NewMessage(pattern=r'^/short(\s|$)', outgoing=True))
        client.add_event_handler(self.handle_pro, NewMessage(pattern=r'^/pro(\s|$)', outgoing=True))
        client.add_event_handler(self.handle_emoji, NewMessage(pattern=r'^/emoji(\s|$)', outgoing=True))
        client.add_event_handler(self.handle_clean, NewMessage(pattern=r'^/clean(\s|$)', outgoing=True))

        # V3: Telegram Commands
        client.add_event_handler(self.handle_copy, NewMessage(pattern=r'^/copy$', outgoing=True))
        client.add_event_handler(self.handle_pin, NewMessage(pattern=r'^/pin$', outgoing=True))
        client.add_event_handler(self.handle_del, NewMessage(pattern=r'^/del$', outgoing=True))
        client.add_event_handler(self.handle_me, NewMessage(pattern=r'^/me$', outgoing=True))
        client.add_event_handler(self.handle_id, NewMessage(pattern=r'^/id$', outgoing=True))
        client.add_event_handler(self.handle_link, NewMessage(pattern=r'^/link$', outgoing=True))

        # V3: AI Reply Commands
        client.add_event_handler(self.handle_reply, NewMessage(pattern=r'^/reply$', outgoing=True))
        client.add_event_handler(self.handle_undo, NewMessage(pattern=r'^/undo$', outgoing=True))

        # Help (must be last to allow /help command_name)
        client.add_event_handler(self.handle_help, NewMessage(pattern=r'^/help', outgoing=True))

        logger.info("All V3 command handlers registered (49 total)")
