"""
Chicago Fleet Wraps — Strategy Agent (CMO) v2.0

The Strategy Agent is the brain of the system.
It analyzes what's working, reads market signals, and decides
what content to create, for which platform, on which day.

Every cycle it:
1. Reads performance reports from the Monitor Agent
2. Checks the Intelligence Bridge for winning topics
3. Consults the optimization engine (multi-armed bandit)
4. Reads seasonal context and competitor signals
5. Issues specific CONTENT_REQUEST messages to the Creative Agent
"""

import os
import json
import random
from datetime import datetime, date

from openai import OpenAI

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base import BaseAgent
from intelligence_bridge import get_cross_platform_content_brief, get_winning_topics

client = OpenAI()

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

CONTENT_ARCHETYPES = [
    "before_after", "day_in_shop", "education",
    "client_story", "competitor_comparison", "rivian_special", "price_transparency"
]

PLATFORMS = ["tiktok", "instagram_reels", "youtube_shorts", "facebook"]

SEASONAL_FOCUS = {
    3: {"theme": "spring_surge", "note": "Color change season + spring booking surge"},
    4: {"theme": "spring_surge", "note": "Peak spring — full booking mode"},
    5: {"theme": "spring_surge", "note": "Late spring — push fleet season"},
    10: {"theme": "q4_tax", "note": "Q4 — fleet + tax deduction angle"},
    11: {"theme": "q4_tax", "note": "Nov — Section 179 deadline push"},
    12: {"theme": "q4_tax", "note": "Dec — December 31 deadline urgency"},
    1: {"theme": "slow_season", "note": "Winter — faster availability + indoor showcase"},
    2: {"theme": "slow_season", "note": "Late winter — pre-spring prep content"},
}


class StrategyAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="strategy",
            role="Chief Marketing Officer",
            capabilities=["trend_analysis", "content_planning", "competitive_intel", "seasonal_strategy"],
        )

    def run(self) -> dict:
        self.heartbeat(status="running", action="strategy_cycle")
        self.log("Starting strategy cycle...")

        results = {
            "content_requests_sent": 0,
            "trends_detected": 0,
            "performance_reports_processed": 0,
            "date": str(date.today()),
        }

        # 1. Process performance reports from Monitor
        messages = self.get_messages(limit=20)
        perf_reports = [m for m in messages if m["type"] in ("PERFORMANCE_REPORT", "LEARNING_UPDATE")]
        self.log(f"Processing {len(perf_reports)} performance reports...")

        learnings = []
        for report in perf_reports:
            payload = report.get("payload", {})
            learnings.append(payload)
            results["performance_reports_processed"] += 1

        # 2. Get intelligence brief
        brief = get_cross_platform_content_brief()
        winning_topics = brief.get("amplify_topics", [])
        suppress_topics = [t["topic"] for t in brief.get("suppress_topics", [])]

        self.log(f"Amplify topics: {len(winning_topics)} | Suppress: {len(suppress_topics)}")
        results["trends_detected"] = len(winning_topics)

        # 3. Determine today's content strategy
        strategy = self._build_content_strategy(winning_topics, suppress_topics, learnings)

        # 4. Issue content requests to Creative Agent
        requests_to_send = strategy.get("content_requests", [])
        for req in requests_to_send[:4]:  # Max 4 content pieces per cycle
            msg_id = self.send(
                to="creative",
                message_type="CONTENT_REQUEST",
                payload=req,
                priority=req.get("priority", 5),
            )
            self.log(f"Sent CONTENT_REQUEST to creative: {req['platform']} | {req['archetype']} [ID: {msg_id}]")
            results["content_requests_sent"] += 1

        # 5. Save current strategy
        self._save_state(strategy)

        self.heartbeat(status="idle", action=f"sent {results['content_requests_sent']} requests")
        self.log(f"Strategy cycle complete: {results}")
        return results

    def _build_content_strategy(self, winning_topics: list, suppress_topics: list, learnings: list) -> dict:
        """Use AI to determine the best content strategy for today."""
        month = date.today().month
        seasonal = SEASONAL_FOCUS.get(month, {"theme": "standard", "note": "Regular operations"})
        day_name = datetime.now().strftime("%A")

        # Platform priorities by day
        day_platform_map = {
            "Monday": ["instagram_reels", "tiktok"],
            "Tuesday": ["tiktok", "youtube_shorts"],
            "Wednesday": ["tiktok", "instagram_reels"],
            "Thursday": ["facebook", "youtube_shorts"],
            "Friday": ["instagram_reels", "tiktok"],
            "Saturday": ["tiktok", "instagram_reels", "facebook"],
            "Sunday": ["facebook"],
        }
        today_platforms = day_platform_map.get(day_name, ["tiktok", "instagram_reels"])

        prompt = f"""You are the Chief Marketing Officer for Chicago Fleet Wraps.
Build today's content strategy.

TODAY: {date.today()} ({day_name})
SEASON: {seasonal['theme']} — {seasonal['note']}
PLATFORMS TO FOCUS ON TODAY: {', '.join(today_platforms)}

WINNING TOPICS (amplify these):
{json.dumps(winning_topics[:5], indent=2)}

TOPICS TO SUPPRESS (avoid these):
{suppress_topics[:5]}

RECENT LEARNINGS:
{json.dumps(learnings[-3:], indent=2) if learnings else 'None yet — early days'}

Generate 2-4 content requests for today. For each:
- Pick the best archetype for today's platform
- Consider what topics are winning vs what to avoid
- Think about the buyer funnel (awareness vs decision)

Available archetypes: {', '.join(CONTENT_ARCHETYPES)}
Available platforms: {', '.join(PLATFORMS)}

Return ONLY valid JSON:
{{
    "daily_focus": "One sentence describing today's strategic focus",
    "seasonal_angle": "{seasonal['note']}",
    "content_requests": [
        {{
            "platform": "tiktok",
            "archetype": "before_after",
            "topic_focus": "cargo van wrap for HVAC company",
            "vehicle_type": "cargo van",
            "hook_direction": "Start with the business owner pain — invisible company",
            "cta": "link_in_bio",
            "priority": 8,
            "reason": "why this content right now"
        }}
    ]
}}"""

        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=1200,
                response_format={"type": "json_object"},
            )
            strategy = json.loads(response.choices[0].message.content)
            strategy["generated_at"] = str(datetime.now())
            return strategy
        except Exception as e:
            self.log(f"Strategy AI error: {e} — using default")
            return {
                "daily_focus": "Before/after content + fleet education",
                "content_requests": [
                    {
                        "platform": today_platforms[0],
                        "archetype": "before_after",
                        "topic_focus": "cargo van transformation",
                        "vehicle_type": "cargo van",
                        "hook_direction": "visual transformation focus",
                        "priority": 7,
                    },
                    {
                        "platform": today_platforms[1] if len(today_platforms) > 1 else "facebook",
                        "archetype": "education",
                        "topic_focus": "how to spot quality wrap install",
                        "vehicle_type": "",
                        "hook_direction": "things most shops won't tell you",
                        "priority": 6,
                    },
                ],
            }
