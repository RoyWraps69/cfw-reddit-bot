"""
Chicago Fleet Wraps — Community Agent v2.0

Handles all engagement: comment replies, hot lead detection, lead alerts,
relationship building, and trend surfing across all platforms.
"""

import os
import sys
from datetime import datetime

from openai import OpenAI

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.base import BaseAgent

client = OpenAI()


class CommunityAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="community",
            role="Community Manager",
            capabilities=["comment_replies", "lead_detection", "relationship_building", "trend_surfing"],
        )

    def run(self) -> dict:
        self.heartbeat(status="running", action="community_cycle")
        self.log("Starting community cycle...")

        results = {
            "replies_sent": 0,
            "proactive_engagements": 0,
            "hot_leads_detected": 0,
            "warm_leads_detected": 0,
        }

        messages = self.get_messages(limit=20)
        respond_reqs = [m for m in messages if m["type"] == "RESPOND_REQUEST"]

        for req in respond_reqs:
            payload = req.get("payload", {})
            reply = self._generate_reply(payload)
            if reply:
                self.log(f"Reply ready for {payload.get('platform', 'unknown')}: {reply[:80]}...")
                results["replies_sent"] += 1

                lead = self._check_lead_intent(
                    payload.get("comment_text", ""),
                    payload.get("username", ""),
                    payload.get("platform", ""),
                )
                if lead.get("level") == "hot":
                    results["hot_leads_detected"] += 1
                elif lead.get("level") == "warm":
                    results["warm_leads_detected"] += 1

        self.heartbeat(status="idle", action=f"handled {results['replies_sent']} engagements")
        self.log(f"Community cycle: {results}")
        return results

    def _generate_reply(self, request: dict) -> str:
        comment = request.get("comment_text", "")
        platform = request.get("platform", "instagram")
        context = request.get("post_context", "vehicle wrap content")

        prompt = f"""Write a reply to this {platform} comment for Chicago Fleet Wraps (owner: Roy).

POST CONTEXT: {context}
COMMENT: {comment}

Rules:
- 1-2 sentences, sounds like Roy — real, direct, not corporate
- Price/availability questions → "DM us or check the link in bio for instant pricing"
- Compliments → thank them with a specific detail
- Negative → address it, offer Roy's direct line (312) 597-1286
- No exclamation marks unless they used them
- Never "Great question!"

Reply text only."""

        try:
            r = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                max_tokens=100,
            )
            return r.choices[0].message.content.strip()
        except Exception:
            return "Thanks for reaching out — DM us for pricing and availability."

    def _check_lead_intent(self, comment_text: str, username: str, platform: str) -> dict:
        try:
            from lead_alert import score_lead, send_hot_lead_alert
            from lead_crm import add_lead, LeadSource

            scored = score_lead(comment_text, source=platform)
            level = scored.get("level", "cold")

            if level in ("hot", "warm"):
                source_map = {
                    "instagram": LeadSource.INSTAGRAM,
                    "facebook": LeadSource.FACEBOOK,
                    "tiktok": LeadSource.TIKTOK,
                    "reddit": LeadSource.REDDIT,
                }
                add_lead(
                    source=source_map.get(platform, LeadSource.INSTAGRAM),
                    platform=platform,
                    username=username,
                    notes=comment_text[:300],
                    intent_level=level,
                    lead_score=scored.get("score", 5),
                )
                if level == "hot":
                    send_hot_lead_alert(
                        platform=platform,
                        username=username,
                        message_text=comment_text,
                        intent_level="hot",
                        lead_score=scored.get("score", 8),
                    )
            return scored
        except Exception:
            return {"level": "cold", "score": 0}
