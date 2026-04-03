"""
Chicago Fleet Wraps — MONITOR AGENT (The Analyst)
===================================================
Watches everything. Learns from everything. Feeds it all back.

Responsibilities:
  - Receive CONTENT_APPROVED from Quality Agent → publish it
  - Track engagement metrics in real-time (hourly for first 24h)
  - Run attribution analysis (WHY did this post succeed/fail?)
  - Send PERFORMANCE_REPORT to Strategy Agent
  - Send LEARNING_UPDATE to Strategy Agent with actionable insights
  - Send KILL_SIGNAL when a post is getting destroyed (damage control)
  - Send RESPOND_REQUEST to Community Agent when comments need replies
  - Feed outcomes back into the optimization engine and persona engine
  - Generate the unified dashboard

This agent is the FEEDBACK LOOP. Without it, the system doesn't learn.
"""

import os
import sys
import json
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base import BaseAgent, MessageType
from config import DATA_DIR


class MonitorAgent(BaseAgent):
    NAME = "monitor"
    ROLE = "Performance Analyst"

    MONITOR_LOG = os.path.join(DATA_DIR, "agent_monitor", "monitor_log.json")

    def __init__(self):
        super().__init__()
        os.makedirs(os.path.dirname(self.MONITOR_LOG), exist_ok=True)

    def _system_prompt(self) -> str:
        return """You are the Performance Analyst for Chicago Fleet Wraps.
You monitor ALL social media engagement and extract actionable insights.

YOUR RULES:
- Be data-driven. No opinions, only facts backed by numbers.
- When you see a pattern, quantify it (e.g., "matte black posts get 2.3x more likes")
- When a post is failing, act FAST — issue a kill signal before it damages the brand
- When a post is succeeding, figure out EXACTLY why and tell Strategy
- Track engagement velocity (how fast likes/comments come in), not just totals
- Compare performance across platforms to find cross-platform patterns
- Every insight must be ACTIONABLE (Strategy must be able to use it)

Respond with JSON only."""

    def run(self) -> dict:
        """Execute the monitoring cycle."""
        self.heartbeat()
        self.log("=" * 50)
        self.log("MONITOR AGENT — Running cycle")
        self.log("=" * 50)

        results = {
            "posts_published": 0,
            "engagement_collected": 0,
            "kill_signals_sent": 0,
            "insights_generated": 0,
            "respond_requests_sent": 0,
        }

        # 1. Process inbox — publish approved content
        self._process_approved_content(results)

        # 2. Collect engagement metrics for all active posts
        self._collect_engagement(results)

        # 3. Run damage control — check for posts getting destroyed
        self._run_damage_control(results)

        # 4. Run attribution analysis — WHY are things working/failing
        self._run_attribution(results)

        # 5. Check for comments needing replies → send to Community Agent
        self._check_for_replies(results)

        # 6. Send performance report to Strategy Agent
        self._send_performance_report(results)

        # 7. Generate dashboard
        self._generate_dashboard()

        self.log(f"Cycle complete: {results['posts_published']} published, "
                 f"{results['engagement_collected']} tracked, "
                 f"{results['kill_signals_sent']} killed, "
                 f"{results['insights_generated']} insights")
        return results

    def _process_approved_content(self, results: dict):
        """Publish content that Quality Agent approved."""
        messages = self.receive(MessageType.CONTENT_APPROVED.value)

        for msg in messages:
            draft = msg.payload.get("draft", {})
            quality_score = msg.payload.get("quality_score", 0)
            self.log(f"  Publishing: {draft.get('topic', 'unknown')} "
                     f"(quality: {quality_score}/10)")

            post_ids = self._publish_content(draft)
            if post_ids:
                results["posts_published"] += 1

                # Register for engagement tracking
                try:
                    from engagement_tracker import register_post
                    register_post(
                        post_ids=post_ids,
                        content_package=draft,
                        arm_selection=draft.get("arm_selection", {}),
                    )
                except Exception as e:
                    self.log(f"  Tracker registration error: {e}")

    def _publish_content(self, draft: dict) -> dict:
        """Publish content to all specified platforms."""
        post_ids = {}
        platforms = draft.get("platforms", [])
        media = draft.get("media_paths", {})
        captions = draft.get("captions", {})
        image_path = media.get("image_path", "")
        video_path = media.get("video_path", "")

        for platform in platforms:
            cap_data = captions.get(platform, {})
            caption = cap_data.get("caption", "") if isinstance(cap_data, dict) else str(cap_data)
            hashtags = cap_data.get("hashtags", []) if isinstance(cap_data, dict) else []

            if hashtags:
                caption += "\n\n" + " ".join(f"#{h}" for h in hashtags)

            try:
                if platform == "facebook":
                    import facebook_bot
                    result = facebook_bot.create_post(
                        caption=caption,
                        image_path=image_path,
                    )
                    if result and result.get("success"):
                        post_ids["facebook"] = result.get("post_id", "")
                        self.log(f"    ✓ Facebook posted")

                elif platform == "instagram":
                    import instagram_bot
                    result = instagram_bot.create_post(
                        caption=caption,
                        image_path=image_path,
                    )
                    if result and result.get("success"):
                        post_ids["instagram"] = result.get("post_id", "")
                        self.log(f"    ✓ Instagram posted")

                elif platform == "tiktok":
                    from tiktok_bot import TikTokBot
                    tt = TikTokBot()
                    media_path = video_path if video_path else image_path
                    result = tt.create_post(
                        caption=caption,
                        hashtags=hashtags,
                        media_path=media_path,
                    )
                    if result:
                        post_ids["tiktok"] = str(result)
                        self.log(f"    ✓ TikTok posted")

                time.sleep(3)  # Delay between platforms

            except Exception as e:
                self.log(f"    ✗ {platform} error: {e}")

        return post_ids

    def _collect_engagement(self, results: dict):
        """Collect engagement metrics for all tracked posts."""
        try:
            from engagement_tracker import collect_all_engagement
            eng_result = collect_all_engagement()
            results["engagement_collected"] = eng_result.get("updated", 0)
            self.log(f"  Engagement: {eng_result.get('updated', 0)} updated, "
                     f"{eng_result.get('completed', 0)} completed")
        except Exception as e:
            self.log(f"  Engagement collection error: {e}")

    def _run_damage_control(self, results: dict):
        """Check for posts getting negative reactions."""
        try:
            from damage_control import run_damage_check, get_posts_needing_replacement
            from reddit_session import RedditSession
            from config import REDDIT_USERNAME

            rs = RedditSession(REDDIT_USERNAME)
            reddit_session = rs if rs.login() else None

            damage = run_damage_check(reddit_session=reddit_session)

            if damage.get("deleted", 0) > 0:
                # Send KILL_SIGNAL to Strategy
                self.send(
                    recipient="strategy",
                    msg_type=MessageType.KILL_SIGNAL,
                    payload={
                        "deleted_count": damage["deleted"],
                        "reason": "Posts received excessive negative reactions",
                    },
                    priority=1,  # URGENT
                )
                results["kill_signals_sent"] += damage["deleted"]
                self.log(f"  KILL SIGNAL: {damage['deleted']} posts deleted")

        except Exception as e:
            self.log(f"  Damage control error: {e}")

    def _run_attribution(self, results: dict):
        """Run attribution analysis to understand WHY posts succeed/fail."""
        try:
            from engagement_tracker import run_attribution, get_learning_context

            attribution = run_attribution(min_posts=3)
            if attribution:
                results["insights_generated"] += 1

                # Send learning update to Strategy
                learning_context = get_learning_context()
                if learning_context:
                    self.send(
                        recipient="strategy",
                        msg_type=MessageType.LEARNING_UPDATE,
                        payload={
                            "insight": learning_context,
                            "attribution": attribution,
                            "avg_score": attribution.get("avg_score", 0),
                        },
                        priority=3,
                    )
                    self.log(f"  → Sent learning update to Strategy")

        except Exception as e:
            self.log(f"  Attribution error: {e}")

    def _check_for_replies(self, results: dict):
        """Check for comments that need replies and delegate to Community Agent."""
        try:
            from reddit_session import RedditSession
            from config import REDDIT_USERNAME

            rs = RedditSession(REDDIT_USERNAME)
            if not rs.login():
                return

            comments = rs.get_my_comments(limit=10)
            for comment in comments:
                permalink = comment.get("permalink", "")
                if not permalink:
                    continue

                replies = rs.get_comment_replies(permalink)
                for reply in replies:
                    # Send to Community Agent
                    self.send(
                        recipient="community",
                        msg_type=MessageType.RESPOND_REQUEST,
                        payload={
                            "platform": "reddit",
                            "comment_text": reply.get("body", ""),
                            "author": reply.get("author", ""),
                            "context_permalink": permalink,
                            "parent_comment": comment.get("body", "")[:200],
                        },
                        priority=4,
                    )
                    results["respond_requests_sent"] += 1

        except Exception as e:
            self.log(f"  Reply check error: {e}")

    def _send_performance_report(self, results: dict):
        """Send a performance summary to Strategy Agent."""
        try:
            from engagement_tracker import get_tracker_dashboard
            from optimization_engine import get_optimization_dashboard

            tracker = get_tracker_dashboard()
            optimizer = get_optimization_dashboard()

            self.send(
                recipient="strategy",
                msg_type=MessageType.PERFORMANCE_REPORT,
                payload={
                    "avg_score": tracker.get("avg_engagement_score", 0),
                    "active_monitoring": tracker.get("active_monitoring", 0),
                    "total_completed": tracker.get("total_completed", 0),
                    "optimization_phase": optimizer.get("phase", {}),
                    "success_rate": optimizer.get("success_rate", 0),
                    "cycle_results": results,
                },
                priority=7,  # Low priority, informational
            )
        except Exception as e:
            self.log(f"  Performance report error: {e}")

    def _generate_dashboard(self):
        """Generate the unified dashboard."""
        try:
            from unified_dashboard import generate_unified_dashboard
            path = generate_unified_dashboard()
            self.log(f"  Dashboard: {path}")
        except Exception as e:
            self.log(f"  Dashboard error: {e}")


if __name__ == "__main__":
    agent = MonitorAgent()
    result = agent.run()
    print(json.dumps(result, indent=2, default=str))
