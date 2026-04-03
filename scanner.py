"""
Chicago Fleet Wraps Reddit Bot — Thread Scanner
Scans target subreddits for relevant threads using Reddit's search and browsing.
"""
import json
import os
import time
import re
import requests
from datetime import datetime, timedelta
from config import (
    ALL_TARGET_SUBS, ALL_KEYWORDS, COMPETITORS,
    MAX_THREAD_AGE_HOURS, MAX_THREAD_COMMENTS,
    WARMING_SUBREDDITS, POSTED_THREADS_FILE,
    PRIMARY_KEYWORDS, SECONDARY_KEYWORDS, TERTIARY_KEYWORDS,
    TIER1_LOCAL, TIER2_VEHICLE, TIER3_COMMERCIAL, INDUSTRY_SUBS,
    get_seasonal_config,
)


def load_posted_threads() -> set:
    """Load the set of thread IDs we've already responded to."""
    if os.path.exists(POSTED_THREADS_FILE):
        with open(POSTED_THREADS_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_posted_thread(thread_id: str):
    """Add a thread ID to the posted set."""
    posted = load_posted_threads()
    posted.add(thread_id)
    with open(POSTED_THREADS_FILE, "w") as f:
        json.dump(list(posted), f)


def search_subreddit(subreddit: str, keywords: list[str], max_results: int = 10) -> list[dict]:
    """Search a subreddit for threads matching keywords using Reddit's JSON API (no auth needed)."""
    threads = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    for keyword in keywords:
        try:
            url = f"https://www.reddit.com/r/{subreddit}/search.json"
            params = {
                "q": keyword,
                "restrict_sr": "on",
                "sort": "new",
                "t": "day",
                "limit": 5,
            }
            resp = requests.get(url, headers=headers, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                for post in data.get("data", {}).get("children", []):
                    post_data = post.get("data", {})
                    threads.append({
                        "id": post_data.get("id", ""),
                        "title": post_data.get("title", ""),
                        "body": post_data.get("selftext", ""),
                        "subreddit": post_data.get("subreddit", subreddit),
                        "url": f"https://www.reddit.com{post_data.get('permalink', '')}",
                        "created_utc": post_data.get("created_utc", 0),
                        "num_comments": post_data.get("num_comments", 0),
                        "score": post_data.get("score", 0),
                        "keyword_matched": keyword,
                    })
            time.sleep(2)  # Rate limit: be polite
        except Exception as e:
            print(f"  [ERROR] Search failed for r/{subreddit} keyword '{keyword}': {e}")
            continue

    return threads


def scan_new_posts(subreddit: str, limit: int = 25) -> list[dict]:
    """Fetch the newest posts from a subreddit using Reddit's JSON API."""
    threads = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    try:
        url = f"https://www.reddit.com/r/{subreddit}/new.json?limit={limit}"
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            for post in data.get("data", {}).get("children", []):
                post_data = post.get("data", {})
                threads.append({
                    "id": post_data.get("id", ""),
                    "title": post_data.get("title", ""),
                    "body": post_data.get("selftext", ""),
                    "subreddit": post_data.get("subreddit", subreddit),
                    "url": f"https://www.reddit.com{post_data.get('permalink', '')}",
                    "created_utc": post_data.get("created_utc", 0),
                    "num_comments": post_data.get("num_comments", 0),
                    "score": post_data.get("score", 0),
                    "keyword_matched": None,
                })
    except Exception as e:
        print(f"  [ERROR] Failed to fetch new posts from r/{subreddit}: {e}")

    return threads


def filter_threads(threads: list[dict]) -> list[dict]:
    """Filter threads based on playbook rules (age, comment count, not already posted)."""
    posted = load_posted_threads()
    cutoff = time.time() - (MAX_THREAD_AGE_HOURS * 3600)
    filtered = []

    for t in threads:
        # Skip if already responded
        if t["id"] in posted:
            continue
        # Skip if too old
        if t["created_utc"] < cutoff:
            continue
        # Skip if too many comments
        if t["num_comments"] >= MAX_THREAD_COMMENTS:
            continue
        # Skip if empty/deleted
        if not t["title"] or t["title"] == "[deleted]":
            continue
        filtered.append(t)

    # Deduplicate by ID
    seen = set()
    unique = []
    for t in filtered:
        if t["id"] not in seen:
            seen.add(t["id"])
            unique.append(t)

    return unique


def is_keyword_relevant(title: str, body: str, keywords: list[str]) -> tuple[bool, str]:
    """Check if a thread's title or body contains any of the target keywords."""
    text = (title + " " + body).lower()
    for kw in keywords:
        if kw.lower() in text:
            return True, kw
    return False, ""


def check_for_competitor_mentions(title: str, body: str) -> tuple[bool, str]:
    """Check if a thread mentions any competitors."""
    text = (title + " " + body).lower()
    for comp in COMPETITORS:
        if comp.lower() in text:
            return True, comp
    return False, ""


def get_thread_comments(thread_url: str) -> list[str]:
    """Fetch existing comments from a thread using Reddit's JSON API."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    comments = []

    try:
        json_url = thread_url.rstrip("/") + ".json"
        resp = requests.get(json_url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if len(data) > 1:
                for comment in data[1].get("data", {}).get("children", []):
                    comment_data = comment.get("data", {})
                    body = comment_data.get("body", "")
                    if body and body != "[deleted]" and body != "[removed]":
                        comments.append(body)
    except Exception as e:
        print(f"  [ERROR] Failed to fetch comments: {e}")

    return comments


def find_opportunities(mode: str = "normal") -> list[dict]:
    """
    Main scanning function. Finds the best threads to respond to.
    mode: "warming" for account warming, "normal" for regular operation
    """
    seasonal = get_seasonal_config()
    print(f"\n{'='*60}")
    print(f"  SCAN STARTED — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Mode: {mode}")
    print(f"  Season: {seasonal['note']}")
    print(f"{'='*60}\n")

    if mode == "warming":
        # During warming, scan casual subreddits for easy comment opportunities
        opportunities = []
        for sub in WARMING_SUBREDDITS:
            print(f"  Scanning r/{sub} (warming)...")
            posts = scan_new_posts(sub, limit=10)
            filtered = filter_threads(posts)
            for t in filtered[:2]:  # Take top 2 from each
                t["response_type"] = "warming"
                t["should_mention_cfw"] = False
                opportunities.append(t)
            time.sleep(2)
        return opportunities[:5]

    # Normal mode: scan target subreddits
    all_threads = []
    focus_subs = seasonal["focus_subs"]
    focus_keywords = seasonal["focus_keywords"]

    for sub in focus_subs:
        print(f"  Scanning r/{sub}...")

        # Method 1: Search by keywords
        keyword_threads = search_subreddit(sub, focus_keywords[:5], max_results=5)
        all_threads.extend(keyword_threads)

        # Method 2: Browse new posts and check for relevance
        new_posts = scan_new_posts(sub, limit=15)
        for post in new_posts:
            # Check keyword relevance
            relevant, matched_kw = is_keyword_relevant(post["title"], post["body"], focus_keywords)
            if relevant:
                post["keyword_matched"] = matched_kw
                all_threads.append(post)

            # Check competitor mentions
            has_competitor, comp_name = check_for_competitor_mentions(post["title"], post["body"])
            if has_competitor:
                post["keyword_matched"] = f"competitor:{comp_name}"
                post["competitor_mentioned"] = comp_name
                all_threads.append(post)

        time.sleep(2)  # Rate limit between subreddits

    # Filter and deduplicate
    filtered = filter_threads(all_threads)

    # Score and sort opportunities
    scored = []
    for t in filtered:
        score = 0
        # Prioritize by keyword tier
        if t.get("keyword_matched"):
            kw = t["keyword_matched"]
            if any(pk in kw for pk in PRIMARY_KEYWORDS):
                score += 100
            elif any(sk in kw for sk in SECONDARY_KEYWORDS):
                score += 70
            elif "competitor:" in kw:
                score += 90  # Competitor mentions are high priority
            else:
                score += 40
        # Boost low-comment threads (easier to be first)
        score += max(0, 20 - t["num_comments"]) * 2
        # Boost recent threads
        age_hours = (time.time() - t["created_utc"]) / 3600
        score += max(0, int((MAX_THREAD_AGE_HOURS - age_hours) * 10))
        t["opportunity_score"] = score
        scored.append(t)

    scored.sort(key=lambda x: x["opportunity_score"], reverse=True)

    print(f"\n  Found {len(scored)} opportunities")
    for t in scored[:10]:
        print(f"    [{t['opportunity_score']}] r/{t['subreddit']}: {t['title'][:60]}...")

    return scored


if __name__ == "__main__":
    # Test scan
    opps = find_opportunities(mode="normal")
    print(f"\nTotal opportunities found: {len(opps)}")
