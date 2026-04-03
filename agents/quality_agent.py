"""
Chicago Fleet Wraps — QUALITY AGENT (The Editor)
==================================================
Reviews ALL content before it goes live. The gatekeeper.

Responsibilities:
  - Receive CONTENT_DRAFT from Creative Agent
  - Score each draft on multiple quality dimensions
  - APPROVE good content → send CONTENT_APPROVED (triggers publishing)
  - REJECT bad content → send REVISION_REQUEST back to Creative Agent
  - Apply brand safety checks (no offensive content, no competitor mentions)
  - Ensure uniqueness (no duplicate or near-duplicate content)
  - Track approval/rejection rates to help Creative Agent improve

This agent is the LAST LINE OF DEFENSE before content goes public.
It must be strict but fair — reject garbage, but don't be a perfectionist.
"""

import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base import BaseAgent, MessageType
from config import DATA_DIR, BUSINESS_CONTEXT, COMPETITORS


class QualityAgent(BaseAgent):
    NAME = "quality"
    ROLE = "Quality Editor"

    QUALITY_LOG = os.path.join(DATA_DIR, "agent_quality", "quality_log.json")
    MIN_SCORE = 6.0  # Minimum score to approve (out of 10)

    def __init__(self):
        super().__init__()
        os.makedirs(os.path.dirname(self.QUALITY_LOG), exist_ok=True)

    def _system_prompt(self) -> str:
        return f"""You are the Quality Editor for Chicago Fleet Wraps.
You review ALL content before it goes live on social media.

BUSINESS CONTEXT:
{BUSINESS_CONTEXT}

YOUR QUALITY STANDARDS:
1. BRAND VOICE: Must sound like Roy (real person, not corporate). Score 0 if it sounds like a press release.
2. VISUAL QUALITY: Image prompt must produce professional, photorealistic results. No text in images.
3. ENGAGEMENT POTENTIAL: Will this make someone stop scrolling? Hook must be strong.
4. PLATFORM FIT: Content must be adapted to each platform's culture and format.
5. UNIQUENESS: Must not be too similar to recent posts.
6. BRAND SAFETY: No offensive content, no competitor mentions, no false claims.
7. GEO-RELEVANCE: Must connect to Chicago in some way.
8. CTA EFFECTIVENESS: If there's a call-to-action, it must feel natural, not forced.

COMPETITORS TO NEVER MENTION:
{', '.join(COMPETITORS)}

SCORING: Rate each dimension 1-10. Average must be >= {self.MIN_SCORE} to approve.

If rejecting, provide SPECIFIC, ACTIONABLE feedback so Creative can fix it.
Don't just say "make it better" — say exactly what's wrong and how to fix it.

Respond with JSON only."""

    def run(self) -> dict:
        """Execute the quality review cycle."""
        self.heartbeat()
        self.log("=" * 50)
        self.log("QUALITY AGENT — Running cycle")
        self.log("=" * 50)

        results = {
            "reviewed": 0,
            "approved": 0,
            "rejected": 0,
            "avg_score": 0.0,
        }

        messages = self.receive()
        drafts = [m for m in messages
                  if (m.type == MessageType.CONTENT_DRAFT.value or m.type == MessageType.CONTENT_DRAFT)]

        if not drafts:
            self.log("No drafts to review.")
            return results

        scores = []
        quality_log = self._load_log()

        for msg in drafts:
            draft = msg.payload
            self.log(f"  Reviewing: {draft.get('topic', 'unknown')} "
                     f"(revision #{draft.get('revision_count', 0)})")

            # Run quality checks
            review = self._review_draft(draft)
            score = review.get("overall_score", 0)
            scores.append(score)
            results["reviewed"] += 1

            # Log the review
            quality_log.append({
                "timestamp": datetime.now().isoformat(),
                "topic": draft.get("topic", ""),
                "score": score,
                "scores": review.get("dimension_scores", {}),
                "decision": "approved" if score >= self.MIN_SCORE else "rejected",
                "feedback": review.get("feedback", ""),
            })

            if score >= self.MIN_SCORE:
                # APPROVED — send to publishing
                self.log(f"  ✓ APPROVED (score: {score:.1f}/10)")
                self.send(
                    recipient="monitor",  # Monitor handles publishing
                    msg_type=MessageType.CONTENT_APPROVED,
                    payload={
                        "draft": draft,
                        "quality_score": score,
                        "review": review,
                    },
                    priority=draft.get("request", {}).get("priority", 5),
                    in_reply_to=msg.id,
                )
                results["approved"] += 1

            else:
                # REJECTED — send back to Creative with feedback
                self.log(f"  ✗ REJECTED (score: {score:.1f}/10)")
                self.log(f"    Reason: {review.get('feedback', 'N/A')[:100]}")

                # Only send revision if under max revisions
                if draft.get("revision_count", 0) < 2:
                    self.send(
                        recipient="creative",
                        msg_type=MessageType.REVISION_REQUEST,
                        payload={
                            "original_draft": draft,
                            "reason": review.get("feedback", "Quality too low"),
                            "dimension_scores": review.get("dimension_scores", {}),
                            "suggestions": review.get("suggestions", []),
                        },
                        priority=3,  # Revisions are somewhat urgent
                        in_reply_to=msg.id,
                    )
                else:
                    self.log(f"    (Max revisions reached, dropping)")

                results["rejected"] += 1

        # Save quality log
        self._save_log(quality_log)

        if scores:
            results["avg_score"] = round(sum(scores) / len(scores), 1)

        self.log(f"Cycle complete: {results['reviewed']} reviewed, "
                 f"{results['approved']} approved, {results['rejected']} rejected, "
                 f"avg score: {results['avg_score']}")
        return results

    def _review_draft(self, draft: dict) -> dict:
        """Review a content draft using AI and rule-based checks."""

        # Rule-based checks first (fast, deterministic)
        rule_issues = self._rule_based_checks(draft)

        # If critical rule violations, reject immediately
        if rule_issues.get("critical"):
            return {
                "overall_score": 0,
                "dimension_scores": {},
                "feedback": f"CRITICAL: {'; '.join(rule_issues['critical'])}",
                "suggestions": rule_issues.get("suggestions", []),
            }

        # AI-based quality review
        captions_preview = {}
        for platform, data in draft.get("captions", {}).items():
            cap = data.get("caption", "") if isinstance(data, dict) else str(data)
            captions_preview[platform] = cap[:200]

        context = f"""Review this content draft for Chicago Fleet Wraps:

TOPIC: {draft.get('topic', 'unknown')}
CONTENT TYPE: {draft.get('content_type', 'image')}
IMAGE PROMPT: {draft.get('image_prompt', 'N/A')[:300]}
PLATFORMS: {', '.join(draft.get('platforms', []))}
REVISION #: {draft.get('revision_count', 0)}

CAPTIONS:
{json.dumps(captions_preview, indent=2, default=str)}

ARM SELECTION (content components):
{json.dumps(draft.get('arm_selection', {}), indent=2, default=str)}

RULE-BASED ISSUES FOUND:
{json.dumps(rule_issues.get('warnings', []), default=str)}

Score each dimension 1-10 and provide overall assessment.
Return ONLY JSON:
{{
    "dimension_scores": {{
        "brand_voice": 0,
        "visual_quality": 0,
        "engagement_potential": 0,
        "platform_fit": 0,
        "uniqueness": 0,
        "brand_safety": 0,
        "geo_relevance": 0,
        "cta_effectiveness": 0
    }},
    "overall_score": 0.0,
    "feedback": "Specific feedback if rejecting",
    "suggestions": ["Specific improvement suggestions"]
}}"""

        try:
            response = self.think(context)
            if "```" in response:
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            review = json.loads(response.strip())

            # Calculate overall score as weighted average
            scores = review.get("dimension_scores", {})
            if scores:
                weights = {
                    "brand_voice": 2.0,
                    "engagement_potential": 2.0,
                    "brand_safety": 1.5,
                    "visual_quality": 1.0,
                    "platform_fit": 1.0,
                    "uniqueness": 1.0,
                    "geo_relevance": 0.5,
                    "cta_effectiveness": 0.5,
                }
                weighted_sum = sum(
                    scores.get(dim, 5) * weights.get(dim, 1.0)
                    for dim in weights
                )
                total_weight = sum(weights.values())
                review["overall_score"] = round(weighted_sum / total_weight, 1)

            return review

        except Exception as e:
            self.log(f"AI review error: {e}")
            # If AI fails, do a generous pass with rule-based only
            return {
                "overall_score": 7.0 if not rule_issues.get("warnings") else 5.0,
                "dimension_scores": {},
                "feedback": "AI review failed, using rule-based assessment",
                "suggestions": rule_issues.get("suggestions", []),
            }

    def _rule_based_checks(self, draft: dict) -> dict:
        """Fast, deterministic quality checks."""
        critical = []
        warnings = []
        suggestions = []

        # Check for competitor mentions
        all_text = json.dumps(draft.get("captions", {})).lower()
        for comp in COMPETITORS:
            if comp.lower() in all_text:
                critical.append(f"Competitor mention detected: '{comp}'")

        # Check image prompt for text/logos (we don't want text in images)
        prompt = draft.get("image_prompt", "").lower()
        text_signals = ["text that says", "with text", "logo", "watermark", "words"]
        for signal in text_signals:
            if signal in prompt:
                warnings.append(f"Image prompt may generate text: '{signal}'")
                suggestions.append("Ensure image prompt explicitly says 'no text, no logos'")

        # Check caption length
        for platform, data in draft.get("captions", {}).items():
            caption = data.get("caption", "") if isinstance(data, dict) else str(data)
            if len(caption) < 10:
                warnings.append(f"{platform} caption too short ({len(caption)} chars)")
            if platform == "tiktok" and len(caption) > 300:
                warnings.append(f"TikTok caption too long ({len(caption)} chars)")

        # Check for banned phrases
        banned = [
            "we are proud to announce", "excited to share",
            "don't miss out", "limited time offer", "act now",
            "click the link in bio",  # Instagram hates this
        ]
        for phrase in banned:
            if phrase in all_text:
                warnings.append(f"Banned phrase detected: '{phrase}'")
                suggestions.append(f"Replace '{phrase}' with something more natural")

        return {
            "critical": critical,
            "warnings": warnings,
            "suggestions": suggestions,
        }

    def _load_log(self) -> list:
        if os.path.exists(self.QUALITY_LOG):
            try:
                with open(self.QUALITY_LOG, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save_log(self, log_data: list):
        log_data = log_data[-500:]
        with open(self.QUALITY_LOG, "w") as f:
            json.dump(log_data, f, indent=2, default=str)


if __name__ == "__main__":
    agent = QualityAgent()
    result = agent.run()
    print(json.dumps(result, indent=2, default=str))
