"""
Chicago Fleet Wraps Reddit Bot — Upvote Tracker v1.0
Checks back on our posted comments after 24h to see which ones got upvoted.
Feeds performance data back into the AI so it learns what works for this account.

Data flow:
  1. Every time we post, record_comment() saves the comment to comment_history.json
  2. This module checks old comments (12-48h old) and fetches their current score
  3. Scores are saved to data/performance_log.json
  4. The AI responder reads this log to learn what style works per subreddit
"""
import json
import os
import time
from datetime import datetime, timedelta
from config import DATA_DIR, LOG_DIR, REDDIT_USERNAME, COMMENT_HISTORY_FILE

PERFORMANCE_LOG_FILE = os.path.join(DATA_DIR, "performance_log.json")
PERFORMANCE_SUMMARY_FILE = os.path.join(DATA_DIR, "performance_summary.json")


def _load_performance_log() -> list:
    """Load the performance log (all tracked comments with scores)."""
    if os.path.exists(PERFORMANCE_LOG_FILE):
        try:
            with open(PERFORMANCE_LOG_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, Exception):
            return []
    return []


def _save_performance_log(log: list):
    """Save the performance log."""
    os.makedirs(DATA_DIR, exist_ok=True)
    # Keep last 500 entries
    log = log[-500:]
    with open(PERFORMANCE_LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)


def _load_comment_history() -> list:
    """Load comment history."""
    if os.path.exists(COMMENT_HISTORY_FILE):
        try:
            with open(COMMENT_HISTORY_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, Exception):
            return []
    return []


def check_comment_performance(reddit_session) -> dict:
    """Check performance of our recent comments.

    Fetches our last 50 comments from Reddit, matches them against
    our comment history, and records the scores.

    Returns a summary dict with stats.
    """
    print(f"\n  [UPVOTE TRACKER] Checking comment performance...", flush=True)

    # Fetch our recent comments from Reddit
    try:
        comments = reddit_session.get_my_comments(limit=50)
    except Exception as e:
        print(f"  [UPVOTE TRACKER] Error fetching comments: {e}", flush=True)
        return {"checked": 0, "new_scores": 0}

    if not comments:
        print(f"  [UPVOTE TRACKER] No comments found.", flush=True)
        return {"checked": 0, "new_scores": 0}

    # We need scores — fetch each comment's score
    perf_log = _load_performance_log()
    already_tracked = {entry["comment_id"] for entry in perf_log}

    new_scores = 0
    session = reddit_session.session

    for comment in comments:
        comment_id = comment.get("id", "")
        if not comment_id:
            continue

        # Skip if already tracked with a mature score (24h+)
        if comment_id in already_tracked:
            continue

        # Fetch the comment's current score
        try:
            permalink = comment.get("permalink", "")
            if not permalink:
                continue

            url = f"https://old.reddit.com{permalink}.json"
            resp = session.get(url, timeout=10)
            if resp.status_code != 200:
                continue

            data = resp.json()
            score = 1  # default

            # Navigate the JSON to find our comment's score
            if isinstance(data, list) and len(data) > 1:
                for child in data[1].get("data", {}).get("children", []):
                    cd = child.get("data", {})
                    if cd.get("id") == comment_id:
                        score = cd.get("score", 1)
                        break

            # Calculate comment age
            created = comment.get("created_utc", 0)
            age_hours = (time.time() - created) / 3600 if created else 0

            # Only track comments that are at least 4 hours old (enough time for votes)
            if age_hours < 4:
                continue

            entry = {
                "comment_id": comment_id,
                "subreddit": comment.get("subreddit", ""),
                "body_preview": comment.get("body", "")[:200],
                "score": score,
                "age_hours": round(age_hours, 1),
                "tracked_at": datetime.now().isoformat(),
                "link_id": comment.get("link_id", ""),
                "word_count": len(comment.get("body", "").split()),
            }

            perf_log.append(entry)
            already_tracked.add(comment_id)
            new_scores += 1

            print(f"  [UPVOTE TRACKER] r/{entry['subreddit']}: score={score}, "
                  f"age={age_hours:.0f}h, \"{entry['body_preview'][:60]}...\"", flush=True)

            time.sleep(1)  # rate limit

        except Exception as e:
            print(f"  [UPVOTE TRACKER] Error checking {comment_id}: {e}", flush=True)
            continue

    _save_performance_log(perf_log)

    # Rebuild the summary
    summary = build_performance_summary(perf_log)

    result = {"checked": len(comments), "new_scores": new_scores}
    print(f"  [UPVOTE TRACKER] Checked {result['checked']} comments, "
          f"recorded {result['new_scores']} new scores.", flush=True)

    return result


def build_performance_summary(perf_log: list = None) -> dict:
    """Build a performance summary from the log.

    This summary is what gets fed to the AI responder so it can learn
    what works for this specific account.

    Returns a dict with:
    - overall_avg_score: average score across all tracked comments
    - best_comments: top 5 highest-scoring comments
    - worst_comments: bottom 5 lowest-scoring comments
    - by_subreddit: per-sub stats (avg score, best comment, count)
    - by_length: performance by comment length bucket
    - by_vibe: performance by thread vibe (if available)
    """
    if perf_log is None:
        perf_log = _load_performance_log()

    if not perf_log:
        return {}

    # Overall stats
    scores = [e["score"] for e in perf_log]
    overall_avg = sum(scores) / len(scores) if scores else 0

    # Sort by score
    sorted_by_score = sorted(perf_log, key=lambda x: x["score"], reverse=True)

    # Best and worst
    best = sorted_by_score[:5]
    worst = sorted_by_score[-5:] if len(sorted_by_score) > 5 else []

    # By subreddit
    by_sub = {}
    for entry in perf_log:
        sub = entry.get("subreddit", "unknown")
        if sub not in by_sub:
            by_sub[sub] = {"scores": [], "best_comment": "", "best_score": 0, "count": 0}
        by_sub[sub]["scores"].append(entry["score"])
        by_sub[sub]["count"] += 1
        if entry["score"] > by_sub[sub]["best_score"]:
            by_sub[sub]["best_score"] = entry["score"]
            by_sub[sub]["best_comment"] = entry.get("body_preview", "")[:100]

    for sub in by_sub:
        by_sub[sub]["avg_score"] = round(sum(by_sub[sub]["scores"]) / len(by_sub[sub]["scores"]), 1)
        del by_sub[sub]["scores"]  # don't store raw scores in summary

    # By comment length
    by_length = {"short": {"scores": [], "count": 0}, "medium": {"scores": [], "count": 0}, "long": {"scores": [], "count": 0}}
    for entry in perf_log:
        wc = entry.get("word_count", 0)
        if wc < 20:
            bucket = "short"
        elif wc < 50:
            bucket = "medium"
        else:
            bucket = "long"
        by_length[bucket]["scores"].append(entry["score"])
        by_length[bucket]["count"] += 1

    for bucket in by_length:
        scores_list = by_length[bucket]["scores"]
        by_length[bucket]["avg_score"] = round(sum(scores_list) / len(scores_list), 1) if scores_list else 0
        del by_length[bucket]["scores"]

    summary = {
        "updated_at": datetime.now().isoformat(),
        "total_tracked": len(perf_log),
        "overall_avg_score": round(overall_avg, 1),
        "best_comments": [
            {"sub": e.get("subreddit", ""), "score": e["score"],
             "preview": e.get("body_preview", "")[:100], "word_count": e.get("word_count", 0)}
            for e in best
        ],
        "worst_comments": [
            {"sub": e.get("subreddit", ""), "score": e["score"],
             "preview": e.get("body_preview", "")[:100], "word_count": e.get("word_count", 0)}
            for e in worst
        ],
        "by_subreddit": by_sub,
        "by_length": by_length,
    }

    # Save summary
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(PERFORMANCE_SUMMARY_FILE, "w") as f:
        json.dump(summary, f, indent=2)

    return summary


def get_performance_context_for_ai(subreddit: str = None) -> str:
    """Get a formatted performance context string for the AI responder.

    This tells the AI what's been working and what hasn't,
    so it can adjust its style accordingly.
    """
    if not os.path.exists(PERFORMANCE_SUMMARY_FILE):
        return ""

    try:
        with open(PERFORMANCE_SUMMARY_FILE, "r") as f:
            summary = json.load(f)
    except Exception:
        return ""

    if not summary or summary.get("total_tracked", 0) < 3:
        return ""  # Not enough data yet

    parts = []
    parts.append(f"YOUR ACCOUNT PERFORMANCE DATA ({summary['total_tracked']} comments tracked):")
    parts.append(f"Overall average score: {summary['overall_avg_score']}")

    # Length insights
    by_len = summary.get("by_length", {})
    if by_len:
        len_parts = []
        for bucket in ["short", "medium", "long"]:
            if bucket in by_len and by_len[bucket]["count"] > 0:
                len_parts.append(f"{bucket} ({by_len[bucket]['avg_score']} avg, n={by_len[bucket]['count']})")
        if len_parts:
            parts.append(f"By length: {', '.join(len_parts)}")

    # Subreddit-specific insights
    if subreddit:
        sub_data = summary.get("by_subreddit", {}).get(subreddit)
        if sub_data:
            parts.append(f"In r/{subreddit}: avg score {sub_data['avg_score']} from {sub_data['count']} comments")
            if sub_data.get("best_comment"):
                parts.append(f"Your best comment here ({sub_data['best_score']}pts): \"{sub_data['best_comment']}\"")

    # Best performing comments overall
    best = summary.get("best_comments", [])
    if best:
        parts.append("Your top performers:")
        for b in best[:3]:
            parts.append(f"  [{b['score']}pts in r/{b['sub']}] \"{b['preview'][:80]}...\" ({b['word_count']}w)")

    return "\n".join(parts)


def get_dashboard_data() -> dict:
    """Get all performance data formatted for the dashboard.

    Returns comprehensive data for the karma dashboard page.
    """
    perf_log = _load_performance_log()
    summary = {}
    if os.path.exists(PERFORMANCE_SUMMARY_FILE):
        try:
            with open(PERFORMANCE_SUMMARY_FILE, "r") as f:
                summary = json.load(f)
        except Exception:
            pass

    # Build daily karma trend
    daily_scores = {}
    for entry in perf_log:
        date_str = entry.get("tracked_at", "")[:10]
        if date_str:
            if date_str not in daily_scores:
                daily_scores[date_str] = {"total_score": 0, "count": 0, "comments": []}
            daily_scores[date_str]["total_score"] += entry.get("score", 0)
            daily_scores[date_str]["count"] += 1
            daily_scores[date_str]["comments"].append({
                "sub": entry.get("subreddit", ""),
                "score": entry.get("score", 0),
                "preview": entry.get("body_preview", "")[:100],
            })

    return {
        "summary": summary,
        "performance_log": perf_log,
        "daily_trend": daily_scores,
    }
