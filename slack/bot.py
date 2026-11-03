"""Resident Slack bot (asari-muse) for the team workspace.

Socket Mode client (slack_bolt). Mirrors the Discord asari-muse design:
owner mentions and DMs are queued to queue/pending.jsonl, and the Muse
bridge (hook on the Muse VM) picks them up and replies through this bot.

Tokens come from the environment (loaded from .env by the systemd unit):
  SLACK_BOT_TOKEN  (xoxb-...) bot user token
  SLACK_APP_TOKEN  (xapp-...) app-level token for Socket Mode
Never hard-code or log the tokens.

Operating rules agreed with the workspace admins: the bot only
responds to its owner's mentions/DMs. It never posts proactively, never
auto-mentions other members, and keeps volume low.
"""

import datetime as dt
import fcntl
import json
import logging
import os
import sys
import uuid

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("asari-muse-slack")

BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")
if not BOT_TOKEN or not APP_TOKEN:
    log.error("SLACK_BOT_TOKEN / SLACK_APP_TOKEN are not set; exiting.")
    sys.exit(1)

BASE = os.path.dirname(os.path.abspath(__file__))
QUEUE_DIR = os.path.join(BASE, "queue")
PENDING_PATH = os.path.join(QUEUE_DIR, "pending.jsonl")
LOCK_PATH = os.path.join(QUEUE_DIR, "queue.lock")
OWNER_PATH = os.path.join(BASE, "owner.json")

app = App(token=BOT_TOKEN)
BOT_USER_ID: str | None = None


def _owner_id() -> str | None:
    try:
        with open(OWNER_PATH) as f:
            return json.load(f).get("owner_id")
    except (OSError, json.JSONDecodeError):
        return None


def _enqueue(entry: dict) -> None:
    os.makedirs(QUEUE_DIR, exist_ok=True)
    line = json.dumps(entry, ensure_ascii=False) + "\n"
    with open(LOCK_PATH, "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        with open(PENDING_PATH, "a") as f:
            f.write(line)
        fcntl.flock(lock, fcntl.LOCK_UN)


def _display_name(client, user_id: str) -> str:
    try:
        info = client.users_info(user=user_id)
        user = info.get("user", {})
        profile = user.get("profile", {})
        return profile.get("display_name") or user.get("real_name") or user_id
    except Exception:
        return user_id


def _ack_eyes(client, channel: str, ts: str) -> None:
    try:
        client.reactions_add(channel=channel, timestamp=ts, name="eyes")
    except Exception:
        pass


def _handle_chat_event(event: dict, client, *, is_dm: bool) -> None:
    user = event.get("user")
    channel = event.get("channel")
    ts = event.get("ts")
    if not user or not channel or not ts:
        return
    if BOT_USER_ID is not None and user == BOT_USER_ID:
        return
    if event.get("bot_id"):
        return
    text = event.get("text") or ""
    if BOT_USER_ID and not is_dm:
        text = text.replace(f"<@{BOT_USER_ID}>", "").strip()
    owner = _owner_id()
    entry = {
        "id": uuid.uuid4().hex,
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
        "channel_id": channel,
        "message_id": ts,
        "thread_ts": event.get("thread_ts") or ts,
        "author_id": user,
        "author_name": _display_name(client, user),
        "content": text[:1500],
    }
    if owner is None:
        entry["kind"] = "claim"
        _enqueue(entry)
        client.chat_postMessage(
            channel=channel, thread_ts=entry["thread_ts"],
            text="オーナー登録の確認用に記録しました。登録が終わるまで少し待ってください。",
        )
    elif user == owner:
        entry["kind"] = "chat"
        _enqueue(entry)
        _ack_eyes(client, channel, ts)
    elif not is_dm:
        client.chat_postMessage(
            channel=channel, thread_ts=entry["thread_ts"],
            text="私はオーナー専用のBotです。",
        )


@app.event("app_mention")
def on_app_mention(event, client):
    _handle_chat_event(event, client, is_dm=False)


@app.event("message")
def on_message(event, client):
    # Only DMs are handled here; channel messages arrive via app_mention.
    if event.get("channel_type") != "im":
        return
    if event.get("subtype"):
        return
    _handle_chat_event(event, client, is_dm=True)


if __name__ == "__main__":
    auth = app.client.auth_test()
    BOT_USER_ID = auth.get("user_id")
    log.info("Logged in as asari-muse (bot user id=%s)", BOT_USER_ID)
    SocketModeHandler(app, APP_TOKEN).start()
