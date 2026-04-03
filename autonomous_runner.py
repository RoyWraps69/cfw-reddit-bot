"""
Chicago Fleet Wraps — Autonomous Runner v1.0

24/7 continuous operation with intelligent scheduling.

The runner knows:
- When to be aggressive (9 AM-8 PM weekdays)
- When to do maintenance (late night/early morning)
- When to create content (Tuesday-Thursday, high engagement days)
- When to run the optimizer (6 AM daily)
- How to recover from errors without dying

Operation Phases (daily):
  6:00 AM  → Daily optimization cycle (self-optimizer.py)
  6:30 AM  → Content creation for the day (content_creator.py)
  7:00 AM  → Reddit warming/normal cycle begins
  7:00 AM - 11:00 PM → Active posting cycle every 45-90 min
  11:00 PM → Wind down (reply checks, DM follow-ups only)
  12:00 AM - 5:59 AM → Maintenance mode (upvote tracking, damage control)

Content creation schedule:
  Tuesday, Thursday, Saturday → Generate this week's TikTok/Reels/Shorts content
  Monday, Wednesday → Queue review and scheduling
  Friday → Weekly performance report
"""

import os
import sys
import time
import json
import random
import subprocess
import logging
from datetime import datetime, date, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
LOG_DIR = os.path.join(BASE_DIR, "logs")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "autonomous_runner.log")),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("CFW_Runner")


# ─────────────────────────────────────────────────────────────────────
# SCHEDULE DEFINITION
# ─────────────────────────────────────────────────────────────────────

DAILY_SCHEDULE = [
    # (hour_start, hour_end, tasks, sleep_between_min, sleep_between_max)
    (0, 5, ["maintenance"], 60, 120),        # 12 AM-6 AM: Maintenance only
    (6, 6, ["optimize", "content_create"], 5, 10),  # 6 AM: Daily brain warm-up
    (7, 10, ["reddit_post", "reply_check"], 30, 60),  # 7-10 AM: Morning active
    (10, 13, ["reddit_post", "dm_check"], 45, 90),   # 10 AM-1 PM: Mid-morning
    (13, 17, ["reddit_post", "reply_check", "content_create"], 45, 90),  # 1-5 PM: Peak
    (17, 20, ["reddit_post", "dm_check"], 30, 60),   # 5-8 PM: Evening rush
    (20, 22, ["reply_check", "upvote_check", "dm_check"], 45, 90),  # 8-10 PM: Wind down
    (22, 24, ["maintenance", "report"], 60, 120),    # 10 PM-12 AM: Night maintenance
]

CONTENT_CREATION_DAYS = {
    "Tuesday": ["tiktok", "instagram_reels"],
    "Thursday": ["youtube_shorts", "facebook"],
    "Saturday": ["tiktok", "instagram_reels", "facebook"],  # Saturday batch
}

WEEKLY_REPORT_DAY = "Friday"


# ─────────────────────────────────────────────────────────────────────
# TASK EXECUTORS
# ─────────────────────────────────────────────────────────────────────

def run_task(task: str) -> dict:
    """Execute a task and return result."""
    log.info(f"Starting task: {task}")
    start = time.time()

    try:
        if task == "reddit_post":
            return _run_reddit_bot("auto")

        elif task == "reply_check":
            return _run_reddit_bot("reply-check")

        elif task == "dm_check":
            return _run_reddit_bot("dm-check")

        elif task == "upvote_check":
            return _run_reddit_bot("upvote-check")

        elif task == "maintenance":
            results = {}
            results["damage_check"] = _run_reddit_bot("damage-check")
            results["upvote_check"] = _run_reddit_bot("upvote-check")
            return results

        elif task == "optimize":
            return _run_optimizer()

        elif task == "content_create":
            day_name = datetime.now().strftime("%A")
            if day_name in CONTENT_CREATION_DAYS:
                platforms = CONTENT_CREATION_DAYS[day_name]
                return _run_content_creator(platforms)
            else:
                return {"skipped": f"Not a content creation day ({day_name})"}

        elif task == "report":
            return _generate_daily_report()

        else:
            return {"error": f"Unknown task: {task}"}

    except Exception as e:
        log.error(f"Task {task} failed: {e}")
        return {"error": str(e), "task": task}
    finally:
        elapsed = round(time.time() - start, 1)
        log.info(f"Task {task} completed in {elapsed}s")


def _run_reddit_bot(mode: str) -> dict:
    """Run the main bot.py with the given mode."""
    try:
        bot_path = os.path.join(BASE_DIR, "bot.py")
        result = subprocess.run(
            [sys.executable, bot_path, mode],
            capture_output=True, text=True,
            timeout=300,  # 5 minute timeout
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout[-2000:] if result.stdout else "",
            "stderr": result.stderr[-500:] if result.stderr else "",
            "mode": mode,
        }
    except subprocess.TimeoutExpired:
        return {"error": "timeout", "mode": mode}
    except Exception as e:
        return {"error": str(e), "mode": mode}


def _run_optimizer() -> dict:
    """Run the daily self-optimization cycle."""
    try:
        from self_optimizer import run_daily_optimization
        result = run_daily_optimization()
        return {"success": True, "days_active": result.get("days_active")}
    except Exception as e:
        log.error(f"Optimizer error: {e}")
        return {"error": str(e)}


def _run_content_creator(platforms: list) -> dict:
    """Generate content for specified platforms."""
    try:
        from content_creator import generate_video_script, save_content_to_queue, CONTENT_ARCHETYPES
        results = []

        # Pick 2 archetypes per run
        archetypes = random.sample(list(CONTENT_ARCHETYPES.keys()), min(2, len(CONTENT_ARCHETYPES)))

        for platform in platforms:
            for archetype in archetypes:
                log.info(f"Generating {archetype} content for {platform}...")
                script = generate_video_script(archetype=archetype, platform=platform)
                filepath = save_content_to_queue(script, platform, archetype)
                results.append({"platform": platform, "archetype": archetype, "file": filepath})
                time.sleep(2)  # Rate limit

        return {"content_generated": len(results), "items": results}
    except Exception as e:
        log.error(f"Content creator error: {e}")
        return {"error": str(e)}


def _generate_daily_report() -> dict:
    """Generate and log the daily activity report."""
    try:
        from tracker import get_daily_summary
        from persona_engine_v2 import get_persona_report

        report = [
            "=" * 60,
            f"CFW BOT DAILY REPORT — {date.today()}",
            "=" * 60,
            get_daily_summary(),
            "",
            get_persona_report(),
        ]

        report_text = "\n".join(report)
        report_path = os.path.join(LOG_DIR, f"daily_report_{date.today()}.txt")
        with open(report_path, "w") as f:
            f.write(report_text)

        print(report_text, flush=True)
        return {"success": True, "report_path": report_path}
    except Exception as e:
        return {"error": str(e)}


# ─────────────────────────────────────────────────────────────────────
# SCHEDULING LOGIC
# ─────────────────────────────────────────────────────────────────────

def get_current_tasks() -> tuple:
    """Return (tasks, min_sleep, max_sleep) for the current hour."""
    current_hour = datetime.now().hour

    for (start, end, tasks, min_s, max_s) in DAILY_SCHEDULE:
        if start <= current_hour < end:
            return tasks, min_s, max_s

    return ["maintenance"], 60, 120


def get_sleep_duration(min_s: int, max_s: int) -> int:
    """Calculate sleep duration in seconds with some randomness."""
    base = random.randint(min_s, max_s)
    # Add ±20% jitter to avoid predictable patterns
    jitter = int(base * 0.2)
    return base * 60 + random.randint(-jitter * 60, jitter * 60)


def should_run_optimizer_today() -> bool:
    """Check if optimizer has already run today."""
    check_file = os.path.join(DATA_DIR, f"optimizer_ran_{date.today()}.flag")
    return not os.path.exists(check_file)


def mark_optimizer_ran():
    """Mark optimizer as having run today."""
    check_file = os.path.join(DATA_DIR, f"optimizer_ran_{date.today()}.flag")
    with open(check_file, "w") as f:
        f.write(str(datetime.now()))


# ─────────────────────────────────────────────────────────────────────
# HEALTH MONITORING
# ─────────────────────────────────────────────────────────────────────

HEALTH_LOG_FILE = os.path.join(DATA_DIR, "health_log.json")


def log_health(task: str, result: dict):
    """Log task health for monitoring."""
    health = []
    if os.path.exists(HEALTH_LOG_FILE):
        try:
            with open(HEALTH_LOG_FILE) as f:
                health = json.load(f)
        except Exception:
            pass

    health.append({
        "timestamp": str(datetime.now()),
        "task": task,
        "success": "error" not in result,
        "error": result.get("error", None),
    })

    # Keep last 200 entries
    health = health[-200:]
    with open(HEALTH_LOG_FILE, "w") as f:
        json.dump(health, f, indent=2)


def get_health_status() -> dict:
    """Get a quick health check of recent operations."""
    if not os.path.exists(HEALTH_LOG_FILE):
        return {"status": "no_data", "recent_errors": 0}

    try:
        with open(HEALTH_LOG_FILE) as f:
            health = json.load(f)
    except Exception:
        return {"status": "read_error"}

    recent = health[-20:]
    errors = [h for h in recent if not h.get("success")]

    return {
        "status": "healthy" if len(errors) < 3 else "degraded",
        "recent_operations": len(recent),
        "recent_errors": len(errors),
        "last_task": health[-1].get("task") if health else "none",
        "last_success": next((h["timestamp"] for h in reversed(health) if h.get("success")), "unknown"),
    }


# ─────────────────────────────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────────────────────────────

def run_forever():
    """The main 24/7 loop. This is what runs on the server."""
    log.info("=" * 60)
    log.info("CHICAGO FLEET WRAPS — AUTONOMOUS RUNNER v1.0")
    log.info("Starting continuous operation...")
    log.info("=" * 60)

    error_streak = 0
    MAX_ERROR_STREAK = 5

    while True:
        try:
            current_hour = datetime.now().hour
            tasks, min_sleep, max_sleep = get_current_tasks()
            day_name = datetime.now().strftime("%A")

            log.info(f"Hour: {current_hour} | Day: {day_name} | Tasks: {tasks}")

            # Run optimizer at 6 AM if not done yet
            if current_hour == 6 and should_run_optimizer_today():
                log.info("Running daily optimizer...")
                result = run_task("optimize")
                log_health("optimize", result)
                mark_optimizer_ran()

            # Run weekly report on Friday evenings
            if day_name == WEEKLY_REPORT_DAY and current_hour == 22:
                weekly_report_flag = os.path.join(DATA_DIR, f"weekly_report_{date.today()}.flag")
                if not os.path.exists(weekly_report_flag):
                    log.info("Generating weekly report...")
                    run_task("report")
                    with open(weekly_report_flag, "w") as f:
                        f.write(str(datetime.now()))

            # Execute current tasks
            for task in tasks:
                result = run_task(task)
                log_health(task, result)

                if "error" in result:
                    error_streak += 1
                    log.warning(f"Task {task} had error: {result['error']} (streak: {error_streak})")
                else:
                    error_streak = 0

            # Check health
            health = get_health_status()
            if health["status"] == "degraded":
                log.warning(f"Health degraded: {health['recent_errors']}/20 recent ops failed")

            # Emergency brake if too many errors
            if error_streak >= MAX_ERROR_STREAK:
                log.error(f"Error streak of {error_streak} detected. Sleeping 30 min before retry.")
                time.sleep(30 * 60)
                error_streak = 0
                continue

            # Sleep until next cycle
            sleep_s = get_sleep_duration(min_sleep, max_sleep)
            next_run = datetime.now() + timedelta(seconds=sleep_s)
            log.info(f"Sleeping {sleep_s // 60} min. Next run: {next_run.strftime('%H:%M')}")
            time.sleep(sleep_s)

        except KeyboardInterrupt:
            log.info("Interrupted by user. Shutting down.")
            break
        except Exception as e:
            log.error(f"Runner error: {e}")
            error_streak += 1
            time.sleep(300)  # 5 min cooldown on unexpected errors


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "health":
        status = get_health_status()
        print(json.dumps(status, indent=2))
    else:
        run_forever()
