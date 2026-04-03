"""
Chicago Fleet Wraps — CREATIVE AGENT (The Artist)
===================================================
Generates all content: images, videos, captions, hooks.

Responsibilities:
  - Receive CONTENT_REQUEST and TREND_ALERT from Strategy Agent
  - Use the optimization engine to build optimized image prompts
  - Use the persona engine to write platform-specific captions
  - Generate AI images and videos via media_generator
  - Send CONTENT_DRAFT to Quality Agent for review
  - Handle REVISION_REQUEST from Quality Agent (fix and resubmit)
  - Pre-generate content into the barrel during off-peak hours

This agent CREATES but never PUBLISHES. Quality Agent must approve first.
"""

import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base import BaseAgent, MessageType
from config import DATA_DIR, BUSINESS_CONTEXT


class CreativeAgent(BaseAgent):
    NAME = "creative"
    ROLE = "Creative Director"

    MAX_REVISIONS = 2  # Max times Quality can send back a draft

    def __init__(self):
        super().__init__()

    def _system_prompt(self) -> str:
        return f"""You are the Creative Director for Chicago Fleet Wraps.
You create ALL content — images, videos, captions, and hooks.

BUSINESS CONTEXT:
{BUSINESS_CONTEXT}

YOUR CREATIVE RULES:
- Every image must be photorealistic and professional
- Captions must sound like Roy (the owner), not a marketing agency
- Each platform gets a UNIQUE caption adapted to its audience
- TikTok: punchy, trendy, hook in first 2 seconds
- Instagram: visual storytelling, hashtag strategy, carousel-friendly
- Facebook: solve pain points, longer form OK, community-focused
- Reddit: genuine, helpful, never salesy
- All content must be geo-relevant to Chicago
- NEVER use corporate speak ("We are proud to announce...")
- NEVER repeat the same hook twice in a row
- Images must NOT contain any text, logos, or watermarks

When given a REVISION_REQUEST, take the feedback seriously and improve.
Respond with JSON only."""

    def run(self) -> dict:
        """Execute the creative cycle."""
        self.heartbeat()
        self.log("=" * 50)
        self.log("CREATIVE AGENT — Running cycle")
        self.log("=" * 50)

        results = {
            "drafts_created": 0,
            "revisions_handled": 0,
            "trend_responses": 0,
            "barrel_items_added": 0,
        }

        # 1. Process inbox — handle requests and revisions
        messages = self.receive()

        # Sort: TREND_ALERTs first (priority 1), then REVISION_REQUESTs, then CONTENT_REQUESTs
        urgent = [m for m in messages
                  if (m.type == MessageType.TREND_ALERT.value or m.type == MessageType.TREND_ALERT)]
        revisions = [m for m in messages
                     if (m.type == MessageType.REVISION_REQUEST.value or m.type == MessageType.REVISION_REQUEST)]
        requests = [m for m in messages
                    if (m.type == MessageType.CONTENT_REQUEST.value or m.type == MessageType.CONTENT_REQUEST)]

        # Handle urgent trends first
        for msg in urgent:
            self.log(f"  ← TREND ALERT: {msg.payload.get('trend', {}).get('topic', 'unknown')}")
            draft = self._create_trend_content(msg.payload)
            if draft:
                self._send_to_quality(draft, msg.id)
                results["trend_responses"] += 1
                results["drafts_created"] += 1

        # Handle revision requests
        for msg in revisions:
            self.log(f"  ← REVISION REQUEST: {msg.payload.get('reason', 'unknown')}")
            revised = self._handle_revision(msg.payload)
            if revised:
                self._send_to_quality(revised, msg.id)
                results["revisions_handled"] += 1
                results["drafts_created"] += 1

        # Handle normal content requests
        for msg in requests:
            self.log(f"  ← Content request: {msg.payload.get('topic', 'unknown')}")
            draft = self._create_content(msg.payload)
            if draft:
                self._send_to_quality(draft, msg.id)
                results["drafts_created"] += 1

        # 2. If no requests, pre-generate content for the barrel
        if not messages:
            self.log("No requests — pre-generating content for the barrel")
            barrel_items = self._prefill_barrel()
            results["barrel_items_added"] = barrel_items

        self.log(f"Cycle complete: {results['drafts_created']} drafts, "
                 f"{results['revisions_handled']} revisions, "
                 f"{results['barrel_items_added']} barrel items")
        return results

    def _create_content(self, request: dict) -> dict:
        """Create a full content package from a strategy request."""
        topic = request.get("topic", "vehicle_wrap_showcase")
        platforms = request.get("platforms", ["facebook", "instagram"])
        visual_style = request.get("visual_style", "")
        hook_style = request.get("hook_style", "")
        tone = request.get("tone", "")
        content_type = request.get("content_type", "image")

        # Get optimized arm selection from the optimization engine
        arm_selection = self._get_arm_selection(request)

        # Build the image prompt
        image_prompt = self._build_image_prompt(arm_selection, topic)

        # Generate the image/video
        media_paths = self._generate_media(image_prompt, content_type)

        # Generate platform-specific captions
        captions = self._generate_captions(topic, arm_selection, platforms)

        return {
            "topic": topic,
            "content_type": content_type,
            "arm_selection": arm_selection,
            "image_prompt": image_prompt,
            "media_paths": media_paths,
            "captions": captions,
            "platforms": platforms,
            "request": request,
            "created_at": datetime.now().isoformat(),
            "revision_count": 0,
        }

    def _create_trend_content(self, alert: dict) -> dict:
        """Create content for a trending topic — FAST."""
        trend = alert.get("trend", {})
        topic = trend.get("topic", "trending_topic")
        platforms = alert.get("platforms", ["tiktok", "instagram"])

        self.log(f"  Creating trend content for: {topic}")

        # For trends, use the optimization engine but bias toward proven winners
        arm_selection = self._get_arm_selection({"topic": topic, "trend": True})
        image_prompt = self._build_image_prompt(arm_selection, topic)
        media_paths = self._generate_media(image_prompt, "image")
        captions = self._generate_captions(topic, arm_selection, platforms)

        return {
            "topic": topic,
            "content_type": "image",
            "arm_selection": arm_selection,
            "image_prompt": image_prompt,
            "media_paths": media_paths,
            "captions": captions,
            "platforms": platforms,
            "is_trend": True,
            "trend_data": trend,
            "created_at": datetime.now().isoformat(),
            "revision_count": 0,
        }

    def _handle_revision(self, revision: dict) -> dict:
        """Handle a revision request from Quality Agent."""
        original = revision.get("original_draft", {})
        feedback = revision.get("reason", "")
        revision_count = original.get("revision_count", 0) + 1

        if revision_count > self.MAX_REVISIONS:
            self.log(f"  Max revisions reached ({self.MAX_REVISIONS}), dropping content")
            return None

        # Use AI to understand the feedback and adjust
        context = f"""The Quality Agent rejected your content draft.

ORIGINAL DRAFT:
Topic: {original.get('topic', '')}
Image prompt: {original.get('image_prompt', '')}
Captions: {json.dumps(original.get('captions', {}), indent=2, default=str)[:500]}

QUALITY FEEDBACK:
{feedback}

Revise the content to address the feedback. Return JSON with:
- revised_image_prompt: The improved image prompt
- revised_caption_notes: Notes on how to improve each platform's caption
- what_changed: Brief description of changes made"""

        try:
            ai_response = self.think(context)
            revisions = json.loads(ai_response) if ai_response.startswith("{") else {}
        except Exception:
            revisions = {}

        # Regenerate with revisions applied
        revised_prompt = revisions.get("revised_image_prompt", original.get("image_prompt", ""))
        media_paths = self._generate_media(revised_prompt, original.get("content_type", "image"))

        arm_selection = original.get("arm_selection", {})
        captions = self._generate_captions(
            original.get("topic", ""),
            arm_selection,
            original.get("platforms", ["facebook", "instagram"]),
        )

        revised_draft = dict(original)
        revised_draft.update({
            "image_prompt": revised_prompt,
            "media_paths": media_paths,
            "captions": captions,
            "revision_count": revision_count,
            "revision_feedback": feedback,
            "revised_at": datetime.now().isoformat(),
        })

        return revised_draft

    def _send_to_quality(self, draft: dict, in_reply_to: str = None):
        """Send a content draft to the Quality Agent for review."""
        self.send(
            recipient="quality",
            msg_type=MessageType.CONTENT_DRAFT,
            payload=draft,
            priority=draft.get("request", {}).get("priority", 5),
            in_reply_to=in_reply_to,
        )
        self.log(f"  → Sent draft to Quality: {draft.get('topic', 'unknown')}")

    def _get_arm_selection(self, request: dict) -> dict:
        """Get optimized content components from the optimization engine."""
        try:
            from optimization_engine import select_arms
            selection = select_arms()

            # Override with any specific requests from Strategy
            if request.get("visual_style"):
                selection["visual_style"] = request["visual_style"]
            if request.get("hook_style"):
                selection["hook_style"] = request["hook_style"]
            if request.get("tone"):
                selection["tone"] = request["tone"]

            return selection
        except Exception as e:
            self.log(f"Optimization engine error: {e}")
            return {
                "visual_style": "matte_black",
                "subject_type": "pickup_truck",
                "lighting": "golden_hour",
                "background": "chicago_skyline",
                "hook_style": "question",
                "tone": "professional",
                "caption_length": "medium",
                "cta_style": "soft",
            }

    def _build_image_prompt(self, arm_selection: dict, topic: str) -> str:
        """Build an AI image generation prompt from arm selections."""
        try:
            from optimization_engine import build_image_prompt
            return build_image_prompt(arm_selection, topic)
        except Exception as e:
            self.log(f"Prompt builder error: {e}")
            return (
                "Photorealistic image of a vehicle with a premium vinyl wrap "
                "in Chicago, professional automotive photography, 4K resolution. "
                "Do NOT include any text, logos, watermarks, or words."
            )

    def _generate_media(self, prompt: str, content_type: str) -> dict:
        """Generate image or video using the media generator."""
        try:
            from media_generator import create_content_package
            package = create_content_package({
                "image_prompt": prompt,
                "content_type": content_type,
                "topic": "wrap_showcase",
            })
            return {
                "image_path": package.get("image_path", ""),
                "video_path": package.get("video_path", ""),
            }
        except Exception as e:
            self.log(f"Media generation error: {e}")
            return {"image_path": "", "video_path": ""}

    def _generate_captions(self, topic: str, arm_selection: dict,
                           platforms: list) -> dict:
        """Generate platform-specific captions using the persona engine."""
        captions = {}

        try:
            from optimization_engine import build_caption_guidance
            from persona_engine import get_persona

            guidance = build_caption_guidance(arm_selection)

            for platform in platforms:
                persona = get_persona(platform)
                caption = self._write_caption(topic, platform, persona, guidance)
                captions[platform] = {
                    "caption": caption,
                    "hashtags": self._generate_hashtags(topic, platform),
                }
        except Exception as e:
            self.log(f"Caption generation error: {e}")
            for platform in platforms:
                captions[platform] = {
                    "caption": f"Check out this wrap! #ChicagoFleetWraps #{topic.replace(' ', '')}",
                    "hashtags": ["ChicagoFleetWraps", "VinylWrap", "Chicago"],
                }

        return captions

    def _write_caption(self, topic: str, platform: str, persona: dict,
                       guidance: dict) -> str:
        """Write a single platform-specific caption."""
        context = f"""Write a {platform} caption for a post about: {topic}

PERSONA VOICE:
{persona.get('system_prompt', '')[:500]}

CAPTION GUIDANCE:
Hook: {guidance.get('hook_instruction', '')}
Tone: {guidance.get('tone_instruction', '')}
Length: {guidance.get('length_instruction', '')}
CTA style: {guidance.get('cta_style', 'none')}

Write ONLY the caption text. No quotes, no explanation. Just the caption."""

        try:
            return self.think(context)
        except Exception:
            return f"Another day, another wrap. #ChicagoFleetWraps"

    def _generate_hashtags(self, topic: str, platform: str) -> list:
        """Generate relevant hashtags for a platform."""
        base = ["ChicagoFleetWraps", "VinylWrap", "CarWrap", "Chicago"]
        if platform == "instagram":
            base.extend(["WrapsOfInstagram", "VehicleWrap", "CustomWrap",
                         "ChicagoCars", "WrapLife"])
        elif platform == "tiktok":
            base.extend(["CarTok", "WrapTok", "Transformation", "BeforeAndAfter"])
        return base[:10]

    def _prefill_barrel(self) -> int:
        """Pre-generate content for the barrel during downtime."""
        try:
            import content_queue
            if content_queue.needs_refill():
                self.log("Barrel is low — refilling...")
                content_queue.refill_queue()
                return content_queue.queue_size()
        except Exception as e:
            self.log(f"Barrel refill error: {e}")
        return 0


if __name__ == "__main__":
    agent = CreativeAgent()
    result = agent.run()
    print(json.dumps(result, indent=2, default=str))
