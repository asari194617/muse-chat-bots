"""Post a threaded reply as the bot.

Usage: reply.py <channel_id> <thread_ts> <text>
Reads the bot token from .env and the egress proxy from proxy.env.
Prints the new message ts on success.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_channel import api  # noqa: E402


def main() -> int:
    if len(sys.argv) < 4:
        print(__doc__, file=sys.stderr)
        return 2
    channel_id, thread_ts, text = sys.argv[1], sys.argv[2], sys.argv[3][:3000]
    res = api("chat.postMessage", channel=channel_id, thread_ts=thread_ts,
              text=text)
    if not res.get("ok"):
        print(f"post failed: {res.get('error')}", file=sys.stderr)
        return 1
    print(res["ts"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
