#!/usr/bin/env python3
"""
Chicago Fleet Wraps Reddit Bot — Scheduler
Runs the bot on a configurable interval. Designed for Railway/server deployment.
"""
import os
import sys
import time
import signal
import traceback
from datetime import datetime

# Add project dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Interval in seconds (default: 2 hours)
RUN_INTERVAL = int(os.environ.get("BOT_INTERVAL_SECONDS", 7200))

# Track if we should keep running
running = True


def handle_signal(signum, frame):
    global running
    print(f"\n  [SCHEDULER] Received signal {signum}. Shutting down gracefully...")
    running = False


signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)


def run_bot():
    """Execute one bot cycle."""
    from bot import main as bot_main
    try:
        # Override sys.argv to run in auto mode
        sys.argv = [sys.argv[0], "auto"]
        bot_main()
    except Exception as e:
        print(f"\n  [SCHEDULER] Bot cycle error: {e}")
        traceback.print_exc()


def main():
    print(f"\n{'#'*60}")
    print(f"  CFW REDDIT BOT — SCHEDULER")
    print(f"  Interval: {RUN_INTERVAL} seconds ({RUN_INTERVAL/3600:.1f} hours)")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*60}\n")

    cycle = 0
    while running:
        cycle += 1
        print(f"\n{'='*60}")
        print(f"  CYCLE #{cycle} — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")

        run_bot()

        if running:
            next_run = datetime.fromtimestamp(time.time() + RUN_INTERVAL)
            print(f"\n  [SCHEDULER] Next run at: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  [SCHEDULER] Sleeping for {RUN_INTERVAL} seconds...")

            # Sleep in small increments so we can respond to signals
            sleep_end = time.time() + RUN_INTERVAL
            while running and time.time() < sleep_end:
                time.sleep(min(30, sleep_end - time.time()))

    print("\n  [SCHEDULER] Shutdown complete.")


if __name__ == "__main__":
    main()
