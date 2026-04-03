#!/usr/bin/env python3
"""
Chicago Fleet Wraps Reddit Bot v2.1 -- Main Orchestrator
Optimized for faster warming, smarter scanning, and maximum efficiency.
All print statements use flush=True for GitHub Actions visibility.

Usage:
  python bot.py                  # Full auto run
  python bot.py warming          # Account warming mode
  python bot.py scan-only        # Scan only, no posting (dry run)
  python bot.py dm-check         # Check for DM follow-up opportunities
  python bot.py create-thread    # Create a proactive thread
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


def log(msg: str):
    """Print a timestamped log message with flush for GitHub Actions."""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"  [{ts}] {msg}", flush=True)


def random_delay(min_s: int = None, max_s: int = None):
    """Wait a random amount of time between actions to appear human.
    v2.1: Reduced warming delays for faster karma building.
    """
    min_s = min_s or MIN_DELAY_BETWEEN_COMMENTS
    max_s = max_s or MAX_DELAY_BETWEEN_COMMENTS
    delay = random.randint(min_s, max_s)
    log(f"Waiting {delay}s before next action...")
    time.sleep(delay)


def get_reddit_session() -> RedditSession:
    """Create and authenticate a Reddit session using cookies."""
    session = RedditSession(REDDIT_USERNAME)
    if not session.login():
        log("ERROR: Failed to log in to Reddit! Check your cookies.")
        sys.exit(1)
    return session


def run_warming_cycle(rs: RedditSession):
    """Run account warming: post casual comments in high-traffic subreddits.
    
    v2.1 optimizations:
    - Posts up to 5 comments per cycle
    - Targets rising/hot threads for maximum visibility
    - Uses varied personas and styles for natural-looking comments
    - Scores threads by karma potential
    - Reduced delays between warming comments (30-90s instead of 60-180s)
    - Better logging for GitHub Actions visibility
    """
    log("=" * 50)
    log("WARMING CYCLE v2.1 (accelerated)")
    log("=" * 50)

    karma = rs.get_karma()
    log(f"Current karma: {karma} (threshold: {WARMING_KARMA_THRESHOLD})")

    if karma >= WARMING_KARMA_THRESHOLD:
        log(f"Karma threshold reached! Switching to normal mode.")
        return run_normal_cycle(rs)

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
    log(f"Target: {comments_to_post} warming comments this cycle ({today_comments} posted today)")

    log("Scanning for warming opportunities...")
    opportunities = find_opportunities(mode="warming")
    if not opportunities:
        log("No warming opportunities found this cycle.")
        return

    log(f"Found {len(opportunities)} warming opportunities. Starting to post...")

    comments_posted = 0
    subs_used = set()

    for i, thread in enumerate(opportunities):
        if comments_posted >= comments_to_post:
            break

        sub = thread["subreddit"]
        # Don't comment in same sub twice per cycle
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

        try:
            log(f"  Generating warming comment...")
            comment = generate_warming_comment(thread["title"], thread["body"], sub)
            log(f"  Generated ({len(comment)} chars): \"{comment[:100]}...\"")

            log(f"  Posting to r/{sub}...")
            success = post_comment(rs, thread["id"], comment)
            if success:
                record_comment(sub, thread["id"], is_promo=False, comment_text=comment)
                save_posted_thread(thread["id"])
                comments_posted += 1
                subs_used.add(sub)
                log(f"  POSTED! ({comments_posted}/{comments_to_post})")
            else:
                log("  Failed to post. Moving on.")
        except Exception as e:
            log(f"  Error: {e}")

        # v2.1: Shorter delays during warming (30-90s) for faster karma building
        # Still human-like but more aggressive than v2.0
        if comments_posted < comments_to_post:
            delay = random.randint(30, 90)
            log(f"  Waiting {delay}s before next comment...")
            time.sleep(delay)

    log(f"")
    log(f"=" * 50)
    log(f"WARMING CYCLE COMPLETE")
    log(f"  Comments posted: {comments_posted}/{comments_to_post}")
    log(f"  Subreddits used: {', '.join(subs_used) if subs_used else 'none'}")
    log(f"=" * 50)
    print(get_daily_summary(), flush=True)


def run_normal_cycle(rs: RedditSession):
    """Run one normal cycle: scan target subs, classify, generate, and post."""
    log("Starting NORMAL cycle...")
    seasonal = get_seasonal_config()
    log(f"Season: {seasonal['note']}")

    if not can_comment():
        log("Daily comment limit reached. Stopping.")
        return

    opportunities = find_opportunities(mode="normal")
    if not opportunities:
        log("No opportunities found this cycle.")
        return

    comments_posted = 0

    for thread in opportunities:
        if not can_comment():
            log("Daily limit reached mid-cycle. Stopping.")
            break
        if not can_comment_in_sub(thread["subreddit"]):
            log(f"Already commented in r/{thread['subreddit']} today. Skipping.")
            continue

        log(f"Classifying: r/{thread['subreddit']} -- {thread['title'][:60]}...")
        classification = classify_thread(
            title=thread["title"],
            body=thread["body"],
            subreddit=thread["subreddit"],
        )

        category = classification.get("category", "irrelevant")
        confidence = classification.get("confidence", 0)
        ai_says_mention = classification.get("should_mention_cfw", False)

        log(f"  Category: {category} | Confidence: {confidence} | Mention CFW: {ai_says_mention}")

        if category == "irrelevant" or confidence < 40:
            log("  Skipping (irrelevant or low confidence)")
            continue

        is_promo = ai_says_mention and should_be_promo()
        if category in ("direct_recommendation", "competitor_mention") and ai_says_mention:
            is_promo = True

        existing_comments = get_thread_comments(thread["url"])
        time.sleep(1)

        our_comments = [c for c in existing_comments if REDDIT_USERNAME.lower() in c.lower()]
        if our_comments:
            log("  Already commented in this thread, skipping.")
            continue

        log(f"  Generating {'PROMO' if is_promo else 'VALUE'} comment...")
        comment = generate_comment(
            title=thread["title"],
            body=thread["body"],
            subreddit=thread["subreddit"],
            category=category,
            should_mention_cfw=is_promo,
            existing_comments=existing_comments,
        )

        log(f"  Generated: \"{comment[:100]}...\"")

        success = post_comment(rs, thread["id"], comment)
        if success:
            record_comment(thread["subreddit"], thread["id"], is_promo=is_promo, comment_text=comment)
            save_posted_thread(thread["id"])
            comments_posted += 1
            log(f"  Posted! ({comments_posted} today)")
        else:
            log("  Failed to post.")

        random_delay()

    log(f"Normal cycle complete. Posted {comments_posted} comments.")
    print(get_daily_summary(), flush=True)


def run_dm_followup(rs: RedditSession):
    """Check for positive replies to our comments and send follow-up DMs."""
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


def run_thread_creation(rs: RedditSession):
    """Create a proactive thread if karma is high enough."""
    log("Starting THREAD CREATION...")

    karma = rs.get_karma()
    log(f"Current karma: {karma}")

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


def run_scan_only():
    """Dry run: scan and classify without posting anything."""
    log("Starting SCAN-ONLY (dry run)...")

    opportunities = find_opportunities(mode="normal")
    if not opportunities:
        log("No opportunities found.")
        return

    log(f"\nFound {len(opportunities)} opportunities:\n")

    for i, thread in enumerate(opportunities[:15], 1):
        classification = classify_thread(
            title=thread["title"],
            body=thread["body"],
            subreddit=thread["subreddit"],
        )

        category = classification.get("category", "irrelevant")
        confidence = classification.get("confidence", 0)
        mention = classification.get("should_mention_cfw", False)

        if category != "irrelevant" and confidence >= 40:
            sample_comment = generate_comment(
                title=thread["title"],
                body=thread["body"],
                subreddit=thread["subreddit"],
                category=category,
                should_mention_cfw=mention,
            )
        else:
            sample_comment = "(would skip)"

        print(f"\n{'='*60}", flush=True)
        print(f"  #{i} | Score: {thread.get('opportunity_score', 0)}", flush=True)
        print(f"  Sub: r/{thread['subreddit']}", flush=True)
        print(f"  Title: {thread['title'][:70]}", flush=True)
        print(f"  Comments: {thread['num_comments']} | Category: {category} | Confidence: {confidence}", flush=True)
        print(f"  Mention CFW: {'YES' if mention else 'no'}", flush=True)
        print(f"  URL: {thread['url']}", flush=True)
        print(f"  Sample response: \"{sample_comment[:150]}...\"", flush=True)

    log("Dry run complete.")


def main():
    """Main entry point."""
    print(f"\n{'='*60}", flush=True)
    print(f"  CHICAGO FLEET WRAPS -- REDDIT BOT v2.1", flush=True)
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
    elif mode == "auto":
        if karma < WARMING_KARMA_THRESHOLD:
            log(f"Karma ({karma}) below {WARMING_KARMA_THRESHOLD} -- running ACCELERATED warming cycle")
            run_warming_cycle(rs)
        else:
            log(f"Karma ({karma}) sufficient -- running normal cycle")
            run_normal_cycle(rs)
            run_dm_followup(rs)
            if random.random() < 0.15:
                run_thread_creation(rs)
    else:
        print(f"  Unknown mode: {mode}", flush=True)
        print("  Available: auto, warming, scan-only, create-thread, dm-check, status", flush=True)

    print("\n" + get_daily_summary(), flush=True)


if __name__ == "__main__":
    main()
