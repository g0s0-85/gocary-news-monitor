"""
Fetch GoCary's news API, diff it against the last known snapshot, and record
any additions/removals/edits. Meant to be run on a schedule by
.github/workflows/check-news.yml, which commits whatever this script writes
under docs/data/.
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

NEWS_API_URL = "https://www.gocarylive.org/News/GetAllNews"

DATA_DIR = Path(__file__).resolve().parent.parent / "docs" / "data"
STATE_FILE = DATA_DIR / "state.json"
LOG_FILE = DATA_DIR / "changelog.jsonl"
STATUS_FILE = DATA_DIR / "status.json"

FIELDS_TO_COMPARE = [
    "title",
    "summary",
    "routes",
    "affectsAllRoutes",
    "publishDateUtc",
    "icon",
    "friendlyUrl",
]


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def fetch_news():
    resp = requests.get(
        NEWS_API_URL,
        params={"_": int(time.time() * 1000)},
        timeout=20,
        headers={"User-Agent": "gocary-news-monitor/1.0 (+github actions)"},
    )
    resp.raise_for_status()
    return resp.json()


def load_json(path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def save_json(path, data):
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def append_log_entries(entries):
    if not entries:
        return
    with LOG_FILE.open("a", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


def diff_snapshot(previous, current_items):
    current = {str(item["newsId"]): item for item in current_items}
    prev_ids = set(previous.keys())
    curr_ids = set(current.keys())

    entries = []
    timestamp = now_iso()

    for news_id in curr_ids - prev_ids:
        item = current[news_id]
        entries.append({
            "timestamp": timestamp,
            "type": "added",
            "newsId": news_id,
            "title": item.get("title"),
            "details": None,
        })

    for news_id in prev_ids - curr_ids:
        item = previous[news_id]
        entries.append({
            "timestamp": timestamp,
            "type": "removed",
            "newsId": news_id,
            "title": item.get("title"),
            "details": None,
        })

    for news_id in curr_ids & prev_ids:
        old_item = previous[news_id]
        new_item = current[news_id]
        changed_fields = {}
        for field in FIELDS_TO_COMPARE:
            if old_item.get(field) != new_item.get(field):
                changed_fields[field] = {
                    "old": old_item.get(field),
                    "new": new_item.get(field),
                }
        if changed_fields:
            entries.append({
                "timestamp": timestamp,
                "type": "modified",
                "newsId": news_id,
                "title": new_item.get("title"),
                "details": changed_fields,
            })

    return entries, current


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    status = load_json(STATUS_FILE, {
        "last_checked": None,
        "last_error": None,
        "checks_run": 0,
        "changes_logged": 0,
    })

    try:
        items = fetch_news()
    except Exception as exc:
        status["last_error"] = f"{now_iso()}: {exc}"
        status["last_checked"] = now_iso()
        status["checks_run"] += 1
        save_json(STATUS_FILE, status)
        raise

    had_error = status.get("last_error") is not None
    previous = load_json(STATE_FILE, {})
    is_baseline_run = not previous

    if is_baseline_run:
        # First run ever: establish a baseline, don't log fake "added" spam
        # for every item that already existed before we started watching.
        entries = []
        current = {str(item["newsId"]): item for item in items}
        save_json(STATE_FILE, current)
    else:
        entries, current = diff_snapshot(previous, items)
        if entries:
            append_log_entries(entries)
            save_json(STATE_FILE, current)

    status["last_checked"] = now_iso()
    status["last_error"] = None
    status["checks_run"] += 1
    status["changes_logged"] += len(entries)

    # Checks run every minute, but a run that found nothing to report has
    # nothing worth committing. Persisting status.json on every single run
    # (rather than only on baseline/real-change/error-recovery runs) made
    # it a hot file that near-simultaneous runs would race to update and
    # conflict on. The dashboard gets its "still checking" freshness signal
    # from the GitHub Actions run history instead, not from this file.
    if is_baseline_run or entries or had_error:
        save_json(STATUS_FILE, status)

    print(f"Checked {len(items)} news items, {len(entries)} change(s) logged.")


if __name__ == "__main__":
    main()
