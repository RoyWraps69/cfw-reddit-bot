"""
Chicago Fleet Wraps — Engagement Tracker v1.0
REAL-TIME ENGAGEMENT INGESTION & ATTRIBUTION ENGINE

This module replaces the slow, batch-oriented engagement checking
with a fast, attribution-aware system that:

1. Polls engagement metrics hourly for the first 24 hours of a post
2. Calculates a unified engagement score across platforms
3. Attributes success/failure to specific content components
4. Feeds results back into the optimization engine and persona engine

The attribution system answers: "WHY did this post succeed or fail?"
by analyzing the relationship between content decisions and outcomes.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from openai import OpenAI
from config import DATA_DIR, OPENAI_MODEL

log = logging.getLogger("engagement_tracker")

TRACKER_DIR = os.path.join(DATA_DIR, "engagement_tracker")
ACTIVE_POSTS_FILE = os.path.join(TRACKER_DIR, "active_posts.json")
COMPLETED_FILE = os.path.join(TRACKER_DIR, "completed_posts.json")
ATTRIBUTION_FILE = os.path.join(TRACKER_DIR, "attributions.json")

MONITORING_HOURS = 24  # How long to actively monitor a post
FINAL_CHECK_HOURS = 72  # Final engagement snapshot

base_url = os.environ.get("OPENAI_BASE_URL", None)
_client = None


def _get_client():
    global _client
    if not _client:
        _client = OpenAI(base_url=base_url) if base_url else OpenAI()
    return _client


def _ensure_dirs():
    os.makedirs(TRACKER_DIR, exist_ok=True)


def _load_json(path, default=None):
    if default is None:
        default = []
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return default


def _save_json(path, data):
    _ensure_dirs()
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


# ═══════════════════════════════════════════════════════════════
# REGISTRATION — Track new posts
# ═══════════════════════════════════════════════════════════════

def register_post(post_ids: dict, content_package: dict, arm_selection: dict = None):
    """Register a newly published post for engagement tracking.

    Args:
        post_ids: Dict of {platform: post_id} from the publishing step.
        content_package: The full content package (decision, captions, image info).
        arm_selection: The optimization engine arm selection used for this post.
    """
    active = _load_json(ACTIVE_POSTS_FILE, [])

    record = {
        "post_ids": post_ids,
        "content_package": {
            "topic": content_package.get("topic", content_package.get("decision", {}).get("topic", "")),
            "caption_preview": str(content_package.get("decision", {}).get("caption", ""))[:200],
            "image_prompt": str(content_package.get("decision", {}).get("image_prompt", ""))[:200],
            "content_type": content_package.get("decision", {}).get("content_type", "image"),
            "audience": content_package.get("decision", {}).get("audience", ""),
            "campaign": content_package.get("decision", {}).get("campaign", ""),
            "cta_style": content_package.get("decision", {}).get("cta_style", "none"),
        },
        "arm_selection": arm_selection or {},
        "posted_at": datetime.now().isoformat(),
        "engagement_snapshots": [],
        "status": "monitoring",  # monitoring, completed, attributed
        "final_score": None,
    }

    active.append(record)
    _save_json(ACTIVE_POSTS_FILE, active)
    log.info(f"Registered post for tracking: {post_ids}")


# ═══════════════════════════════════════════════════════════════
# COLLECTION — Pull engagement metrics
# ═══════════════════════════════════════════════════════════════

def collect_all_engagement():
    """Pull engagement metrics for all actively monitored posts.

    This should be called hourly by the master orchestrator.
    """
    active = _load_json(ACTIVE_POSTS_FILE, [])
    completed = _load_json(COMPLETED_FILE, [])
    now = datetime.now()
    updated = 0
    newly_completed = 0

    for record in active:
        if record["status"] != "monitoring":
            continue

        posted_at = datetime.fromisoformat(record["posted_at"])
        age_hours = (now - posted_at).total_seconds() / 3600

        # Collect engagement snapshot
        snapshot = _collect_snapshot(record["post_ids"])
        if snapshot:
            snapshot["collected_at"] = now.isoformat()
            snapshot["age_hours"] = round(age_hours, 1)
            record["engagement_snapshots"].append(snapshot)
            updated += 1

        # Check if monitoring period is over
        if age_hours >= MONITORING_HOURS:
            record["status"] = "completed"
            record["final_score"] = _calculate_final_score(record)
            completed.append(record)
            newly_completed += 1

    # Remove completed posts from active list
    active = [r for r in active if r["status"] == "monitoring"]

    _save_json(ACTIVE_POSTS_FILE, active)
    _save_json(COMPLETED_FILE, completed[-500:])  # Keep last 500

    log.info(f"Engagement collection: {updated} updated, {newly_completed} completed")
    return {"updated": updated, "completed": newly_completed}


def _collect_snapshot(post_ids: dict) -> dict:
    """Collect engagement metrics from each platform for a set of post IDs."""
    snapshot = {}

    # Facebook
    fb_id = post_ids.get("facebook")
    if fb_id:
        try:
            import facebook_bot
            eng = facebook_bot.get_engagement(fb_id)
            if eng:
                snapshot["facebook"] = eng
        except Exception as e:
            log.debug(f"FB engagement error: {e}")

    # Instagram
    ig_id = post_ids.get("instagram")
    if ig_id:
        try:
            import instagram_bot
            eng = instagram_bot.get_engagement(ig_id)
            if eng:
                snapshot["instagram"] = eng
        except Exception as e:
            log.debug(f"IG engagement error: {e}")

    return snapshot


def _calculate_final_score(record: dict) -> float:
    """Calculate a unified engagement score from all snapshots.

    Uses the latest snapshot (most complete data) and weights
    different engagement types by their value.
    """
    if not record.get("engagement_snapshots"):
        return 0.0

    latest = record["engagement_snapshots"][-1]
    score = 0.0

    for platform in ["facebook", "instagram"]:
        e = latest.get(platform, {})
        likes = (
            e.get("likes", 0)
            or e.get("like_count", 0)
            or e.get("reactions", {}).get("summary", {}).get("total_count", 0)
        )
        comments = e.get("comments", 0) or e.get("comments_count", 0) or e.get("comment_count", 0)
        shares = e.get("shares", 0) or e.get("share_count", 0)
        saves = e.get("saves", 0) or e.get("saved", 0)
        reach = e.get("reach", 0) or e.get("impressions", 0)

        # Weighted scoring: comments and shares are worth far more than likes
        score += likes * 1.0
        score += comments * 5.0
        score += shares * 8.0
        score += saves * 3.0
        score += reach * 0.01  # Small bonus for reach

    return round(score, 1)


# ═══════════════════════════════════════════════════════════════
# ATTRIBUTION — WHY did this post succeed or fail?
# ═══════════════════════════════════════════════════════════════

def run_attribution(min_posts: int = 5):
    """Analyze completed posts and attribute success/failure to content components.

    This is the core learning mechanism. It uses an LLM to identify patterns
    in what drives engagement, then feeds those insights back into the
    optimization engine and persona engine.
    """
    completed = _load_json(COMPLETED_FILE, [])
    attributed = [r for r in completed if r.get("status") == "attributed"]
    unattributed = [r for r in completed if r.get("status") == "completed"]

    if len(unattributed) < min_posts:
        log.info(f"Not enough unattributed posts ({len(unattributed)}/{min_posts})")
        return {}

    # Sort by score to identify top and bottom performers
    scored = sorted(unattributed, key=lambda r: r.get("final_score", 0), reverse=True)
    top = scored[:max(3, len(scored) // 4)]
    bottom = scored[-max(3, len(scored) // 4):]
    avg_score = sum(r.get("final_score", 0) for r in scored) / len(scored)

    # Build analysis prompt
    top_summary = []
    for r in top[:5]:
        cp = r.get("content_package", {})
        arms = r.get("arm_selection", {})
        top_summary.append(
            f"Score {r.get('final_score', 0)}: "
            f"topic='{cp.get('topic', '')}', "
            f"style='{arms.get('visual_style', '')}', "
            f"hook='{arms.get('hook_style', '')}', "
            f"tone='{arms.get('tone', '')}', "
            f"caption='{cp.get('caption_preview', '')[:100]}'"
        )

    bottom_summary = []
    for r in bottom[:5]:
        cp = r.get("content_package", {})
        arms = r.get("arm_selection", {})
        bottom_summary.append(
            f"Score {r.get('final_score', 0)}: "
            f"topic='{cp.get('topic', '')}', "
            f"style='{arms.get('visual_style', '')}', "
            f"hook='{arms.get('hook_style', '')}', "
            f"tone='{arms.get('tone', '')}', "
            f"caption='{cp.get('caption_preview', '')[:100]}'"
        )

    try:
        prompt = f"""Analyze these social media posts for Chicago Fleet Wraps (vehicle wrap company).

TOP PERFORMERS (high engagement):
{chr(10).join(top_summary)}

BOTTOM PERFORMERS (low engagement):
{chr(10).join(bottom_summary)}

Average score: {avg_score:.1f}

Identify the KEY PATTERNS that drive engagement. Return ONLY valid JSON:
{{
    "winning_patterns": [
        "Specific pattern that drives engagement (be precise)"
    ],
    "losing_patterns": [
        "Specific pattern that kills engagement (be precise)"
    ],
    "visual_style_winner": "The visual style that works best",
    "hook_style_winner": "The hook style that works best",
    "tone_winner": "The tone that works best",
    "actionable_insight": "One specific, actionable recommendation for the next batch",
    "confidence": "low|medium|high"
}}"""

        response = _get_client().chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=400,
        )

        result = response.choices[0].message.content.strip()
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]

        attribution = json.loads(result.strip())
        attribution["analyzed_at"] = datetime.now().isoformat()
        attribution["posts_analyzed"] = len(scored)
        attribution["avg_score"] = round(avg_score, 1)

        # Save attribution
        attributions = _load_json(ATTRIBUTION_FILE, [])
        attributions.append(attribution)
        _save_json(ATTRIBUTION_FILE, attributions[-100:])

        # Mark posts as attributed
        for r in unattributed:
            r["status"] = "attributed"
        _save_json(COMPLETED_FILE, completed[-500:])

        # Feed results back into optimization engine
        _feed_back_to_optimizer(scored)

        # Feed results back into persona engine
        _feed_back_to_persona(top, bottom)

        log.info(f"Attribution complete: {len(scored)} posts analyzed")
        return attribution

    except Exception as e:
        log.error(f"Attribution error: {e}")
        return {}


def _feed_back_to_optimizer(scored_posts: list):
    """Feed engagement outcomes back into the optimization engine."""
    try:
        from optimization_engine import record_outcome

        for record in scored_posts:
            arm_selection = record.get("arm_selection", {})
            final_score = record.get("final_score", 0)
            if arm_selection:
                record_outcome(arm_selection, final_score)

        log.info(f"Fed {len(scored_posts)} outcomes to optimization engine")
    except Exception as e:
        log.error(f"Optimizer feedback error: {e}")


def _feed_back_to_persona(top_posts: list, bottom_posts: list):
    """Feed engagement outcomes back into the persona engine."""
    try:
        from persona_engine import evolve_persona

        # Group by platform
        platforms = set()
        for r in top_posts + bottom_posts:
            for platform in r.get("post_ids", {}).keys():
                platforms.add(platform)

        for platform in platforms:
            top_for_platform = [
                {
                    "caption": r.get("content_package", {}).get("caption_preview", ""),
                    "score": r.get("final_score", 0),
                }
                for r in top_posts
                if platform in r.get("post_ids", {})
            ]
            bottom_for_platform = [
                {
                    "caption": r.get("content_package", {}).get("caption_preview", ""),
                    "score": r.get("final_score", 0),
                }
                for r in bottom_posts
                if platform in r.get("post_ids", {})
            ]

            if top_for_platform or bottom_for_platform:
                evolve_persona(platform, top_for_platform, bottom_for_platform)

        log.info(f"Fed persona evolution for {len(platforms)} platforms")
    except Exception as e:
        log.error(f"Persona feedback error: {e}")


# ═══════════════════════════════════════════════════════════════
# INSIGHTS — Get learning context for content generation
# ═══════════════════════════════════════════════════════════════

def get_learning_context() -> str:
    """Get a formatted string of attribution insights to inject into content prompts.

    This replaces the basic get_learning_context() in content_queue.py with
    richer, attribution-based insights.
    """
    attributions = _load_json(ATTRIBUTION_FILE, [])
    if not attributions:
        return ""

    latest = attributions[-1]
    parts = []

    winning = latest.get("winning_patterns", [])
    if winning:
        parts.append(f"WINNING PATTERNS: {'; '.join(winning[:3])}")

    losing = latest.get("losing_patterns", [])
    if losing:
        parts.append(f"AVOID THESE PATTERNS: {'; '.join(losing[:3])}")

    if latest.get("visual_style_winner"):
        parts.append(f"BEST VISUAL STYLE: {latest['visual_style_winner']}")

    if latest.get("hook_style_winner"):
        parts.append(f"BEST HOOK STYLE: {latest['hook_style_winner']}")

    if latest.get("tone_winner"):
        parts.append(f"BEST TONE: {latest['tone_winner']}")

    if latest.get("actionable_insight"):
        parts.append(f"KEY INSIGHT: {latest['actionable_insight']}")

    if latest.get("avg_score"):
        parts.append(f"Current avg engagement score: {latest['avg_score']} (beat this!)")

    return "\n".join(parts)


# ═══════════════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════════════

def get_tracker_dashboard() -> dict:
    """Get engagement tracker data for the unified dashboard."""
    active = _load_json(ACTIVE_POSTS_FILE, [])
    completed = _load_json(COMPLETED_FILE, [])
    attributions = _load_json(ATTRIBUTION_FILE, [])

    scored = [r for r in completed if r.get("final_score") is not None]
    avg_score = (
        sum(r["final_score"] for r in scored) / len(scored) if scored else 0
    )

    return {
        "active_monitoring": len(active),
        "total_completed": len(completed),
        "total_attributions": len(attributions),
        "avg_engagement_score": round(avg_score, 1),
        "latest_attribution": attributions[-1] if attributions else None,
    }


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd == "collect":
        collect_all_engagement()
    elif cmd == "attribute":
        result = run_attribution(min_posts=3)
        print(json.dumps(result, indent=2))
    elif cmd == "insights":
        print(get_learning_context())
    elif cmd == "status":
        dashboard = get_tracker_dashboard()
        print(json.dumps(dashboard, indent=2))
    else:
        print("Usage: python engagement_tracker.py [collect|attribute|insights|status]")
