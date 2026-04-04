#!/usr/bin/env python3
"""
Chicago Fleet Wraps — MULTI-AGENT ORCHESTRATOR v2.0
=====================================================
Replaces the monolithic master.py with a multi-agent system.

Five specialized agents collaborate through a shared message bus:

  STRATEGY  (CMO)       → Decides what to post, where, and when
  CREATIVE  (Artist)    → Generates images, videos, captions
  QUALITY   (Editor)    → Reviews everything before publishing
  MONITOR   (Analyst)   → Tracks engagement, feeds learnings back
  COMMUNITY (Networker) → Responds to comments, builds relationships

Communication flow:
  Strategy → Creative → Quality → Monitor (publish) → Strategy (loop)
  Community runs in parallel, handling all inbound engagement.

Usage:
  python orchestrator.py                # Full cycle (all agents)
  python orchestrator.py strategy       # Strategy Agent only
  python orchestrator.py creative       # Creative Agent only
  python orchestrator.py quality        # Quality Agent only
  python orchestrator.py monitor        # Monitor Agent only
  python orchestrator.py community      # Community Agent only
  python orchestrator.py pipeline       # Content pipeline only (S→C→Q→M)
  python orchestrator.py engage         # Community + Monitor only
  python orchestrator.py refill         # Pre-generate content barrel
  python orchestrator.py learn          # Collect engagement + learn
  python orchestrator.py status         # Show all agent statuses
  python orchestrator.py purge          # Clean old messages from bus
"""

import sys
import os
import json
import traceback
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DATA_DIR, LOG_DIR
from agents.base import MessageBus, AgentRegistry

# ─────────────────────────────────────────────────────────────
# Agent imports (lazy — only import what we need per mode)
# ─────────────────────────────────────────────────────────────

def get_strategy():
    from agents.strategy_agent import StrategyAgent
    return StrategyAgent()

def get_creative():
    from agents.creative_agent import CreativeAgent
    return CreativeAgent()

def get_quality():
    from agents.quality_agent import QualityAgent
    return QualityAgent()

def get_monitor():
    from agents.monitor_agent import MonitorAgent
    return MonitorAgent()

def get_community():
    from agents.community_agent import CommunityAgent
    return CommunityAgent()


# ─────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────

ORCHESTRATOR_LOG = os.path.join(LOG_DIR, "orchestrator_log.json")

def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"  [{ts}] [ORCHESTRATOR] {msg}", flush=True)

def log_cycle(cycle_data: dict):
    os.makedirs(LOG_DIR, exist_ok=True)
    history = []
    if os.path.exists(ORCHESTRATOR_LOG):
        try:
            with open(ORCHESTRATOR_LOG, "r") as f:
                history = json.load(f)
        except Exception:
            pass
    cycle_data["timestamp"] = datetime.now().isoformat()
    history.append(cycle_data)
    history = history[-200:]
    with open(ORCHESTRATOR_LOG, "w") as f:
        json.dump(history, f, indent=2, default=str)


# ═══════════════════════════════════════════════════════════════
# FULL CYCLE — All agents, in order
# ═══════════════════════════════════════════════════════════════

def run_full_cycle():
    """Run the complete multi-agent cycle.

    The content pipeline runs sequentially:
      Strategy → Creative → Quality → Monitor (publish)

    Community runs after the pipeline to handle engagement.
    Each agent processes its inbox, does its work, and sends
    messages to the next agent in the chain.
    """
    banner = f"""
{'='*70}
  CHICAGO FLEET WRAPS — MULTI-AGENT ORCHESTRATOR v2.0
  ─────────────────────────────────────────────────────
  Agents: Strategy | Creative | Quality | Monitor | Community
  Bus:    Message-based inter-agent communication
  Learn:  Optimization Engine + Engagement Tracker
  ─────────────────────────────────────────────────────
  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*70}
"""
    print(banner, flush=True)

    cycle_results = {}
    bus = MessageBus()

    # ── Phase 1: Strategy Agent decides what to create ──────
    log("PHASE 1/5: STRATEGY AGENT")
    try:
        strategy = get_strategy()
        cycle_results["strategy"] = strategy.run()
    except Exception as e:
        log(f"Strategy error: {e}")
        traceback.print_exc()
        cycle_results["strategy"] = {"error": str(e)}

    # ── Phase 2: Creative Agent generates content ───────────
    log("PHASE 2/5: CREATIVE AGENT")
    try:
        creative = get_creative()
        cycle_results["creative"] = creative.run()
    except Exception as e:
        log(f"Creative error: {e}")
        traceback.print_exc()
        cycle_results["creative"] = {"error": str(e)}

    # ── Phase 3: Quality Agent reviews drafts ───────────────
    log("PHASE 3/5: QUALITY AGENT")
    try:
        quality = get_quality()
        cycle_results["quality"] = quality.run()
    except Exception as e:
        log(f"Quality error: {e}")
        traceback.print_exc()
        cycle_results["quality"] = {"error": str(e)}

    # ── Phase 4: Monitor Agent publishes + tracks ───────────
    log("PHASE 4/5: MONITOR AGENT")
    try:
        monitor = get_monitor()
        cycle_results["monitor"] = monitor.run()
    except Exception as e:
        log(f"Monitor error: {e}")
        traceback.print_exc()
        cycle_results["monitor"] = {"error": str(e)}

    # ── Phase 5: Community Agent handles engagement ─────────
    log("PHASE 5/5: COMMUNITY AGENT")
    try:
        community = get_community()
        cycle_results["community"] = community.run()
    except Exception as e:
        log(f"Community error: {e}")
        traceback.print_exc()
        cycle_results["community"] = {"error": str(e)}

    # ── Cleanup ─────────────────────────────────────────────
    bus.purge_old(max_age_hours=48)

    # ── Log + Summary ───────────────────────────────────────
    log_cycle(cycle_results)
    _print_summary(cycle_results)

    return cycle_results


# ═══════════════════════════════════════════════════════════════
# PIPELINE MODE — Content creation only (no engagement)
# ═══════════════════════════════════════════════════════════════

def run_pipeline():
    """Run just the content pipeline: Strategy → Creative → Quality → Monitor."""
    log("PIPELINE MODE: Strategy → Creative → Quality → Monitor")

    results = {}
    for name, factory in [("strategy", get_strategy), ("creative", get_creative),
                          ("quality", get_quality), ("monitor", get_monitor)]:
        try:
            log(f"Running {name}...")
            agent = factory()
            results[name] = agent.run()
        except Exception as e:
            log(f"{name} error: {e}")
            results[name] = {"error": str(e)}

    log_cycle({"mode": "pipeline", **results})
    return results


# ═══════════════════════════════════════════════════════════════
# ENGAGE MODE — Community + Monitor only
# ═══════════════════════════════════════════════════════════════

def run_engage():
    """Run engagement: Community Agent + Monitor Agent."""
    log("ENGAGE MODE: Community + Monitor")

    results = {}
    for name, factory in [("community", get_community), ("monitor", get_monitor)]:
        try:
            log(f"Running {name}...")
            agent = factory()
            results[name] = agent.run()
        except Exception as e:
            log(f"{name} error: {e}")
            results[name] = {"error": str(e)}

    log_cycle({"mode": "engage", **results})
    return results


# ═══════════════════════════════════════════════════════════════
# LEARN MODE — Collect engagement data and update models
# ═══════════════════════════════════════════════════════════════

def run_learn():
    """Collect engagement metrics and run the learning loop."""
    log("LEARN MODE: Collecting engagement + updating models")

    results = {}

    # Collect engagement
    try:
        from engagement_tracker import collect_all_engagement, run_attribution
        eng = collect_all_engagement()
        results["engagement"] = eng
        log(f"Engagement: {eng.get('updated', 0)} posts updated")

        attr = run_attribution()
        results["attribution"] = attr
    except Exception as e:
        log(f"Engagement error: {e}")
        results["engagement"] = {"error": str(e)}

    # Update optimization engine
    try:
        from optimization_engine import update_from_engagement
        opt = update_from_engagement()
        results["optimization"] = opt
        log(f"Optimization engine updated")
    except Exception as e:
        log(f"Optimization error: {e}")

    # Update persona engine
    try:
        from persona_engine import update_personas
        pers = update_personas()
        results["persona"] = pers
        log(f"Persona engine updated")
    except Exception as e:
        log(f"Persona error: {e}")

    # Content queue learning
    try:
        import content_queue
        content_queue.collect_engagement()
        content_queue.analyze_and_learn()
        log("Content queue learning complete")
    except Exception as e:
        log(f"Content queue error: {e}")

    log_cycle({"mode": "learn", **results})
    return results


# ═══════════════════════════════════════════════════════════════
# REFILL MODE — Pre-generate content barrel
# ═══════════════════════════════════════════════════════════════

def run_refill():
    """Pre-generate content into the barrel."""
    log("REFILL MODE: Pre-generating content barrel")

    try:
        import content_queue
        before = content_queue.queue_size()
        content_queue.refill_queue()
        after = content_queue.queue_size()
        log(f"Barrel: {before} → {after} posts")
        return {"before": before, "after": after}
    except Exception as e:
        log(f"Refill error: {e}")
        return {"error": str(e)}


# ═══════════════════════════════════════════════════════════════
# STATUS MODE — Show all agent statuses
# ═══════════════════════════════════════════════════════════════

def run_status():
    """Show the status of all agents and the message bus."""
    registry = AgentRegistry()
    bus = MessageBus()

    print(f"\n{'='*60}", flush=True)
    print(f"  AGENT STATUS REPORT — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print(f"{'='*60}", flush=True)

    agents = registry.get_all()
    if not agents:
        print("  No agents registered yet. Run a full cycle first.", flush=True)
        return

    for name, info in agents.items():
        pending = bus.peek(name)
        last_hb = info.get("last_heartbeat", "never")
        status = info.get("status", "unknown")
        role = info.get("role", "unknown")

        print(f"\n  {name.upper()} ({role})", flush=True)
        print(f"    Status:    {status}", flush=True)
        print(f"    Heartbeat: {last_hb}", flush=True)
        print(f"    Inbox:     {pending} pending messages", flush=True)

    print(f"\n{'='*60}\n", flush=True)


# ═══════════════════════════════════════════════════════════════
# PURGE MODE — Clean old messages
# ═══════════════════════════════════════════════════════════════

def run_purge():
    """Purge old delivered messages from the bus."""
    bus = MessageBus()
    bus.purge_old(max_age_hours=24)
    log("Purged messages older than 24 hours")


# ═══════════════════════════════════════════════════════════════
# SINGLE AGENT MODE — Run one agent
# ═══════════════════════════════════════════════════════════════

def run_single_agent(name: str):
    """Run a single agent by name."""
    factories = {
        "strategy": get_strategy,
        "creative": get_creative,
        "quality": get_quality,
        "monitor": get_monitor,
        "community": get_community,
    }

    if name not in factories:
        print(f"Unknown agent: {name}. Available: {', '.join(factories.keys())}")
        sys.exit(1)

    log(f"SINGLE AGENT MODE: {name.upper()}")
    agent = factories[name]()
    result = agent.run()
    print(json.dumps(result, indent=2, default=str))
    return result


# ═══════════════════════════════════════════════════════════════
# SUMMARY PRINTER
# ═══════════════════════════════════════════════════════════════

def _print_summary(results: dict):
    """Print a human-readable summary of the cycle."""
    s = results.get("strategy", {})
    c = results.get("creative", {})
    q = results.get("quality", {})
    m = results.get("monitor", {})
    cm = results.get("community", {})

    print(f"""
{'='*70}
  CYCLE COMPLETE — {datetime.now().strftime('%H:%M:%S')}
  ─────────────────────────────────────────────────────
  Strategy:  {s.get('content_requests_sent', 0)} requests, {s.get('trends_detected', 0)} trends
  Creative:  {c.get('drafts_created', 0)} drafts, {c.get('revisions_handled', 0)} revisions
  Quality:   {q.get('reviewed', 0)} reviewed, {q.get('approved', 0)} approved, {q.get('rejected', 0)} rejected (avg: {q.get('avg_score', 0)}/10)
  Monitor:   {m.get('posts_published', 0)} published, {m.get('kill_signals_sent', 0)} killed, {m.get('insights_generated', 0)} insights
  Community: {cm.get('replies_sent', 0)} replies, {cm.get('proactive_engagements', 0)} proactive
{'='*70}
""", flush=True)


# ═══════════════════════════════════════════════════════════════
# MAIN — Entry point
# ═══════════════════════════════════════════════════════════════

def main():
    from config import POSTING_ENABLED
    if not POSTING_ENABLED:
        print("\n" + "=" * 60, flush=True)
        print("  POSTING_ENABLED = False in config.py", flush=True)
        print("  ALL posting is DISABLED. No actions will be taken.", flush=True)
        print("  Set POSTING_ENABLED = True to resume.", flush=True)
        print("=" * 60 + "\n", flush=True)
        return

    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)

    mode = sys.argv[1] if len(sys.argv) > 1 else "full"

    mode_map = {
        "full": run_full_cycle,
        "pipeline": run_pipeline,
        "engage": run_engage,
        "learn": run_learn,
        "refill": run_refill,
        "status": run_status,
        "purge": run_purge,
    }

    # Check if it's a known mode
    if mode in mode_map:
        mode_map[mode]()
    # Check if it's a single agent name
    elif mode in ("strategy", "creative", "quality", "monitor", "community"):
        run_single_agent(mode)
    # Backward compatibility with old master.py modes
    elif mode == "reddit":
        run_single_agent("community")
    elif mode == "social":
        run_pipeline()
    elif mode == "content":
        run_pipeline()
    elif mode == "analyze":
        run_single_agent("strategy")
    elif mode == "damage":
        run_single_agent("monitor")
    elif mode == "dashboard":
        run_single_agent("monitor")
    elif mode == "post":
        try:
            import content_queue
            content_queue.post_from_queue()
        except Exception as e:
            log(f"Post error: {e}")
    else:
        print(f"Unknown mode: {mode}")
        print("Available: full, pipeline, engage, learn, refill, status, purge")
        print("Agents:    strategy, creative, quality, monitor, community")
        sys.exit(1)


if __name__ == "__main__":
    main()
