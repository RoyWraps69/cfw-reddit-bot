"""
Chicago Fleet Wraps — Proactive Engagement Agent v1.0
RELATIONSHIP BUILDING & TREND SURFING

This module handles the "turned on to accept all help" mandate.
Instead of just dropping comments on keyword-matched posts,
it builds genuine relationships and surfs trends.

Three modes:
1. RELATIONSHIP BUILDER: Identify high-value accounts and consistently
   engage with their content to build rapport over time.
2. TREND SURFER: Monitor rapidly rising topics/trends and generate
   relevant content to ride the wave.
3. COMMUNITY RESPONDER: Reply to every comment, DM, and mention
   with genuine, persona-driven responses.
"""

import os
import json
import random
from datetime import datetime, timedelta
from config import DATA_DIR

ENGAGE_DIR = os.path.join(DATA_DIR, "proactive_engagement")
RELATIONSHIPS_FILE = os.path.join(ENGAGE_DIR, "relationships.json")
TREND_LOG_FILE = os.path.join(ENGAGE_DIR, "trend_log.json")
INTERACTION_LOG_FILE = os.path.join(ENGAGE_DIR, "interaction_log.json")

# High-value account categories to track
ACCOUNT_CATEGORIES = {
    "local_businesses": {
        "description": "Chicago-area businesses that could need wraps or refer clients",
        "engagement_strategy": "Be supportive and helpful. Comment on their wins. Share their content.",
        "examples": [
            "Chicago food trucks", "local auto dealers", "Chicago real estate agents",
            "Chicago contractors", "Chicago event planners",
        ],
    },
    "car_influencers": {
        "description": "Automotive content creators who could feature CFW work",
        "engagement_strategy": "Show genuine appreciation for their content. Offer insights on wraps.",
        "examples": [
            "Car detailing channels", "automotive photographers", "car meet organizers",
            "car review channels", "drift/racing content creators",
        ],
    },
    "wrap_community": {
        "description": "Other wrap shops and vinyl enthusiasts (community, not competition)",
        "engagement_strategy": "Respect their work. Share techniques. Build industry rapport.",
        "examples": [
            "Wrap shops in other cities", "vinyl manufacturers", "wrap training accounts",
            "3M/Avery/Inozetek brand accounts",
        ],
    },
    "chicago_community": {
        "description": "Chicago-focused accounts that build local presence",
        "engagement_strategy": "Be a proud Chicagoan. Engage with city pride content.",
        "examples": [
            "Chicago news", "Chicago events", "Chicago sports",
            "Chicago neighborhoods", "Chicago small business groups",
        ],
    },
}


def _ensure_dirs():
    os.makedirs(ENGAGE_DIR, exist_ok=True)


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
# RELATIONSHIP BUILDER
# ═══════════════════════════════════════════════════════════════

def add_relationship(platform: str, username: str, category: str,
                     notes: str = "") -> dict:
    """Add a high-value account to the relationship tracker.

    Args:
        platform: The platform (reddit, facebook, instagram, tiktok).
        username: The account username/handle.
        category: One of the ACCOUNT_CATEGORIES keys.
        notes: Optional notes about this account.
    """
    relationships = _load_json(RELATIONSHIPS_FILE, [])

    # Check for duplicates
    for r in relationships:
        if r["platform"] == platform and r["username"] == username:
            return r

    record = {
        "platform": platform,
        "username": username,
        "category": category,
        "notes": notes,
        "added_at": datetime.now().isoformat(),
        "interactions": 0,
        "last_interaction": None,
        "rapport_score": 0,  # 0-100, increases with consistent engagement
        "status": "new",  # new, building, established, champion
    }

    relationships.append(record)
    _save_json(RELATIONSHIPS_FILE, relationships)
    return record


def get_engagement_targets(platform: str, max_targets: int = 5) -> list:
    """Get a list of accounts to engage with today.

    Prioritizes accounts that haven't been engaged with recently
    and those in the "building" phase of the relationship.
    """
    relationships = _load_json(RELATIONSHIPS_FILE, [])
    now = datetime.now()

    platform_accounts = [r for r in relationships if r["platform"] == platform]

    # Score each account for engagement priority
    scored = []
    for r in platform_accounts:
        priority = 0

        # New accounts get high priority (first impressions matter)
        if r["status"] == "new":
            priority += 50

        # Building relationships need consistent attention
        elif r["status"] == "building":
            priority += 30

        # Haven't interacted recently? Bump priority
        if r.get("last_interaction"):
            last = datetime.fromisoformat(r["last_interaction"])
            days_since = (now - last).days
            if days_since >= 3:
                priority += 20
            elif days_since >= 1:
                priority += 10
        else:
            priority += 25  # Never interacted

        # Add some randomness to avoid being predictable
        priority += random.randint(0, 10)

        scored.append((r, priority))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [r for r, _ in scored[:max_targets]]


def record_interaction(platform: str, username: str, interaction_type: str,
                       content: str = ""):
    """Record an interaction with a tracked account.

    Args:
        platform: The platform.
        username: The account interacted with.
        interaction_type: "comment", "like", "share", "reply", "dm".
        content: The content of the interaction (optional).
    """
    relationships = _load_json(RELATIONSHIPS_FILE, [])

    for r in relationships:
        if r["platform"] == platform and r["username"] == username:
            r["interactions"] += 1
            r["last_interaction"] = datetime.now().isoformat()

            # Update rapport score
            interaction_values = {
                "like": 1, "comment": 3, "reply": 4, "share": 5, "dm": 2,
            }
            r["rapport_score"] = min(
                100, r["rapport_score"] + interaction_values.get(interaction_type, 1)
            )

            # Update status based on rapport
            if r["rapport_score"] >= 50:
                r["status"] = "established"
            elif r["rapport_score"] >= 15:
                r["status"] = "building"

            break

    _save_json(RELATIONSHIPS_FILE, relationships)

    # Also log the interaction
    log = _load_json(INTERACTION_LOG_FILE, [])
    log.append({
        "timestamp": datetime.now().isoformat(),
        "platform": platform,
        "username": username,
        "type": interaction_type,
        "content_preview": content[:200] if content else "",
    })
    _save_json(INTERACTION_LOG_FILE, log[-1000:])


# ═══════════════════════════════════════════════════════════════
# TREND SURFER
# ═══════════════════════════════════════════════════════════════

def log_trend(platform: str, trend_topic: str, relevance: str,
              action_taken: str = ""):
    """Log a detected trend and any action taken.

    Args:
        platform: Where the trend was detected.
        trend_topic: The trending topic or hashtag.
        relevance: How relevant it is to CFW (high/medium/low).
        action_taken: What the agent did (e.g., "generated video", "posted comment").
    """
    trends = _load_json(TREND_LOG_FILE, [])
    trends.append({
        "timestamp": datetime.now().isoformat(),
        "platform": platform,
        "topic": trend_topic,
        "relevance": relevance,
        "action": action_taken,
    })
    _save_json(TREND_LOG_FILE, trends[-500:])


def get_trend_keywords() -> list:
    """Get a list of keywords to monitor for trends relevant to CFW."""
    return [
        # Direct business keywords
        "vehicle wrap", "car wrap", "vinyl wrap", "fleet wrap",
        "color change wrap", "ppf", "paint protection",
        # Chicago-specific
        "Chicago cars", "Chicago auto", "Chicago custom",
        "Chicago fleet", "Chicago truck",
        # Industry trends
        "matte wrap", "chrome delete", "wrap fail", "wrap reveal",
        "before after car", "car transformation",
        # Broader automotive
        "new car", "truck build", "car mod", "car customization",
        "fleet branding", "mobile billboard",
    ]


# ═══════════════════════════════════════════════════════════════
# COMMUNITY RESPONDER
# ═══════════════════════════════════════════════════════════════

def should_respond(comment_text: str) -> dict:
    """Determine if and how to respond to a comment.

    Returns a dict with response guidance.
    """
    text_lower = comment_text.lower()

    # Always respond to questions
    if "?" in comment_text:
        return {
            "should_respond": True,
            "priority": "high",
            "type": "answer_question",
            "guidance": "Answer their question directly and helpfully.",
        }

    # Always respond to compliments
    positive_signals = [
        "love", "amazing", "awesome", "great", "beautiful",
        "sick", "fire", "clean", "dope", "nice",
    ]
    if any(word in text_lower for word in positive_signals):
        return {
            "should_respond": True,
            "priority": "medium",
            "type": "thank_compliment",
            "guidance": "Be gracious. Thank them genuinely. Maybe share a detail about the work.",
        }

    # Always respond to criticism (professionally)
    negative_signals = [
        "ugly", "bad", "terrible", "waste", "expensive",
        "rip off", "overpriced", "cheap",
    ]
    if any(word in text_lower for word in negative_signals):
        return {
            "should_respond": True,
            "priority": "high",
            "type": "address_criticism",
            "guidance": "Be professional and real. Don't be defensive. Address the concern honestly.",
        }

    # Respond to wrap-related comments
    wrap_signals = [
        "wrap", "vinyl", "color", "matte", "gloss",
        "how much", "price", "cost", "quote",
    ]
    if any(word in text_lower for word in wrap_signals):
        return {
            "should_respond": True,
            "priority": "high",
            "type": "business_inquiry",
            "guidance": "Be helpful and informative. Invite them to reach out for details.",
        }

    # For other comments, respond with moderate priority
    if len(comment_text.strip()) > 10:
        return {
            "should_respond": True,
            "priority": "low",
            "type": "general_engagement",
            "guidance": "Keep it brief and genuine. A simple acknowledgment is fine.",
        }

    return {
        "should_respond": False,
        "priority": "none",
        "type": "skip",
        "guidance": "Too short or generic to warrant a response.",
    }


# ═══════════════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════════════

def get_engagement_dashboard() -> dict:
    """Get proactive engagement data for the unified dashboard."""
    relationships = _load_json(RELATIONSHIPS_FILE, [])
    interactions = _load_json(INTERACTION_LOG_FILE, [])
    trends = _load_json(TREND_LOG_FILE, [])

    by_status = {}
    for r in relationships:
        s = r.get("status", "unknown")
        by_status[s] = by_status.get(s, 0) + 1

    by_platform = {}
    for r in relationships:
        p = r.get("platform", "unknown")
        by_platform[p] = by_platform.get(p, 0) + 1

    return {
        "total_relationships": len(relationships),
        "by_status": by_status,
        "by_platform": by_platform,
        "total_interactions": len(interactions),
        "recent_interactions": interactions[-10:],
        "total_trends_logged": len(trends),
        "recent_trends": trends[-5:],
    }


if __name__ == "__main__":
    import sys

    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd == "status":
        dashboard = get_engagement_dashboard()
        print(json.dumps(dashboard, indent=2))
    elif cmd == "targets":
        platform = sys.argv[2] if len(sys.argv) > 2 else "instagram"
        targets = get_engagement_targets(platform)
        for t in targets:
            print(f"  {t['username']} ({t['status']}, rapport: {t['rapport_score']})")
    elif cmd == "keywords":
        for kw in get_trend_keywords():
            print(f"  - {kw}")
    else:
        print("Usage: python proactive_engagement.py [status|targets <platform>|keywords]")
