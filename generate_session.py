"""
Script to generate a Telegram session string locally.
Run this script on your local machine to create the session.

Usage:
    python generate_session.py
"""

import asyncio
import sys
from telethon import TelegramClient
from telethon.sessions import StringSession


async def generate_session():
    """Generate a new Telegram session string."""
    print("=" * 60)
    print("Telegram Session Generator")
    print("=" * 60)
    print()

    api_id = input("Enter your TELEGRAM_API_ID: ").strip()
    api_hash = input("Enter your TELEGRAM_API_HASH: ").strip()

    if not api_id or not api_hash:
        print("\nError: API ID and API Hash are required")
        sys.exit(1)

    try:
        api_id = int(api_id)
    except ValueError:
        print("\nError: API ID must be a number")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("Starting Telegram authentication...")
    print("=" * 60)

    client = TelegramClient(StringSession(), api_id, api_hash)

    try:
        await client.connect()

        if not await client.is_user_authorized():
            phone = input("\nEnter your phone number (with country code, e.g., +1234567890): ").strip()

            await client.send_code_request(phone)
            print("\nA verification code has been sent to your Telegram account")
            code = input("Enter the verification code: ").strip()

            try:
                await client.sign_in(phone, code)
            except Exception as e:
                if "Two-steps verification" in str(e) or "password" in str(e).lower():
                    password = input("\nTwo-factor authentication enabled.\nEnter your 2FA password: ").strip()
                    await client.sign_in(password=password)
                else:
                    raise

        me = await client.get_me()
        session_string = client.session.save()

        print("\n" + "=" * 60)
        print("✅ Session created successfully!")
        print("=" * 60)
        print(f"\nLogged in as: @{me.username} (ID: {me.id})")
        print(f"Name: {me.first_name} {me.last_name or ''}".strip())
        print("\n" + "=" * 60)
        print("TELEGRAM_SESSION string:")
        print("=" * 60)
        print(session_string)
        print("=" * 60)
        print("\nIMPORTANT:")
        print("1. Copy the session string above")
        print("2. Add it to your .env file or Render environment variables")
        print("3. Set TELEGRAM_SESSION=<the string above>")
        print("4. NEVER share this session string with anyone")
        print("5. NEVER commit it to git")
        print("=" * 60)

        await client.disconnect()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        await client.disconnect()
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(generate_session())
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        sys.exit(0)
