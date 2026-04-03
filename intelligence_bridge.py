"""
Chicago Fleet Wraps — Intelligence Bridge v1.0

The Reddit bot (bot.py) and the multi-platform orchestrator (orchestrator.py)
are currently two isolated systems. This bridge creates a shared intelligence layer.

Data flows:
  Reddit comments → shared_learnings → Strategy Agent (what topics resonate)
  TikTok/IG engagement → shared_learnings → Reddit bot (what content to reference)
  Competitor mentions → shared_alert_bus → All agents simultaneously
  Hot leads → CRM + Lead Alert simultaneously
  Persona performance → shared → all AI response generators

The bridge also normalizes data formats across the two systems so they
can actually learn from each other.
"""

import os
import json
from datetime import datetime, date, timedelta
from typing import Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

BRIDGE_FILE = os.path.join(DATA_DIR, "intelligence_bridge.json")
SHARED_TOPICS_FILE = os.path.join(DATA_DIR, "shared_winning_topics.json")
SHARED_SIGNALS_FILE = os.path.join(DATA_DIR, "shared_signals.json")


# ─────────────────────────────────────────────────────────────────────
# TOPIC INTELLIGENCE — What's resonating, shared across all systems
# ─────────────────────────────────────────────────────────────────────

def record_topic_performance(
    topic: str,
    platform: str,
    content_type: str,
    engagement_score: float,
    converted_to_lead: bool = False,
    vehicle_type: str = "",
    subreddit: str = "",
):
    """Record that a topic performed well (or poorly) on a given platform.

    Called by:
    - Reddit bot: when a comment gets upvotes
    - Orchestrator monitor agent: when content gets engagement
    - Calculator webhook: when a lead comes in for a specific vehicle type
    """
    topics = _load_topics()

    key = f"{topic.lower()[:50]}_{platform}"
    if key not in topics:
        topics[key] = {
            "topic": topic,
            "platform": platform,
            "content_type": content_type,
            "vehicle_type": vehicle_type,
            "subreddit": subreddit,
            "occurrences": 0,
            "total_engagement": 0,
            "lead_conversions": 0,
            "avg_engagement": 0,
            "first_seen": str(date.today()),
            "last_seen": str(date.today()),
        }

    t = topics[key]
    t["occurrences"] += 1
    t["total_engagement"] += engagement_score
    t["avg_engagement"] = round(t["total_engagement"] / t["occurrences"], 2)
    t["last_seen"] = str(date.today())
    if converted_to_lead:
        t["lead_conversions"] += 1

    _save_topics(topics)


def get_winning_topics(platform: str = None, min_occurrences: int = 2, limit: int = 10) -> list:
    """Get the top-performing topics to prioritize in content creation."""
    topics = _load_topics()

    entries = list(topics.values())
    if platform:
        entries = [t for t in entries if t["platform"] == platform]

    entries = [t for t in entries if t["occurrences"] >= min_occurrences]
    entries.sort(key=lambda x: (x.get("lead_conversions", 0) * 3 + x.get("avg_engagement", 0)), reverse=True)

    return entries[:limit]


def get_suppress_topics(platform: str = None, max_avg_engagement: float = 1.0) -> list:
    """Get topics that consistently underperform — suppress these."""
    topics = _load_topics()
    entries = list(topics.values())
    if platform:
        entries = [t for t in entries if t["platform"] == platform]

    entries = [t for t in entries
               if t["occurrences"] >= 3 and t.get("avg_engagement", 0) <= max_avg_engagement]
    return entries


def get_cross_platform_content_brief() -> dict:
    """
    Build a content brief that the Strategy Agent can use.
    Includes winning topics from all platforms + suppressed topics.
    """
    winners = get_winning_topics(limit=5)
    suppressions = get_suppress_topics()

    # Vehicle types that converted to leads
    all_topics = list(_load_topics().values())
    converting_vehicles = {}
    for t in all_topics:
        vt = t.get("vehicle_type", "")
        if vt and t.get("lead_conversions", 0) > 0:
            converting_vehicles[vt] = converting_vehicles.get(vt, 0) + t["lead_conversions"]

    top_vehicles = sorted(converting_vehicles.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "amplify_topics": [{"topic": t["topic"], "platform": t["platform"],
                            "score": t["avg_engagement"]} for t in winners],
        "suppress_topics": [{"topic": t["topic"], "platform": t["platform"],
                             "reason": f"avg engagement {t['avg_engagement']}"} for t in suppressions],
        "top_converting_vehicles": [{"vehicle": v, "conversions": c} for v, c in top_vehicles],
        "generated_at": str(datetime.now()),
    }


# ─────────────────────────────────────────────────────────────────────
# SIGNAL BUS — Real-time signals all agents can read
# ─────────────────────────────────────────────────────────────────────

class SignalType:
    HOT_LEAD = "hot_lead"
    COMPETITOR_SURGE = "competitor_surge"  # Competitor being mentioned heavily
    TREND_SPIKE = "trend_spike"            # Topic trending on a platform
    NEGATIVE_REVIEW = "negative_review"   # Bad review posted
    VIRAL_CONTENT = "viral_content"       # Our content going viral
    LOW_ENGAGEMENT = "low_engagement"     # Performance dip


def emit_signal(signal_type: str, data: dict, urgency: str = "normal"):
    """Emit a signal to the shared bus. All agents check this."""
    signals = _load_signals()

    signal = {
        "id": f"{signal_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "type": signal_type,
        "urgency": urgency,
        "data": data,
        "emitted_at": str(datetime.now()),
        "processed_by": [],
    }

    signals.append(signal)
    signals = signals[-200:]  # Keep last 200 signals
    _save_signals(signals)

    print(f"[BRIDGE] Signal emitted: {signal_type} ({urgency})", flush=True)
    return signal["id"]


def get_pending_signals(agent_name: str, signal_types: list = None) -> list:
    """Get signals that haven't been processed by this agent yet."""
    signals = _load_signals()
    pending = []

    for signal in signals:
        if agent_name not in signal.get("processed_by", []):
            if not signal_types or signal["type"] in signal_types:
                pending.append(signal)

    return pending


def mark_signal_processed(signal_id: str, agent_name: str):
    """Mark a signal as processed by an agent."""
    signals = _load_signals()
    for signal in signals:
        if signal["id"] == signal_id:
            signal.setdefault("processed_by", []).append(agent_name)
            break
    _save_signals(signals)


# ─────────────────────────────────────────────────────────────────────
# PERSONA BRIDGE — Sync persona performance across both systems
# ─────────────────────────────────────────────────────────────────────

def sync_persona_performance():
    """Sync persona performance data from persona_engine_v2 into the bridge."""
    persona_stats_file = os.path.join(DATA_DIR, "persona_stats.json")
    if not os.path.exists(persona_stats_file):
        return

    with open(persona_stats_file) as f:
        persona_stats = json.load(f)

    # Find the top performer
    if not persona_stats:
        return

    top_persona = max(persona_stats.items(),
                      key=lambda x: x[1].get("avg_upvotes", 0), default=("none", {}))

    bridge = _load_bridge()
    bridge["top_persona"] = top_persona[0]
    bridge["top_persona_avg_upvotes"] = top_persona[1].get("avg_upvotes", 0)
    bridge["persona_stats_synced_at"] = str(datetime.now())
    _save_bridge(bridge)


def get_recommended_persona(subreddit: str = None, platform: str = "reddit") -> str:
    """Get the currently best-performing persona for a given context."""
    bridge = _load_bridge()
    return bridge.get("top_persona", "roy_craftsman")


# ─────────────────────────────────────────────────────────────────────
# DAILY BRIDGE SYNC — Called by autonomous_runner.py
# ─────────────────────────────────────────────────────────────────────

def run_daily_sync() -> dict:
    """Full daily sync of all intelligence across both systems."""
    results = {}

    # 1. Sync persona performance
    try:
        sync_persona_performance()
        results["persona_sync"] = "done"
    except Exception as e:
        results["persona_sync"] = f"error: {e}"

    # 2. Build content brief for tomorrow
    try:
        brief = get_cross_platform_content_brief()
        brief_file = os.path.join(DATA_DIR, "todays_content_brief.json")
        with open(brief_file, "w") as f:
            json.dump(brief, f, indent=2)
        results["content_brief"] = f"{len(brief['amplify_topics'])} amplify, {len(brief['suppress_topics'])} suppress"
    except Exception as e:
        results["content_brief"] = f"error: {e}"

    # 3. Clear stale signals (older than 48 hours)
    try:
        signals = _load_signals()
        cutoff = (datetime.now() - timedelta(hours=48)).isoformat()
        signals = [s for s in signals if s.get("emitted_at", "") > cutoff]
        _save_signals(signals)
        results["signal_cleanup"] = "done"
    except Exception as e:
        results["signal_cleanup"] = f"error: {e}"

    print(f"[BRIDGE] Daily sync complete: {results}", flush=True)
    return results


# ─────────────────────────────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────────────────────────────

def _load_bridge() -> dict:
    if os.path.exists(BRIDGE_FILE):
        try:
            with open(BRIDGE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_bridge(data: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(BRIDGE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _load_topics() -> dict:
    if os.path.exists(SHARED_TOPICS_FILE):
        try:
            with open(SHARED_TOPICS_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_topics(topics: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(SHARED_TOPICS_FILE, "w") as f:
        json.dump(topics, f, indent=2)


def _load_signals() -> list:
    if os.path.exists(SHARED_SIGNALS_FILE):
        try:
            with open(SHARED_SIGNALS_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_signals(signals: list):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(SHARED_SIGNALS_FILE, "w") as f:
        json.dump(signals, f, indent=2)
