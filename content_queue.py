"""
Chicago Fleet Wraps — Content Queue + Engagement Learning Engine v2.0

SELF-IMPROVING CONTENT BARREL:
- Pre-built posts with AI images + geo/SEO/AI-optimized captions
- FB: 4 posts/day (business pain points, ROI, insider knowledge)
- IG: 12 posts/day (tips, behind-the-scenes, wrap knowledge giveaways)
- Every post ends with an engagement question for business owners
- Smart scheduling: randomized times based on engagement metrics
- Tracks engagement on every post (likes, comments, shares, views)
- Learns what works and feeds insights back into content generation
- Auto-refills when queue gets low
- Gets smarter with every single post until everything is a homerun

Queue structure (data/content_queue/):
  queue.json          — list of ready-to-post content packages (with image_url)
  posted.json         — history of posted content + engagement scores
  learning.json       — learned patterns (what works, what doesn't)
  schedule.json       — optimized posting schedule (learns from engagement)
  audit_log.json      — weekly profile audit results
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
SCHEDULE_FILE = os.path.join(QUEUE_DIR, "schedule.json")
AUDIT_LOG = os.path.join(QUEUE_DIR, "audit_log.json")

# ── CADENCE ──
FB_POSTS_PER_DAY = 4
IG_POSTS_PER_DAY = 12
TOTAL_POSTS_PER_DAY = FB_POSTS_PER_DAY + IG_POSTS_PER_DAY  # 16

MIN_QUEUE_SIZE = TOTAL_POSTS_PER_DAY * 2   # 2 days buffer = 32
BATCH_SIZE = TOTAL_POSTS_PER_DAY           # generate 1 full day per refill

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
        except Exception:
            return default
    return default


def _save_json(path, data):
    _ensure_dirs()
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


# ═══════════════════════════════════════════════════════════════
# SMART SCHEDULING
# ═══════════════════════════════════════════════════════════════

def _get_default_schedule():
    """Default posting schedule (CDT). Will be optimized over time."""
    return {
        "facebook": {
            "slots": [
                {"hour": 7, "minute": 15, "label": "early_morning"},
                {"hour": 11, "minute": 30, "label": "lunch"},
                {"hour": 15, "minute": 45, "label": "afternoon"},
                {"hour": 19, "minute": 0, "label": "evening"},
            ],
            "best_hours": [7, 11, 15, 19],
            "randomize_minutes": 20,
        },
        "instagram": {
            "slots": [
                {"hour": 6, "minute": 30, "label": "early_am"},
                {"hour": 8, "minute": 0, "label": "commute"},
                {"hour": 9, "minute": 30, "label": "mid_morning"},
                {"hour": 10, "minute": 45, "label": "late_morning"},
                {"hour": 12, "minute": 0, "label": "noon"},
                {"hour": 13, "minute": 15, "label": "early_afternoon"},
                {"hour": 14, "minute": 30, "label": "mid_afternoon"},
                {"hour": 16, "minute": 0, "label": "late_afternoon"},
                {"hour": 17, "minute": 30, "label": "commute_home"},
                {"hour": 19, "minute": 0, "label": "dinner"},
                {"hour": 20, "minute": 30, "label": "evening"},
                {"hour": 21, "minute": 45, "label": "late_evening"},
            ],
            "best_hours": [6, 8, 9, 10, 12, 13, 14, 16, 17, 19, 20, 21],
            "randomize_minutes": 15,
        },
        "updated_at": None,
        "optimization_count": 0,
    }


def get_schedule():
    """Load or create the posting schedule."""
    schedule = _load_json(SCHEDULE_FILE, {})
    if not schedule or "facebook" not in schedule:
        schedule = _get_default_schedule()
        _save_json(SCHEDULE_FILE, schedule)
    return schedule


def should_post_now(platform: str) -> bool:
    """Check if it's time to post on this platform based on the schedule."""
    schedule = get_schedule()
    plat_sched = schedule.get(platform, {})
    slots = plat_sched.get("slots", [])
    randomize = plat_sched.get("randomize_minutes", 15)

    now = datetime.now()
    current_hour = now.hour
    current_minute = now.minute

    for slot in slots:
        slot_hour = slot["hour"]
        slot_minute = slot["minute"]
        # Check if we're within the window (slot time +/- randomize minutes)
        slot_time = now.replace(hour=slot_hour, minute=slot_minute, second=0)
        window_start = slot_time - timedelta(minutes=randomize)
        window_end = slot_time + timedelta(minutes=randomize)
        if window_start <= now <= window_end:
            return True

    return False


def get_next_slot(platform: str) -> dict:
    """Get the next upcoming posting slot for a platform."""
    schedule = get_schedule()
    plat_sched = schedule.get(platform, {})
    slots = plat_sched.get("slots", [])
    now = datetime.now()

    for slot in sorted(slots, key=lambda s: s["hour"] * 60 + s["minute"]):
        slot_time = now.replace(hour=slot["hour"], minute=slot["minute"], second=0)
        if slot_time > now:
            return slot

    # Wrap to tomorrow's first slot
    return slots[0] if slots else {}


def optimize_schedule():
    """Use engagement data to optimize posting times. Called weekly."""
    posted = _load_json(POSTED_FILE, [])
    if len(posted) < 20:
        log.info("Not enough data to optimize schedule yet")
        return

    schedule = get_schedule()

    # Analyze engagement by hour for each platform
    for platform in ["facebook", "instagram"]:
        hour_scores = {}
        for record in posted:
            ids = record.get("post_ids", {})
            if platform not in ids:
                continue
            posted_at = record.get("posted_at", "")
            try:
                dt = datetime.fromisoformat(posted_at)
                hour = dt.hour
            except Exception:
                continue
            score = record.get("score", 0)
            if hour not in hour_scores:
                hour_scores[hour] = []
            hour_scores[hour].append(score)

        if not hour_scores:
            continue

        # Calculate average score per hour
        avg_by_hour = {h: sum(s) / len(s) for h, s in hour_scores.items() if s}
        sorted_hours = sorted(avg_by_hour.keys(), key=lambda h: avg_by_hour[h], reverse=True)

        # Update best hours
        num_slots = FB_POSTS_PER_DAY if platform == "facebook" else IG_POSTS_PER_DAY
        best = sorted_hours[:num_slots]

        if best:
            schedule[platform]["best_hours"] = best
            # Rebuild slots from best hours
            new_slots = []
            for i, hour in enumerate(sorted(best)):
                minute = random.randint(0, 45)
                label = f"optimized_slot_{i+1}"
                new_slots.append({"hour": hour, "minute": minute, "label": label})
            schedule[platform]["slots"] = new_slots
            log.info(f"  {platform} schedule optimized: best hours = {best}")

    schedule["updated_at"] = datetime.now().isoformat()
    schedule["optimization_count"] = schedule.get("optimization_count", 0) + 1
    _save_json(SCHEDULE_FILE, schedule)
    log.info(f"Schedule optimization #{schedule['optimization_count']} complete")


# ═══════════════════════════════════════════════════════════════
# QUEUE MANAGEMENT
# ═══════════════════════════════════════════════════════════════

def queue_size(platform: str = None) -> int:
    """How many posts are ready. Optionally filter by platform."""
    queue = _load_json(QUEUE_FILE, [])
    if platform:
        return len([q for q in queue if _post_targets_platform(q, platform)])
    return len(queue)


def _post_targets_platform(post: dict, platform: str) -> bool:
    """Check if a post targets a specific platform."""
    target = post.get("platform_target", "both")
    if target == "both":
        return True
    return target == platform


def needs_refill() -> bool:
    """Check if queue is running low."""
    return queue_size() < MIN_QUEUE_SIZE


def pop_next(platform: str = None) -> dict:
    """Grab the next post from the queue for a specific platform.
    Returns {} if empty."""
    queue = _load_json(QUEUE_FILE, [])
    if not queue:
        return {}

    if platform:
        # Find first post that targets this platform
        for i, post in enumerate(queue):
            if _post_targets_platform(post, platform):
                queue.pop(i)
                _save_json(QUEUE_FILE, queue)
                return post
        return {}
    else:
        post = queue.pop(0)
        _save_json(QUEUE_FILE, queue)
        return post


def push_to_queue(content_package: dict):
    """Add a generated content package to the queue."""
    queue = _load_json(QUEUE_FILE, [])
    if "queued_at" not in content_package:
        content_package["queued_at"] = datetime.now().isoformat()
    if "queue_id" not in content_package:
        content_package["queue_id"] = f"q_{int(time.time())}_{random.randint(100, 999)}"
    if "ready" not in content_package:
        content_package["ready"] = True
    queue.append(content_package)
    _save_json(QUEUE_FILE, queue)


def record_posted(content_package: dict, post_ids: dict, platform: str = ""):
    """Record that a post was published. post_ids = {platform: post_id}."""
    posted = _load_json(POSTED_FILE, [])
    record = {
        "content": content_package,
        "post_ids": post_ids,
        "platform": platform,
        "posted_at": datetime.now().isoformat(),
        "engagement": {},
        "score": 0.0,
    }
    posted.append(record)
    if len(posted) > 500:
        posted = posted[-500:]
    _save_json(POSTED_FILE, posted)


def get_posts_today(platform: str) -> int:
    """Count how many posts were made today on a platform."""
    posted = _load_json(POSTED_FILE, [])
    today = datetime.now().date()
    count = 0
    for record in posted:
        try:
            dt = datetime.fromisoformat(record.get("posted_at", ""))
            if dt.date() == today and platform in record.get("post_ids", {}):
                count += 1
        except Exception:
            continue
    return count


def remaining_today(platform: str) -> int:
    """How many more posts should go out today on this platform."""
    limit = FB_POSTS_PER_DAY if platform == "facebook" else IG_POSTS_PER_DAY
    done = get_posts_today(platform)
    return max(0, limit - done)


# ═══════════════════════════════════════════════════════════════
# ENGAGEMENT TRACKING
# ═══════════════════════════════════════════════════════════════

def collect_engagement():
    """Pull engagement stats for all recent posts from FB/IG APIs."""
    import facebook_bot, instagram_bot

    posted = _load_json(POSTED_FILE, [])
    if not posted:
        log.info("No posted history to analyze")
        return 0

    updated = 0
    for record in posted:
        posted_at = record.get("posted_at", "")
        try:
            post_date = datetime.fromisoformat(posted_at)
            if datetime.now() - post_date > timedelta(days=14):
                continue
        except Exception:
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
    """Calculate a unified engagement score. Higher = better.
    Comments weighted 3x, shares 5x — comments are the real signal."""
    score = 0.0
    for platform in ["facebook", "instagram"]:
        e = engagement.get(platform, {})
        likes = (
            e.get("likes", 0)
            or e.get("like_count", 0)
            or e.get("reactions", {}).get("summary", {}).get("total_count", 0)
        )
        comments = e.get("comments", 0) or e.get("comments_count", 0) or e.get("comment_count", 0)
        shares = e.get("shares", 0) or e.get("share_count", 0)
        score += likes * 1.0 + comments * 3.0 + shares * 5.0
    return round(score, 1)


# ═══════════════════════════════════════════════════════════════
# LEARNING ENGINE
# ═══════════════════════════════════════════════════════════════

def analyze_and_learn() -> dict:
    """Analyze all posted content, find patterns, update learning file."""
    posted = _load_json(POSTED_FILE, [])
    if len(posted) < 3:
        log.info("Not enough posts to learn from yet")
        return _load_json(LEARNING_FILE, {})

    scored = [p for p in posted if p.get("score", 0) > 0]
    scored.sort(key=lambda x: x["score"], reverse=True)

    if not scored:
        log.info("No engagement data yet")
        return _load_json(LEARNING_FILE, {})

    top = scored[: max(3, len(scored) // 4)]
    bottom = scored[-max(3, len(scored) // 4) :]
    avg_score = sum(p["score"] for p in scored) / len(scored)

    # Extract patterns
    top_topics, top_hooks, top_questions, bottom_topics = [], [], [], []

    for p in top:
        c = p.get("content", {})
        decision = c.get("decision", {})
        if decision.get("topic"):
            top_topics.append(decision["topic"])
        captions = c.get("captions", {})
        fb_cap = captions.get("facebook", "")
        if fb_cap:
            hook = fb_cap.split("\n")[0][:100]
            top_hooks.append(hook)
            # Extract engagement questions (lines ending with ?)
            for line in fb_cap.split("\n"):
                if line.strip().endswith("?") and len(line.strip()) > 20:
                    top_questions.append(line.strip())

    for p in bottom:
        c = p.get("content", {})
        decision = c.get("decision", {})
        if decision.get("topic"):
            bottom_topics.append(decision["topic"])

    # Track engagement question performance
    question_scores = {}
    for p in scored:
        c = p.get("content", {})
        captions = c.get("captions", {})
        fb_cap = captions.get("facebook", "")
        for line in fb_cap.split("\n"):
            if line.strip().endswith("?") and len(line.strip()) > 20:
                q = line.strip()
                if q not in question_scores:
                    question_scores[q] = []
                question_scores[q].append(p.get("score", 0))

    best_questions = sorted(
        question_scores.keys(),
        key=lambda q: sum(question_scores[q]) / len(question_scores[q]),
        reverse=True,
    )[:10]

    learning = {
        "updated_at": datetime.now().isoformat(),
        "total_posts_analyzed": len(scored),
        "avg_score": round(avg_score, 1),
        "best_score": round(scored[0]["score"], 1) if scored else 0,
        "top_performing_topics": top_topics[:10],
        "top_hooks": top_hooks[:10],
        "best_engagement_questions": best_questions,
        "underperforming_topics": bottom_topics[:10],
        "trend_direction": (
            "improving"
            if len(scored) > 5 and sum(p["score"] for p in scored[:3]) / 3 > avg_score
            else "learning"
        ),
        "insights_summary": "",
    }

    if len(scored) >= 5:
        try:
            learning["insights_summary"] = _generate_ai_insights(top, bottom, avg_score)
        except Exception as e:
            log.warning(f"AI insights failed: {e}")
            learning["insights_summary"] = (
                f"Top topics: {', '.join(top_topics[:5])}. "
                f"Avoid: {', '.join(bottom_topics[:5])}"
            )

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
        top_summary.append(f"Score {p['score']}: topic='{d.get('topic', '')}' caption='{cap}'")

    bottom_summary = []
    for p in bottom_posts[:5]:
        c = p.get("content", {})
        d = c.get("decision", {})
        cap = c.get("captions", {}).get("facebook", "")[:200]
        bottom_summary.append(f"Score {p['score']}: topic='{d.get('topic', '')}' caption='{cap}'")

    prompt = f"""You are analyzing social media performance for Chicago Fleet Wraps (vehicle wrap company in Chicago, IL).

TOP PERFORMERS (high engagement):
{chr(10).join(top_summary)}

BOTTOM PERFORMERS (low engagement):
{chr(10).join(bottom_summary)}

Average score: {avg_score}

In 3-4 sentences, identify the KEY PATTERNS:
1. What topics/styles/hooks/questions get the most engagement?
2. What should we AVOID?
3. What type of engagement questions get business owners to comment?
4. One specific actionable recommendation for the next batch of posts.
Be specific and data-driven."""

    resp = _get_client().chat.completions.create(
        model=os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
        temperature=0.3,
    )
    return resp.choices[0].message.content.strip()


def get_learning_context() -> str:
    """Get a formatted string of learning insights to inject into content generation."""
    learning = _load_json(LEARNING_FILE, {})
    if not learning or not learning.get("total_posts_analyzed"):
        return ""

    parts = []
    if learning.get("insights_summary"):
        parts.append(f"PERFORMANCE INSIGHTS: {learning['insights_summary']}")
    if learning.get("top_performing_topics"):
        parts.append(f"HIGH-PERFORMING TOPICS: {', '.join(learning['top_performing_topics'][:5])}")
    if learning.get("underperforming_topics"):
        parts.append(f"AVOID THESE TOPICS: {', '.join(learning['underperforming_topics'][:5])}")
    if learning.get("top_hooks"):
        parts.append(f"HOOKS THAT WORKED: {' | '.join(learning['top_hooks'][:3])}")
    if learning.get("best_engagement_questions"):
        parts.append(f"QUESTIONS THAT GOT COMMENTS: {' | '.join(learning['best_engagement_questions'][:3])}")
    if learning.get("avg_score"):
        parts.append(f"Average engagement score: {learning['avg_score']} (beat this!)")

    return "\n".join(parts)


# ═══════════════════════════════════════════════════════════════
# POSTING — PLATFORM-SPECIFIC WITH IMAGE URL SUPPORT
# ═══════════════════════════════════════════════════════════════

def post_to_facebook(post: dict = None) -> dict:
    """Post one item from the queue to Facebook.
    Supports image_url (CDN) or image_path (local file)."""
    import facebook_bot

    if not post:
        post = pop_next("facebook")
    if not post:
        log.warning("No Facebook posts in queue")
        return {}

    captions = post.get("captions", {})
    fb_caption = captions.get("facebook", captions.get("default", ""))
    image_url = post.get("image_url", "")
    image_path = post.get("image_path", "")

    try:
        if image_url:
            # Post with pre-uploaded CDN image URL
            result = facebook_bot.create_post(caption=fb_caption, image_url=image_url)
        elif image_path and os.path.exists(image_path):
            result = facebook_bot.create_post(caption=fb_caption, image_path=image_path)
        else:
            result = facebook_bot.create_post(caption=fb_caption)

        if result.get("success"):
            post_ids = {"facebook": result.get("post_id", "")}
            record_posted(post, post_ids, platform="facebook")
            log.info(f"✓ Facebook posted: {result.get('post_id')}")
            return result
        else:
            log.error(f"✗ Facebook post failed: {result}")
            return result
    except Exception as e:
        log.error(f"✗ Facebook error: {e}")
        return {"success": False, "error": str(e)}


def post_to_instagram(post: dict = None) -> dict:
    """Post one item from the queue to Instagram.
    Supports image_url (CDN) or image_path (local file)."""
    import instagram_bot

    if not post:
        post = pop_next("instagram")
    if not post:
        log.warning("No Instagram posts in queue")
        return {}

    captions = post.get("captions", {})
    ig_caption = captions.get("instagram", captions.get("default", ""))
    image_url = post.get("image_url", "")
    image_path = post.get("image_path", "")

    try:
        if image_url:
            result = instagram_bot.create_post(caption=ig_caption, image_url=image_url)
        elif image_path and os.path.exists(image_path):
            result = instagram_bot.create_post(caption=ig_caption, image_path=image_path)
        else:
            log.error("Instagram requires an image — no image_url or image_path found")
            return {"success": False, "error": "No image available"}

        if result.get("success"):
            post_ids = {"instagram": result.get("post_id", result.get("media_id", ""))}
            record_posted(post, post_ids, platform="instagram")
            log.info(f"✓ Instagram posted: {post_ids['instagram']}")
            return result
        else:
            log.error(f"✗ Instagram post failed: {result}")
            return result
    except Exception as e:
        log.error(f"✗ Instagram error: {e}")
        return {"success": False, "error": str(e)}


def post_cycle():
    """Run one posting cycle. Called hourly by GitHub Actions.
    Checks schedule, posts if it's time, respects daily limits."""
    log.info("=" * 50)
    log.info("CONTENT QUEUE — POST CYCLE")
    log.info(f"Queue: {queue_size()} total | FB: {queue_size('facebook')} | IG: {queue_size('instagram')}")

    results = {"facebook": [], "instagram": []}

    # Facebook: check if we should post now and haven't hit daily limit
    fb_remaining = remaining_today("facebook")
    if fb_remaining > 0 and should_post_now("facebook"):
        log.info(f"Facebook: posting ({fb_remaining} remaining today)")
        result = post_to_facebook()
        if result.get("success"):
            results["facebook"].append(result)
    else:
        next_fb = get_next_slot("facebook")
        log.info(f"Facebook: not posting now (remaining: {fb_remaining}, next slot: {next_fb})")

    time.sleep(3)

    # Instagram: check if we should post now and haven't hit daily limit
    ig_remaining = remaining_today("instagram")
    if ig_remaining > 0 and should_post_now("instagram"):
        log.info(f"Instagram: posting ({ig_remaining} remaining today)")
        result = post_to_instagram()
        if result.get("success"):
            results["instagram"].append(result)
    else:
        next_ig = get_next_slot("instagram")
        log.info(f"Instagram: not posting now (remaining: {ig_remaining}, next slot: {next_ig})")

    # Auto-refill check
    if needs_refill():
        log.info(f"Queue low ({queue_size()}), needs refill!")

    log.info(f"Cycle done. Queue: {queue_size()} remaining")
    return results


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

    queue = _load_json(QUEUE_FILE, [])
    queued_topics = [q.get("decision", {}).get("topic", "") for q in queue]

    for i in range(count):
        try:
            log.info(f"  Generating post {i + 1}/{count}...")

            decision = brain.decide_content(avoid_topics=queued_topics)

            if not decision or not decision.get("topic"):
                log.warning(f"  Brain returned empty decision for post {i + 1}")
                continue

            if learning_context:
                decision["learning_context"] = learning_context

            package = create_content_package(decision)

            if not package or package.get("unique") == False:
                log.warning(f"  Content not unique, skipping")
                continue

            package["decision"] = decision

            # Assign platform target based on position in batch
            # First FB_POSTS_PER_DAY go to both, rest are IG-only
            if i < FB_POSTS_PER_DAY:
                package["platform_target"] = "both"
            else:
                package["platform_target"] = "instagram"

            push_to_queue(package)
            queued_topics.append(decision.get("topic", ""))
            added += 1
            log.info(f"  ✓ Post {i + 1} queued: {decision.get('topic', 'unknown')}")

        except Exception as e:
            log.error(f"  ✗ Failed to generate post {i + 1}: {e}")
            continue

    log.info(f"Refill complete: added {added} posts, queue now has {queue_size()}")
    return added


# ═══════════════════════════════════════════════════════════════
# WEEKLY PROFILE AUDIT
# ═══════════════════════════════════════════════════════════════

def run_weekly_audit() -> dict:
    """Audit FB and IG profiles, analyze performance, suggest improvements.
    Returns audit results dict."""
    import facebook_bot, instagram_bot

    log.info("=" * 50)
    log.info("WEEKLY PROFILE AUDIT")
    log.info("=" * 50)

    audit = {
        "date": datetime.now().isoformat(),
        "facebook": {},
        "instagram": {},
        "recommendations": [],
    }

    # Collect stats
    posted = _load_json(POSTED_FILE, [])
    learning = _load_json(LEARNING_FILE, {})

    # Last 7 days performance
    week_ago = datetime.now() - timedelta(days=7)
    week_posts = [
        p for p in posted
        if p.get("posted_at") and datetime.fromisoformat(p["posted_at"]) > week_ago
    ]

    fb_posts = [p for p in week_posts if "facebook" in p.get("post_ids", {})]
    ig_posts = [p for p in week_posts if "instagram" in p.get("post_ids", {})]

    fb_scores = [p.get("score", 0) for p in fb_posts]
    ig_scores = [p.get("score", 0) for p in ig_posts]

    audit["facebook"] = {
        "posts_this_week": len(fb_posts),
        "target_posts": FB_POSTS_PER_DAY * 7,
        "avg_score": round(sum(fb_scores) / len(fb_scores), 1) if fb_scores else 0,
        "best_score": max(fb_scores) if fb_scores else 0,
        "worst_score": min(fb_scores) if fb_scores else 0,
    }

    audit["instagram"] = {
        "posts_this_week": len(ig_posts),
        "target_posts": IG_POSTS_PER_DAY * 7,
        "avg_score": round(sum(ig_scores) / len(ig_scores), 1) if ig_scores else 0,
        "best_score": max(ig_scores) if ig_scores else 0,
        "worst_score": min(ig_scores) if ig_scores else 0,
    }

    # Generate AI recommendations
    try:
        prompt = f"""You are auditing social media profiles for Chicago Fleet Wraps (vehicle wrap company, 4711 N Lamon Ave, Chicago IL 60630).

FACEBOOK PERFORMANCE (last 7 days):
- Posts: {audit['facebook']['posts_this_week']} / {audit['facebook']['target_posts']} target
- Avg engagement score: {audit['facebook']['avg_score']}
- Best: {audit['facebook']['best_score']}, Worst: {audit['facebook']['worst_score']}

INSTAGRAM PERFORMANCE (last 7 days):
- Posts: {audit['instagram']['posts_this_week']} / {audit['instagram']['target_posts']} target
- Avg engagement score: {audit['instagram']['avg_score']}
- Best: {audit['instagram']['best_score']}, Worst: {audit['instagram']['worst_score']}

LEARNING DATA:
- Top topics: {', '.join(learning.get('top_performing_topics', [])[:5])}
- Underperforming: {', '.join(learning.get('underperforming_topics', [])[:5])}
- Best questions: {', '.join(learning.get('best_engagement_questions', [])[:3])}

Give 5 specific, actionable recommendations to improve performance next week.
Focus on: content mix, posting times, engagement tactics, profile optimization, and audience growth.
Be specific to a vehicle wrap business targeting Chicago business owners."""

        resp = _get_client().chat.completions.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.4,
        )
        audit["recommendations"] = resp.choices[0].message.content.strip().split("\n")
    except Exception as e:
        log.warning(f"AI audit recommendations failed: {e}")
        audit["recommendations"] = ["Insufficient data for AI recommendations"]

    # Optimize schedule based on this week's data
    optimize_schedule()

    # Save audit log
    audit_history = _load_json(AUDIT_LOG, [])
    audit_history.append(audit)
    if len(audit_history) > 52:  # Keep 1 year of audits
        audit_history = audit_history[-52:]
    _save_json(AUDIT_LOG, audit_history)

    log.info(f"Audit complete: FB {audit['facebook']['posts_this_week']} posts, "
             f"IG {audit['instagram']['posts_this_week']} posts")
    for rec in audit.get("recommendations", []):
        if rec.strip():
            log.info(f"  REC: {rec.strip()}")

    return audit


# ═══════════════════════════════════════════════════════════════
# FULL CYCLE HELPERS
# ═══════════════════════════════════════════════════════════════

def full_cycle():
    """Run the complete cycle: collect engagement → learn → post → refill if needed."""
    log.info("=" * 50)
    log.info("CONTENT QUEUE — FULL CYCLE")
    log.info(f"Queue: {queue_size()} total | FB: {queue_size('facebook')} | IG: {queue_size('instagram')}")

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

    # Step 3: Post from queue (respecting cadence)
    results = post_cycle()

    # Step 4: Refill if running low
    if needs_refill():
        log.info(f"Queue low ({queue_size()}), refilling...")
        refill_queue()

    log.info(f"Cycle complete. Queue: {queue_size()} posts ready")
    return results


# Legacy compatibility
def post_from_queue() -> dict:
    """Legacy: post to both platforms from queue. Use post_cycle() instead."""
    results = {}
    fb = post_to_facebook()
    if fb.get("success"):
        results["facebook"] = fb.get("post_id", "")
    ig = post_to_instagram()
    if ig.get("success"):
        results["instagram"] = ig.get("post_id", ig.get("media_id", ""))
    return results


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd == "refill":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else BATCH_SIZE
        refill_queue(n)
    elif cmd == "post":
        post_cycle()
    elif cmd == "post-fb":
        post_to_facebook()
    elif cmd == "post-ig":
        post_to_instagram()
    elif cmd == "analyze":
        collect_engagement()
        learning = analyze_and_learn()
        print(json.dumps(learning, indent=2))
    elif cmd == "cycle":
        full_cycle()
    elif cmd == "audit":
        audit = run_weekly_audit()
        print(json.dumps(audit, indent=2))
    elif cmd == "schedule":
        sched = get_schedule()
        print(json.dumps(sched, indent=2))
    elif cmd == "optimize":
        optimize_schedule()
    elif cmd == "status":
        q = queue_size()
        fb_q = queue_size("facebook")
        ig_q = queue_size("instagram")
        posted = len(_load_json(POSTED_FILE, []))
        learning = _load_json(LEARNING_FILE, {})
        fb_today = get_posts_today("facebook")
        ig_today = get_posts_today("instagram")
        print(f"Queue: {q} total ({fb_q} FB-eligible, {ig_q} IG-eligible)")
        print(f"Today: FB {fb_today}/{FB_POSTS_PER_DAY} | IG {ig_today}/{IG_POSTS_PER_DAY}")
        print(f"Posted history: {posted} posts")
        print(f"Learning: {learning.get('total_posts_analyzed', 0)} posts analyzed")
        print(f"Avg score: {learning.get('avg_score', 'N/A')}")
        print(f"Trend: {learning.get('trend_direction', 'N/A')}")
        if learning.get("insights_summary"):
            print(f"Insights: {learning['insights_summary']}")
        if learning.get("best_engagement_questions"):
            print(f"Best questions: {', '.join(learning['best_engagement_questions'][:3])}")
    else:
        print(f"Usage: python content_queue.py [refill|post|post-fb|post-ig|analyze|cycle|audit|schedule|optimize|status]")
