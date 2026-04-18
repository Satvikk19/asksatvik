#!/usr/bin/env python3
from dotenv import load_dotenv; load_dotenv()
"""
asksatvik — Slack bot powered by Claude Code CLI
Uses Socket Mode (no public URL needed). Works as long as this machine is running.
Claude CLI handles auth and all MCP tools (Mixpanel, Jira, etc.) automatically.
"""

import os
import re
import json
import subprocess
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]  # xoxb-...
SLACK_APP_TOKEN = os.environ["SLACK_APP_TOKEN"]   # xapp-...

# Comma-separated Slack user IDs allowed to use this bot (e.g. "U012AB3CD,U056EF7GH")
# Find your ID: Slack → profile → three-dot menu → Copy member ID
_allowed = os.environ.get("ALLOWED_USER_IDS", "")
ALLOWED_USER_IDS = set(uid.strip() for uid in _allowed.split(",") if uid.strip())

# Claude Workshop directory — loads CLAUDE.md + all MCP context automatically
CLAUDE_CWD = os.path.expanduser("~/Documents/Coding Projects/Claude Workshop")

app = App(token=SLACK_BOT_TOKEN)
_bot_user_id = None  # cached on first use


def get_bot_user_id(client):
    global _bot_user_id
    if not _bot_user_id:
        _bot_user_id = client.auth_test()["user_id"]
    return _bot_user_id


def get_thread_context(client, channel, thread_ts, bot_user_id):
    """Fetch previous messages in a thread for multi-turn context."""
    try:
        messages = client.conversations_replies(
            channel=channel, ts=thread_ts, limit=20
        )["messages"]
        lines = []
        for msg in messages[:-1]:  # skip the latest (current) message
            role = "assistant" if msg.get("user") == bot_user_id else "user"
            text = re.sub(r"<@[A-Z0-9]+>", "", msg.get("text", "")).strip()
            if text:
                lines.append(f"{role}: {text}")
        return "\n".join(lines)
    except Exception:
        return ""


def ask_claude(prompt, context=""):
    """Spawn claude CLI and return its response. Inherits all MCP servers."""
    if context:
        full_prompt = f"Conversation so far:\n{context}\n\nLatest message: {prompt}"
    else:
        full_prompt = prompt

    try:
        result = subprocess.run(
            [
                "claude",
                "-p", full_prompt,
                "--output-format", "json",
                "--dangerously-skip-permissions",
            ],
            capture_output=True,
            text=True,
            timeout=300,  # 5 min — enough for Mixpanel queries
            cwd=CLAUDE_CWD,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data.get("result") or "No response."
        else:
            return f"Claude error:\n```{result.stderr[:800]}```"
    except subprocess.TimeoutExpired:
        return "Timed out after 5 min. Try a simpler query or break it into smaller steps."
    except FileNotFoundError:
        return "Error: `claude` CLI not found. Make sure Claude Code is installed and in PATH."
    except Exception as e:
        return f"Error: {e}"


def process_message(client, channel, ts, thread_ts, raw_text, say, user_id):
    """Core handler — strip mention, get context, call Claude, reply."""
    # Reject anyone not in the whitelist
    if ALLOWED_USER_IDS and user_id not in ALLOWED_USER_IDS:
        say(text="Sorry, you're not authorised to use this bot.", thread_ts=thread_ts)
        return

    user_text = re.sub(r"<@[A-Z0-9]+>", "", raw_text).strip()
    if not user_text:
        return

    bot_user_id = get_bot_user_id(client)

    # Get thread history if this is a reply
    context = ""
    if thread_ts != ts:
        context = get_thread_context(client, channel, thread_ts, bot_user_id)

    # Show loading reaction while Claude runs
    try:
        client.reactions_add(channel=channel, timestamp=ts, name="loading-dots")
    except Exception:
        pass

    response = ask_claude(user_text, context)

    try:
        client.reactions_remove(channel=channel, timestamp=ts, name="loading-dots")
    except Exception:
        pass

    say(text=response, thread_ts=thread_ts)


@app.event("app_mention")
def handle_mention(event, say, client):
    process_message(
        client=client,
        channel=event["channel"],
        ts=event["ts"],
        thread_ts=event.get("thread_ts", event["ts"]),
        raw_text=event.get("text", ""),
        say=say,
        user_id=event.get("user", ""),
    )


@app.event("message")
def handle_dm(event, say, client):
    # Only handle DMs; ignore bot messages, edits, deletes
    if event.get("channel_type") != "im":
        return
    if event.get("subtype") or event.get("bot_id"):
        return

    ts = event["ts"]
    process_message(
        client=client,
        channel=event["channel"],
        ts=ts,
        thread_ts=event.get("thread_ts", ts),
        raw_text=event.get("text", ""),
        say=say,
        user_id=event.get("user", ""),
    )


if __name__ == "__main__":
    print("asksatvik is running (Socket Mode). Ctrl+C to stop.")
    SocketModeHandler(app, SLACK_APP_TOKEN).start()
