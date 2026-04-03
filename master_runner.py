"""
Chicago Fleet Wraps — MASTER UNIFIED RUNNER v1.0

The single process that runs the entire operation.
All systems, fully integrated, continuously running.

Every cycle (45-90 min during business hours):
  Phase 1: Intelligence sync (bridge + optimizer)
  Phase 2: Reddit bot (scan → comment → reply → DM)
  Phase 3: Orchestrator (Strategy → Creative → Quality → Monitor → Community)
  Phase 4: Lead processing (CRM follow-ups + email nurture)
  Phase 5: GBP management (reviews + posts)
  Phase 6: SEO content (weekly blog posts)
  Phase 7: Review requests (post-job customer follow-up)
  Phase 8: Alerts (morning brief to Roy)

Daily (6 AM):
  Self-optimizer runs → questions → answers → strategy update

Weekly (Friday):
  Full performance report → CRM summary → SEO report → persona report

Usage:
  python master_runner.py          # Full 24/7 autonomous operation
  python master_runner.py once     # Run one cycle and exit
  python master_runner.py status   # Print system status
  python master_runner.py leads    # Show CRM lead report
  python master_runner.py brief    # Send morning brief to Roy
  python master_runner.py health   # Health check all systems
"""

import os
import sys
import time
import json
import logging
import subprocess
import random
from datetime import datetime, date, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
LOG_DIR = os.path.join(BASE_DIR, "logs")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "master_runner.log")),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("CFW_MASTER")

# ─────────────────────────────────────────────────────────────────────
# SCHEDULE
# ─────────────────────────────────────────────────────────────────────

SCHEDULE = {
    # hour: (tasks, min_sleep_min, max_sleep_min)
    "dead":    (["maintenance", "upvote_check", "damage_check"], 60, 90),
    "morning": (["reddit", "orchestrator", "leads", "gbp_reviews"], 45, 75),
    "peak":    (["reddit", "orchestrator", "leads", "email_nurture"], 45, 60),
    "evening": (["reddit", "reply_check", "leads", "email_nurture"], 45, 75),
    "wind":    (["reply_check", "dm_check", "maintenance"], 60, 90),
}

def get_time_block(hour: int) -> str:
    if 0 <= hour < 6:
        return "dead"
    elif 6 <= hour < 11:
        return "morning"
    elif 11 <= hour < 19:
        return "peak"
    elif 19 <= hour < 22:
        return "evening"
    else:
        return "wind"


# ─────────────────────────────────────────────────────────────────────
# TASK RUNNERS
# ─────────────────────────────────────────────────────────────────────

def run_reddit(mode: str = "auto") -> dict:
    """Run the Reddit bot."""
    try:
        result = subprocess.run(
            [sys.executable, os.path.join(BASE_DIR, "bot.py"), mode],
            capture_output=True, text=True, timeout=300,
        )
        return {"success": result.returncode == 0, "mode": mode, "output": result.stdout[-1000:]}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def run_orchestrator(mode: str = "full") -> dict:
    """Run the multi-agent orchestrator."""
    try:
        result = subprocess.run(
            [sys.executable, os.path.join(BASE_DIR, "orchestrator.py"), mode],
            capture_output=True, text=True, timeout=600,
        )
        return {"success": result.returncode == 0, "mode": mode}
    except Exception as e:
        return {"success": False, "error": str(e)}


def run_optimizer() -> dict:
    try:
        from self_optimizer import run_daily_optimization
        result = run_daily_optimization()
        return {"success": True, "days_active": result.get("days_active")}
    except Exception as e:
        return {"success": False, "error": str(e)}


def run_gbp_weekly_post() -> dict:
    try:
        from google_business_profile import run_weekly_gbp_post
        return run_weekly_gbp_post()
    except Exception as e:
        return {"success": False, "error": str(e)}


def run_gbp_reviews() -> dict:
    try:
        from google_business_profile import run_review_response_cycle
        return run_review_response_cycle()
    except Exception as e:
        return {"success": False, "error": str(e)}


def run_review_requests() -> dict:
    try:
        from review_generator import run_review_request_cycle
        return run_review_request_cycle()
    except Exception as e:
        return {"success": False, "error": str(e)}


def run_email_nurture() -> dict:
    try:
        from email_nurture import run_email_send_cycle
        return run_email_send_cycle()
    except Exception as e:
        return {"success": False, "error": str(e)}


def run_crm_followups() -> dict:
    try:
        from lead_crm import get_leads_needing_followup, complete_followup
        from lead_alert import send_hot_lead_alert

        leads = get_leads_needing_followup()
        results = {"followed_up": 0, "hot_alerts_sent": 0}

        for lead in leads[:5]:  # Max 5 follow-ups per cycle
            log.info(f"Follow-up needed: #{lead['lead_id']} — {lead.get('username')} — {lead.get('intent_level')}")

            if lead.get("intent_level") == "hot":
                send_hot_lead_alert(
                    platform=lead.get("platform", "unknown"),
                    username=lead.get("username", "unknown"),
                    message_text=f"Follow-up needed: {lead.get('notes', '')}",
                    vehicle_type=lead.get("vehicle_type", ""),
                    intent_level="hot",
                    lead_score=lead.get("lead_score", 8),
                )
                results["hot_alerts_sent"] += 1

            complete_followup(lead["lead_id"])
            results["followed_up"] += 1

        return results
    except Exception as e:
        return {"success": False, "error": str(e)}


def run_intelligence_sync() -> dict:
    try:
        from intelligence_bridge import run_daily_sync
        return run_daily_sync()
    except Exception as e:
        return {"success": False, "error": str(e)}


def run_seo_content() -> dict:
    try:
        from seo_content_engine import run_seo_content_cycle
        return {"result": run_seo_content_cycle(posts_to_generate=1)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def run_morning_brief() -> dict:
    try:
        from lead_alert import send_morning_brief
        return send_morning_brief()
    except Exception as e:
        return {"success": False, "error": str(e)}


def run_maintenance() -> dict:
    results = {}
    results["upvote_check"] = run_reddit("upvote-check")
    results["damage_check"] = run_reddit("damage-check")
    results["bridge_sync"] = run_intelligence_sync()
    return results


# ─────────────────────────────────────────────────────────────────────
# DAILY TASKS (run once per day)
# ─────────────────────────────────────────────────────────────────────

def should_run_once_today(task_name: str) -> bool:
    flag_file = os.path.join(DATA_DIR, f"daily_flag_{task_name}_{date.today()}.flag")
    return not os.path.exists(flag_file)


def mark_done_today(task_name: str):
    flag_file = os.path.join(DATA_DIR, f"daily_flag_{task_name}_{date.today()}.flag")
    with open(flag_file, "w") as f:
        f.write(str(datetime.now()))


# ─────────────────────────────────────────────────────────────────────
# WEEKLY TASKS
# ─────────────────────────────────────────────────────────────────────

def should_run_once_this_week(task_name: str) -> bool:
    week = date.today().isocalendar()[1]
    flag_file = os.path.join(DATA_DIR, f"weekly_flag_{task_name}_{date.today().year}_{week}.flag")
    return not os.path.exists(flag_file)


def mark_done_this_week(task_name: str):
    week = date.today().isocalendar()[1]
    flag_file = os.path.join(DATA_DIR, f"weekly_flag_{task_name}_{date.today().year}_{week}.flag")
    with open(flag_file, "w") as f:
        f.write(str(datetime.now()))


# ─────────────────────────────────────────────────────────────────────
# MAIN CYCLE
# ─────────────────────────────────────────────────────────────────────

def run_cycle() -> dict:
    """Run one complete cycle of all systems."""
    hour = datetime.now().hour
    time_block = get_time_block(hour)
    tasks, min_sleep, max_sleep = SCHEDULE[time_block]
    results = {"time_block": time_block, "hour": hour, "tasks_run": {}}

    log.info(f"=== MASTER CYCLE | {datetime.now().strftime('%H:%M')} | {time_block.upper()} ===")

    # ── DAILY TASKS ────────────────────────────────────────────────

    # 6 AM: Self-optimizer
    if hour == 6 and should_run_once_today("optimizer"):
        log.info("Running daily self-optimizer...")
        results["tasks_run"]["optimizer"] = run_optimizer()
        mark_done_today("optimizer")

    # 6:30 AM: Morning brief to Roy
    if hour == 6 and should_run_once_today("morning_brief"):
        log.info("Sending morning brief...")
        results["tasks_run"]["morning_brief"] = run_morning_brief()
        mark_done_today("morning_brief")

    # 7 AM: Intelligence bridge sync
    if hour == 7 and should_run_once_today("bridge_sync"):
        log.info("Syncing intelligence bridge...")
        results["tasks_run"]["bridge_sync"] = run_intelligence_sync()
        mark_done_today("bridge_sync")

    # ── WEEKLY TASKS ───────────────────────────────────────────────

    # Monday: GBP weekly post
    if datetime.now().strftime("%A") == "Monday" and should_run_once_this_week("gbp_post"):
        log.info("Publishing weekly GBP post...")
        results["tasks_run"]["gbp_post"] = run_gbp_weekly_post()
        mark_done_this_week("gbp_post")

    # Wednesday: SEO blog post
    if datetime.now().strftime("%A") == "Wednesday" and should_run_once_this_week("seo_post"):
        log.info("Generating SEO blog post...")
        results["tasks_run"]["seo_post"] = run_seo_content()
        mark_done_this_week("seo_post")

    # Friday: Weekly CRM + persona report
    if datetime.now().strftime("%A") == "Friday" and should_run_once_this_week("weekly_report"):
        from lead_crm import get_crm_report
        from persona_engine_v2 import get_persona_report
        report = f"{get_crm_report()}\n\n{get_persona_report()}"
        report_path = os.path.join(LOG_DIR, f"weekly_report_{date.today()}.txt")
        with open(report_path, "w") as f:
            f.write(report)
        log.info(f"Weekly report saved: {report_path}")
        mark_done_this_week("weekly_report")

    # ── REGULAR CYCLE TASKS ────────────────────────────────────────

    for task in tasks:
        log.info(f"Running task: {task}")
        try:
            if task == "reddit":
                results["tasks_run"]["reddit"] = run_reddit("auto")
            elif task == "reply_check":
                results["tasks_run"]["reply_check"] = run_reddit("reply-check")
            elif task == "dm_check":
                results["tasks_run"]["dm_check"] = run_reddit("dm-check")
            elif task == "upvote_check":
                results["tasks_run"]["upvote_check"] = run_reddit("upvote-check")
            elif task == "damage_check":
                results["tasks_run"]["damage_check"] = run_reddit("damage-check")
            elif task == "orchestrator":
                results["tasks_run"]["orchestrator"] = run_orchestrator("full")
            elif task == "leads":
                results["tasks_run"]["crm_followups"] = run_crm_followups()
            elif task == "gbp_reviews":
                results["tasks_run"]["gbp_reviews"] = run_gbp_reviews()
            elif task == "review_requests":
                results["tasks_run"]["review_requests"] = run_review_requests()
            elif task == "email_nurture":
                results["tasks_run"]["email_nurture"] = run_email_nurture()
            elif task == "maintenance":
                results["tasks_run"]["maintenance"] = run_maintenance()
        except Exception as e:
            log.error(f"Task {task} failed: {e}")
            results["tasks_run"][task] = {"error": str(e)}

    results["sleep_min"] = random.randint(min_sleep, max_sleep)
    results["next_cycle"] = str(datetime.now() + timedelta(minutes=results["sleep_min"]))

    log.info(f"Cycle complete. Sleeping {results['sleep_min']} min. Next: {results['next_cycle']}")
    return results


# ─────────────────────────────────────────────────────────────────────
# STATUS + HEALTH
# ─────────────────────────────────────────────────────────────────────

def get_system_status() -> str:
    lines = [
        "=" * 60,
        "CHICAGO FLEET WRAPS — SYSTEM STATUS",
        f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * 60,
        "",
    ]

    # CRM
    try:
        from lead_crm import get_pipeline_summary
        s = get_pipeline_summary()
        lines += [
            "LEAD PIPELINE:",
            f"  Total: {s['total_leads']} | This week: {s['this_week']} | Close rate: {s['close_rate_pct']}%",
            f"  Hot leads needing attention: {s['hot_leads_needing_attention']}",
            f"  Follow-ups due today: {s['needs_followup_today']}",
            "",
        ]
    except Exception as e:
        lines.append(f"CRM: error — {e}")

    # Review stats
    try:
        from review_generator import get_review_stats
        rs = get_review_stats()
        lines += [
            "REVIEWS:",
            f"  Requested: {rs['total_requested']} | Received: {rs['reviews_received']} | Rate: {rs['conversion_rate_pct']}%",
            "",
        ]
    except Exception as e:
        lines.append(f"Reviews: error — {e}")

    # SEO
    try:
        from seo_content_engine import _load_seo_log
        seo_log = _load_seo_log()
        lines += [
            "SEO CONTENT:",
            f"  Blog posts published: {len(seo_log)}",
            f"  Latest: {seo_log[-1]['keyword'] if seo_log else 'none'}",
            "",
        ]
    except Exception:
        pass

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────

def main():
    print(f"""
{'='*70}
  CHICAGO FLEET WRAPS — MASTER UNIFIED RUNNER v1.0
  ALL SYSTEMS INTEGRATED
  Reddit | Orchestrator | CRM | GBP | Reviews | SEO | Email | Alerts
  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*70}
""", flush=True)

    mode = sys.argv[1] if len(sys.argv) > 1 else "run"

    if mode == "status":
        print(get_system_status())

    elif mode == "leads":
        from lead_crm import get_crm_report
        print(get_crm_report())

    elif mode == "brief":
        run_morning_brief()

    elif mode == "health":
        print(get_system_status())

    elif mode == "once":
        run_cycle()

    elif mode == "run":
        # 24/7 continuous operation
        error_streak = 0
        while True:
            try:
                results = run_cycle()
                sleep_min = results.get("sleep_min", 60)
                error_streak = 0
                time.sleep(sleep_min * 60)

            except KeyboardInterrupt:
                log.info("Shutting down.")
                break
            except Exception as e:
                error_streak += 1
                log.error(f"Cycle error: {e} (streak: {error_streak})")
                if error_streak >= 5:
                    log.error("5 consecutive errors. Sleeping 30 min.")
                    time.sleep(30 * 60)
                    error_streak = 0
                else:
                    time.sleep(5 * 60)
    else:
        print(f"Unknown mode: {mode}")
        print("Available: run, once, status, leads, brief, health")


if __name__ == "__main__":
    main()
