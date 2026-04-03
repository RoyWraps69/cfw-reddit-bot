"""
Chicago Fleet Wraps Reddit Bot — Activity Tracker
Tracks daily activity to enforce anti-ban limits.
"""
import json
import os
from datetime import datetime, date
from config import (
    DAILY_LOG_FILE, COMMENT_HISTORY_FILE,
    MAX_COMMENTS_PER_DAY, MAX_COMMENTS_PER_SUB_PER_DAY,
    DATA_DIR, LOG_DIR,
)


def _ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)


def _load_daily_log() -> dict:
    """Load today's activity log."""
    _ensure_dirs()
    if os.path.exists(DAILY_LOG_FILE):
        with open(DAILY_LOG_FILE, "r") as f:
            data = json.load(f)
            if data.get("date") == str(date.today()):
                return data
    # New day, reset
    return {
        "date": str(date.today()),
        "total_comments": 0,
        "promo_comments": 0,
        "non_promo_comments": 0,
        "subreddits_commented": {},
        "threads_commented": [],
        "dms_sent": 0,
        "threads_created": 0,
    }


def _save_daily_log(log: dict):
    _ensure_dirs()
    with open(DAILY_LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)


def can_comment() -> bool:
    """Check if we can still comment today (global limit)."""
    log = _load_daily_log()
    return log["total_comments"] < MAX_COMMENTS_PER_DAY


def can_comment_in_sub(subreddit: str) -> bool:
    """Check if we can comment in a specific subreddit today."""
    log = _load_daily_log()
    sub_count = log["subreddits_commented"].get(subreddit, 0)
    return sub_count < MAX_COMMENTS_PER_SUB_PER_DAY


def should_be_promo() -> bool:
    """Determine if the next comment should include a CFW mention (10% ratio)."""
    log = _load_daily_log()
    total = log["total_comments"]
    promo = log["promo_comments"]
    if total == 0:
        return False  # First comment of the day is never promo
    # Aim for ~10% promo rate
    current_ratio = promo / total if total > 0 else 0
    return current_ratio < 0.10


def record_comment(subreddit: str, thread_id: str, is_promo: bool, comment_text: str):
    """Record that we posted a comment."""
    log = _load_daily_log()
    log["total_comments"] += 1
    if is_promo:
        log["promo_comments"] += 1
    else:
        log["non_promo_comments"] += 1
    log["subreddits_commented"][subreddit] = log["subreddits_commented"].get(subreddit, 0) + 1
    log["threads_commented"].append({
        "thread_id": thread_id,
        "subreddit": subreddit,
        "is_promo": is_promo,
        "time": datetime.now().isoformat(),
    })
    _save_daily_log(log)

    # Also save to comment history
    _save_comment_history(subreddit, thread_id, is_promo, comment_text)


def record_dm():
    """Record that we sent a DM."""
    log = _load_daily_log()
    log["dms_sent"] += 1
    _save_daily_log(log)


def record_thread_created():
    """Record that we created a thread."""
    log = _load_daily_log()
    log["threads_created"] += 1
    _save_daily_log(log)


def _save_comment_history(subreddit: str, thread_id: str, is_promo: bool, comment_text: str):
    """Save comment to persistent history for deduplication and analysis."""
    _ensure_dirs()
    history = []
    if os.path.exists(COMMENT_HISTORY_FILE):
        with open(COMMENT_HISTORY_FILE, "r") as f:
            history = json.load(f)

    history.append({
        "date": str(date.today()),
        "time": datetime.now().isoformat(),
        "subreddit": subreddit,
        "thread_id": thread_id,
        "is_promo": is_promo,
        "comment_preview": comment_text[:200],
    })

    # Keep last 500 entries
    history = history[-500:]
    with open(COMMENT_HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def get_daily_summary() -> str:
    """Get a human-readable summary of today's activity."""
    log = _load_daily_log()
    total = log["total_comments"]
    promo = log["promo_comments"]
    non_promo = log["non_promo_comments"]
    subs = log["subreddits_commented"]
    ratio = f"{(promo/total*100):.0f}%" if total > 0 else "N/A"

    summary = f"""
Daily Activity Summary — {log['date']}
{'='*40}
Total comments:     {total}/{MAX_COMMENTS_PER_DAY}
  Promotional:      {promo} ({ratio})
  Non-promotional:  {non_promo}
DMs sent:           {log['dms_sent']}
Threads created:    {log['threads_created']}
Subreddits active:  {', '.join(subs.keys()) if subs else 'None'}
"""
    return summary
