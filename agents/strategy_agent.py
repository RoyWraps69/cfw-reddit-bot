"""
Chicago Fleet Wraps — STRATEGY AGENT (The CMO)
================================================
Decides WHAT to post, WHERE to post it, and WHEN.

Responsibilities:
  - Analyze trends across all platforms
  - Consult the optimization engine for winning content components
  - Issue CONTENT_REQUEST messages to the Creative Agent
  - Receive PERFORMANCE_REPORT and LEARNING_UPDATE from Monitor Agent
  - Adjust strategy based on feedback
  - Manage the posting schedule (FB 4x/day, IG 12x/day, TikTok hourly)
  - Decide when to ride a trend vs stick to the plan

This agent NEVER creates content itself. It only decides and delegates.
"""

import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base import BaseAgent, MessageType
from config import DATA_DIR, BUSINESS_CONTEXT


class StrategyAgent(BaseAgent):
    NAME = "strategy"
    ROLE = "Chief Marketing Officer"

    STRATEGY_FILE = os.path.join(DATA_DIR, "agent_strategy", "current_strategy.json")

    def __init__(self):
        super().__init__()
        os.makedirs(os.path.dirname(self.STRATEGY_FILE), exist_ok=True)

    def _system_prompt(self) -> str:
        return f"""You are the Chief Marketing Officer (CMO) for Chicago Fleet Wraps.
You decide the content strategy — what topics to cover, which platforms to prioritize,
and how to allocate the content calendar.

BUSINESS CONTEXT:
{BUSINESS_CONTEXT}

POSTING SCHEDULE:
- Facebook: 4 posts per day (solve pain points for business owners)
- Instagram: 12 posts per 24 hours (build audience, share insider knowledge)
- TikTok: Post hourly (ride trends, high energy, short-form)
- Reddit: 8 comments per day (genuine community engagement)

YOUR RULES:
- Every decision must be data-driven (use engagement data, not gut feeling)
- Prioritize content that has PROVEN to work (from the optimization engine)
- When a trend is hot, act FAST — issue urgent content requests
- Balance between proven winners and experimental content (per the 30-day plan)
- All content must be geo-relevant to Chicago (4711 N. Lamon Ave, Chicago, IL 60630)
- Never repeat the same topic within 24 hours across any platform
- If the Monitor Agent reports a failing pattern, STOP using it immediately

Respond with JSON only."""

    def run(self) -> dict:
        """Execute the strategy cycle."""
        self.heartbeat()
        self.log("=" * 50)
        self.log("STRATEGY AGENT — Running cycle")
        self.log("=" * 50)

        results = {
            "content_requests_sent": 0,
            "trends_detected": 0,
            "strategy_adjustments": 0,
        }

        # 1. Process inbox — learn from Monitor Agent
        self._process_inbox(results)

        # 2. Analyze current trends
        trends = self._analyze_trends()
        results["trends_detected"] = len(trends.get("hot_topics", []))

        # 3. Consult optimization engine for winning components
        winning_components = self._get_winning_components()

        # 4. Check what's already been posted today (avoid repeats)
        recent_topics = self._get_recent_topics()

        # 5. Make content decisions and send requests to Creative Agent
        decisions = self._make_decisions(trends, winning_components, recent_topics)

        for decision in decisions:
            self.send(
                recipient="creative",
                msg_type=MessageType.CONTENT_REQUEST,
                payload=decision,
                priority=decision.get("priority", 5),
            )
            results["content_requests_sent"] += 1
            self.log(f"  → Sent content request: {decision.get('topic', 'unknown')} "
                     f"(priority {decision.get('priority', 5)})")

        # 6. Check for urgent trends that need immediate action
        for topic in trends.get("hot_topics", []):
            if topic.get("score", 0) >= 80 and topic.get("topic") not in recent_topics:
                self.send(
                    recipient="creative",
                    msg_type=MessageType.TREND_ALERT,
                    payload={
                        "trend": topic,
                        "instruction": "Create content for this trend IMMEDIATELY",
                        "platforms": ["tiktok", "instagram"],
                    },
                    priority=1,  # URGENT
                )
                self.log(f"  → TREND ALERT: {topic.get('topic', '')} (score {topic.get('score', 0)})")

        # 7. Save current strategy state
        self._save_strategy(results, decisions)

        self.log(f"Cycle complete: {results['content_requests_sent']} requests sent, "
                 f"{results['trends_detected']} trends detected")
        return results

    def _process_inbox(self, results: dict):
        """Process messages from other agents (mainly Monitor)."""
        messages = self.receive()
        for msg in messages:
            if msg.type == MessageType.PERFORMANCE_REPORT.value or msg.type == MessageType.PERFORMANCE_REPORT:
                self.log(f"  ← Performance report from {msg.sender}")
                self._apply_performance_insights(msg.payload)
                results["strategy_adjustments"] += 1

            elif msg.type == MessageType.LEARNING_UPDATE.value or msg.type == MessageType.LEARNING_UPDATE:
                self.log(f"  ← Learning update from {msg.sender}")
                self._apply_learning(msg.payload)
                results["strategy_adjustments"] += 1

            elif msg.type == MessageType.KILL_SIGNAL.value or msg.type == MessageType.KILL_SIGNAL:
                self.log(f"  ← KILL SIGNAL from {msg.sender}: {msg.payload.get('reason', '')}")
                # Avoid this content type in future
                self._blacklist_content_type(msg.payload)

    def _analyze_trends(self) -> dict:
        """Analyze trends across all platforms."""
        try:
            from trend_analyzer import TrendAnalyzer
            analyzer = TrendAnalyzer()
            return analyzer.analyze_all()
        except Exception as e:
            self.log(f"Trend analysis error: {e}")
            return {"hot_topics": []}

    def _get_winning_components(self) -> dict:
        """Get the current winning content components from the optimization engine."""
        try:
            from optimization_engine import get_top_arms, get_current_phase
            phase = get_current_phase()
            top = get_top_arms(3)
            return {"phase": phase, "top_arms": top}
        except Exception as e:
            self.log(f"Optimization engine error: {e}")
            return {}

    def _get_recent_topics(self) -> list:
        """Get topics posted in the last 24 hours to avoid repeats."""
        try:
            import content_queue
            recent = content_queue.get_recent_posts(hours=24)
            return [p.get("topic", "") for p in recent]
        except Exception:
            return []

    def _make_decisions(self, trends: dict, winning: dict, recent: list) -> list:
        """Use AI to make content decisions based on all available data."""
        phase = winning.get("phase", {})
        top_arms = winning.get("top_arms", {})

        context = f"""Current optimization phase: {phase.get('description', 'Unknown')}
Epsilon (exploration rate): {phase.get('epsilon', 0.5)}

Top performing content components:
{json.dumps(top_arms, indent=2, default=str) if top_arms else 'No data yet'}

Trending topics:
{json.dumps(trends.get('hot_topics', [])[:5], indent=2, default=str)}

Recently posted topics (AVOID REPEATS):
{json.dumps(recent[:10], default=str)}

Based on this data, decide on 1-3 content pieces to create right now.
For each, specify:
- topic: What the content is about
- platforms: Which platforms to post on (list)
- priority: 1 (urgent) to 10 (low)
- visual_style: Preferred visual style
- hook_style: How to open the caption
- tone: Voice/tone to use
- content_type: "image" or "video"
- reasoning: Why this content right now

Return ONLY a JSON array of decision objects."""

        try:
            response = self.think(context)
            # Parse JSON from response
            if "```" in response:
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            decisions = json.loads(response.strip())
            if isinstance(decisions, dict):
                decisions = [decisions]
            return decisions[:3]  # Max 3 decisions per cycle
        except Exception as e:
            self.log(f"Decision-making error: {e}")
            # Fallback: one generic decision
            return [{
                "topic": "vehicle_wrap_showcase",
                "platforms": ["facebook", "instagram"],
                "priority": 5,
                "visual_style": "matte_black",
                "hook_style": "question",
                "tone": "professional",
                "content_type": "image",
                "reasoning": "Fallback — AI decision failed",
            }]

    def _apply_performance_insights(self, payload: dict):
        """Adjust strategy based on performance data from Monitor."""
        self.log(f"  Applying performance insights: "
                 f"avg_score={payload.get('avg_score', 'N/A')}")

    def _apply_learning(self, payload: dict):
        """Apply learning updates from Monitor."""
        self.log(f"  Applying learning: {payload.get('insight', 'N/A')}")

    def _blacklist_content_type(self, payload: dict):
        """Blacklist a content type that got killed."""
        self.log(f"  Blacklisting: {payload.get('topic', 'unknown')}")

    def _save_strategy(self, results: dict, decisions: list):
        """Save the current strategy state to disk."""
        state = {
            "timestamp": datetime.now().isoformat(),
            "cycle_results": results,
            "decisions_made": decisions,
        }
        try:
            with open(self.STRATEGY_FILE, "w") as f:
                json.dump(state, f, indent=2, default=str)
        except Exception as e:
            self.log(f"Save error: {e}")


if __name__ == "__main__":
    agent = StrategyAgent()
    result = agent.run()
    print(json.dumps(result, indent=2, default=str))
