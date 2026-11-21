# Telegram Heartbeat Monitoring

## Overview

The userbot includes heartbeat monitoring that sends periodic status updates to a private Telegram chat.

## Commands

### `/monitor_on`
Enables monitoring in the current chat. Sends status updates every 3 minutes (configurable).

### `/monitor_off`
Disables monitoring and stops status updates.

### `/monitor_status`
Shows current monitoring configuration and state.

## Status Information

Each status message shows:
- Userbot online status
- AI enabled/disabled
- Telegram connection status
- Database status
- Current AI model
- Uptime
- Last check timestamp

## Features

- Edits previous message instead of creating new ones
- Handles FloodWait and network errors gracefully
- Persists settings across restarts
- Prevents duplicate monitoring loops
- Auto-resumes on restart if previously enabled

## Configuration

Default interval: 180 seconds (3 minutes)
Minimum interval: 60 seconds

Settings are stored in the SQLite database `settings` table:
- `monitor_enabled`: '0' or '1'
- `monitor_chat_id`: chat ID
- `monitor_message_id`: last message ID
- `monitor_interval`: interval in seconds

## Usage

1. Create a private group with only yourself
2. Send `/monitor_on` in that group
3. Status updates will appear every 3 minutes
4. Send `/monitor_off` to stop

All commands are owner-only and responses are in Uzbek.
