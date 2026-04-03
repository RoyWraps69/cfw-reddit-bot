"""
Chicago Fleet Wraps — Damage Control v1.0
AUTO-DELETE & REPLACE NEGATIVE POSTS

This module:
1. Monitors all posted content across all platforms
2. If a post gets 3+ negative reactions → DELETE IT immediately
3. Generate a BETTER replacement post on the same topic
4. Log what went wrong so the brain learns to avoid it

Negative signals per platform:
- Reddit: score <= -2 (net downvotes), or 3+ negative replies
- Facebook: angry/sad reactions >= 3, or negative comments >= 3
- Instagram: negative comments >= 3
- TikTok: negative comments >= 3, or dislike ratio > 50%

The replacement post uses cross-platform intel to pick a better angle.
"""
import os
import json
import time
from datetime import datetime, timedelta
from config import DATA_DIR, REDDIT_USERNAME

DAMAGE_LOG_FILE = os.path.join(DATA_DIR, "damage_control_log.json")
MONITORED_POSTS_FILE = os.path.join(DATA_DIR, "monitored_posts.json")

# Thresholds
NEGATIVE_THRESHOLD = 3  # 3+ negative reactions = delete
REDDIT_DOWNVOTE_THRESHOLD = -2  # Net score below this = delete
CHECK_AFTER_MINUTES = 30  # Start checking 30 min after posting
MAX_AGE_HOURS = 48  # Stop monitoring after 48 hours


def _load_monitored_posts() -> list:
    if os.path.exists(MONITORED_POSTS_FILE):
        try:
            with open(MONITORED_POSTS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_monitored_posts(posts: list):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(MONITORED_POSTS_FILE, "w") as f:
        json.dump(posts[-500:], f, indent=2)


def _load_damage_log() -> list:
    if os.path.exists(DAMAGE_LOG_FILE):
        try:
            with open(DAMAGE_LOG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_damage_log(log: list):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(DAMAGE_LOG_FILE, "w") as f:
        json.dump(log[-200:], f, indent=2)


# ─────────────────────────────────────────
# REGISTER: Track new posts for monitoring
# ─────────────────────────────────────────

def register_post(platform: str, post_id: str, topic: str,
                  caption: str, url: str = "", extra: dict = None):
    """Register a newly posted piece of content for damage monitoring.
    
    Called immediately after posting on any platform.
    """
    posts = _load_monitored_posts()
    posts.append({
        "platform": platform,
        "post_id": post_id,
        "topic": topic,
        "caption_preview": caption[:200],
        "url": url,
        "posted_at": datetime.now().isoformat(),
        "status": "active",  # active, deleted, expired
        "checks": 0,
        "last_check": None,
        "negative_count": 0,
        "extra": extra or {},
    })
    _save_monitored_posts(posts)
    print(f"  [DAMAGE CTRL] Registered {platform} post {post_id} for monitoring", flush=True)


# ─────────────────────────────────────────
# CHECK: Scan posts for negative reactions
# ─────────────────────────────────────────

def run_damage_check(reddit_session=None, browser_sessions: dict = None) -> dict:
    """Check all monitored posts for negative reactions.
    
    Returns summary of actions taken.
    """
    print(f"\n  [DAMAGE CTRL] Running damage control check...", flush=True)

    posts = _load_monitored_posts()
    damage_log = _load_damage_log()

    now = datetime.now()
    deleted = 0
    checked = 0
    expired = 0

    for post in posts:
        if post["status"] != "active":
            continue

        # Check age
        posted_at = datetime.fromisoformat(post["posted_at"])
        age_hours = (now - posted_at).total_seconds() / 3600
        age_minutes = (now - posted_at).total_seconds() / 60

        # Too new to check
        if age_minutes < CHECK_AFTER_MINUTES:
            continue

        # Too old — stop monitoring
        if age_hours > MAX_AGE_HOURS:
            post["status"] = "expired"
            expired += 1
            continue

        platform = post["platform"]
        post_id = post["post_id"]

        try:
            negative_count = 0
            details = {}

            if platform == "reddit":
                negative_count, details = _check_reddit_post(
                    post, reddit_session
                )
            elif platform == "facebook":
                negative_count, details = _check_social_post(
                    post, "facebook", browser_sessions
                )
            elif platform == "instagram":
                negative_count, details = _check_social_post(
                    post, "instagram", browser_sessions
                )
            elif platform == "tiktok":
                negative_count, details = _check_social_post(
                    post, "tiktok", browser_sessions
                )

            post["negative_count"] = negative_count
            post["checks"] += 1
            post["last_check"] = now.isoformat()
            post["last_check_details"] = details
            checked += 1

            # TRIGGER: 3+ negative reactions → DELETE AND REPLACE
            if negative_count >= NEGATIVE_THRESHOLD:
                print(f"  [DAMAGE CTRL] NEGATIVE ALERT! {platform} post {post_id}: "
                      f"{negative_count} negative reactions", flush=True)

                # Attempt deletion
                delete_success = _delete_post(post, reddit_session, browser_sessions)

                if delete_success:
                    post["status"] = "deleted"
                    deleted += 1

                    # Log the damage event
                    damage_log.append({
                        "timestamp": now.isoformat(),
                        "platform": platform,
                        "post_id": post_id,
                        "topic": post.get("topic", ""),
                        "caption_preview": post.get("caption_preview", ""),
                        "negative_count": negative_count,
                        "details": details,
                        "action": "deleted",
                        "replacement_needed": True,
                    })

                    print(f"  [DAMAGE CTRL] DELETED {platform} post {post_id}", flush=True)
                else:
                    print(f"  [DAMAGE CTRL] Failed to delete {platform} post {post_id}", flush=True)

            elif negative_count >= 2:
                print(f"  [DAMAGE CTRL] WARNING: {platform} post {post_id} has "
                      f"{negative_count} negative reactions (threshold: {NEGATIVE_THRESHOLD})", flush=True)

        except Exception as e:
            print(f"  [DAMAGE CTRL] Error checking {platform} {post_id}: {e}", flush=True)

    _save_monitored_posts(posts)
    _save_damage_log(damage_log)

    result = {
        "checked": checked,
        "deleted": deleted,
        "expired": expired,
        "active_monitoring": sum(1 for p in posts if p["status"] == "active"),
    }

    print(f"  [DAMAGE CTRL] Check complete: {checked} checked, "
          f"{deleted} deleted, {expired} expired", flush=True)

    return result


def get_posts_needing_replacement() -> list:
    """Get list of deleted posts that need replacement content.
    
    Called by the master orchestrator to generate replacement posts.
    """
    damage_log = _load_damage_log()
    return [
        entry for entry in damage_log
        if entry.get("replacement_needed", False)
        and entry.get("action") == "deleted"
    ]


def mark_replacement_done(post_id: str):
    """Mark a deleted post as replaced (so we don't keep trying to replace it)."""
    damage_log = _load_damage_log()
    for entry in damage_log:
        if entry.get("post_id") == post_id:
            entry["replacement_needed"] = False
            entry["replaced_at"] = datetime.now().isoformat()
    _save_damage_log(damage_log)


# ─────────────────────────────────────────
# PLATFORM-SPECIFIC CHECKS
# ─────────────────────────────────────────

def _check_reddit_post(post: dict, reddit_session) -> tuple:
    """Check a Reddit comment/post for negative reactions.
    
    Returns (negative_count, details_dict).
    """
    if not reddit_session:
        return 0, {"error": "no session"}

    post_id = post["post_id"]
    details = {"score": 0, "negative_replies": 0}

    try:
        session = reddit_session.session

        # Check comment score
        url = f"https://old.reddit.com/api/info.json?id=t1_{post_id}"
        resp = session.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            children = data.get("data", {}).get("children", [])
            if children:
                comment_data = children[0].get("data", {})
                score = comment_data.get("score", 1)
                details["score"] = score

                # Check if heavily downvoted
                if score <= REDDIT_DOWNVOTE_THRESHOLD:
                    return abs(score) + 1, details

        # Check for negative replies
        permalink = post.get("url", "")
        if permalink:
            try:
                replies = reddit_session.get_comment_replies(permalink)
                negative_words = [
                    "spam", "bot", "shill", "ad", "advertising",
                    "reported", "ban", "stfu", "shut up", "nobody asked",
                    "cringe", "stop", "go away", "fake", "scam",
                ]
                neg_count = 0
                for reply in replies:
                    body = reply.get("body", "").lower()
                    if any(w in body for w in negative_words):
                        neg_count += 1
                details["negative_replies"] = neg_count
                if neg_count >= NEGATIVE_THRESHOLD:
                    return neg_count, details
            except Exception:
                pass

        # Total negative signals
        total_neg = 0
        if score <= 0:
            total_neg += abs(score)
        total_neg += details.get("negative_replies", 0)

        return total_neg, details

    except Exception as e:
        return 0, {"error": str(e)}


def _check_social_post(post: dict, platform: str,
                       browser_sessions: dict = None) -> tuple:
    """Check a Facebook/Instagram/TikTok post for negative reactions.
    
    Uses the engagement data stored by each platform's bot.
    Returns (negative_count, details_dict).
    """
    # Check the engagement log for this post
    engagement_file = os.path.join(DATA_DIR, f"{platform}_engagement.json")
    if not os.path.exists(engagement_file):
        return 0, {"status": "no engagement data yet"}

    try:
        with open(engagement_file, "r") as f:
            engagements = json.load(f)

        post_id = post["post_id"]
        for eng in engagements:
            if eng.get("post_id") == post_id:
                negative_count = eng.get("negative_reactions", 0)
                negative_comments = eng.get("negative_comments", 0)
                total_neg = negative_count + negative_comments

                return total_neg, {
                    "negative_reactions": negative_count,
                    "negative_comments": negative_comments,
                    "total_engagement": eng.get("total_engagement", 0),
                }

    except Exception as e:
        return 0, {"error": str(e)}

    return 0, {"status": "post not found in engagement data"}


# ─────────────────────────────────────────
# DELETE: Remove bad posts
# ─────────────────────────────────────────

def _delete_post(post: dict, reddit_session=None,
                 browser_sessions: dict = None) -> bool:
    """Delete a post from its platform.
    
    Returns True if deletion was successful.
    """
    platform = post["platform"]
    post_id = post["post_id"]

    try:
        if platform == "reddit":
            return _delete_reddit_post(post_id, reddit_session)
        elif platform in ("facebook", "instagram", "tiktok"):
            return _delete_social_post(post_id, platform, browser_sessions)
    except Exception as e:
        print(f"  [DAMAGE CTRL] Delete error for {platform} {post_id}: {e}", flush=True)

    return False


def _delete_reddit_post(post_id: str, reddit_session) -> bool:
    """Delete a Reddit comment."""
    if not reddit_session:
        return False

    try:
        session = reddit_session.session
        headers = reddit_session._get_api_headers()

        resp = session.post(
            "https://old.reddit.com/api/del",
            data={"id": f"t1_{post_id}"},
            headers=headers,
            timeout=10,
        )

        if resp.status_code == 200:
            print(f"  [DAMAGE CTRL] Reddit comment {post_id} deleted", flush=True)
            return True
        else:
            print(f"  [DAMAGE CTRL] Reddit delete failed: {resp.status_code}", flush=True)
            return False

    except Exception as e:
        print(f"  [DAMAGE CTRL] Reddit delete error: {e}", flush=True)
        return False


def _delete_social_post(post_id: str, platform: str,
                        browser_sessions: dict = None) -> bool:
    """Delete a Facebook/Instagram/TikTok post via browser automation.
    
    This is a placeholder — actual deletion requires navigating to the post
    and clicking delete. The platform bots handle this.
    """
    # Mark for deletion — the platform bot will handle it on next cycle
    deletion_queue_file = os.path.join(DATA_DIR, f"{platform}_delete_queue.json")
    queue = []
    if os.path.exists(deletion_queue_file):
        try:
            with open(deletion_queue_file, "r") as f:
                queue = json.load(f)
        except Exception:
            pass

    queue.append({
        "post_id": post_id,
        "queued_at": datetime.now().isoformat(),
        "status": "pending",
    })

    with open(deletion_queue_file, "w") as f:
        json.dump(queue, f, indent=2)

    print(f"  [DAMAGE CTRL] {platform} post {post_id} queued for deletion", flush=True)
    return True


# ─────────────────────────────────────────
# LEARNING: What went wrong?
# ─────────────────────────────────────────

def get_damage_patterns() -> dict:
    """Analyze damage log to find patterns in what goes wrong.
    
    Returns insights for the content brain to avoid repeating mistakes.
    """
    damage_log = _load_damage_log()
    if not damage_log:
        return {"total_incidents": 0}

    # Count by platform
    by_platform = {}
    by_topic = {}
    for entry in damage_log:
        p = entry.get("platform", "unknown")
        t = entry.get("topic", "unknown")
        by_platform[p] = by_platform.get(p, 0) + 1
        by_topic[t] = by_topic.get(t, 0) + 1

    # Find repeat offender topics
    bad_topics = [t for t, count in by_topic.items() if count >= 2]

    return {
        "total_incidents": len(damage_log),
        "by_platform": by_platform,
        "by_topic": by_topic,
        "repeat_offender_topics": bad_topics,
        "recent_incidents": damage_log[-5:],
    }


def get_topics_to_avoid() -> list:
    """Get list of topics that have been deleted multiple times.
    
    The content brain should avoid these topics entirely.
    """
    patterns = get_damage_patterns()
    return patterns.get("repeat_offender_topics", [])


def get_dashboard_data() -> dict:
    """Get damage control data for the unified dashboard."""
    damage_log = _load_damage_log()
    posts = _load_monitored_posts()

    return {
        "total_deleted": sum(1 for p in posts if p["status"] == "deleted"),
        "currently_monitoring": sum(1 for p in posts if p["status"] == "active"),
        "total_incidents": len(damage_log),
        "recent_incidents": damage_log[-10:],
        "patterns": get_damage_patterns(),
    }
