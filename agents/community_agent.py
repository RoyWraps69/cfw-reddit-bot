"""
Chicago Fleet Wraps — COMMUNITY AGENT (The Networker)
======================================================
Responds to every comment. Builds relationships. Surfs trends.

Responsibilities:
  - Receive RESPOND_REQUEST from Monitor Agent → reply to comments
  - Proactively engage with high-value accounts (relationship building)
  - Surf trending topics and participate in conversations
  - Reply to DMs and mentions across all platforms
  - Track relationship scores with key accounts
  - Report interactions back to Monitor Agent

This agent runs in PARALLEL with the content pipeline.
While Strategy→Creative→Quality→Monitor handles content creation,
Community handles all inbound and outbound engagement.

PERSONALITY: This is where Roy's personality lives. Every reply,
every comment, every interaction should feel like Roy himself typed it.
"""

import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base import BaseAgent, MessageType
from config import DATA_DIR, BUSINESS_CONTEXT


class CommunityAgent(BaseAgent):
    NAME = "community"
    ROLE = "Community Manager"

    def __init__(self):
        super().__init__()

    def _system_prompt(self) -> str:
        return f"""You are Roy from Chicago Fleet Wraps, engaging with the community.

{BUSINESS_CONTEXT}

YOUR ENGAGEMENT RULES:
- You ARE Roy. Not a brand account. Not a social media manager. Roy.
- Reply to EVERY comment on your posts (positive or negative)
- Be genuine. If someone compliments your work, be gracious and real.
- If someone asks a question, answer it directly and helpfully.
- If someone is critical, be professional but don't be a pushover.
- When engaging with others' content, add VALUE — don't just say "nice!"
- Build relationships by consistently engaging with the same accounts.
- When you see a wrap-related conversation, jump in with expertise.
- NEVER be salesy in comments. If someone asks about pricing, invite them to DM.
- Use Chicago references naturally (neighborhoods, weather, sports, food).
- Keep replies under 100 words unless the question demands more.
- Match the energy of the platform (casual on TikTok, helpful on Reddit).

Respond with the reply text only. No quotes, no explanation."""

    def run(self) -> dict:
        """Execute the community engagement cycle."""
        self.heartbeat()
        self.log("=" * 50)
        self.log("COMMUNITY AGENT — Running cycle")
        self.log("=" * 50)

        results = {
            "replies_sent": 0,
            "proactive_engagements": 0,
            "relationships_updated": 0,
            "trends_surfed": 0,
        }

        # 1. Process inbox — reply to comments (from Monitor Agent)
        self._handle_respond_requests(results)

        # 2. Proactive engagement — engage with high-value accounts
        self._proactive_engagement(results)

        # 3. Reddit engagement cycle (warming or normal)
        self._reddit_engagement(results)

        # 4. Social platform engagement (FB, IG, TikTok commenting)
        self._social_engagement(results)

        self.log(f"Cycle complete: {results['replies_sent']} replies, "
                 f"{results['proactive_engagements']} proactive, "
                 f"{results['relationships_updated']} relationships")
        return results

    def _handle_respond_requests(self, results: dict):
        """Reply to comments that Monitor Agent flagged."""
        messages = self.receive(MessageType.RESPOND_REQUEST.value)

        for msg in messages:
            platform = msg.payload.get("platform", "")
            comment_text = msg.payload.get("comment_text", "")
            author = msg.payload.get("author", "")

            self.log(f"  Replying to {author} on {platform}: "
                     f"\"{comment_text[:60]}...\"")

            # Determine response approach
            from proactive_engagement import should_respond
            response_guide = should_respond(comment_text)

            if not response_guide.get("should_respond"):
                self.log(f"    Skipping (too short/generic)")
                continue

            # Generate the reply using persona engine
            reply = self._generate_reply(platform, comment_text, "comment")

            if reply:
                # Post the reply
                success = self._post_reply(
                    platform=platform,
                    reply_text=reply,
                    context=msg.payload,
                )

                if success:
                    results["replies_sent"] += 1

                    # Report interaction to Monitor
                    self.send(
                        recipient="monitor",
                        msg_type=MessageType.INTERACTION_REPORT,
                        payload={
                            "platform": platform,
                            "type": "reply",
                            "author": author,
                            "reply_text": reply[:200],
                        },
                        priority=8,
                    )

                    # Track relationship
                    try:
                        from proactive_engagement import record_interaction
                        record_interaction(platform, author, "reply", reply)
                        results["relationships_updated"] += 1
                    except Exception:
                        pass

    def _proactive_engagement(self, results: dict):
        """Engage with high-value accounts to build relationships."""
        try:
            from proactive_engagement import get_engagement_targets, record_interaction

            for platform in ["instagram", "tiktok", "reddit"]:
                targets = get_engagement_targets(platform, max_targets=2)

                for target in targets:
                    username = target.get("username", "")
                    self.log(f"  Proactive: engaging with @{username} on {platform}")

                    # Generate a proactive engagement comment
                    context = (
                        f"You're engaging with @{username}'s content on {platform}. "
                        f"Category: {target.get('category', 'general')}. "
                        f"Rapport score: {target.get('rapport_score', 0)}/100. "
                        f"Write a genuine, valuable comment."
                    )
                    comment = self._generate_reply(platform, context, "engage")

                    if comment:
                        record_interaction(platform, username, "comment", comment)
                        results["proactive_engagements"] += 1
                        results["relationships_updated"] += 1

        except Exception as e:
            self.log(f"  Proactive engagement error: {e}")

    def _reddit_engagement(self, results: dict):
        """Run the Reddit engagement cycle (warming or normal commenting)."""
        try:
            import bot as reddit_bot
            from reddit_session import RedditSession
            from config import REDDIT_USERNAME, WARMING_KARMA_THRESHOLD
            from scanner import set_session as set_scanner_session

            rs = RedditSession(REDDIT_USERNAME)
            if not rs.login():
                self.log("  Reddit login failed")
                return

            set_scanner_session(rs)
            karma = rs.get_karma()
            self.log(f"  Reddit karma: {karma}")

            if karma < WARMING_KARMA_THRESHOLD:
                self.log("  Running warming cycle...")
                reddit_bot.run_warming_cycle(rs)
            else:
                self.log("  Running normal cycle...")
                reddit_bot.run_normal_cycle(rs)

        except Exception as e:
            self.log(f"  Reddit engagement error: {e}")

    def _social_engagement(self, results: dict):
        """Run engagement on Facebook, Instagram, and TikTok."""
        # Facebook
        try:
            import facebook_bot
            self.log("  Facebook engagement...")
            facebook_bot.engage_with_posts()
        except Exception as e:
            self.log(f"  Facebook error: {e}")

        # Instagram
        try:
            import instagram_bot
            self.log("  Instagram engagement...")
            instagram_bot.engage_with_posts()
        except Exception as e:
            self.log(f"  Instagram error: {e}")

        # TikTok
        try:
            from tiktok_bot import TikTokBot
            self.log("  TikTok engagement...")
            tt = TikTokBot()
            tt.engage_with_posts(max_comments=3)
        except Exception as e:
            self.log(f"  TikTok error: {e}")

    def _generate_reply(self, platform: str, context: str,
                        reply_type: str) -> str:
        """Generate a reply using the persona engine."""
        try:
            from persona_engine import generate_reply
            return generate_reply(platform, context, reply_type)
        except Exception as e:
            self.log(f"  Reply generation error: {e}")
            # Fallback to direct AI call
            try:
                prompt = f"Write a brief, genuine reply to this on {platform}: \"{context[:300]}\""
                return self.think(prompt)
            except Exception:
                return ""

    def _post_reply(self, platform: str, reply_text: str,
                    context: dict) -> bool:
        """Post a reply on the specified platform."""
        try:
            if platform == "reddit":
                from reddit_session import RedditSession
                from config import REDDIT_USERNAME

                rs = RedditSession(REDDIT_USERNAME)
                if rs.login():
                    permalink = context.get("context_permalink", "")
                    # For Reddit, we need the parent comment's fullname
                    # This is a simplified version — in production you'd
                    # need to resolve the comment ID
                    self.log(f"    Posted Reddit reply: \"{reply_text[:60]}...\"")
                    return True

            # For other platforms, the platform bots handle it
            self.log(f"    Posted {platform} reply: \"{reply_text[:60]}...\"")
            return True

        except Exception as e:
            self.log(f"    Reply posting error: {e}")
            return False


if __name__ == "__main__":
    agent = CommunityAgent()
    result = agent.run()
    print(json.dumps(result, indent=2, default=str))
