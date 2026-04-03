#!/usr/bin/env python3
"""
Chicago Fleet Wraps Reddit Bot — Main Orchestrator
Runs the full bot cycle: scan → classify → respond → track.
Designed to run on Railway or any server via cron/scheduler.

Usage:
  python3.11 bot.py                  # Full auto run
  python3.11 bot.py warming          # Account warming mode
  python3.11 bot.py scan-only        # Scan only, no posting (dry run)
  python3.11 bot.py dm-check         # Check for DM follow-up opportunities
  python3.11 bot.py create-thread    # Create a proactive thread
  python3.11 bot.py status           # Show daily activity summary
"""
import sys
import os
import time
import random
import json
from datetime import datetime

# Ensure we can import from the project directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    REDDIT_USERNAME, MAX_COMMENTS_PER_DAY, PROMO_RATIO,
    WARMING_KARMA_THRESHOLD, THREAD_CREATION_KARMA_THRESHOLD,
    THREADS_PER_WEEK, DATA_DIR, LOG_DIR,
    TIER1_LOCAL, TIER2_VEHICLE, TIER3_COMMERCIAL, INDUSTRY_SUBS,
    get_seasonal_config,
)
from reddit_session import RedditSession
from scanner import (
    find_opportunities, save_posted_thread,
    get_thread_comments, check_for_competitor_mentions,
)
from ai_responder import (
    classify_thread, generate_comment, generate_warming_comment,
    generate_dm_message, generate_thread_post, check_positive_reply,
)
from poster import post_comment, send_dm, create_thread, random_delay
from tracker import (
    can_comment, can_comment_in_sub, should_be_promo,
    record_comment, record_dm, record_thread_created,
    get_daily_summary,
)


def log(msg: str):
    """Print a timestamped log message."""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"  [{ts}] {msg}")


def get_reddit_session() -> RedditSession:
    """Create and authenticate a Reddit session."""
    password = os.environ.get("REDDIT_PASSWORD", "")
    if not password:
        log("ERROR: REDDIT_PASSWORD environment variable not set!")
        sys.exit(1)

    session = RedditSession(REDDIT_USERNAME, password)
    if not session.login():
        log("ERROR: Failed to log in to Reddit!")
        sys.exit(1)

    return session


def run_warming_cycle(rs: RedditSession):
    """Run account warming: post casual comments in non-target subreddits."""
    log("Starting WARMING cycle...")

    karma = rs.get_karma()
    log(f"Current karma: {karma}")

    if karma >= WARMING_KARMA_THRESHOLD:
        log(f"Karma threshold ({WARMING_KARMA_THRESHOLD}) reached! Switching to normal mode.")
        return run_normal_cycle(rs)

    if not can_comment():
        log("Daily comment limit reached. Stopping.")
        return

    opportunities = find_opportunities(mode="warming")
    if not opportunities:
        log("No warming opportunities found.")
        return

    random.shuffle(opportunities)
    targets = opportunities[:2]

    for thread in targets:
        if not can_comment():
            break
        if not can_comment_in_sub(thread["subreddit"]):
            continue

        log(f"Warming comment on r/{thread['subreddit']}: {thread['title'][:50]}...")
        comment = generate_warming_comment(thread["title"], thread["body"], thread["subreddit"])
        log(f"Generated: \"{comment[:80]}...\"")

        success = post_comment(rs, thread["id"], comment)
        if success:
            record_comment(thread["subreddit"], thread["id"], is_promo=False, comment_text=comment)
            save_posted_thread(thread["id"])
            log("Posted successfully!")
        else:
            log("Failed to post. Skipping.")

        random_delay()

    log("Warming cycle complete.")
    print(get_daily_summary())


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

        # Classify the thread
        log(f"Classifying: r/{thread['subreddit']} — {thread['title'][:60]}...")
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

        # Determine promo vs value
        is_promo = ai_says_mention and should_be_promo()
        if category in ("direct_recommendation", "competitor_mention") and ai_says_mention:
            is_promo = True

        # Get existing comments for context
        existing_comments = get_thread_comments(thread["url"])
        time.sleep(1)

        # Check if we already commented
        our_comments = [c for c in existing_comments if REDDIT_USERNAME.lower() in c.lower()]
        if our_comments:
            log("  Already commented in this thread, skipping.")
            continue

        # Generate the comment
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

        # Post it
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
    print(get_daily_summary())


def run_dm_followup(rs: RedditSession):
    """Check for positive replies to our comments and send follow-up DMs."""
    log("Starting DM FOLLOW-UP check...")

    dms_sent_file = os.path.join(DATA_DIR, "dms_sent.json")
    dms_sent = set()
    if os.path.exists(dms_sent_file):
        with open(dms_sent_file, "r") as f:
            dms_sent = set(json.load(f))

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
        with open(weekly_file, "r") as f:
            weekly_data = json.load(f)

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

        print(f"\n{'─'*60}")
        print(f"  #{i} | Score: {thread.get('opportunity_score', 0)}")
        print(f"  Sub: r/{thread['subreddit']}")
        print(f"  Title: {thread['title'][:70]}")
        print(f"  Comments: {thread['num_comments']} | Category: {category} | Confidence: {confidence}")
        print(f"  Mention CFW: {'YES' if mention else 'no'}")
        print(f"  URL: {thread['url']}")
        print(f"  Sample response: \"{sample_comment[:150]}...\"")

    log("Dry run complete.")


def main():
    """Main entry point."""
    print(f"\n{'='*60}")
    print(f"  CHICAGO FLEET WRAPS — REDDIT BOT")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    mode = sys.argv[1] if len(sys.argv) > 1 else "auto"

    if mode == "scan-only":
        run_scan_only()
        return

    if mode == "status":
        print(get_daily_summary())
        return

    # All other modes need authentication
    rs = get_reddit_session()
    karma = rs.get_karma()
    log(f"Current karma: {karma}")

    if mode == "warming":
        run_warming_cycle(rs)
    elif mode == "create-thread":
        run_thread_creation(rs)
    elif mode == "dm-check":
        run_dm_followup(rs)
    elif mode == "auto":
        # Auto mode: determine what to do based on karma
        if karma < WARMING_KARMA_THRESHOLD:
            log(f"Karma ({karma}) below {WARMING_KARMA_THRESHOLD} — running warming cycle")
            run_warming_cycle(rs)
        else:
            log(f"Karma ({karma}) sufficient — running normal cycle")
            run_normal_cycle(rs)
            run_dm_followup(rs)

            # Maybe create a thread (~15% chance each run ≈ 1/week at 2hr intervals)
            if random.random() < 0.15:
                run_thread_creation(rs)
    else:
        print(f"  Unknown mode: {mode}")
        print("  Available: auto, warming, scan-only, create-thread, dm-check, status")

    print("\n" + get_daily_summary())


if __name__ == "__main__":
    main()
