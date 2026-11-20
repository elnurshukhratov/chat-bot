# Telegram AI Userbot

A production-ready Telegram userbot that automatically responds to incoming messages using AI through the OpenRouter API.

## Features

- ✅ **Personal Account Authentication**: Uses your personal Telegram account (userbot, not bot)
- 🤖 **AI-Powered Responses**: Powered by OpenRouter with configurable models
- 💬 **Smart Message Handling**:
  - Automatic responses in private chats
  - Responds in groups only when mentioned or replied to
  - Per-user conversation history
  - Configurable cooldowns and rate limiting
- 🗄️ **Persistent Memory**: SQLite database for conversation history
- 🛡️ **Safety Features**:
  - User blocklist/allowlist
  - Duplicate message protection
  - Graceful error handling
- ⚙️ **Owner Commands**: `/ai_on`, `/ai_off`, `/status`, `/clear`, `/help`
- 🚀 **Render Deployment**: Ready to deploy with persistent disk storage

## Requirements

- Python 3.11+
- Telegram account (no Premium required)
- OpenRouter API key
- Render account (for deployment)

## Telegram API Credentials

Before you begin, you need to obtain Telegram API credentials:

1. Go to https://my.telegram.org
2. Log in with your phone number
3. Click on "API development tools"
4. Create a new application (if you haven't already)
5. Note down your `api_id` and `api_hash`

## Local Setup

### 1. Clone and Install Dependencies

```bash
cd /path/to/project
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Generate Telegram Session

Run the session generator script locally:

```bash
python generate_session.py
```

Follow the prompts:
1. Enter your `TELEGRAM_API_ID`
2. Enter your `TELEGRAM_API_HASH`
3. Enter your phone number (with country code, e.g., `+1234567890`)
4. Enter the verification code sent to your Telegram
5. If you have 2FA enabled, enter your password

The script will output a session string. **Keep this safe and never share it.**

### 3. Configure Environment Variables

Create a `.env` file:

```bash
cp .env.example .env
```

Edit `.env` and fill in your values:

```env
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890
TELEGRAM_SESSION=your_session_string_from_previous_step

OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet
```

### 4. Test Locally

```bash
python main.py
```

You should see:
```
============================================================
Telegram AI Userbot Starting
============================================================
...
Userbot is now running
Account: @your_username (ID: 123456789)
AI Model: anthropic/claude-3.5-sonnet
AI Status: Enabled
============================================================
```

Send yourself a message from another account to test.

## Render Deployment

### 1. Create Render Account

Sign up at https://render.com

### 2. Create New Web Service

1. Click "New +" → "Web Service"
2. Connect your Git repository (or deploy from dashboard)
3. Configure:
   - **Name**: `telegram-ai-userbot`
   - **Runtime**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`
   - **Plan**: Starter (or higher for 24/7 uptime)

### 3. Add Persistent Disk

**CRITICAL**: Render's filesystem is ephemeral on free tier. You need a persistent disk.

1. In your service settings, go to "Disks"
2. Click "Add Disk"
3. Configure:
   - **Name**: `userbot-data`
   - **Mount Path**: `/var/data`
   - **Size**: 1 GB (minimum)

### 4. Configure Environment Variables

In Render dashboard, add these environment variables:

```
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_SESSION=your_session_string
OPENROUTER_API_KEY=your_openrouter_key
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet
DATABASE_PATH=/var/data/database.sqlite3
SESSION_PATH=/var/data/telegram.session
LOG_LEVEL=INFO
```

### 5. Deploy

Click "Create Web Service" or "Manual Deploy"

Monitor the logs to ensure successful startup.

## Render Free Tier Limitations

⚠️ **IMPORTANT**: Render's free tier has significant limitations:

- **Automatic Sleep**: Services sleep after 15 minutes of inactivity
- **Cold Starts**: Takes 30-60 seconds to wake up
- **Monthly Limits**: 750 hours/month (not 24/7 coverage)
- **No Guaranteed Uptime**: Not suitable for mission-critical applications

### Recommendations

For reliable 24/7 operation:
- Use Render **Starter plan** ($7/month) or higher
- Or use alternative hosting (VPS, DigitalOcean, AWS, etc.)

The free tier is best for:
- Testing and development
- Low-traffic personal use
- Non-critical automation

## OpenRouter Configuration

### Getting API Key

1. Sign up at https://openrouter.ai
2. Go to "Keys" section
3. Create a new API key
4. Add credits to your account

### Available Models

Popular models you can use:
- `anthropic/claude-3.5-sonnet` (recommended)
- `anthropic/claude-3-opus`
- `anthropic/claude-3-haiku`
- `openai/gpt-4-turbo`
- `openai/gpt-3.5-turbo`
- `meta-llama/llama-3.1-70b-instruct`

See full list at: https://openrouter.ai/models

## Usage

### Owner Commands

These commands only work for the account owner:

- `/ai_on` - Enable automatic AI replies
- `/ai_off` - Disable automatic AI replies (pause mode)
- `/status` - Show current bot status and configuration
- `/clear` - Clear conversation history for current chat
- `/help` - Show help message with available commands

### Behavior

**Private Chats:**
- Automatically responds to all incoming messages
- Maintains separate conversation context for each user
- Respects cooldown periods between responses

**Groups:**
- Only responds when:
  - Someone mentions your username (e.g., `@your_username hello`)
  - Someone replies to one of your messages
- Does NOT respond to every group message (prevents spam)
- Maintains separate context for each group

**Safety:**
- Never responds to other bots
- Never responds to your own messages
- Respects user blocklist
- Prevents duplicate responses with message deduplication

## Configuration Options

Customize via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `AI_SYSTEM_PROMPT` | (default personality) | AI personality and behavior |
| `AI_TEMPERATURE` | `0.7` | Creativity (0.0-2.0) |
| `AI_MAX_TOKENS` | `500` | Max response length |
| `CONVERSATION_HISTORY_LIMIT` | `20` | Messages sent to AI for context |
| `RESPONSE_COOLDOWN_SECONDS` | `5` | Min time between responses to same user |
| `LOG_LEVEL` | `INFO` | Logging verbosity (DEBUG, INFO, WARNING, ERROR) |

## Security Best Practices

🔒 **NEVER**:
- Commit `.env` file to git
- Share your session string
- Share your API keys
- Expose your Telegram API credentials
- Run the bot on untrusted infrastructure

✅ **ALWAYS**:
- Use environment variables for secrets
- Keep your session string secure
- Regularly monitor bot activity
- Use strong 2FA on your Telegram account
- Review logs for suspicious activity

## Troubleshooting

### "Session is not authorized"

Your session has expired or been revoked. Generate a new session:
```bash
python generate_session.py
```

### "OpenRouter API error 401"

Invalid API key. Check your `OPENROUTER_API_KEY` in environment variables.

### "OpenRouter API error 429"

Rate limited. The bot will automatically retry with exponential backoff.

### Bot not responding in groups

Make sure:
1. You mentioned the bot's username: `@your_username hello`
2. Or replied to one of the bot's messages
3. Bot is not in cooldown period
4. `/ai_on` has been enabled

### Database errors

Ensure `/var/data` directory exists and is writable:
```bash
mkdir -p /var/data
chmod 755 /var/data
```

## Project Structure

```
.
├── main.py                 # Application entry point
├── config.py              # Configuration management
├── database.py            # SQLite database operations
├── telegram_client.py     # Telegram client initialization
├── openrouter.py          # OpenRouter API integration
├── message_handler.py     # Message processing logic
├── commands.py            # Command handlers
├── logging_config.py      # Logging setup
├── generate_session.py    # Session generation script
├── requirements.txt       # Python dependencies
├── render.yaml           # Render deployment config
├── .env.example          # Environment variables template
├── .gitignore           # Git ignore rules
└── README.md            # This file
```

## Architecture

```
┌─────────────────┐
│  Telegram API   │
└────────┬────────┘
         │
    ┌────▼─────┐
    │ Telethon │ (MTProto client)
    └────┬─────┘
         │
    ┌────▼─────────────┐
    │ Message Handler  │
    └────┬─────────────┘
         │
    ┌────▼──────┐      ┌──────────────┐
    │  Database │      │  OpenRouter  │
    │  (SQLite) │      │     API      │
    └───────────┘      └──────────────┘
```

## Development

### Running Tests

```bash
# Test database connection
python -c "import asyncio; from database import Database; asyncio.run(Database('test.db').connect())"

# Test OpenRouter API
python -c "
import asyncio
from openrouter import OpenRouterClient
async def test():
    async with OpenRouterClient('your_key', 'anthropic/claude-3.5-sonnet', 'Test') as client:
        response = await client.generate_response([{'role': 'user', 'content': 'Hi'}])
        print(response)
asyncio.run(test())
"
```

### Adding New Features

1. Message handling: Edit `message_handler.py`
2. New commands: Edit `commands.py`
3. Database schema: Edit `database.py` → `_initialize_schema()`
4. AI behavior: Modify `AI_SYSTEM_PROMPT` in `.env`

## License

This project is provided as-is for personal use. By using this software, you agree to:
- Comply with Telegram's Terms of Service
- Comply with OpenRouter's Terms of Service
- Use the bot responsibly and ethically
- Not use it for spam or abuse

## Support

For issues and questions:
1. Check the Troubleshooting section
2. Review Render logs: Dashboard → Your Service → Logs
3. Check Telegram API status: https://telegram.org/
4. Check OpenRouter status: https://openrouter.ai/

## Disclaimer

This is a userbot (automated personal account), not an official Telegram bot. Use at your own risk. The authors are not responsible for any account restrictions, bans, or other consequences resulting from the use of this software.

Telegram's Terms of Service prohibit certain automated behaviors. Ensure your usage complies with all applicable terms and laws.
