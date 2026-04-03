"""
Chicago Fleet Wraps Reddit Bot — Strategic Timing v1.0
Posts when threads are 1-3 hours old (the sweet spot for getting upvoted).

Research shows:
- Comments on threads < 1 hour old: thread might die before getting traction
- Comments on threads 1-3 hours old: SWEET SPOT — thread is rising, early comments get upvoted
- Comments on threads 3-6 hours old: still decent, but top spots are taken
- Comments on threads 6+ hours old: buried, almost no karma potential

This module:
1. Scores threads by timing (how close to the sweet spot)
2. Filters out threads that are too new or too old
3. Prioritizes threads that are actively rising (upvote velocity)
4. Adjusts for subreddit size (bigger subs move faster)
"""
import time
from datetime import datetime


# Timing sweet spots (hours)
IDEAL_MIN_AGE = 1.0     # Don't comment on threads younger than 1 hour
IDEAL_MAX_AGE = 3.0     # Best window is 1-3 hours
ACCEPTABLE_MAX_AGE = 6.0  # Still okay up to 6 hours
ABSOLUTE_MAX_AGE = 12.0   # Never comment on threads older than 12 hours

# Subreddit size tiers (affects timing)
# Bigger subs move faster, so the window is tighter
BIG_SUBS = [
    "cars", "idiotsincars", "teslamotors", "bmw", "porsche",
    "chicago", "smallbusiness", "entrepreneur", "carporn",
    "justrolledintotheshop", "cartalk", "mechanicadvice",
]
MEDIUM_SUBS = [
    "mustang", "corvette", "wrx", "charger", "f150", "ram_trucks",
    "trucks", "rivian", "autodetailing", "vandwellers",
    "chicagosuburbs", "foodtrucks",
]
# Everything else is considered a small sub


def get_thread_timing_score(thread: dict) -> float:
    """Score a thread based on how well-timed it is for commenting.

    Returns a score from 0 to 100:
    - 80-100: Perfect timing (1-3 hours old, rising)
    - 50-79: Good timing (slightly outside sweet spot)
    - 20-49: Okay timing (still worth it if content is great)
    - 0-19: Bad timing (too new or too old)
    """
    age_hours = (time.time() - thread.get("created_utc", 0)) / 3600
    subreddit = thread.get("subreddit", "").lower()
    score_val = thread.get("score", 0)
    num_comments = thread.get("num_comments", 0)
    upvote_ratio = thread.get("upvote_ratio", 0.5)

    # Adjust sweet spot based on sub size
    if subreddit in BIG_SUBS:
        # Big subs: window is 0.5-2 hours (moves fast)
        min_age = 0.5
        ideal_max = 2.0
        acceptable_max = 4.0
    elif subreddit in MEDIUM_SUBS:
        # Medium subs: window is 1-3 hours
        min_age = 1.0
        ideal_max = 3.0
        acceptable_max = 6.0
    else:
        # Small subs: window is 1-5 hours (moves slow)
        min_age = 1.0
        ideal_max = 5.0
        acceptable_max = 8.0

    timing_score = 0.0

    # Age scoring
    if age_hours < min_age:
        # Too new — risky, thread might not take off
        timing_score = max(0, 30 * (age_hours / min_age))
    elif min_age <= age_hours <= ideal_max:
        # SWEET SPOT
        # Peak score at the middle of the sweet spot
        mid = (min_age + ideal_max) / 2
        distance_from_mid = abs(age_hours - mid) / (ideal_max - min_age)
        timing_score = 100 - (distance_from_mid * 20)
    elif ideal_max < age_hours <= acceptable_max:
        # Still okay but declining
        progress = (age_hours - ideal_max) / (acceptable_max - ideal_max)
        timing_score = 60 - (progress * 40)
    elif age_hours > acceptable_max:
        # Too old
        timing_score = max(0, 20 - ((age_hours - acceptable_max) * 5))

    # Bonus: thread is actively rising (high upvote ratio + growing comments)
    if upvote_ratio > 0.85 and score_val > 5:
        timing_score += 10  # Thread is hot

    # Bonus: thread has engagement but not too much (sweet spot for visibility)
    if 3 <= num_comments <= 20:
        timing_score += 5  # Good comment count — we'll be visible
    elif num_comments < 3:
        timing_score += 3  # Very early — could be great or could die
    elif num_comments > 50:
        timing_score -= 10  # Too many comments, we'll be buried

    return min(100, max(0, timing_score))


def filter_by_timing(threads: list, min_score: float = 20.0) -> list:
    """Filter and re-sort threads by timing score.

    Threads below min_score are dropped entirely.
    Remaining threads are sorted by timing score (best first).
    """
    scored = []
    for t in threads:
        timing_score = get_thread_timing_score(t)
        t["timing_score"] = timing_score
        if timing_score >= min_score:
            scored.append(t)

    scored.sort(key=lambda x: x["timing_score"], reverse=True)
    return scored


def get_optimal_post_times() -> dict:
    """Return the optimal posting times based on research.

    Reddit peak activity (US-centric):
    - Weekdays: 6-8 AM EST (people checking Reddit before work)
    - Weekdays: 12-2 PM EST (lunch break)
    - Weekdays: 6-9 PM EST (after work)
    - Weekends: 9-11 AM EST (lazy morning browsing)

    For a Chicago-focused bot, we want to be active when Chicago
    people are online (Central time = EST - 1).
    """
    now = datetime.now()
    hour = now.hour  # Server time (likely UTC, but we handle it)
    day = now.weekday()  # 0=Monday

    # These are CDT (UTC-5) hours
    # Convert if needed based on server timezone
    peak_windows = {
        "early_morning": (5, 8),    # 5-8 AM CDT
        "lunch": (11, 14),          # 11 AM - 2 PM CDT
        "evening": (17, 21),        # 5-9 PM CDT
        "weekend_morning": (8, 12), # 8 AM - 12 PM CDT (weekends)
    }

    is_weekend = day >= 5
    is_peak = False

    if is_weekend:
        start, end = peak_windows["weekend_morning"]
        is_peak = start <= hour <= end
    else:
        for window_name in ["early_morning", "lunch", "evening"]:
            start, end = peak_windows[window_name]
            if start <= hour <= end:
                is_peak = True
                break

    return {
        "is_peak_time": is_peak,
        "current_hour": hour,
        "is_weekend": is_weekend,
        "recommendation": "post now" if is_peak else "wait for peak hours if possible",
    }


def should_skip_cycle() -> bool:
    """Determine if we should skip this cycle entirely based on timing.

    We don't want to waste API calls during dead hours.
    Returns True if it's a dead time (2-5 AM CDT).
    """
    hour = datetime.now().hour
    # Dead hours: 2-5 AM CDT
    if 2 <= hour <= 4:
        return True
    return False


def get_timing_report(threads: list) -> str:
    """Generate a human-readable timing report for logging."""
    if not threads:
        return "No threads to analyze."

    lines = []
    optimal = get_optimal_post_times()
    lines.append(f"Current time: {datetime.now().strftime('%I:%M %p')} "
                 f"({'PEAK' if optimal['is_peak_time'] else 'off-peak'})")

    for t in threads[:10]:
        age_hours = (time.time() - t.get("created_utc", 0)) / 3600
        timing_score = t.get("timing_score", get_thread_timing_score(t))

        if timing_score >= 80:
            label = "PERFECT"
        elif timing_score >= 50:
            label = "GOOD"
        elif timing_score >= 20:
            label = "OKAY"
        else:
            label = "SKIP"

        lines.append(f"  [{label} {timing_score:.0f}] r/{t['subreddit']}: "
                     f"\"{t['title'][:45]}...\" (age: {age_hours:.1f}h, "
                     f"score: {t.get('score', 0)}, comments: {t.get('num_comments', 0)})")

    return "\n".join(lines)
