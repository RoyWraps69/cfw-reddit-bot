"""
Chicago Fleet Wraps — Content Queue + Engagement Learning Engine v1.0

PRE-GENERATED CONTENT BARREL:
- Batch-generates posts ahead of time so posting is instant
- Tracks engagement on every post (likes, comments, shares, views)
- Learns what works and feeds insights back into content generation
- Auto-refills when queue gets low
- Gets smarter with every single post until everything is a homerun

Queue structure (data/content_queue/):
  queue.json          — list of ready-to-post content packages
  posted.json         — history of posted content + engagement scores
  learning.json       — learned patterns (what works, what doesn't)
  engagement_log.json — raw engagement data over time
"""

import os, json, time, random, logging
from datetime import datetime, timedelta
from openai import OpenAI

log = logging.getLogger("content_queue")

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
QUEUE_DIR = os.path.join(DATA_DIR, "content_queue")
QUEUE_FILE = os.path.join(QUEUE_DIR, "queue.json")
POSTED_FILE = os.path.join(QUEUE_DIR, "posted.json")
LEARNING_FILE = os.path.join(QUEUE_DIR, "learning.json")
ENGAGEMENT_LOG = os.path.join(QUEUE_DIR, "engagement_log.json")

MIN_QUEUE_SIZE = 5   # refill when below this
BATCH_SIZE = 8       # how many to generate per refill
TOP_N_LEARN = 20     # analyze top N posts to learn from

base_url = os.environ.get("OPENAI_BASE_URL", None)
_client = None

def _get_client():
    global _client
    if not _client:
        _client = OpenAI(base_url=base_url) if base_url else OpenAI()
    return _client

def _ensure_dirs():
    os.makedirs(QUEUE_DIR, exist_ok=True)

def _load_json(path, default=None):
    if default is None:
        default = []
    if os.path.exists(path):
        try:
            return json.load(open(path))
        except:
            return default
    return default

def _save_json(path, data):
    _ensure_dirs()
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


# ═══════════════════════════════════════════════════════════════
# QUEUE MANAGEMENT
# ═══════════════════════════════════════════════════════════════

def queue_size() -> int:
    """How many posts are ready in the barrel."""
    return len(_load_json(QUEUE_FILE, []))

def needs_refill() -> bool:
    """Check if queue is running low."""
    return queue_size() < MIN_QUEUE_SIZE

def pop_next() -> dict:
    """Grab the next post from the queue. Returns {} if empty."""
    queue = _load_json(QUEUE_FILE, [])
    if not queue:
        return {}
    post = queue.pop(0)
    _save_json(QUEUE_FILE, queue)
    return post

def push_to_queue(content_package: dict):
    """Add a generated content package to the queue."""
    queue = _load_json(QUEUE_FILE, [])
    content_package["queued_at"] = datetime.now().isoformat()
    content_package["queue_id"] = f"q_{int(time.time())}_{random.randint(100,999)}"
    queue.append(content_package)
    _save_json(QUEUE_FILE, queue)

def record_posted(content_package: dict, post_ids: dict):
    """Record that a post was published. post_ids = {platform: post_id}."""
    posted = _load_json(POSTED_FILE, [])
    record = {
        "content": content_package,
        "post_ids": post_ids,
        "posted_at": datetime.now().isoformat(),
        "engagement": {},  # filled in later by analyze
        "score": 0.0
    }
    posted.append(record)
    # Keep last 200 posts
    if len(posted) > 200:
        posted = posted[-200:]
    _save_json(POSTED_FILE, posted)


# ═══════════════════════════════════════════════════════════════
# ENGAGEMENT TRACKING
# ═══════════════════════════════════════════════════════════════

def collect_engagement():
    """Pull engagement stats for all recent posts from FB/IG APIs."""
    import facebook_bot, instagram_bot
    posted = _load_json(POSTED_FILE, [])
    if not posted:
        log.info("No posted history to analyze")
        return
    
    updated = 0
    for record in posted:
        # Only check posts from last 14 days
        posted_at = record.get("posted_at", "")
        try:
            post_date = datetime.fromisoformat(posted_at)
            if datetime.now() - post_date > timedelta(days=14):
                continue
        except:
            continue
        
        ids = record.get("post_ids", {})
        eng = record.get("engagement", {})
        
        # Facebook engagement
        fb_id = ids.get("facebook")
        if fb_id and not eng.get("facebook_final"):
            try:
                fb_eng = facebook_bot.get_engagement(fb_id)
                if fb_eng:
                    eng["facebook"] = fb_eng
                    # Mark as final after 3 days
                    if datetime.now() - post_date > timedelta(days=3):
                        eng["facebook_final"] = True
                    updated += 1
            except Exception as e:
                log.debug(f"FB engagement error: {e}")
        
        # Instagram engagement
        ig_id = ids.get("instagram")
        if ig_id and not eng.get("instagram_final"):
            try:
                ig_eng = instagram_bot.get_engagement(ig_id)
                if ig_eng:
                    eng["instagram"] = ig_eng
                    if datetime.now() - post_date > timedelta(days=3):
                        eng["instagram_final"] = True
                    updated += 1
            except Exception as e:
                log.debug(f"IG engagement error: {e}")
        
        record["engagement"] = eng
        record["score"] = _calculate_score(eng)
    
    _save_json(POSTED_FILE, posted)
    log.info(f"Updated engagement for {updated} posts")
    return updated

def _calculate_score(engagement: dict) -> float:
    """Calculate a unified engagement score. Higher = better."""
    score = 0.0
    for platform in ["facebook", "instagram"]:
        e = engagement.get(platform, {})
        likes = e.get("likes", 0) or e.get("like_count", 0) or e.get("reactions", {}).get("summary", {}).get("total_count", 0)
        comments = e.get("comments", 0) or e.get("comments_count", 0) or e.get("comment_count", 0)
        shares = e.get("shares", 0) or e.get("share_count", 0)
        # Comments and shares are worth more than likes
        score += likes * 1.0 + comments * 3.0 + shares * 5.0
    return round(score, 1)


# ═══════════════════════════════════════════════════════════════
# LEARNING ENGINE
# ═══════════════════════════════════════════════════════════════

def analyze_and_learn() -> dict:
    """Analyze all posted content, find patterns, update learning file.
    Returns the learning insights dict."""
    posted = _load_json(POSTED_FILE, [])
    if len(posted) < 3:
        log.info("Not enough posts to learn from yet")
        return _load_json(LEARNING_FILE, {})
    
    # Sort by score
    scored = [p for p in posted if p.get("score", 0) > 0]
    scored.sort(key=lambda x: x["score"], reverse=True)
    
    if not scored:
        log.info("No engagement data yet")
        return _load_json(LEARNING_FILE, {})
    
    # Analyze top performers vs bottom performers
    top = scored[:max(3, len(scored)//4)]
    bottom = scored[-max(3, len(scored)//4):]
    avg_score = sum(p["score"] for p in scored) / len(scored)
    
    # Extract patterns from top performers
    top_topics = []
    top_styles = []
    top_headlines = []
    top_hooks = []
    for p in top:
        c = p.get("content", {})
        decision = c.get("decision", {})
        if decision.get("topic"):
            top_topics.append(decision["topic"])
        if decision.get("style"):
            top_styles.append(decision["style"])
        captions = c.get("captions", {})
        fb_cap = captions.get("facebook", "")
        if fb_cap:
            # First line is usually the hook
            hook = fb_cap.split("\n")[0][:100]
            top_hooks.append(hook)
        headline = c.get("headline", decision.get("headline", ""))
        if headline:
            top_headlines.append(headline)
    
    # Extract patterns from bottom performers
    bottom_topics = []
    for p in bottom:
        c = p.get("content", {})
        decision = c.get("decision", {})
        if decision.get("topic"):
            bottom_topics.append(decision["topic"])
    
    # Build learning insights
    learning = {
        "updated_at": datetime.now().isoformat(),
        "total_posts_analyzed": len(scored),
        "avg_score": round(avg_score, 1),
        "best_score": round(scored[0]["score"], 1) if scored else 0,
        "top_performing_topics": top_topics[:10],
        "top_performing_styles": top_styles[:10],
        "top_hooks": top_hooks[:10],
        "top_headlines": top_headlines[:10],
        "underperforming_topics": bottom_topics[:10],
        "trend_direction": "improving" if len(scored) > 5 and 
            sum(p["score"] for p in scored[:3])/3 > avg_score else "learning",
        "insights_summary": ""
    }
    
    # Use AI to generate deeper insights if we have enough data
    if len(scored) >= 5:
        try:
            learning["insights_summary"] = _generate_ai_insights(top, bottom, avg_score)
        except Exception as e:
            log.warning(f"AI insights failed: {e}")
            learning["insights_summary"] = f"Top topics: {', '.join(top_topics[:5])}. Avoid: {', '.join(bottom_topics[:5])}"
    
    _save_json(LEARNING_FILE, learning)
    log.info(f"Learning updated: {len(scored)} posts analyzed, avg score {avg_score:.1f}")
    return learning

def _generate_ai_insights(top_posts, bottom_posts, avg_score) -> str:
    """Use AI to find patterns in what works vs what doesn't."""
    top_summary = []
    for p in top_posts[:5]:
        c = p.get("content", {})
        d = c.get("decision", {})
        cap = c.get("captions", {}).get("facebook", "")[:200]
        top_summary.append(f"Score {p['score']}: topic='{d.get('topic','')}' caption='{cap}'")
    
    bottom_summary = []
    for p in bottom_posts[:5]:
        c = p.get("content", {})
        d = c.get("decision", {})
        cap = c.get("captions", {}).get("facebook", "")[:200]
        bottom_summary.append(f"Score {p['score']}: topic='{d.get('topic','')}' caption='{cap}'")
    
    prompt = f"""You are analyzing social media performance for Chicago Fleet Wraps (vehicle wrap company).

TOP PERFORMERS (high engagement):
{chr(10).join(top_summary)}

BOTTOM PERFORMERS (low engagement):
{chr(10).join(bottom_summary)}

Average score: {avg_score}

In 3-4 sentences, identify the KEY PATTERNS:
1. What topics/styles/hooks get the most engagement?
2. What should we AVOID?
3. One specific actionable recommendation for the next batch of posts.
Be specific and data-driven."""

    resp = _get_client().chat.completions.create(
        model=os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
        temperature=0.3
    )
    return resp.choices[0].message.content.strip()

def get_learning_context() -> str:
    """Get a formatted string of learning insights to inject into content generation prompts."""
    learning = _load_json(LEARNING_FILE, {})
    if not learning or not learning.get("total_posts_analyzed"):
        return ""
    
    parts = []
    if learning.get("insights_summary"):
        parts.append(f"PERFORMANCE INSIGHTS: {learning['insights_summary']}")
    if learning.get("top_performing_topics"):
        parts.append(f"HIGH-PERFORMING TOPICS: {', '.join(learning['top_performing_topics'][:5])}")
    if learning.get("underperforming_topics"):
        parts.append(f"AVOID THESE TOPICS (low engagement): {', '.join(learning['underperforming_topics'][:5])}")
    if learning.get("top_hooks"):
        parts.append(f"HOOKS THAT WORKED: {' | '.join(learning['top_hooks'][:3])}")
    if learning.get("avg_score"):
        parts.append(f"Average engagement score: {learning['avg_score']} (beat this!)")
    
    return "\n".join(parts)


# ═══════════════════════════════════════════════════════════════
# BATCH CONTENT GENERATION (REFILL THE BARREL)
# ═══════════════════════════════════════════════════════════════

def refill_queue(count: int = None) -> int:
    """Generate a batch of posts and add them to the queue.
    Returns number of posts added."""
    from content_brain import ContentBrain
    from media_generator import create_content_package
    
    if count is None:
        count = BATCH_SIZE
    
    current = queue_size()
    log.info(f"Refilling queue: {current} in queue, generating {count} more")
    
    brain = ContentBrain()
    learning_context = get_learning_context()
    added = 0
    
    # Get topics we already have queued to avoid duplicates
    queue = _load_json(QUEUE_FILE, [])
    queued_topics = [q.get("decision", {}).get("topic", "") for q in queue]
    
    for i in range(count):
        try:
            log.info(f"  Generating post {i+1}/{count}...")
            
            # Get content decision from brain, with learning context injected
            decision = brain.decide_content(
                avoid_topics=queued_topics
            )
            
            if not decision or not decision.get("topic"):
                log.warning(f"  Brain returned empty decision for post {i+1}")
                continue
            
            # Inject learning insights into the decision
            if learning_context:
                decision["learning_context"] = learning_context
            
            # Generate the full content package (image + captions)
            package = create_content_package(decision)
            
            if not package or package.get("unique") == False:
                log.warning(f"  Content not unique, skipping")
                continue
            
            # Store the decision with the package for later analysis
            package["decision"] = decision
            
            # Add to queue
            push_to_queue(package)
            queued_topics.append(decision.get("topic", ""))
            added += 1
            log.info(f"  ✓ Post {i+1} queued: {decision.get('topic', 'unknown')}")
            
        except Exception as e:
            log.error(f"  ✗ Failed to generate post {i+1}: {e}")
            continue
    
    log.info(f"Refill complete: added {added} posts, queue now has {queue_size()}")
    return added


# ═══════════════════════════════════════════════════════════════
# FULL CYCLE HELPERS
# ═══════════════════════════════════════════════════════════════

def post_from_queue() -> dict:
    """Grab next post from queue and publish to all platforms.
    Returns {platform: post_id} dict."""
    import facebook_bot, instagram_bot
    
    post = pop_next()
    if not post:
        log.warning("Queue empty! Triggering emergency refill...")
        refill_queue(3)
        post = pop_next()
        if not post:
            log.error("Failed to generate content even after refill")
            return {}
    
    captions = post.get("captions", {})
    image_path = post.get("image_path", "")
    post_ids = {}
    
    # Post to Facebook
    try:
        fb_caption = captions.get("facebook", captions.get("default", ""))
        if image_path and os.path.exists(image_path):
            result = facebook_bot.create_post(caption=fb_caption, image_path=image_path)
        else:
            result = facebook_bot.create_post(caption=fb_caption)
        if result.get("success"):
            post_ids["facebook"] = result.get("post_id", "")
            log.info(f"✓ Facebook posted: {result.get('post_id')}")
    except Exception as e:
        log.error(f"✗ Facebook failed: {e}")
    
    # Post to Instagram
    try:
        ig_caption = captions.get("instagram", captions.get("default", ""))
        if image_path and os.path.exists(image_path):
            result = instagram_bot.create_post(caption=ig_caption, image_path=image_path)
            if result.get("success"):
                post_ids["instagram"] = result.get("post_id", result.get("media_id", ""))
                log.info(f"✓ Instagram posted: {post_ids['instagram']}")
    except Exception as e:
        log.error(f"✗ Instagram failed: {e}")
    
    # Record what was posted
    if post_ids:
        record_posted(post, post_ids)
        log.info(f"Posted to {len(post_ids)} platforms, {queue_size()} posts remaining in queue")
    
    return post_ids

def full_cycle():
    """Run the complete cycle: analyze → post → refill if needed."""
    log.info("=" * 50)
    log.info("CONTENT QUEUE — FULL CYCLE")
    log.info(f"Queue size: {queue_size()}")
    
    # Step 1: Collect engagement on past posts
    try:
        collect_engagement()
    except Exception as e:
        log.error(f"Engagement collection failed: {e}")
    
    # Step 2: Learn from engagement data
    try:
        analyze_and_learn()
    except Exception as e:
        log.error(f"Learning analysis failed: {e}")
    
    # Step 3: Post from queue
    post_ids = post_from_queue()
    
    # Step 4: Refill if running low
    if needs_refill():
        log.info(f"Queue low ({queue_size()}), refilling...")
        refill_queue()
    
    log.info(f"Cycle complete. Queue: {queue_size()} posts ready")
    return post_ids


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    
    if cmd == "refill":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else BATCH_SIZE
        refill_queue(n)
    elif cmd == "post":
        post_from_queue()
    elif cmd == "analyze":
        collect_engagement()
        learning = analyze_and_learn()
        print(json.dumps(learning, indent=2))
    elif cmd == "cycle":
        full_cycle()
    elif cmd == "status":
        q = queue_size()
        posted = len(_load_json(POSTED_FILE, []))
        learning = _load_json(LEARNING_FILE, {})
        print(f"Queue: {q} posts ready")
        print(f"Posted history: {posted} posts")
        print(f"Learning: {learning.get('total_posts_analyzed', 0)} posts analyzed")
        print(f"Avg score: {learning.get('avg_score', 'N/A')}")
        print(f"Trend: {learning.get('trend_direction', 'N/A')}")
        if learning.get("insights_summary"):
            print(f"Insights: {learning['insights_summary']}")
    else:
        print(f"Usage: python content_queue.py [refill|post|analyze|cycle|status]")
