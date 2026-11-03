"""Read recent Slack messages for bridge context.

Usage:
  fetch_channel.py <channel_id> [limit]            -> channel history
  fetch_channel.py <channel_id> <thread_ts> [limit] -> thread replies

Prints a JSON array, newest first, of {id, ts, author_id, author_name,
content}. Reads the bot token from .env next to this script and the egress
proxy from proxy.env when present (this VM reaches the internet via proxy;
on the bot host neither file is needed by this helper).
"""

import json
import os
import sys
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
API = "https://slack.com/api/"


def _load_env(path: str) -> dict:
    env = {}
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip().strip('"').strip("'")
    return env


_ENV = _load_env(os.path.join(BASE, ".env"))
_PROXY = _load_env(os.path.join(BASE, "proxy.env"))
TOKEN = _ENV.get("SLACK_BOT_TOKEN") or os.environ.get("SLACK_BOT_TOKEN")
PROXY = (
    _PROXY.get("HTTPS_PROXY")
    or _PROXY.get("https_proxy")
    or os.environ.get("HTTPS_PROXY")
    or os.environ.get("https_proxy")
)


def api(method: str, **params):
    data = json.dumps(params).encode()
    req = urllib.request.Request(
        API + method, data=data,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": PROXY, "https": PROXY} if PROXY else {})
    )
    with opener.open(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


_names: dict[str, str] = {}


def author_name(user_id: str) -> str:
    if user_id not in _names:
        try:
            info = api("users.info", user=user_id)
            user = info.get("user", {})
            profile = user.get("profile", {})
            _names[user_id] = (
                profile.get("display_name") or user.get("real_name") or user_id
            )
        except Exception:
            _names[user_id] = user_id
    return _names[user_id]


def shape(m: dict) -> dict:
    import datetime as dt

    ts = m.get("ts", "")
    try:
        iso = dt.datetime.fromtimestamp(float(ts), dt.timezone.utc).isoformat()
    except (ValueError, TypeError):
        iso = ts
    return {
        "id": ts,
        "ts": iso,
        "author_id": m.get("user", ""),
        "author_name": author_name(m.get("user", "")) if m.get("user") else "",
        "content": m.get("text", ""),
    }


def main() -> int:
    if not TOKEN:
        print("SLACK_BOT_TOKEN not set", file=sys.stderr)
        return 1
    channel = sys.argv[1]
    args = sys.argv[2:]
    thread_ts = None
    limit = 30
    for a in args:
        if "." in a and a.replace(".", "").isdigit():
            thread_ts = a
        else:
            limit = int(a)
    if thread_ts:
        res = api("conversations.replies", channel=channel, ts=thread_ts,
                  limit=limit)
        msgs = res.get("messages", [])
        print(json.dumps([shape(m) for m in msgs], ensure_ascii=False, indent=1))
    else:
        res = api("conversations.history", channel=channel, limit=limit)
        msgs = res.get("messages", [])
        print(json.dumps([shape(m) for m in msgs], ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
