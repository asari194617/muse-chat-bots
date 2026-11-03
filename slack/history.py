"""Bridge conversation log helper (per-channel JSONL).

Usage:
  history.py add <channel_id> <role> <author> <text>
  history.py show <channel_id> [count]
"""

import datetime as dt
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
HIST_DIR = os.path.join(BASE, "history")


def _path(channel_id: str) -> str:
    return os.path.join(HIST_DIR, f"{channel_id}.jsonl")


def main() -> int:
    os.makedirs(HIST_DIR, exist_ok=True)
    if len(sys.argv) >= 2 and sys.argv[1] == "add":
        _, _, channel_id, role, author, text = sys.argv[:6]
        entry = {
            "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
            "role": role,
            "author": author,
            "text": text,
        }
        with open(_path(channel_id), "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return 0
    if len(sys.argv) >= 2 and sys.argv[1] == "show":
        channel_id = sys.argv[2]
        count = int(sys.argv[3]) if len(sys.argv) > 3 else 20
        path = _path(channel_id)
        if not os.path.exists(path):
            print("[]")
            return 0
        with open(path) as f:
            lines = [ln for ln in f.read().splitlines() if ln.strip()]
        entries = [json.loads(ln) for ln in lines[-count:]]
        print(json.dumps(entries, ensure_ascii=False, indent=1))
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
