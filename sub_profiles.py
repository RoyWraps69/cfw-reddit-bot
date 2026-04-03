"""
Chicago Fleet Wraps Reddit Bot — Subreddit Personality Profiles v1.0
Builds and maintains a style profile per subreddit based on top-voted comments
we've analyzed. The bot gets smarter the more it posts.

Each profile tracks:
- Average winning comment length
- Dominant tone (humor, technical, personal, casual)
- Common patterns (questions, links, specific details)
- Our own performance in that sub (from upvote_tracker)
- Sample winning comments for the AI to study
"""
import json
import os
from datetime import datetime
from config import DATA_DIR

SUB_PROFILES_FILE = os.path.join(DATA_DIR, "sub_profiles.json")
MAX_SAMPLES_PER_SUB = 10  # Keep top 10 sample comments per sub


def _load_profiles() -> dict:
    """Load all subreddit profiles."""
    if os.path.exists(SUB_PROFILES_FILE):
        try:
            with open(SUB_PROFILES_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, Exception):
            return {}
    return {}


def _save_profiles(profiles: dict):
    """Save all subreddit profiles."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(SUB_PROFILES_FILE, "w") as f:
        json.dump(profiles, f, indent=2)


def update_profile(subreddit: str, thread_context: dict):
    """Update a subreddit's personality profile based on new thread context data.

    Called every time we analyze a thread in a subreddit. Over time, this builds
    a rich picture of what works in each community.
    """
    if not thread_context or not thread_context.get("top_comments"):
        return

    profiles = _load_profiles()
    sub = subreddit.lower()

    if sub not in profiles:
        profiles[sub] = {
            "subreddit": subreddit,
            "created_at": datetime.now().isoformat(),
            "threads_analyzed": 0,
            "total_comments_seen": 0,
            "avg_winning_length": 0,
            "tone_counts": {"humor": 0, "technical": 0, "personal": 0, "casual": 0, "supportive": 0},
            "pattern_counts": {"questions": 0, "links": 0, "specific_details": 0, "one_liners": 0},
            "sample_winners": [],
            "vibe_counts": {"question": 0, "showcase": 0, "rant": 0, "humor": 0, "discussion": 0, "news": 0},
            "our_avg_score": 0,
            "our_comment_count": 0,
        }

    profile = profiles[sub]
    profile["threads_analyzed"] += 1
    profile["updated_at"] = datetime.now().isoformat()

    top_comments = thread_context.get("top_comments", [])
    profile["total_comments_seen"] += len(top_comments)

    # Update average winning length (rolling average)
    if top_comments:
        new_avg = sum(c.get("word_count", 0) for c in top_comments) / len(top_comments)
        old_avg = profile["avg_winning_length"]
        n = profile["threads_analyzed"]
        # Weighted rolling average
        profile["avg_winning_length"] = round(((old_avg * (n - 1)) + new_avg) / n, 1)

    # Analyze tone patterns from top comments
    for c in top_comments[:5]:  # Only analyze top 5
        body = c.get("body", "").lower()
        score = c.get("score", 0)

        # Only learn from comments with positive scores
        if score < 2:
            continue

        # Tone detection
        if any(w in body for w in ["lol", "lmao", "haha", "😂", "💀", "bruh", "dead"]):
            profile["tone_counts"]["humor"] += 1
        if any(w in body for w in ["because", "actually", "specifically", "technically", "the reason"]):
            profile["tone_counts"]["technical"] += 1
        if any(w in body for w in ["i ", "my ", "i'm", "i've", "i had", "my car", "my truck"]):
            profile["tone_counts"]["personal"] += 1
        if any(w in body for w in ["sorry", "that sucks", "hope", "good luck", "hang in there"]):
            profile["tone_counts"]["supportive"] += 1
        if len(body.split()) < 30 and not any(w in body for w in ["because", "actually"]):
            profile["tone_counts"]["casual"] += 1

        # Pattern detection
        if "?" in body:
            profile["pattern_counts"]["questions"] += 1
        if "http" in body or "www." in body:
            profile["pattern_counts"]["links"] += 1
        if any(char.isdigit() for char in body) or "$" in body:
            profile["pattern_counts"]["specific_details"] += 1
        if len(body.split()) < 15:
            profile["pattern_counts"]["one_liners"] += 1

    # Track thread vibes
    vibe = thread_context.get("thread_vibe", "discussion")
    if vibe in profile["vibe_counts"]:
        profile["vibe_counts"][vibe] += 1

    # Store sample winning comments (highest-scored from this thread)
    for c in top_comments[:2]:
        if c.get("score", 0) >= 5:
            sample = {
                "body": c["body"][:200],
                "score": c["score"],
                "word_count": c.get("word_count", 0),
                "added_at": datetime.now().isoformat(),
            }
            profile["sample_winners"].append(sample)

    # Keep only the best samples
    profile["sample_winners"].sort(key=lambda x: x["score"], reverse=True)
    profile["sample_winners"] = profile["sample_winners"][:MAX_SAMPLES_PER_SUB]

    profiles[sub] = profile
    _save_profiles(profiles)


def update_our_performance(subreddit: str, score: int):
    """Update our own performance stats in a subreddit.

    Called by the upvote tracker when it checks our comment scores.
    """
    profiles = _load_profiles()
    sub = subreddit.lower()

    if sub not in profiles:
        return  # Don't create a profile just for performance data

    profile = profiles[sub]
    old_avg = profile.get("our_avg_score", 0)
    old_count = profile.get("our_comment_count", 0)
    new_count = old_count + 1
    profile["our_avg_score"] = round(((old_avg * old_count) + score) / new_count, 1)
    profile["our_comment_count"] = new_count

    profiles[sub] = profile
    _save_profiles(profiles)


def get_profile_for_ai(subreddit: str) -> str:
    """Get a formatted profile string for the AI responder.

    This tells the AI exactly what works in this specific subreddit
    based on all the data we've collected.
    """
    profiles = _load_profiles()
    sub = subreddit.lower()

    if sub not in profiles or profiles[sub].get("threads_analyzed", 0) < 2:
        return ""  # Not enough data yet

    profile = profiles[sub]

    parts = []
    parts.append(f"SUBREDDIT PERSONALITY PROFILE for r/{subreddit}:")
    parts.append(f"Based on {profile['threads_analyzed']} threads analyzed, "
                 f"{profile['total_comments_seen']} comments studied.")

    # Winning length
    avg_len = profile.get("avg_winning_length", 0)
    if avg_len > 0:
        if avg_len < 20:
            parts.append(f"Winning comments here are SHORT (~{avg_len:.0f} words). Keep it brief.")
        elif avg_len < 50:
            parts.append(f"Winning comments here are MEDIUM length (~{avg_len:.0f} words).")
        else:
            parts.append(f"Winning comments here are DETAILED (~{avg_len:.0f} words). More info = more upvotes.")

    # Dominant tone
    tones = profile.get("tone_counts", {})
    if tones:
        dominant = max(tones, key=tones.get)
        total_tone = sum(tones.values())
        if total_tone > 0:
            pct = round(tones[dominant] / total_tone * 100)
            tone_desc = {
                "humor": "funny/sarcastic",
                "technical": "technical/informative",
                "personal": "personal experience sharing",
                "casual": "casual/brief",
                "supportive": "supportive/empathetic",
            }
            parts.append(f"Dominant tone: {tone_desc.get(dominant, dominant)} ({pct}% of winners)")

    # Patterns
    patterns = profile.get("pattern_counts", {})
    if patterns:
        active_patterns = [(k, v) for k, v in patterns.items() if v > 2]
        if active_patterns:
            active_patterns.sort(key=lambda x: x[1], reverse=True)
            pattern_desc = {
                "questions": "follow-up questions",
                "links": "include links/references",
                "specific_details": "specific numbers/details",
                "one_liners": "one-liners",
            }
            pattern_strs = [pattern_desc.get(p[0], p[0]) for p in active_patterns[:3]]
            parts.append(f"Winning patterns: {', '.join(pattern_strs)}")

    # Our performance
    if profile.get("our_comment_count", 0) > 0:
        parts.append(f"YOUR performance here: avg score {profile['our_avg_score']} "
                     f"from {profile['our_comment_count']} comments")

    # Sample winners
    samples = profile.get("sample_winners", [])
    if samples:
        parts.append("Example winning comments in this sub:")
        for s in samples[:3]:
            parts.append(f"  [{s['score']}pts, {s['word_count']}w] \"{s['body'][:80]}...\"")

    return "\n".join(parts)


def get_all_profiles_summary() -> dict:
    """Get a summary of all profiles for the dashboard."""
    profiles = _load_profiles()

    summary = {}
    for sub, profile in profiles.items():
        tones = profile.get("tone_counts", {})
        dominant_tone = max(tones, key=tones.get) if tones and sum(tones.values()) > 0 else "unknown"

        summary[sub] = {
            "threads_analyzed": profile.get("threads_analyzed", 0),
            "avg_winning_length": profile.get("avg_winning_length", 0),
            "dominant_tone": dominant_tone,
            "our_avg_score": profile.get("our_avg_score", 0),
            "our_comment_count": profile.get("our_comment_count", 0),
            "sample_count": len(profile.get("sample_winners", [])),
        }

    return summary
