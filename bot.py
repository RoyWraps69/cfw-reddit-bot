#!/usr/bin/env python3
"""
Chicago Fleet Wraps Reddit Bot v5.0 -- FULL INTELLIGENCE SUITE
All 6 upgrades integrated:
  1. Upvote tracking — checks comment performance, feeds data back to AI
  2. Subreddit personality profiles — per-sub style learning
  3. Reply-to-replies — detects and responds to replies on our comments
  4. Strategic timing — filters threads to the 1-3 hour sweet spot
  5. Competitor monitoring — detects competitor mentions, responds strategically
  6. Cross-platform intelligence — learns from FB/IG/TT performance
  + Damage control — auto-deletes posts with 3+ negative reactions

Usage:
  python bot.py                  # Full auto run (all features)
  python bot.py warming          # Account warming mode
  python bot.py scan-only        # Scan only, no posting (dry run)
  python bot.py dm-check         # Check for DM follow-up opportunities
  python bot.py create-thread    # Create a proactive thread
  python bot.py reply-check      # Check and reply to replies
  python bot.py upvote-check     # Check comment performance
  python bot.py damage-check     # Check for negative posts
  python bot.py status           # Show daily activity summary
"""
import sys
import os
import time
import random
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    REDDIT_USERNAME, MAX_COMMENTS_PER_DAY, PROMO_RATIO,
    WARMING_KARMA_THRESHOLD, THREAD_CREATION_KARMA_THRESHOLD,
    WARMING_COMMENTS_PER_CYCLE, WARMING_MAX_PER_DAY,
    THREADS_PER_WEEK, DATA_DIR, LOG_DIR,
    TIER1_LOCAL, TIER2_VEHICLE, TIER3_COMMERCIAL, INDUSTRY_SUBS,
    MIN_DELAY_BETWEEN_COMMENTS, MAX_DELAY_BETWEEN_COMMENTS,
    get_seasonal_config,
)
from reddit_session import RedditSession
from scanner import (
    find_opportunities, save_posted_thread,
    get_thread_comments, check_for_competitor_mentions,
    fetch_thread_context,
    set_session as set_scanner_session,
)
from ai_responder import (
    classify_thread, generate_comment, generate_warming_comment,
    generate_dm_message, generate_thread_post, check_positive_reply,
)
from poster import post_comment, send_dm, create_thread
from tracker import (
    can_comment, can_comment_in_sub, should_be_promo,
    record_comment, record_dm, record_thread_created,
    get_daily_summary,
)

# ── NEW v5.0 MODULES ──
from upvote_tracker import check_comment_performance, get_performance_context_for_ai
from sub_profiles import update_profile, get_profile_for_ai
from reply_engine import run_reply_cycle
from timing import filter_by_timing, should_skip_cycle, get_timing_report
from competitor_monitor import (
    scan_for_competitor_mentions, should_respond_to_competitor,
    get_competitor_response_strategy, log_competitor_mention,
)
from damage_control import register_post, run_damage_check, get_posts_needing_replacement, mark_replacement_done
from cross_platform_intel import get_cross_intel


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"  [{ts}] {msg}", flush=True)


def random_delay(min_s: int = None, max_s: int = None):
    min_s = min_s or MIN_DELAY_BETWEEN_COMMENTS
    max_s = max_s or MAX_DELAY_BETWEEN_COMMENTS
    delay = random.randint(min_s, max_s)
    log(f"Waiting {delay}s before next action...")
    time.sleep(delay)


def get_reddit_session() -> RedditSession:
    session = RedditSession(REDDIT_USERNAME)
    if not session.login():
        log("ERROR: Failed to log in to Reddit! Check your cookies.")
        sys.exit(1)
    return session


# ─────────────────────────────────────────
# WARMING CYCLE v5.0
# ─────────────────────────────────────────

def run_warming_cycle(rs: RedditSession):
    """Warming cycle with ALL intelligence features."""
    log("=" * 60)
    log("WARMING CYCLE v5.0 (full intelligence suite)")
    log("=" * 60)

    karma = rs.get_karma()
    log(f"Current karma: {karma} (threshold: {WARMING_KARMA_THRESHOLD})")

    if karma >= WARMING_KARMA_THRESHOLD:
        log(f"Karma threshold reached! Switching to normal mode.")
        return run_normal_cycle(rs)

    # v5.0: Check if this is a dead hour
    if should_skip_cycle():
        log("Dead hour detected (2-4 AM). Skipping cycle.")
        return

    # Check daily warming limit
    daily_log_path = os.path.join(LOG_DIR, "daily_activity.json")
    today_comments = 0
    if os.path.exists(daily_log_path):
        try:
            with open(daily_log_path, "r") as f:
                dl = json.load(f)
                if dl.get("date") == str(datetime.now().date()):
                    today_comments = dl.get("total_comments", 0)
        except Exception:
            pass

    remaining = WARMING_MAX_PER_DAY - today_comments
    if remaining <= 0:
        log(f"Daily warming limit ({WARMING_MAX_PER_DAY}) reached. Stopping.")
        return

    comments_to_post = min(WARMING_COMMENTS_PER_CYCLE, remaining)
    log(f"Target: {comments_to_post} warming comments ({today_comments} posted today)")

    # v5.0: Get cross-platform intel for smarter topic selection
    cross_intel = get_cross_intel()
    reddit_recs = cross_intel.get_platform_recommendations("reddit")
    if reddit_recs.get("amplify_topics"):
        log(f"Cross-platform amplify: {[a['topic'] for a in reddit_recs['amplify_topics'][:3]]}")
    if reddit_recs.get("suppress_topics"):
        log(f"Cross-platform suppress: {[s['topic'] for s in reddit_recs['suppress_topics'][:3]]}")

    log("Scanning for warming opportunities...")
    opportunities = find_opportunities(mode="warming")
    if not opportunities:
        log("No warming opportunities found this cycle.")
        return

    # v5.0: Apply strategic timing filter
    opportunities = filter_by_timing(opportunities)
    log(f"After timing filter: {len(opportunities)} opportunities")
    log(get_timing_report(opportunities[:10]))

    # v5.0: Scan for competitor mentions
    scan_for_competitor_mentions(opportunities)
    competitor_threads = [t for t in opportunities if t.get("competitor_mentioned")]
    if competitor_threads:
        log(f"Found {len(competitor_threads)} competitor mention threads!")

    log(f"Starting context-aware posting...")

    comments_posted = 0
    subs_used = set()

    for i, thread in enumerate(opportunities):
        if comments_posted >= comments_to_post:
            break

        sub = thread["subreddit"]
        if sub in subs_used:
            continue
        if not can_comment_in_sub(sub):
            log(f"  Skipping r/{sub} (already commented today)")
            continue

        log(f"")
        log(f"--- Warming Comment {comments_posted + 1}/{comments_to_post} ---")
        log(f"  Sub: r/{sub}")
        log(f"  Title: {thread['title'][:70]}...")
        log(f"  Score: {thread.get('score', 0)} | Comments: {thread['num_comments']}")
        if thread.get("timing_score"):
            log(f"  Timing score: {thread['timing_score']:.0f}")
        if thread.get("competitor_mentioned"):
            log(f"  COMPETITOR DETECTED: {thread['competitor_mentioned']}")

        try:
            # Fetch thread context
            log(f"  Fetching thread context...")
            thread_context = fetch_thread_context(thread["url"])
            time.sleep(1)

            vibe = thread_context.get("thread_vibe", "unknown")
            avg_len = thread_context.get("avg_comment_length", 0)
            style = thread_context.get("top_comment_style", "no data")
            top_count = len(thread_context.get("top_comments", []))

            log(f"  Context: vibe={vibe}, avg_len={avg_len}w, top_comments={top_count}")

            # v5.0: Update subreddit profile with this thread's data
            update_profile(sub, thread_context)

            # v5.0: Get sub-specific profile for AI
            sub_profile = get_profile_for_ai(sub)
            if sub_profile:
                log(f"  Sub profile loaded ({sub})")

            # v5.0: Get performance context for AI
            perf_context = get_performance_context_for_ai(sub)
            if perf_context:
                log(f"  Performance data loaded")

            # Check if we already commented
            our_username = REDDIT_USERNAME.lower()
            already_commented = False
            for c in thread_context.get("top_comments", []):
                if c.get("author", "").lower() == our_username:
                    already_commented = True
                    break
            if already_commented:
                log(f"  Already commented, skipping.")
                save_posted_thread(thread["id"])
                continue

            # v5.0: Handle competitor threads differently
            if thread.get("competitor_mentioned") and should_respond_to_competitor(thread):
                strategy = get_competitor_response_strategy(thread)
                log(f"  Competitor strategy: {strategy.get('approach', 'unknown')}")

                # Inject competitor strategy into thread_context for AI
                thread_context["competitor_strategy"] = strategy
                thread_context["is_competitor_thread"] = True

            # Generate comment with ALL intelligence
            log(f"  Generating intelligent warming comment...")
            comment = generate_warming_comment(
                thread["title"], thread["body"], sub,
                thread_context=thread_context,
                sub_profile=sub_profile,
                performance_context=perf_context,
            )
            log(f"  Generated ({len(comment)} chars): \"{comment[:120]}\"")

            # Post it
            log(f"  Posting to r/{sub}...")
            success = post_comment(rs, thread["id"], comment)
            if success:
                record_comment(sub, thread["id"], is_promo=False, comment_text=comment)
                save_posted_thread(thread["id"])
                comments_posted += 1
                subs_used.add(sub)
                log(f"  POSTED! ({comments_posted}/{comments_to_post})")

                # v5.0: Register for damage control monitoring
                register_post("reddit", thread["id"], thread["title"][:100],
                              caption=comment, url=thread.get("url", ""))

                # v5.0: Log competitor mention if applicable
                if thread.get("competitor_mentioned"):
                    log_competitor_mention(thread, responded=True)

                # v5.0: Feed to cross-platform intel
                cross_intel.ingest_performance("reddit", {
                    "topic": thread["title"][:50],
                    "audience": sub,
                    "content_type": "comment",
                    "engagement_score": 0,  # Will be updated by upvote tracker
                    "likes": 0,
                    "comments": 0,
                    "shares": 0,
                })
            else:
                log("  Failed to post. Moving on.")

        except Exception as e:
            log(f"  Error: {e}")

        if comments_posted < comments_to_post:
            delay = random.randint(45, 120)
            log(f"  Waiting {delay}s before next comment...")
            time.sleep(delay)

    log(f"")
    log(f"=" * 60)
    log(f"WARMING CYCLE COMPLETE")
    log(f"  Comments posted: {comments_posted}/{comments_to_post}")
    log(f"  Subreddits used: {', '.join(subs_used) if subs_used else 'none'}")
    log(f"=" * 60)
    print(get_daily_summary(), flush=True)


# ─────────────────────────────────────────
# NORMAL CYCLE v5.0
# ─────────────────────────────────────────

def run_normal_cycle(rs: RedditSession):
    """Normal cycle with ALL intelligence features."""
    log("Starting NORMAL cycle v5.0 (full intelligence suite)...")
    seasonal = get_seasonal_config()
    log(f"Season: {seasonal['note']}")

    if should_skip_cycle():
        log("Dead hour detected. Skipping cycle.")
        return

    if not can_comment():
        log("Daily comment limit reached. Stopping.")
        return

    cross_intel = get_cross_intel()

    opportunities = find_opportunities(mode="normal")
    if not opportunities:
        log("No opportunities found this cycle.")
        return

    # Apply timing filter
    opportunities = filter_by_timing(opportunities)
    log(f"After timing filter: {len(opportunities)} opportunities")

    # Scan for competitor mentions
    scan_for_competitor_mentions(opportunities)
    competitor_threads = [t for t in opportunities if t.get("competitor_mentioned")]
    if competitor_threads:
        log(f"Found {len(competitor_threads)} competitor mention threads — prioritizing!")
        # Move competitor threads to the front
        non_competitor = [t for t in opportunities if not t.get("competitor_mentioned")]
        opportunities = competitor_threads + non_competitor

    comments_posted = 0

    for thread in opportunities:
        if not can_comment():
            log("Daily limit reached mid-cycle. Stopping.")
            break
        if not can_comment_in_sub(thread["subreddit"]):
            continue

        sub = thread["subreddit"]
        log(f"Classifying: r/{sub} -- {thread['title'][:60]}...")

        classification = classify_thread(
            title=thread["title"],
            body=thread["body"],
            subreddit=sub,
        )

        category = classification.get("category", "irrelevant")
        confidence = classification.get("confidence", 0)
        ai_says_mention = classification.get("should_mention_cfw", False)

        log(f"  Category: {category} | Confidence: {confidence} | Mention CFW: {ai_says_mention}")

        if category == "irrelevant" or confidence < 40:
            log("  Skipping (irrelevant or low confidence)")
            continue

        # Fetch context
        thread_context = fetch_thread_context(thread["url"])
        time.sleep(1)

        vibe = thread_context.get("thread_vibe", "unknown")
        log(f"  Context: vibe={vibe}")

        # Update sub profile
        update_profile(sub, thread_context)

        # Check if already commented
        our_username = REDDIT_USERNAME.lower()
        already_commented = False
        for c in thread_context.get("top_comments", []):
            if c.get("author", "").lower() == our_username:
                already_commented = True
                break
        for ct in thread_context.get("all_comment_texts", []):
            if our_username in ct.lower():
                already_commented = True
                break
        if already_commented:
            log("  Already commented, skipping.")
            save_posted_thread(thread["id"])
            continue

        # Competitor strategy
        if thread.get("competitor_mentioned") and should_respond_to_competitor(thread):
            strategy = get_competitor_response_strategy(thread)
            thread_context["competitor_strategy"] = strategy
            thread_context["is_competitor_thread"] = True
            log(f"  Competitor strategy: {strategy.get('approach', 'unknown')}")

        is_promo = ai_says_mention and should_be_promo()
        if category in ("direct_recommendation", "competitor_mention") and ai_says_mention:
            is_promo = True

        existing_comments = [c["body"] for c in thread_context.get("top_comments", [])[:5]]

        # Get intelligence layers
        sub_profile = get_profile_for_ai(sub)
        perf_context = get_performance_context_for_ai(sub)

        # Cross-platform check
        override = cross_intel.get_strategy_override("reddit", thread["title"][:50])
        if override.get("action") == "suppress":
            log(f"  Cross-platform SUPPRESS: {override.get('reason')}")
            continue
        elif override.get("action") == "amplify":
            log(f"  Cross-platform AMPLIFY: {override.get('reason')}")

        comment = generate_comment(
            title=thread["title"],
            body=thread["body"],
            subreddit=sub,
            category=category,
            should_mention_cfw=is_promo,
            existing_comments=existing_comments,
            thread_context=thread_context,
            sub_profile=sub_profile,
            performance_context=perf_context,
        )

        log(f"  Generated: \"{comment[:120]}\"")

        success = post_comment(rs, thread["id"], comment)
        if success:
            record_comment(sub, thread["id"], is_promo=is_promo, comment_text=comment)
            save_posted_thread(thread["id"])
            comments_posted += 1
            log(f"  Posted! ({comments_posted} today)")

            register_post("reddit", thread["id"], thread["title"][:100],
                          caption=comment, url=thread.get("url", ""))

            if thread.get("competitor_mentioned"):
                log_competitor_mention(thread, responded=True)

            cross_intel.ingest_performance("reddit", {
                "topic": thread["title"][:50],
                "audience": sub,
                "content_type": "comment",
                "engagement_score": 0,
                "likes": 0, "comments": 0, "shares": 0,
            })
        else:
            log("  Failed to post.")

        random_delay()

    log(f"Normal cycle complete. Posted {comments_posted} comments.")
    print(get_daily_summary(), flush=True)


# ─────────────────────────────────────────
# DM FOLLOW-UP
# ─────────────────────────────────────────

def run_dm_followup(rs: RedditSession):
    """Check for positive replies and send follow-up DMs."""
    log("Starting DM FOLLOW-UP check...")

    dms_sent_file = os.path.join(DATA_DIR, "dms_sent.json")
    dms_sent = set()
    if os.path.exists(dms_sent_file):
        try:
            with open(dms_sent_file, "r") as f:
                dms_sent = set(json.load(f))
        except Exception:
            pass

    all_target_subs = TIER1_LOCAL + TIER2_VEHICLE + TIER3_COMMERCIAL + INDUSTRY_SUBS
    my_comments = rs.get_my_comments(limit=20)
    promo_comments = [c for c in my_comments if c.get("subreddit") in all_target_subs]

    dm_count = 0
    for comment in promo_comments[:10]:
        if dm_count >= 3:
            break

        replies = rs.get_comment_replies(comment["permalink"])
        for reply in replies:
            author = reply.get("author", "")
            if not author or author == REDDIT_USERNAME or author in dms_sent:
                continue

            if check_positive_reply(reply["body"]):
                log(f"Positive reply from u/{author}: {reply['body'][:50]}...")

                dm_text = generate_dm_message(
                    username=author,
                    their_comment=reply["body"],
                    original_thread_title="vehicle wrap discussion",
                )

                success = send_dm(rs, author, "Quick follow-up on wraps", dm_text)
                if success:
                    dms_sent.add(author)
                    record_dm()
                    dm_count += 1
                    time.sleep(random.randint(30, 90))

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(dms_sent_file, "w") as f:
        json.dump(list(dms_sent), f)

    log(f"DM follow-up complete. Sent {dm_count} DMs.")


# ─────────────────────────────────────────
# THREAD CREATION
# ─────────────────────────────────────────

def run_thread_creation(rs: RedditSession):
    """Create a proactive thread if karma is high enough."""
    log("Starting THREAD CREATION...")

    karma = rs.get_karma()
    if karma < THREAD_CREATION_KARMA_THRESHOLD:
        log(f"Karma ({karma}) below threshold ({THREAD_CREATION_KARMA_THRESHOLD}). Skipping.")
        return

    weekly_file = os.path.join(DATA_DIR, "weekly_threads.json")
    weekly_data = {"week": "", "count": 0}
    current_week = datetime.now().strftime("%Y-W%W")

    if os.path.exists(weekly_file):
        try:
            with open(weekly_file, "r") as f:
                weekly_data = json.load(f)
        except Exception:
            pass

    if weekly_data.get("week") == current_week and weekly_data.get("count", 0) >= THREADS_PER_WEEK:
        log(f"Already created {THREADS_PER_WEEK} thread(s) this week. Skipping.")
        return

    seasonal = get_seasonal_config()
    target_sub = random.choice(seasonal["focus_subs"])
    thread_type = random.choice(["educational", "experience", "discussion"])

    log(f"Creating '{thread_type}' thread in r/{target_sub}...")
    thread_data = generate_thread_post(target_sub, thread_type)

    if thread_data and thread_data.get("title") and thread_data.get("body"):
        success = create_thread(rs, target_sub, thread_data["title"], thread_data["body"])
        if success:
            record_thread_created()
            weekly_data = {"week": current_week, "count": weekly_data.get("count", 0) + 1}
            with open(weekly_file, "w") as f:
                json.dump(weekly_data, f)
    else:
        log("Failed to generate thread content.")


# ─────────────────────────────────────────
# SCAN ONLY (dry run)
# ─────────────────────────────────────────

def run_scan_only():
    """Dry run with full intelligence analysis."""
    log("Starting SCAN-ONLY v5.0 (full intelligence)...")

    opportunities = find_opportunities(mode="warming")
    if not opportunities:
        log("No opportunities found.")
        return

    # Apply timing
    opportunities = filter_by_timing(opportunities)

    # Check competitors
    scan_for_competitor_mentions(opportunities)

    log(f"\nFound {len(opportunities)} opportunities. Analyzing top 5:\n")

    for i, thread in enumerate(opportunities[:5], 1):
        thread_context = fetch_thread_context(thread["url"])
        time.sleep(1)

        update_profile(thread["subreddit"], thread_context)

        vibe = thread_context.get("thread_vibe", "unknown")
        avg_len = thread_context.get("avg_comment_length", 0)
        top_comments = thread_context.get("top_comments", [])
        sub_profile = get_profile_for_ai(thread["subreddit"])

        sample_comment = generate_warming_comment(
            thread["title"], thread["body"], thread["subreddit"],
            thread_context=thread_context,
            sub_profile=sub_profile,
        )

        print(f"\n{'='*60}", flush=True)
        print(f"  #{i} | Timing: {thread.get('timing_score', 0):.0f}", flush=True)
        print(f"  Sub: r/{thread['subreddit']}", flush=True)
        print(f"  Title: {thread['title'][:70]}", flush=True)
        print(f"  Vibe: {vibe} | Avg len: {avg_len}w | Top comments: {len(top_comments)}", flush=True)
        if thread.get("competitor_mentioned"):
            print(f"  COMPETITOR: {thread['competitor_mentioned']}", flush=True)
        if sub_profile:
            print(f"  Sub profile: loaded", flush=True)
        print(f"  URL: {thread['url']}", flush=True)
        print(f"  SAMPLE: \"{sample_comment}\"", flush=True)

    log("Dry run complete.")


# ─────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────

def main():
    print(f"\n{'='*60}", flush=True)
    print(f"  CHICAGO FLEET WRAPS -- REDDIT BOT v5.0", flush=True)
    print(f"  Full Intelligence Suite", flush=True)
    print(f"  Upvote Tracking | Sub Profiles | Reply Engine", flush=True)
    print(f"  Strategic Timing | Competitor Monitor | Cross-Platform Intel", flush=True)
    print(f"  Damage Control | Auto-Delete & Replace", flush=True)
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print(f"{'='*60}\n", flush=True)

    mode = sys.argv[1] if len(sys.argv) > 1 else "auto"
    log(f"Mode: {mode}")

    if mode == "scan-only":
        rs = get_reddit_session()
        set_scanner_session(rs)
        run_scan_only()
        return

    if mode == "status":
        print(get_daily_summary(), flush=True)
        return

    rs = get_reddit_session()
    set_scanner_session(rs)
    karma = rs.get_karma()
    log(f"Current karma: {karma}")

    if mode == "warming":
        run_warming_cycle(rs)
    elif mode == "create-thread":
        run_thread_creation(rs)
    elif mode == "dm-check":
        run_dm_followup(rs)
    elif mode == "reply-check":
        log("Running reply-to-replies engine...")
        run_reply_cycle(rs)
    elif mode == "upvote-check":
        log("Running upvote performance tracker...")
        check_comment_performance(rs)
    elif mode == "damage-check":
        log("Running damage control check...")
        result = run_damage_check(reddit_session=rs)
        log(f"Damage check: {result}")
        # Handle replacements
        replacements = get_posts_needing_replacement()
        if replacements:
            log(f"Found {len(replacements)} posts needing replacement")
            for r in replacements[:2]:
                log(f"  Replacement needed: {r.get('platform')} - {r.get('topic', '')[:50]}")
                mark_replacement_done(r.get("post_id", ""))
    elif mode == "auto":
        # ── FULL AUTO MODE v5.0 ──
        # Step 1: Check timing
        if should_skip_cycle():
            log("Dead hour — running maintenance only (upvote check, damage control)")
            check_comment_performance(rs)
            run_damage_check(reddit_session=rs)
            return

        # Step 2: Run upvote tracking first (feeds data to AI)
        log("\n--- PHASE 1: Upvote Tracking ---")
        check_comment_performance(rs)

        # Step 3: Run damage control
        log("\n--- PHASE 2: Damage Control ---")
        damage_result = run_damage_check(reddit_session=rs)
        if damage_result.get("deleted", 0) > 0:
            log(f"Deleted {damage_result['deleted']} negative posts")

        # Step 4: Run cross-platform analysis
        log("\n--- PHASE 3: Cross-Platform Analysis ---")
        cross_intel = get_cross_intel()
        cross_result = cross_intel.run_cross_analysis()
        if cross_result:
            log(f"Cross-platform insights: {len(cross_result.get('insights', []))}")

        # Step 5: Main posting cycle
        log("\n--- PHASE 4: Main Posting Cycle ---")
        if karma < WARMING_KARMA_THRESHOLD:
            log(f"Karma ({karma}) below {WARMING_KARMA_THRESHOLD} -- warming mode")
            run_warming_cycle(rs)
        else:
            log(f"Karma ({karma}) sufficient -- normal mode")
            run_normal_cycle(rs)

        # Step 6: Reply to replies
        log("\n--- PHASE 5: Reply Engine ---")
        run_reply_cycle(rs)

        # Step 7: DM follow-up
        log("\n--- PHASE 6: DM Follow-up ---")
        run_dm_followup(rs)

        # Step 8: Occasional thread creation
        if random.random() < 0.15:
            log("\n--- PHASE 7: Thread Creation ---")
            run_thread_creation(rs)

    else:
        print(f"  Unknown mode: {mode}", flush=True)
        print("  Available: auto, warming, scan-only, create-thread, dm-check,", flush=True)
        print("             reply-check, upvote-check, damage-check, status", flush=True)

    print("\n" + get_daily_summary(), flush=True)


if __name__ == "__main__":
    main()
