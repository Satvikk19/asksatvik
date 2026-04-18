# asksatvik

A Slack bot powered by Claude Code CLI. Ask it anything you'd ask Claude — it has full access to Mixpanel, Jira, and other tools via MCP.

## How it works

When you send it a message, it spawns a local `claude` CLI subprocess with your full Claude Code context — CLAUDE.md, all MCP servers, everything. No Anthropic API key needed; it runs on your Claude.ai subscription.

## Setup

### 1. Prerequisites

- Claude Code installed and logged in
- A Slack app with Socket Mode enabled

### 2. Slack app configuration

At [api.slack.com/apps](https://api.slack.com/apps):

- **Socket Mode** → Enable → create App-Level Token with `connections:write` scope → copy `xapp-...`
- **OAuth & Permissions** → Bot Token Scopes: `app_mentions:read`, `chat:write`, `im:read`, `im:history`, `channels:history`, `reactions:write` → Install to workspace → copy `xoxb-...`
- **Event Subscriptions** → Enable → subscribe to `app_mention` and `message.im`

### 3. Environment

```bash
cp .env.example .env
```

Fill in `.env`:

```
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
ALLOWED_USER_IDS=U012AB3CD   # comma-separated Slack user IDs
```

To find your user ID: Slack → Profile → ··· → Copy member ID.

### 4. Install and run

```bash
pip install slack-bolt python-dotenv
python bot.py
```

## Usage

DM the bot or `@mention` it in a channel:

- `what was yesterday's ERP CPL?`
- `run ads-summary for this week`
- `show me the MoM conversion table for ERP`

## Security

- Only users listed in `ALLOWED_USER_IDS` can interact with the bot
- `.env` is gitignored — never commit it
- The bot only acts when explicitly asked; it does nothing proactively
