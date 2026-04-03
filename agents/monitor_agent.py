"""
Chicago Fleet Wraps — Monitor Agent v2.0

Publishes approved content, tracks performance, runs attribution,
issues kill signals for failing posts, feeds learnings back to Strategy.
"""

import os
import json
import sys
from datetime import datetime, date

from openai import OpenAI

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.base import BaseAgent
from intelligence_bridge import record_topic_performance, emit_signal, SignalType
from content_creator import log_content_performance

client = OpenAI()
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
PUBLISHED_CONTENT_FILE = os.path.join(DATA_DIR, "published_content.json")


class MonitorAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="monitor",
            role="Performance Analyst",
            capabilities=["publishing", "engagement_tracking", "attribution", "kill_signals"],
        )

    def run(self) -> dict:
        self.heartbeat(status="running", action="monitor_cycle")
        self.log("Starting monitor cycle...")

        results = {"posts_published": 0, "kill_signals_sent": 0,
                   "insights_generated": 0, "performance_checked": 0}

        messages = self.get_messages(limit=20)

        # Publish approved content
        approved = [m for m in messages if m["type"] == "CONTENT_APPROVED"]
        self.log(f"Publishing {len(approved)} approved pieces...")

        for msg in approved:
            content = msg.get("payload", {})
            publish_result = self._publish_content(content)
            if publish_result.get("status") in ("published", "queued"):
                results["posts_published"] += 1
                self._track_published(content, publish_result)

        # Check performance of existing posts
        published = self._load_published()
        recent = [p for p in published[-20:] if not p.get("performance_checked")]

        for post in recent:
            perf = self._check_post_performance(post)
            results["performance_checked"] += 1

            log_content_performance(
                platform=post.get("platform", "unknown"),
                archetype=post.get("archetype", "unknown"),
                hook=post.get("hook", "")[:100],
                views=perf.get("views", 0),
                likes=perf.get("likes", 0),
                comments=perf.get("comments", 0),
                shares=perf.get("shares", 0),
            )

            record_topic_performance(
                topic=post.get("archetype", ""),
                platform=post.get("platform", ""),
                content_type="video",
                engagement_score=perf.get("engagement_score", 0),
            )

            if perf.get("engagement_score", 0) < 1.0 and perf.get("hours_live", 0) > 4:
                emit_signal(SignalType.LOW_ENGAGEMENT, {
                    "post_id": post.get("post_id"),
                    "platform": post.get("platform"),
                }, urgency="normal")
                results["kill_signals_sent"] += 1

            post["performance_checked"] = True
            post["last_performance"] = perf

        self._save_published(published)

        if results["performance_checked"] > 0:
            insights = self._generate_insights(recent)
            self.send(
                to="strategy",
                message_type="PERFORMANCE_REPORT",
                payload={"insights": insights, "date": str(date.today()),
                         "posts_checked": results["performance_checked"]},
                priority=6,
            )
            results["insights_generated"] = len(insights)

        self.heartbeat(status="idle", action=f"published {results['posts_published']}")
        self.log(f"Monitor cycle: {results}")
        return results

    def _publish_content(self, content: dict) -> dict:
        platform = content.get("platform", "tiktok")
        self.log(f"Publishing to {platform}...")

        if platform == "facebook":
            return self._publish_facebook(content)
        return {"status": "queued",
                "reason": f"{platform} — script ready, video file needed for upload"}

    def _publish_facebook(self, content: dict) -> dict:
        page_token = os.environ.get("FACEBOOK_PAGE_TOKEN", "")
        page_id = os.environ.get("FACEBOOK_PAGE_ID", "")
        if not page_token or not page_id:
            return {"status": "queued", "reason": "Facebook credentials not set in .env"}
        try:
            import requests
            caption = content.get("caption", "") + "\n\n" + " ".join(content.get("hashtags", [])[:3])
            r = requests.post(
                f"https://graph.facebook.com/v18.0/{page_id}/feed",
                data={"message": caption[:2000], "access_token": page_token},
                timeout=20,
            )
            if r.status_code == 200:
                return {"status": "published", "post_id": r.json().get("id")}
            return {"status": "error", "code": r.status_code}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _check_post_performance(self, post: dict) -> dict:
        return {"views": 0, "likes": 0, "comments": 0, "shares": 0,
                "engagement_score": 0, "hours_live": 0,
                "note": "Connect platform analytics APIs for live data"}

    def _generate_insights(self, posts: list) -> list:
        if not posts:
            return []
        try:
            perf_data = [{"platform": p.get("platform"), "archetype": p.get("archetype"),
                          "hook": p.get("hook", "")[:80]} for p in posts]
            prompt = f"""Analyze this content data for Chicago Fleet Wraps and give 3 actionable insights.
DATA: {json.dumps(perf_data, indent=2)[:1500]}
Return ONLY valid JSON: {{"insights": [{{"finding": "...", "action": "...", "confidence": "high/medium/low"}}]}}"""
            response = client.chat.completions.create(
                model="gpt-4o", messages=[{"role": "user", "content": prompt}],
                temperature=0.4, max_tokens=400, response_format={"type": "json_object"})
            return json.loads(response.choices[0].message.content).get("insights", [])
        except Exception:
            return [{"finding": "Building data baseline", "action": "Continue posting consistently", "confidence": "low"}]

    def _track_published(self, content: dict, publish_result: dict):
        published = self._load_published()
        published.append({
            "published_at": str(datetime.now()),
            "platform": content.get("platform"),
            "archetype": content.get("archetype"),
            "hook": content.get("hook", "")[:100],
            "caption": content.get("caption", "")[:200],
            "post_id": publish_result.get("post_id"),
            "status": publish_result.get("status"),
            "performance_checked": False,
        })
        self._save_published(published[-500:])

    def _load_published(self) -> list:
        if os.path.exists(PUBLISHED_CONTENT_FILE):
            try:
                with open(PUBLISHED_CONTENT_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save_published(self, published: list):
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(PUBLISHED_CONTENT_FILE, "w") as f:
            json.dump(published, f, indent=2)
