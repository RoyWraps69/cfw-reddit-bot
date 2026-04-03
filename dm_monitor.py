"""
Chicago Fleet Wraps Reddit Bot — DM Follow-Up Monitor
Checks for positive replies to our comments and sends follow-up DMs.
"""
import json
import os
import time
import requests
from config import COMMENT_HISTORY_FILE, REDDIT_USERNAME
from ai_responder import check_positive_reply, generate_dm_message
from poster import send_dm_via_script
from tracker import record_dm


def get_recent_comment_threads() -> list[dict]:
    """Get threads we've commented on recently (for reply monitoring)."""
    if not os.path.exists(COMMENT_HISTORY_FILE):
        return []
    with open(COMMENT_HISTORY_FILE, "r") as f:
        history = json.load(f)
    # Only check promo comments from last 3 days
    recent = [h for h in history if h.get("is_promo", False)]
    return recent[-20:]  # Last 20 promo comments


def check_replies_to_our_comments():
    """
    Check if anyone replied positively to our comments.
    Uses Reddit's JSON API to check comment replies.
    """
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    # Check the user's comment replies via inbox
    try:
        url = f"https://www.reddit.com/user/{REDDIT_USERNAME}/comments.json?limit=25"
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            print(f"  [WARN] Could not fetch user comments: {resp.status_code}")
            return []

        data = resp.json()
        our_comments = []
        for item in data.get("data", {}).get("children", []):
            comment_data = item.get("data", {})
            our_comments.append({
                "id": comment_data.get("id", ""),
                "thread_id": comment_data.get("link_id", "").replace("t3_", ""),
                "thread_title": comment_data.get("link_title", ""),
                "subreddit": comment_data.get("subreddit", ""),
                "permalink": comment_data.get("permalink", ""),
                "body": comment_data.get("body", ""),
            })
        return our_comments
    except Exception as e:
        print(f"  [ERROR] Failed to check replies: {e}")
        return []


def check_comment_replies(comment_permalink: str) -> list[dict]:
    """Check for replies to a specific comment."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    replies = []

    try:
        url = f"https://www.reddit.com{comment_permalink}.json"
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if len(data) > 1:
                for item in data[1].get("data", {}).get("children", []):
                    reply_data = item.get("data", {})
                    if reply_data.get("author") and reply_data["author"] != REDDIT_USERNAME:
                        replies.append({
                            "author": reply_data.get("author", ""),
                            "body": reply_data.get("body", ""),
                            "id": reply_data.get("id", ""),
                        })
    except Exception as e:
        print(f"  [ERROR] Failed to fetch comment replies: {e}")

    return replies


def process_dm_followups():
    """Main function: check for positive replies and send DMs."""
    print("\n  [DM MONITOR] Checking for positive replies to our comments...")

    our_comments = check_replies_to_our_comments()
    if not our_comments:
        print("  [DM MONITOR] No comments found to check")
        return

    dm_sent_file = "/home/ubuntu/cfw_automation/data/dms_sent.json"
    dms_sent = set()
    if os.path.exists(dm_sent_file):
        with open(dm_sent_file, "r") as f:
            dms_sent = set(json.load(f))

    for comment in our_comments[:10]:  # Check last 10 comments
        replies = check_comment_replies(comment["permalink"])
        for reply in replies:
            reply_key = f"{reply['author']}_{reply['id']}"
            if reply_key in dms_sent:
                continue

            # Check if the reply is positive
            if check_positive_reply(reply["body"]):
                print(f"  [DM MONITOR] Positive reply from u/{reply['author']}: {reply['body'][:50]}...")

                # Generate and send DM
                dm_text = generate_dm_message(
                    username=reply["author"],
                    their_comment=reply["body"],
                    original_thread_title=comment["thread_title"],
                )

                success = send_dm_via_script(
                    username=reply["author"],
                    subject="Re: Vehicle wrap question",
                    message=dm_text,
                )

                if success:
                    dms_sent.add(reply_key)
                    record_dm()
                    print(f"  [DM MONITOR] DM sent to u/{reply['author']}")

                time.sleep(30)  # Wait between DMs

    # Save DM tracking
    with open(dm_sent_file, "w") as f:
        json.dump(list(dms_sent), f)

    print("  [DM MONITOR] Done checking replies")


if __name__ == "__main__":
    process_dm_followups()
