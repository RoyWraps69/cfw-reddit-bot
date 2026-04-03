#!/usr/bin/env python3
"""
Chicago Fleet Wraps — MASTER ORCHESTRATOR v1.0
THE BRAIN THAT RUNS EVERYTHING

This is the single entry point that coordinates ALL platforms:
- Reddit (commenting, warming, DMs, thread creation)
- Facebook (posting, commenting, engagement)
- Instagram (posting, stories, commenting, engagement)
- TikTok (posting, commenting, engagement)

Every hour it:
1. Analyzes trends across all platforms
2. Runs the content brain to decide what to post
3. Generates AI images/videos
4. Posts unique content across all platforms simultaneously
5. Engages with existing threads/posts on all platforms
6. Checks for negative reactions and deletes bad posts
7. Tracks performance and feeds it back into the learning loop
8. Runs cross-platform analysis to optimize strategy

Usage:
  python master.py                    # Full hourly cycle (all platforms)
  python master.py reddit             # Reddit only
  python master.py social             # Facebook + Instagram + TikTok only
  python master.py content            # Generate and post content only
  python master.py engage             # Engage/comment only (all platforms)
  python master.py analyze            # Trend analysis + cross-platform intel only
  python master.py damage             # Damage control check only
  python master.py dashboard          # Generate dashboard only
  python master.py refill             # Batch-generate posts into the content queue
  python master.py post               # Post next item from queue (fast, no generation)
  python master.py learn              # Collect engagement + learn what works
"""
import sys
import os
import time
import json
import traceback
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DATA_DIR, LOG_DIR

# Platform modules
import bot as reddit_bot
from trend_analyzer import TrendAnalyzer
from content_brain import ContentBrain
from media_generator import create_content_package
import facebook_bot
import instagram_bot
from tiktok_bot import TikTokBot
from cross_platform_intel import get_cross_intel
import content_queue
from damage_control import (
    run_damage_check, get_posts_needing_replacement,
    mark_replacement_done, get_topics_to_avoid,
)

MASTER_LOG_FILE = os.path.join(LOG_DIR, "master_log.json")


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"  [{ts}] [MASTER] {msg}", flush=True)


def log_cycle(cycle_data: dict):
    """Log a complete cycle's results."""
    os.makedirs(LOG_DIR, exist_ok=True)
    master_log = []
    if os.path.exists(MASTER_LOG_FILE):
        try:
            with open(MASTER_LOG_FILE, "r") as f:
                master_log = json.load(f)
        except Exception:
            pass

    cycle_data["timestamp"] = datetime.now().isoformat()
    master_log.append(cycle_data)
    master_log = master_log[-200:]

    with open(MASTER_LOG_FILE, "w") as f:
        json.dump(master_log, f, indent=2)


# ─────────────────────────────────────────────
# PHASE 1: TREND ANALYSIS
# ─────────────────────────────────────────────

def run_trend_analysis() -> dict:
    """Analyze trends across all platforms."""
    log("=" * 60)
    log("PHASE 1: TREND ANALYSIS")
    log("=" * 60)

    try:
        analyzer = TrendAnalyzer()
        trends = analyzer.analyze_all()

        hot_topics = trends.get("hot_topics", [])
        log(f"Found {len(hot_topics)} trending topics")
        for topic in hot_topics[:5]:
            log(f"  TREND: {topic.get('topic', '')} "
                f"(score: {topic.get('score', 0):.0f}, "
                f"source: {topic.get('source', '')})")

        return trends

    except Exception as e:
        log(f"Trend analysis error: {e}")
        traceback.print_exc()
        return {"hot_topics": [], "error": str(e)}


# ─────────────────────────────────────────────
# PHASE 2: CONTENT DECISION
# ─────────────────────────────────────────────

def run_content_decision(trends: dict) -> dict:
    """Use the content brain to decide what to post."""
    log("=" * 60)
    log("PHASE 2: CONTENT DECISION")
    log("=" * 60)

    try:
        brain = ContentBrain()

        # Get cross-platform recommendations
        cross_intel = get_cross_intel()

        # Get topics to avoid (from damage control)
        avoid_topics = get_topics_to_avoid()
        if avoid_topics:
            log(f"Avoiding topics (damage history): {avoid_topics}")

        # Get platform-specific recommendations
        platform_recs = {}
        for platform in ["reddit", "facebook", "instagram", "tiktok"]:
            platform_recs[platform] = cross_intel.get_platform_recommendations(platform)

        decision = brain.decide_content(
            trends=trends,
            cross_platform_recs=platform_recs,
            avoid_topics=avoid_topics,
        )

        if decision:
            log(f"Content decision: {decision.get('topic', 'unknown')}")
            log(f"  Audience: {decision.get('audience', 'unknown')}")
            log(f"  Campaign: {decision.get('campaign', 'unknown')}")
            log(f"  Image prompt: {decision.get('image_prompt', '')[:80]}...")
        else:
            log("No content decision made this cycle.")

        return decision or {}

    except Exception as e:
        log(f"Content decision error: {e}")
        traceback.print_exc()
        return {}


# ─────────────────────────────────────────────
# PHASE 3: CONTENT GENERATION & POSTING
# ─────────────────────────────────────────────

def run_content_posting(decision: dict) -> dict:
    """Generate media and post content across all platforms."""
    log("=" * 60)
    log("PHASE 3: CONTENT GENERATION & POSTING")
    log("=" * 60)

    results = {"facebook": None, "instagram": None, "tiktok": None}

    if not decision or not decision.get("topic"):
        log("No content to post this cycle.")
        return results

    # Generate the content package (image + adapted captions)
    log("Generating content package...")
    try:
        package = create_content_package(decision)
    except Exception as e:
        log(f"Content package generation error: {e}")
        traceback.print_exc()
        return results

    if not package.get("unique"):
        log("Content not unique, skipping posting.")
        return results

    image_path = package.get("image_path", "")
    video_path = package.get("video_path", "")
    platform_content = package.get("platforms", {})

    log(f"Content package ready: image={'YES' if image_path else 'NO'}, "
        f"video={'YES' if video_path else 'NO'}")

    # Cross-platform check before posting
    cross_intel = get_cross_intel()
    topic = decision.get("topic", "")

    # POST TO FACEBOOK
    try:
        override = cross_intel.get_strategy_override("facebook", topic)
        if override["action"] != "suppress":
            fb_content = platform_content.get("facebook", {})
            if fb_content:
                log("Posting to Facebook via Graph API...")
                fb_caption = fb_content.get("caption", "")
                fb_hashtags = fb_content.get("hashtags", [])
                if fb_hashtags:
                    fb_caption += "\n\n" + " ".join(f"#{h}" for h in fb_hashtags)
                fb_result = facebook_bot.create_post(
                    caption=fb_caption,
                    image_path=image_path,
                )
                results["facebook"] = fb_result
                log(f"  Facebook: {'SUCCESS' if fb_result.get('success') else 'FAILED'} — {fb_result}")
        else:
            log(f"  Facebook SUPPRESSED: {override.get('reason', '')}")
    except Exception as e:
        log(f"  Facebook error: {e}")

    time.sleep(5)  # Delay between platforms

    # POST TO INSTAGRAM
    try:
        override = cross_intel.get_strategy_override("instagram", topic)
        if override["action"] != "suppress":
            ig_content = platform_content.get("instagram", {})
            if ig_content:
                log("Posting to Instagram via Graph API...")
                ig_caption = ig_content.get("caption", "")
                ig_hashtags = ig_content.get("hashtags", [])
                if ig_hashtags:
                    ig_caption += "\n.\n.\n.\n" + " ".join(f"#{h}" for h in ig_hashtags)
                ig_result = instagram_bot.create_post(
                    caption=ig_caption,
                    image_path=image_path,
                )
                results["instagram"] = ig_result
                log(f"  Instagram: {'SUCCESS' if ig_result.get('success') else 'FAILED'} — {ig_result}")
        else:
            log(f"  Instagram SUPPRESSED: {override.get('reason', '')}")
    except Exception as e:
        log(f"  Instagram error: {e}")

    time.sleep(5)

    # POST TO TIKTOK
    try:
        override = cross_intel.get_strategy_override("tiktok", topic)
        if override["action"] != "suppress":
            tt_content = platform_content.get("tiktok", {})
            if tt_content:
                log("Posting to TikTok...")
                tt = TikTokBot()
                media = video_path if video_path else image_path
                tt_result = tt.create_post(
                    caption=tt_content.get("caption", ""),
                    hashtags=tt_content.get("hashtags", []),
                    media_path=media,
                )
                results["tiktok"] = tt_result
                log(f"  TikTok: {'SUCCESS' if tt_result else 'FAILED'}")
        else:
            log(f"  TikTok SUPPRESSED: {override.get('reason', '')}")
    except Exception as e:
        log(f"  TikTok error: {e}")

    return results


# ─────────────────────────────────────────────
# PHASE 4: ENGAGEMENT (commenting on others' content)
# ─────────────────────────────────────────────

def run_engagement() -> dict:
    """Run engagement across all platforms."""
    log("=" * 60)
    log("PHASE 4: ENGAGEMENT")
    log("=" * 60)

    results = {"reddit": None, "facebook": None, "instagram": None, "tiktok": None}

    # Reddit engagement (the main bot)
    try:
        log("Running Reddit engagement...")
        from reddit_session import RedditSession
        from scanner import set_session as set_scanner_session
        from config import REDDIT_USERNAME, WARMING_KARMA_THRESHOLD

        rs = RedditSession(REDDIT_USERNAME)
        if rs.login():
            set_scanner_session(rs)
            karma = rs.get_karma()
            log(f"Reddit karma: {karma}")

            if karma < WARMING_KARMA_THRESHOLD:
                reddit_bot.run_warming_cycle(rs)
            else:
                reddit_bot.run_normal_cycle(rs)

            results["reddit"] = {"status": "completed", "karma": karma}
        else:
            log("Reddit login failed!")
            results["reddit"] = {"status": "login_failed"}
    except Exception as e:
        log(f"Reddit engagement error: {e}")
        results["reddit"] = {"status": "error", "error": str(e)}

    time.sleep(10)

    # Facebook engagement
    try:
        log("Running Facebook engagement check...")
        fb_result = facebook_bot.engage_with_posts()
        results["facebook"] = fb_result
        log(f"  Facebook engagement: {fb_result}")
    except Exception as e:
        log(f"Facebook engagement error: {e}")
        results["facebook"] = {"status": "error", "error": str(e)}

    time.sleep(5)

    # Instagram engagement
    try:
        log("Running Instagram engagement check...")
        ig_result = instagram_bot.engage_with_posts()
        results["instagram"] = ig_result
        log(f"  Instagram engagement: {ig_result}")
    except Exception as e:
        log(f"Instagram engagement error: {e}")
        results["instagram"] = {"status": "error", "error": str(e)}

    time.sleep(5)

    # TikTok engagement
    try:
        log("Running TikTok engagement...")
        tt = TikTokBot()
        tt_result = tt.engage_with_posts(max_comments=3)
        results["tiktok"] = tt_result
        log(f"  TikTok engagement: {tt_result}")
    except Exception as e:
        log(f"TikTok engagement error: {e}")
        results["tiktok"] = {"status": "error", "error": str(e)}

    return results


# ─────────────────────────────────────────────
# PHASE 5: DAMAGE CONTROL
# ─────────────────────────────────────────────

def run_damage_control() -> dict:
    """Check all posts for negative reactions and handle them."""
    log("=" * 60)
    log("PHASE 5: DAMAGE CONTROL")
    log("=" * 60)

    results = {"checked": 0, "deleted": 0, "replaced": 0}

    try:
        # Get Reddit session for Reddit damage checks
        from reddit_session import RedditSession
        from config import REDDIT_USERNAME

        rs = RedditSession(REDDIT_USERNAME)
        reddit_session = rs if rs.login() else None

        # Run damage check across all platforms
        damage_result = run_damage_check(reddit_session=reddit_session)
        results.update(damage_result)

        # Handle replacements
        needs_replacement = get_posts_needing_replacement()
        if needs_replacement:
            log(f"  {len(needs_replacement)} posts need replacement content")

            for entry in needs_replacement[:2]:  # Max 2 replacements per cycle
                try:
                    # Generate replacement content
                    brain = ContentBrain()
                    replacement = brain.decide_replacement(
                        failed_topic=entry.get("topic", ""),
                        failed_platform=entry.get("platform", ""),
                        failure_details=entry.get("details", {}),
                    )

                    if replacement:
                        log(f"  Replacement: {replacement.get('topic', '')}")
                        # Post the replacement
                        package = create_content_package(replacement)
                        if package.get("unique"):
                            # Post to the same platform
                            platform = entry.get("platform", "")
                            if platform == "facebook":
                                facebook_bot.create_post(
                                    caption=replacement.get("caption", ""),
                                    image_path=package.get("image_path", ""),
                                )
                            elif platform == "instagram":
                                instagram_bot.create_post(
                                    caption=replacement.get("caption", ""),
                                    image_path=package.get("image_path", ""),
                                )
                            elif platform == "tiktok":
                                tt = TikTokBot()
                                tt.create_post(
                                    caption=replacement.get("caption", ""),
                                    hashtags=replacement.get("hashtags", []),
                                    media_path=package.get("video_path", "") or package.get("image_path", ""),
                                )

                            results["replaced"] += 1

                    mark_replacement_done(entry.get("post_id", ""))

                except Exception as e:
                    log(f"  Replacement error: {e}")

    except Exception as e:
        log(f"Damage control error: {e}")
        traceback.print_exc()

    log(f"  Damage control: {results['checked']} checked, "
        f"{results['deleted']} deleted, {results['replaced']} replaced")

    return results


# ─────────────────────────────────────────────
# PHASE 6: INTELLIGENCE & LEARNING
# ─────────────────────────────────────────────

def run_intelligence() -> dict:
    """Run all intelligence and learning systems."""
    log("=" * 60)
    log("PHASE 6: INTELLIGENCE & LEARNING")
    log("=" * 60)

    results = {}

    # Reddit upvote tracking
    try:
        from reddit_session import RedditSession
        from config import REDDIT_USERNAME
        from upvote_tracker import check_comment_performance

        rs = RedditSession(REDDIT_USERNAME)
        if rs.login():
            log("Tracking Reddit comment performance...")
            track_result = check_comment_performance(rs)
            results["upvote_tracking"] = track_result

            # Reply to replies
            from reply_engine import run_reply_cycle
            log("Checking for replies to engage with...")
            run_reply_cycle(rs)
    except Exception as e:
        log(f"Reddit intelligence error: {e}")

    # Cross-platform analysis
    try:
        log("Running cross-platform analysis...")
        cross_intel = get_cross_intel()
        analysis = cross_intel.run_cross_analysis()
        results["cross_analysis"] = {
            "insights": len(analysis.get("insights", [])),
            "amplifications": len(analysis.get("amplifications", [])),
            "suppressions": len(analysis.get("suppressions", [])),
        }
    except Exception as e:
        log(f"Cross-platform analysis error: {e}")

    return results


# ─────────────────────────────────────────────
# PHASE 7: DASHBOARD
# ─────────────────────────────────────────────

def run_dashboard_generation():
    """Generate the unified multi-platform dashboard."""
    log("=" * 60)
    log("PHASE 7: DASHBOARD GENERATION")
    log("=" * 60)

    try:
        from unified_dashboard import generate_unified_dashboard
        dashboard_path = generate_unified_dashboard()
        log(f"Dashboard generated: {dashboard_path}")
        return dashboard_path
    except ImportError:
        log("Unified dashboard module not yet available, using Reddit-only dashboard.")
        try:
            from dashboard import generate_dashboard
            path = generate_dashboard()
            log(f"Reddit dashboard generated: {path}")
            return path
        except Exception as e:
            log(f"Dashboard error: {e}")
            return None
    except Exception as e:
        log(f"Dashboard error: {e}")
        return None


# ─────────────────────────────────────────────
# FULL HOURLY CYCLE
# ─────────────────────────────────────────────

def run_full_cycle():
    """Run the complete hourly cycle across all platforms."""
    print(f"\n{'='*70}", flush=True)
    print(f"  CHICAGO FLEET WRAPS — MASTER ORCHESTRATOR v1.0", flush=True)
    print(f"  Reddit | Facebook | Instagram | TikTok", flush=True)
    print(f"  Cross-Platform Intelligence | Damage Control | Auto-Learning", flush=True)
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print(f"{'='*70}\n", flush=True)

    cycle_results = {}

    # Phase 1: Analyze trends
    trends = run_trend_analysis()
    cycle_results["trends"] = {
        "topics_found": len(trends.get("hot_topics", [])),
    }

    # Phase 2: Content decision
    decision = run_content_decision(trends)
    cycle_results["content_decision"] = {
        "topic": decision.get("topic", "none"),
        "audience": decision.get("audience", "none"),
    }

    # Phase 3: Post from queue (or generate+post if queue empty)
    log(f"Content queue: {content_queue.queue_size()} posts ready")
    if content_queue.queue_size() > 0:
        posting_results = {}
        post_ids = content_queue.post_from_queue()
        posting_results["facebook"] = {"success": bool(post_ids.get("facebook"))}
        posting_results["instagram"] = {"success": bool(post_ids.get("instagram"))}
    else:
        posting_results = run_content_posting(decision)
    cycle_results["posting"] = posting_results

    # Auto-refill queue if low
    if content_queue.needs_refill():
        log(f"Queue low ({content_queue.queue_size()}), auto-refilling...")
        content_queue.refill_queue()

    # Phase 4: Engagement
    engagement_results = run_engagement()
    cycle_results["engagement"] = engagement_results

    # Phase 5: Damage control
    damage_results = run_damage_control()
    cycle_results["damage_control"] = damage_results

    # Phase 6: Intelligence & learning
    intel_results = run_intelligence()
    cycle_results["intelligence"] = intel_results

    # Phase 7: Dashboard
    dashboard_path = run_dashboard_generation()
    cycle_results["dashboard"] = dashboard_path

    # Log the full cycle
    log_cycle(cycle_results)

    # Summary
    print(f"\n{'='*70}", flush=True)
    print(f"  CYCLE COMPLETE — {datetime.now().strftime('%H:%M:%S')}", flush=True)
    print(f"  Trends: {cycle_results['trends']['topics_found']} topics found", flush=True)
    print(f"  Content: {cycle_results['content_decision']['topic']}", flush=True)
    print(f"  Posting: FB={'OK' if posting_results.get('facebook') else 'skip'} | "
          f"IG={'OK' if posting_results.get('instagram') else 'skip'} | "
          f"TT={'OK' if posting_results.get('tiktok') else 'skip'}", flush=True)
    print(f"  Damage: {damage_results.get('checked', 0)} checked, "
          f"{damage_results.get('deleted', 0)} deleted", flush=True)
    print(f"{'='*70}\n", flush=True)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "full"

    if mode == "full":
        run_full_cycle()
    elif mode == "reddit":
        # Reddit only (uses the existing bot.py)
        reddit_bot.main()
    elif mode == "social":
        # Use queue system: post from barrel, refill if needed
        log(f"Queue status: {content_queue.queue_size()} posts ready")
        content_queue.collect_engagement()  # track past posts
        content_queue.analyze_and_learn()   # learn from data
        if content_queue.queue_size() > 0:
            content_queue.post_from_queue()
        else:
            log("Queue empty — generating on the fly + refilling")
            trends = run_trend_analysis()
            decision = run_content_decision(trends)
            run_content_posting(decision)
            content_queue.refill_queue(5)  # fill barrel for next time
        if content_queue.needs_refill():
            content_queue.refill_queue()
    elif mode == "content":
        trends = run_trend_analysis()
        decision = run_content_decision(trends)
        run_content_posting(decision)
    elif mode == "engage":
        run_engagement()
    elif mode == "analyze":
        trends = run_trend_analysis()
        run_intelligence()
    elif mode == "damage":
        run_damage_control()
    elif mode == "dashboard":
        run_dashboard_generation()
    elif mode == "refill":
        # Batch-generate posts into the queue
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 8
        log(f"Refilling content queue with {n} posts...")
        content_queue.refill_queue(n)
        log(f"Queue now has {content_queue.queue_size()} posts ready")
    elif mode == "post":
        # Fast post from queue — no generation
        log(f"Posting from queue ({content_queue.queue_size()} ready)...")
        post_ids = content_queue.post_from_queue()
        log(f"Posted: {post_ids}")
    elif mode == "learn":
        # Collect engagement data and learn
        log("Collecting engagement data...")
        content_queue.collect_engagement()
        log("Analyzing patterns...")
        learning = content_queue.analyze_and_learn()
        log(f"Learning complete: {learning.get('total_posts_analyzed', 0)} posts analyzed")
        log(f"Avg score: {learning.get('avg_score', 'N/A')}")
        log(f"Trend: {learning.get('trend_direction', 'N/A')}")
        if learning.get('insights_summary'):
            log(f"Insights: {learning['insights_summary']}")
    else:
        print(f"Unknown mode: {mode}", flush=True)
        print("Available: full, reddit, social, content, engage, analyze, damage, dashboard, refill, post, learn", flush=True)


if __name__ == "__main__":
    main()
