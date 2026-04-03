"""
Chicago Fleet Wraps Reddit Bot — Thread Scanner v2.1
Fixed: Uses authenticated RedditSession for all requests (prevents 403 on datacenter IPs).
Optimized for faster warming, smarter scanning, and efficient API usage.
"""
import json
import os
import time
import re
import random
from datetime import datetime, timedelta
from config import (
    ALL_TARGET_SUBS, ALL_KEYWORDS, COMPETITORS,
    MAX_THREAD_AGE_HOURS, MAX_THREAD_COMMENTS,
    WARMING_SUBREDDITS, POSTED_THREADS_FILE,
    PRIMARY_KEYWORDS, SECONDARY_KEYWORDS, TERTIARY_KEYWORDS,
    TIER1_LOCAL, TIER2_VEHICLE, TIER3_COMMERCIAL, INDUSTRY_SUBS,
    WARMING_MIN_SCORE, WARMING_MAX_EXISTING_COMMENTS,
    WARMING_PREFER_RISING, WARMING_COMMENTS_PER_CYCLE,
    get_seasonal_config,
)

# Module-level reference to the authenticated session — set via set_session()
_auth_session = None


def set_session(reddit_session):
    """Set the authenticated RedditSession for all scanner requests.
    Must be called before any scanning functions.
    """
    global _auth_session
    _auth_session = reddit_session


def _get_request_session():
    """Get the requests.Session to use — authenticated if available."""
    if _auth_session and hasattr(_auth_session, 'session'):
        return _auth_session.session
    # Fallback to a plain session (will likely get 403 on datacenter IPs)
    import requests
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json",
    })
    print("  [WARN] Using unauthenticated session — may get 403 errors")
    return s


def load_posted_threads() -> set:
    """Load the set of thread IDs we've already responded to."""
    if os.path.exists(POSTED_THREADS_FILE):
        try:
            with open(POSTED_THREADS_FILE, "r") as f:
                return set(json.load(f))
        except (json.JSONDecodeError, Exception):
            return set()
    return set()


def save_posted_thread(thread_id: str):
    """Add a thread ID to the posted set."""
    posted = load_posted_threads()
    posted.add(thread_id)
    # Keep only last 1000 to prevent file bloat
    if len(posted) > 1000:
        posted = set(list(posted)[-1000:])
    os.makedirs(os.path.dirname(POSTED_THREADS_FILE), exist_ok=True)
    with open(POSTED_THREADS_FILE, "w") as f:
        json.dump(list(posted), f)


def _fetch_reddit_json(url: str, params: dict = None, retries: int = 2) -> dict | None:
    """Fetch a Reddit JSON endpoint with retry logic and rate limiting.
    Uses the authenticated session to avoid 403 blocks.
    """
    session = _get_request_session()
    
    for attempt in range(retries + 1):
        try:
            resp = session.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 429:
                # Rate limited — back off
                wait = min(30, 5 * (attempt + 1))
                print(f"  [RATE LIMIT] Waiting {wait}s...")
                time.sleep(wait)
            elif resp.status_code == 403:
                print(f"  [403] Access denied for {url}")
                # If using authenticated session and still 403, try old.reddit.com
                if _auth_session and "www.reddit.com" in url:
                    alt_url = url.replace("www.reddit.com", "old.reddit.com")
                    print(f"  [RETRY] Trying old.reddit.com...")
                    resp2 = session.get(alt_url, params=params, timeout=10)
                    if resp2.status_code == 200:
                        return resp2.json()
                    print(f"  [403] old.reddit.com also denied")
                return None
            else:
                print(f"  [HTTP {resp.status_code}] {url}")
                time.sleep(2)
        except Exception as e:
            print(f"  [ERROR] {url}: {e}")
            if attempt < retries:
                time.sleep(2)
            else:
                return None
    return None


def _parse_posts(data: dict, subreddit: str = "") -> list[dict]:
    """Parse Reddit listing JSON into standardized thread dicts."""
    threads = []
    for post in data.get("data", {}).get("children", []):
        pd = post.get("data", {})
        if not pd.get("id"):
            continue
        threads.append({
            "id": pd.get("id", ""),
            "title": pd.get("title", ""),
            "body": pd.get("selftext", ""),
            "subreddit": pd.get("subreddit", subreddit),
            "url": f"https://www.reddit.com{pd.get('permalink', '')}",
            "created_utc": pd.get("created_utc", 0),
            "num_comments": pd.get("num_comments", 0),
            "score": pd.get("score", 0),
            "upvote_ratio": pd.get("upvote_ratio", 0.5),
            "is_self": pd.get("is_self", True),
            "keyword_matched": None,
        })
    return threads


def fetch_subreddit_posts(subreddit: str, sort: str = "new", limit: int = 25) -> list[dict]:
    """Fetch posts from a subreddit sorted by new, hot, or rising."""
    url = f"https://www.reddit.com/r/{subreddit}/{sort}.json"
    data = _fetch_reddit_json(url, params={"limit": limit})
    if data:
        return _parse_posts(data, subreddit)
    return []


def search_subreddit(subreddit: str, keywords: list[str], max_results: int = 10) -> list[dict]:
    """Search a subreddit with batched keywords for efficiency."""
    threads = []
    
    # Batch keywords into groups of 3 using OR syntax for fewer API calls
    keyword_batches = []
    for i in range(0, len(keywords), 3):
        batch = keywords[i:i+3]
        keyword_batches.append(" OR ".join(batch))
    
    for query in keyword_batches[:5]:  # Max 5 batched queries per sub
        url = f"https://www.reddit.com/r/{subreddit}/search.json"
        params = {
            "q": query,
            "restrict_sr": "on",
            "sort": "new",
            "t": "week",  # Expanded from "day" to "week" for more results
            "limit": 10,
        }
        data = _fetch_reddit_json(url, params=params)
        if data:
            posts = _parse_posts(data, subreddit)
            for p in posts:
                p["keyword_matched"] = query.split(" OR ")[0]  # Tag with first keyword
            threads.extend(posts)
        time.sleep(1.5)  # Slightly faster than before but still polite
    
    return threads


def filter_threads(threads: list[dict], mode: str = "normal") -> list[dict]:
    """Filter threads based on playbook rules (age, comment count, not already posted)."""
    posted = load_posted_threads()
    
    if mode == "warming":
        # Warming: wider window, prefer threads with some traction
        cutoff = time.time() - (24 * 3600)  # Last 24 hours for warming
        max_comments = WARMING_MAX_EXISTING_COMMENTS
        min_score = WARMING_MIN_SCORE
    else:
        cutoff = time.time() - (MAX_THREAD_AGE_HOURS * 3600)
        max_comments = MAX_THREAD_COMMENTS
        min_score = 0
    
    filtered = []
    seen = set()
    
    for t in threads:
        tid = t["id"]
        # Skip duplicates
        if tid in seen:
            continue
        seen.add(tid)
        # Skip if already responded
        if tid in posted:
            continue
        # Skip if too old
        if t["created_utc"] < cutoff:
            continue
        # Skip if too many comments
        if t["num_comments"] >= max_comments:
            continue
        # Skip if empty/deleted
        if not t["title"] or t["title"] in ("[deleted]", "[removed]"):
            continue
        # Skip if below minimum score (for warming)
        if t["score"] < min_score:
            continue
        filtered.append(t)
    
    return filtered


def score_warming_thread(t: dict) -> float:
    """Score a warming thread for maximum karma potential."""
    score = 0.0
    
    # High-score threads = more eyeballs = more upvotes on your comment
    score += min(t["score"], 500) * 0.5
    
    # Sweet spot: 5-30 comments (active but not buried)
    if 5 <= t["num_comments"] <= 30:
        score += 50
    elif t["num_comments"] < 5:
        score += 30  # Early = good but less traffic
    elif t["num_comments"] <= 80:
        score += 20  # Still okay
    
    # Prefer self posts (text) — easier to comment on
    if t.get("is_self"):
        score += 20
    
    # Prefer threads with high upvote ratio (community likes it)
    score += t.get("upvote_ratio", 0.5) * 30
    
    # Prefer threads 1-6 hours old (sweet spot for visibility)
    age_hours = (time.time() - t["created_utc"]) / 3600
    if 1 <= age_hours <= 6:
        score += 40
    elif age_hours < 1:
        score += 25  # Very new, might not get traction
    elif age_hours <= 12:
        score += 15
    
    # Bonus for question-style titles (easy to reply to)
    title_lower = t["title"].lower()
    if any(q in title_lower for q in ["?", "what", "how", "why", "anyone", "recommend", "advice", "help", "tips", "thoughts"]):
        score += 30
    
    return score


def find_warming_opportunities() -> list[dict]:
    """Find the best threads for account warming — optimized for fast karma building."""
    print(f"\n  WARMING SCAN — Targeting high-karma subreddits")
    
    opportunities = []
    
    # Shuffle warming subs to vary which ones we hit each cycle
    subs = list(WARMING_SUBREDDITS)
    random.shuffle(subs)
    
    for sub in subs[:10]:  # Scan 10 random warming subs per cycle
        print(f"  Scanning r/{sub} (warming)...")
        
        # Fetch both rising and hot — rising gives the best karma ROI
        posts = []
        if WARMING_PREFER_RISING:
            rising = fetch_subreddit_posts(sub, sort="rising", limit=15)
            posts.extend(rising)
            time.sleep(1)
        
        hot = fetch_subreddit_posts(sub, sort="hot", limit=15)
        posts.extend(hot)
        time.sleep(1)
        
        # Filter
        filtered = filter_threads(posts, mode="warming")
        
        # Score each thread for karma potential
        for t in filtered:
            t["warming_score"] = score_warming_thread(t)
            t["response_type"] = "warming"
            t["should_mention_cfw"] = False
        
        # Take top 3 from each sub
        filtered.sort(key=lambda x: x["warming_score"], reverse=True)
        opportunities.extend(filtered[:3])
    
    # Sort all opportunities by warming score and return the best ones
    opportunities.sort(key=lambda x: x["warming_score"], reverse=True)
    
    # Return more than we need — the bot will pick the top N
    result = opportunities[:WARMING_COMMENTS_PER_CYCLE * 3]
    
    print(f"\n  Found {len(result)} warming opportunities (top {WARMING_COMMENTS_PER_CYCLE * 3})")
    for t in result[:10]:
        print(f"    [{t['warming_score']:.0f}] r/{t['subreddit']}: {t['title'][:55]}... (score:{t['score']}, comments:{t['num_comments']})")
    
    return result


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
    comments = []
    json_url = thread_url.rstrip("/") + ".json"
    data = _fetch_reddit_json(json_url)
    
    if data and isinstance(data, list) and len(data) > 1:
        for comment in data[1].get("data", {}).get("children", []):
            comment_data = comment.get("data", {})
            body = comment_data.get("body", "")
            if body and body not in ("[deleted]", "[removed]"):
                comments.append(body)
    
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
    if _auth_session:
        print(f"  Auth: Using authenticated session")
    else:
        print(f"  Auth: WARNING — no authenticated session set!")
    print(f"{'='*60}\n")

    if mode == "warming":
        return find_warming_opportunities()

    # Normal mode: scan target subreddits
    all_threads = []
    focus_subs = seasonal["focus_subs"]
    focus_keywords = seasonal["focus_keywords"]

    # Deduplicate focus subs
    seen_subs = set()
    unique_subs = []
    for s in focus_subs:
        if s.lower() not in seen_subs:
            seen_subs.add(s.lower())
            unique_subs.append(s)
    focus_subs = unique_subs

    for sub in focus_subs:
        print(f"  Scanning r/{sub}...")

        # Method 1: Search by keywords (batched for efficiency)
        keyword_threads = search_subreddit(sub, focus_keywords[:9], max_results=10)
        all_threads.extend(keyword_threads)

        # Method 2: Browse new and rising posts for relevance
        for sort in ["new", "rising"]:
            posts = fetch_subreddit_posts(sub, sort=sort, limit=15)
            for post in posts:
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
            time.sleep(1)

        time.sleep(1)  # Rate limit between subreddits

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
        # Boost threads with some traction (score > 1)
        if t["score"] > 1:
            score += min(t["score"], 50) * 0.5
        t["opportunity_score"] = score
        scored.append(t)

    scored.sort(key=lambda x: x["opportunity_score"], reverse=True)

    print(f"\n  Found {len(scored)} opportunities")
    for t in scored[:10]:
        print(f"    [{t['opportunity_score']:.0f}] r/{t['subreddit']}: {t['title'][:60]}...")

    return scored


if __name__ == "__main__":
    # Test scan
    opps = find_opportunities(mode="warming")
    print(f"\nTotal warming opportunities found: {len(opps)}")
