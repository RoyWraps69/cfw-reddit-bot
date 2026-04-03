"""
Chicago Fleet Wraps — Quality Agent v2.0

Reviews all content drafts before publishing.
Scores each piece against 8 criteria.
Approves high-scoring content → Monitor.
Rejects low-scoring → Creative with specific feedback.
"""

import os
import json
import sys
from openai import OpenAI

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.base import BaseAgent

client = OpenAI()

QUALITY_THRESHOLD = 7.0  # Out of 10 — content below this gets revised

BRAND_STANDARDS = """
Chicago Fleet Wraps Brand Standards:
1. Voice: Direct, honest, knowledgeable, Chicago-authentic. Never corporate.
2. Claims: Only factual claims. No "best in Chicago" without proof.
3. Tone: Blue-collar expertise meets professional quality. Not salesy.
4. Hook: Must stop the scroll in 3 seconds. Must create a specific emotion.
5. CTA: One clear action per piece. No multiple CTAs.
6. Accuracy: All prices, timelines, material names must be correct.
7. Differentiation: Must say something a competitor couldn't say (specific numbers, Roy's story, 600 Rivians, etc.)
8. Platform fit: Must feel native to the platform, not repurposed from another.
"""


class QualityAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="quality",
            role="Quality Editor",
            capabilities=["brand_review", "accuracy_check", "engagement_prediction", "revision_feedback"],
        )

    def run(self) -> dict:
        self.heartbeat(status="running", action="quality_review")
        self.log("Starting quality review cycle...")

        results = {"reviewed": 0, "approved": 0, "rejected": 0, "avg_score": 0, "scores": []}
        messages = self.get_messages(limit=20)
        drafts = [m for m in messages if m["type"] == "CONTENT_DRAFT"]

        self.log(f"Reviewing {len(drafts)} drafts...")

        for msg in drafts:
            draft = msg.get("payload", {})
            review = self._review_draft(draft)
            score = review.get("score", 0)
            results["reviewed"] += 1
            results["scores"].append(score)

            if score >= QUALITY_THRESHOLD:
                # Approved — send to Monitor for publishing
                draft["quality_review"] = review
                self.send(to="monitor", message_type="CONTENT_APPROVED", payload=draft, priority=7)
                self.log(f"APPROVED ({score}/10): {draft.get('platform')} | {draft.get('archetype')}")
                results["approved"] += 1
            else:
                # Rejected — send back to Creative with feedback
                self.send(
                    to="creative",
                    message_type="REVISION_REQUEST",
                    payload={"original_draft": draft, "feedback": review.get("feedback", ""), "score": score},
                    priority=8,
                )
                self.log(f"REJECTED ({score}/10): {review.get('primary_issue', 'quality')} — {draft.get('platform')}")
                results["rejected"] += 1

        if results["scores"]:
            results["avg_score"] = round(sum(results["scores"]) / len(results["scores"]), 1)

        self.heartbeat(status="idle", action=f"approved {results['approved']}/{results['reviewed']}")
        self.log(f"Quality cycle: {results['approved']} approved, {results['rejected']} rejected, avg {results['avg_score']}/10")
        return results

    def _review_draft(self, draft: dict) -> dict:
        hook = draft.get("hook", "")
        script = draft.get("script", "")
        caption = draft.get("caption", "")
        platform = draft.get("platform", "tiktok")
        archetype = draft.get("archetype", "")

        prompt = f"""Review this content draft for Chicago Fleet Wraps. Score it 0-10.

PLATFORM: {platform}
ARCHETYPE: {archetype}
HOOK: {hook}
SCRIPT: {script[:500]}
CAPTION: {caption[:300]}

BRAND STANDARDS:
{BRAND_STANDARDS}

Score on these 8 criteria (each 0-10, then average):
1. Hook strength — does it stop the scroll in 3 seconds?
2. Brand voice — sounds like Roy, not a marketing bot?
3. Factual accuracy — are all claims verifiable and correct?
4. Platform fit — feels native to {platform}?
5. Engagement prediction — will it get comments/shares?
6. Differentiation — says something competitors can't?
7. CTA clarity — one clear action?
8. Chicago authenticity — local context present?

Return ONLY valid JSON:
{{
    "score": 7.5,
    "scores_breakdown": {{"hook": 8, "brand_voice": 7, "accuracy": 9, "platform_fit": 7, "engagement": 7, "differentiation": 7, "cta": 8, "chicago": 7}},
    "approved": true,
    "primary_issue": "hook could be stronger",
    "feedback": "Specific actionable feedback for revision if rejected",
    "strengths": ["what works well"],
    "reviewer_note": "one sentence summary"
}}"""

        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500,
                response_format={"type": "json_object"},
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            self.log(f"Review error: {e}")
            return {"score": 6.0, "approved": False,
                    "feedback": "Review failed — default reject", "primary_issue": "review_error"}
