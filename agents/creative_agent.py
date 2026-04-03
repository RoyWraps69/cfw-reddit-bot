"""
Chicago Fleet Wraps — Creative Agent v2.0

Generates all content based on CONTENT_REQUEST messages from Strategy.
Sends drafts to Quality Agent for review.
Handles REVISION_REQUEST messages and resubmits improved content.
"""

import os
import json
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base import BaseAgent
from content_creator import generate_video_script, save_content_to_queue


class CreativeAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="creative",
            role="Creative Director",
            capabilities=["video_scripts", "captions", "hooks", "thumbnails", "voiceover_copy"],
        )

    def run(self) -> dict:
        self.heartbeat(status="running", action="creative_cycle")
        self.log("Starting creative cycle...")

        results = {"drafts_created": 0, "revisions_handled": 0, "errors": 0}
        messages = self.get_messages(limit=15)

        for msg in messages:
            msg_type = msg.get("type")
            payload = msg.get("payload", {})

            if msg_type == "CONTENT_REQUEST":
                draft = self._create_content(payload)
                if draft:
                    self.send(to="quality", message_type="CONTENT_DRAFT",
                              payload=draft, priority=payload.get("priority", 5))
                    self.log(f"Draft sent to quality: {payload.get('platform')} | {payload.get('archetype')}")
                    results["drafts_created"] += 1
                else:
                    results["errors"] += 1

            elif msg_type == "REVISION_REQUEST":
                revised = self._revise_content(payload)
                if revised:
                    self.send(to="quality", message_type="CONTENT_DRAFT",
                              payload=revised, priority=8)
                    results["revisions_handled"] += 1

        self.heartbeat(status="idle", action=f"created {results['drafts_created']} drafts")
        self.log(f"Creative cycle complete: {results}")
        return results

    def _create_content(self, request: dict) -> dict:
        try:
            platform = request.get("platform", "tiktok")
            archetype = request.get("archetype", "before_after")
            vehicle_focus = request.get("vehicle_type", "")
            hook_direction = request.get("hook_direction", "")

            script = generate_video_script(
                archetype=archetype,
                platform=platform,
                vehicle_focus=vehicle_focus,
            )

            # Add strategy context to the draft
            script["strategy_context"] = {
                "topic_focus": request.get("topic_focus", ""),
                "hook_direction": hook_direction,
                "cta": request.get("cta", "link_in_bio"),
                "priority": request.get("priority", 5),
                "request_id": request.get("id", ""),
            }
            script["revision_count"] = 0

            # Save to queue for posting
            save_content_to_queue(script, platform, archetype)
            return script

        except Exception as e:
            self.log(f"Content creation error: {e}")
            return None

    def _revise_content(self, revision_request: dict) -> dict:
        """Revise content based on Quality Agent feedback."""
        original = revision_request.get("original_draft", {})
        feedback = revision_request.get("feedback", "")
        revision_count = original.get("revision_count", 0) + 1

        if revision_count > 2:
            self.log("Max revisions reached — skipping this content")
            return None

        platform = original.get("platform", "tiktok")
        archetype = original.get("archetype", "before_after")

        # Add feedback to the generation prompt
        revised = generate_video_script(archetype=archetype, platform=platform)
        revised["revision_count"] = revision_count
        revised["revision_feedback"] = feedback
        revised["strategy_context"] = original.get("strategy_context", {})
        return revised
