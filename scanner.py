"""
Chicago Fleet Wraps Reddit Bot — Thread Scanner v3.0
NEW: Fetches top-voted comments from each thread so the AI can study
what style/tone earns karma in that specific conversation.
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
    """Set the authenticated RedditSession for all scanner requests."""
    global _auth_session
    _auth_session = reddit_session


def _get_request_session():
    """Get the requests.Session to use — authenticated if available."""
    if _auth_session and hasattr(_auth_session, 'session'):
        return _auth_session.session
    import requests
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json",
    })
    print(f"  [WARN] Using unauthenticated session — may get 403 errors", flush=True)
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
    if len(posted) > 1000:
        posted = set(list(posted)[-1000:])
    os.makedirs(os.path.dirname(POSTED_THREADS_FILE), exist_ok=True)
    with open(POSTED_THREADS_FILE, "w") as f:
        json.dump(list(posted), f)


def _fetch_reddit_json(url: str, params: dict = None, retries: int = 2) -> dict | None:
    """Fetch a Reddit JSON endpoint with retry logic and rate limiting."""
    session = _get_request_session()

    for attempt in range(retries + 1):
        try:
            resp = session.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 429:
                wait = min(30, 5 * (attempt + 1))
                print(f"  [RATE LIMIT] Waiting {wait}s...", flush=True)
                time.sleep(wait)
            elif resp.status_code == 403:
                print(f"  [403] Access denied for {url}", flush=True)
                if _auth_session and "www.reddit.com" in url:
                    alt_url = url.replace("www.reddit.com", "old.reddit.com")
                    print(f"  [RETRY] Trying old.reddit.com...", flush=True)
                    resp2 = session.get(alt_url, params=params, timeout=10)
                    if resp2.status_code == 200:
                        return resp2.json()
                return None
            else:
                print(f"  [HTTP {resp.status_code}] {url}", flush=True)
                time.sleep(2)
        except Exception as e:
            print(f"  [ERROR] {url}: {e}", flush=True)
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


# ─────────────────────────────────────────────
# NEW v3.0: Fetch top-voted comments from a thread
# This is the core intelligence upgrade — the bot now
# studies what's getting upvoted BEFORE it responds.
# ─────────────────────────────────────────────

def fetch_thread_context(thread_url: str, max_comments: int = 15) -> dict:
    """Fetch rich context from a thread: top comments with scores, OP details, and thread vibe.
    
    Returns a dict with:
    - top_comments: list of {body, score, author, is_op} sorted by score desc
    - thread_vibe: quick classification (question, discussion, rant, humor, showcase)
    - avg_comment_length: average word count of top comments
    - top_comment_style: description of what the winning comments look like
    """
    json_url = thread_url.rstrip("/") + ".json"
    data = _fetch_reddit_json(json_url, params={"sort": "top", "limit": 50})

    result = {
        "top_comments": [],
        "all_comment_texts": [],
        "thread_vibe": "unknown",
        "avg_comment_length": 0,
        "top_comment_style": "",
        "op_username": "",
    }

    if not data or not isinstance(data, list):
        return result

    # Get OP username from the post data
    if len(data) > 0:
        post_data = data[0].get("data", {}).get("children", [])
        if post_data:
            result["op_username"] = post_data[0].get("data", {}).get("author", "")

    # Parse comments
    if len(data) > 1:
        comments_raw = []
        for child in data[1].get("data", {}).get("children", []):
            cd = child.get("data", {})
            body = cd.get("body", "")
            author = cd.get("author", "")
            score = cd.get("score", 0)

            if not body or body in ("[deleted]", "[removed]"):
                continue
            if author in ("[deleted]", "AutoModerator"):
                continue

            comments_raw.append({
                "body": body[:500],  # cap length to save tokens
                "score": score if isinstance(score, int) else 0,
                "author": author,
                "is_op": author == result["op_username"],
                "word_count": len(body.split()),
            })

        # Sort by score descending
        comments_raw.sort(key=lambda x: x["score"], reverse=True)

        # Take top N
        result["top_comments"] = comments_raw[:max_comments]
        result["all_comment_texts"] = [c["body"] for c in comments_raw[:30]]

        # Calculate stats from top comments
        if comments_raw:
            top_5 = comments_raw[:5]
            word_counts = [c["word_count"] for c in top_5]
            result["avg_comment_length"] = sum(word_counts) // max(len(word_counts), 1)

            # Analyze what the top comments look like
            result["top_comment_style"] = _analyze_comment_style(top_5)

    # Classify thread vibe
    result["thread_vibe"] = _classify_thread_vibe(
        data[0].get("data", {}).get("children", [{}])[0].get("data", {}) if data[0].get("data", {}).get("children") else {},
        result["top_comments"]
    )

    return result


def _analyze_comment_style(top_comments: list) -> str:
    """Analyze the style of top-voted comments to guide AI response generation.
    Returns a human-readable style description.
    """
    if not top_comments:
        return "no data"

    avg_words = sum(c["word_count"] for c in top_comments) / len(top_comments)
    max_score = top_comments[0]["score"] if top_comments else 0

    # Check patterns
    has_questions = sum(1 for c in top_comments if "?" in c["body"])
    has_personal = sum(1 for c in top_comments if any(w in c["body"].lower() for w in ["i ", "my ", "i'm", "i've", "my "]))
    has_humor = sum(1 for c in top_comments if any(w in c["body"].lower() for w in ["lol", "lmao", "haha", "😂", "💀", "bruh"]))
    has_technical = sum(1 for c in top_comments if any(w in c["body"].lower() for w in ["because", "actually", "specifically", "technically"]))
    has_links = sum(1 for c in top_comments if "http" in c["body"] or "www." in c["body"])

    style_parts = []

    # Length
    if avg_words < 20:
        style_parts.append("very short (under 20 words)")
    elif avg_words < 50:
        style_parts.append("short-medium (20-50 words)")
    elif avg_words < 100:
        style_parts.append("medium (50-100 words)")
    else:
        style_parts.append("detailed (100+ words)")

    # Tone
    if has_humor >= 2:
        style_parts.append("humorous/casual tone")
    elif has_personal >= 3:
        style_parts.append("personal experience sharing")
    elif has_technical >= 2:
        style_parts.append("technical/informative tone")
    else:
        style_parts.append("conversational tone")

    # Structure
    if has_questions >= 2:
        style_parts.append("includes follow-up questions")
    if has_links >= 2:
        style_parts.append("includes references/links")

    return f"Top comments are {', '.join(style_parts)}. Highest score: {max_score}."


def _classify_thread_vibe(post_data: dict, top_comments: list) -> str:
    """Quick classification of thread type based on title and content patterns."""
    title = post_data.get("title", "").lower()
    body = post_data.get("selftext", "").lower()
    text = title + " " + body

    # Question thread
    if "?" in title or any(w in title for w in ["how", "what", "why", "where", "anyone", "recommend", "advice", "help", "tips", "should i"]):
        return "question"

    # Showcase/brag
    if any(w in title for w in ["just got", "just finished", "check out", "new wrap", "finally", "before and after", "just picked up"]):
        return "showcase"

    # Rant/complaint
    if any(w in text for w in ["terrible", "worst", "scam", "ripped off", "never again", "warning", "avoid", "disappointed"]):
        return "rant"

    # Humor
    if any(w in text for w in ["lol", "lmao", "haha", "meme", "funny"]):
        return "humor"

    # Discussion
    if any(w in title for w in ["thoughts on", "opinion", "debate", "vs", "compared to", "which"]):
        return "discussion"

    # News/info
    if any(w in title for w in ["new", "announced", "update", "recall", "report"]):
        return "news"

    return "discussion"  # default


def get_thread_comments(thread_url: str) -> list[str]:
    """Fetch existing comment texts from a thread (backwards compatible)."""
    json_url = thread_url.rstrip("/") + ".json"
    data = _fetch_reddit_json(json_url)
    comments = []
    if data and isinstance(data, list) and len(data) > 1:
        for comment in data[1].get("data", {}).get("children", []):
            comment_data = comment.get("data", {})
            body = comment_data.get("body", "")
            if body and body not in ("[deleted]", "[removed]"):
                comments.append(body)
    return comments


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
    keyword_batches = []
    for i in range(0, len(keywords), 3):
        batch = keywords[i:i+3]
        keyword_batches.append(" OR ".join(batch))

    for query in keyword_batches[:5]:
        url = f"https://www.reddit.com/r/{subreddit}/search.json"
        params = {
            "q": query,
            "restrict_sr": "on",
            "sort": "new",
            "t": "week",
            "limit": 10,
        }
        data = _fetch_reddit_json(url, params=params)
        if data:
            posts = _parse_posts(data, subreddit)
            for p in posts:
                p["keyword_matched"] = query.split(" OR ")[0]
            threads.extend(posts)
        time.sleep(1.5)

    return threads


def filter_threads(threads: list[dict], mode: str = "normal") -> list[dict]:
    """Filter threads based on playbook rules."""
    posted = load_posted_threads()

    if mode == "warming":
        cutoff = time.time() - (24 * 3600)
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
        if tid in seen:
            continue
        seen.add(tid)
        if tid in posted:
            continue
        if t["created_utc"] < cutoff:
            continue
        if t["num_comments"] >= max_comments:
            continue
        if not t["title"] or t["title"] in ("[deleted]", "[removed]"):
            continue
        if t["score"] < min_score:
            continue
        filtered.append(t)

    return filtered


def score_warming_thread(t: dict) -> float:
    """Score a warming thread for maximum karma potential."""
    score = 0.0
    score += min(t["score"], 500) * 0.5

    if 5 <= t["num_comments"] <= 30:
        score += 50
    elif t["num_comments"] < 5:
        score += 30
    elif t["num_comments"] <= 80:
        score += 20

    if t.get("is_self"):
        score += 20

    score += t.get("upvote_ratio", 0.5) * 30

    age_hours = (time.time() - t["created_utc"]) / 3600
    if 1 <= age_hours <= 6:
        score += 40
    elif age_hours < 1:
        score += 25
    elif age_hours <= 12:
        score += 15

    title_lower = t["title"].lower()
    if any(q in title_lower for q in ["?", "what", "how", "why", "anyone", "recommend", "advice", "help", "tips", "thoughts"]):
        score += 30

    return score


def find_warming_opportunities() -> list[dict]:
    """Find the best threads for account warming."""
    print(f"\n  WARMING SCAN v3.0 — Context-aware targeting", flush=True)

    opportunities = []
    subs = list(WARMING_SUBREDDITS)
    random.shuffle(subs)

    for sub in subs[:10]:
        print(f"  Scanning r/{sub} (warming)...", flush=True)

        posts = []
        if WARMING_PREFER_RISING:
            rising = fetch_subreddit_posts(sub, sort="rising", limit=15)
            posts.extend(rising)
            time.sleep(1)

        hot = fetch_subreddit_posts(sub, sort="hot", limit=15)
        posts.extend(hot)
        time.sleep(1)

        filtered = filter_threads(posts, mode="warming")

        for t in filtered:
            t["warming_score"] = score_warming_thread(t)
            t["response_type"] = "warming"
            t["should_mention_cfw"] = False

        filtered.sort(key=lambda x: x["warming_score"], reverse=True)
        opportunities.extend(filtered[:3])

    opportunities.sort(key=lambda x: x.get("warming_score", 0), reverse=True)
    result = opportunities[:WARMING_COMMENTS_PER_CYCLE * 3]

    print(f"\n  Found {len(result)} warming opportunities (top {WARMING_COMMENTS_PER_CYCLE * 3})", flush=True)
    for t in result[:10]:
        print(f"    [{t['warming_score']:.0f}] r/{t['subreddit']}: {t['title'][:55]}... (score:{t['score']}, comments:{t['num_comments']})", flush=True)

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


def find_opportunities(mode: str = "normal") -> list[dict]:
    """Main scanning function. Finds the best threads to respond to."""
    seasonal = get_seasonal_config()
    print(f"\n{'='*60}", flush=True)
    print(f"  SCAN STARTED v3.0 — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print(f"  Mode: {mode}", flush=True)
    print(f"  Season: {seasonal['note']}", flush=True)
    if _auth_session:
        print(f"  Auth: Using authenticated session", flush=True)
    else:
        print(f"  Auth: WARNING — no authenticated session set!", flush=True)
    print(f"{'='*60}\n", flush=True)

    if mode == "warming":
        return find_warming_opportunities()

    all_threads = []
    focus_subs = seasonal["focus_subs"]
    focus_keywords = seasonal["focus_keywords"]

    seen_subs = set()
    unique_subs = []
    for s in focus_subs:
        if s.lower() not in seen_subs:
            seen_subs.add(s.lower())
            unique_subs.append(s)
    focus_subs = unique_subs

    for sub in focus_subs:
        print(f"  Scanning r/{sub}...", flush=True)
        keyword_threads = search_subreddit(sub, focus_keywords[:9], max_results=10)
        all_threads.extend(keyword_threads)

        for sort in ["new", "rising"]:
            posts = fetch_subreddit_posts(sub, sort=sort, limit=15)
            for post in posts:
                relevant, matched_kw = is_keyword_relevant(post["title"], post["body"], focus_keywords)
                if relevant:
                    post["keyword_matched"] = matched_kw
                    all_threads.append(post)
                has_competitor, comp_name = check_for_competitor_mentions(post["title"], post["body"])
                if has_competitor:
                    post["keyword_matched"] = f"competitor:{comp_name}"
                    post["competitor_mentioned"] = comp_name
                    all_threads.append(post)
            time.sleep(1)
        time.sleep(1)

    filtered = filter_threads(all_threads)

    scored = []
    for t in filtered:
        score = 0
        if t.get("keyword_matched"):
            kw = t["keyword_matched"]
            if any(pk in kw for pk in PRIMARY_KEYWORDS):
                score += 100
            elif any(sk in kw for sk in SECONDARY_KEYWORDS):
                score += 70
            elif "competitor:" in kw:
                score += 90
            else:
                score += 40
        score += max(0, 20 - t["num_comments"]) * 2
        age_hours = (time.time() - t["created_utc"]) / 3600
        score += max(0, int((MAX_THREAD_AGE_HOURS - age_hours) * 10))
        if t["score"] > 1:
            score += min(t["score"], 50) * 0.5
        t["opportunity_score"] = score
        scored.append(t)

    scored.sort(key=lambda x: x["opportunity_score"], reverse=True)

    print(f"\n  Found {len(scored)} opportunities", flush=True)
    for t in scored[:10]:
        print(f"    [{t['opportunity_score']:.0f}] r/{t['subreddit']}: {t['title'][:60]}...", flush=True)

    return scored


if __name__ == "__main__":
    opps = find_opportunities(mode="warming")
    print(f"\nTotal warming opportunities found: {len(opps)}", flush=True)
