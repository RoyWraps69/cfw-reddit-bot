"""
Chicago Fleet Wraps — Facebook Bot v2.0
FULL CONTENT MACHINE: Posts original content + engages with comments.

Every hour:
1. Gets content decision from the brain (what to post, who to target)
2. Generates AI images/videos for the post
3. Posts to the CFW Facebook page
4. Engages with relevant posts in groups (comments)
5. Tracks engagement for self-improvement

Uses Playwright browser automation for all Facebook interactions.
"""
import os
import json
import time
import random
import asyncio
from datetime import datetime
from config import DATA_DIR, LOG_DIR
from content_brain import ContentBrain, get_brain

FB_COMMENT_LOG = os.path.join(DATA_DIR, "fb_comment_history.json")
FB_POST_LOG = os.path.join(DATA_DIR, "fb_post_history.json")
FB_DAILY_LOG = os.path.join(DATA_DIR, "fb_daily_activity.json")

# Rate limits
FB_MAX_POSTS_PER_DAY = 8
FB_MAX_COMMENTS_PER_DAY = 15
FB_MIN_DELAY_SECONDS = 120
FB_MAX_DELAY_SECONDS = 300


class FacebookBot:
    """Facebook content machine using Playwright browser automation."""

    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.brain = get_brain()
        self.posts_today = 0
        self.comments_today = 0
        self._load_daily_state()

    def _load_daily_state(self):
        if os.path.exists(FB_DAILY_LOG):
            try:
                with open(FB_DAILY_LOG, "r") as f:
                    data = json.load(f)
                if data.get("date") == datetime.now().strftime("%Y-%m-%d"):
                    self.posts_today = data.get("posts", 0)
                    self.comments_today = data.get("comments", 0)
            except Exception:
                pass

    def _save_daily_state(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(FB_DAILY_LOG, "w") as f:
            json.dump({
                "date": datetime.now().strftime("%Y-%m-%d"),
                "posts": self.posts_today,
                "comments": self.comments_today,
            }, f)

    async def start(self):
        """Launch browser with restored Facebook session cookies."""
        from browser_launcher import launch_browser
        self._pw, self.browser, self.context, self.page = await launch_browser("facebook")
        print("  [FB] Browser started with restored session", flush=True)

    async def stop(self):
        if self.page:
            try:
                await self.page.close()
            except Exception:
                pass
        if hasattr(self, '_pw') and self._pw:
            from browser_launcher import close_browser
            await close_browser(self._pw, self.browser)

    # ─────────────────────────────────────────
    # MAIN CYCLE: Post + Engage
    # ─────────────────────────────────────────

    async def run_cycle(self, trends: dict = None, generated_image_path: str = None):
        """Run one full Facebook cycle: post content + engage with others."""
        print(f"\n{'='*50}", flush=True)
        print(f"  [FB] Starting cycle — Posts: {self.posts_today}/{FB_MAX_POSTS_PER_DAY}, "
              f"Comments: {self.comments_today}/{FB_MAX_COMMENTS_PER_DAY}", flush=True)

        results = {"posts": 0, "comments": 0, "status": "complete"}

        try:
            await self.page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            if "login" in self.page.url.lower():
                print("  [FB] Not logged in. Skipping.", flush=True)
                results["status"] = "not_logged_in"
                return results

            # PHASE 1: Post original content
            if self.posts_today < FB_MAX_POSTS_PER_DAY:
                post_result = await self._post_content(trends, generated_image_path)
                if post_result:
                    results["posts"] = 1
                    self.posts_today += 1
                    self._save_daily_state()

            # PHASE 2: Engage with others' posts
            if self.comments_today < FB_MAX_COMMENTS_PER_DAY:
                comments = await self._engage_with_posts(trends)
                results["comments"] = comments
                self.comments_today += comments
                self._save_daily_state()

        except Exception as e:
            print(f"  [FB] Cycle error: {e}", flush=True)
            results["status"] = f"error: {str(e)[:100]}"

        print(f"  [FB] Cycle done. Posted {results['posts']}, commented {results['comments']}", flush=True)
        return results

    # ─────────────────────────────────────────
    # POSTING: Create original content
    # ─────────────────────────────────────────

    async def _post_content(self, trends: dict, image_path: str = None) -> bool:
        """Post original content to the CFW Facebook page."""
        try:
            # Get content decision from the brain
            decision = self.brain.decide_next_post("facebook", trends)
            caption = decision.get("caption", "")
            hashtags = decision.get("hashtags", [])

            if hashtags:
                caption += "\n\n" + " ".join(f"#{tag}" for tag in hashtags[:5])

            print(f"  [FB] Posting: {caption[:80]}...", flush=True)

            # Navigate to CFW page
            await self.page.goto("https://www.facebook.com/chicagofleetwraps",
                               wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(5)

            # Find the "Create post" or "What's on your mind" box
            create_post = await self.page.query_selector(
                '[aria-label*="Create a post"], [aria-label*="create a post"], '
                '[role="button"]:has-text("Create post"), '
                '[aria-label*="What\'s on your mind"]'
            )

            if not create_post:
                # Try clicking on the post creation area
                create_post = await self.page.query_selector(
                    '[data-pagelet*="ProfileComposer"], '
                    '[class*="composer"], '
                    'div:has-text("What\'s on your mind")'
                )

            if create_post:
                await create_post.click()
                await asyncio.sleep(3)

                # Find the text input area
                text_area = await self.page.query_selector(
                    '[contenteditable="true"][role="textbox"], '
                    '[aria-label*="What\'s on your mind"]'
                )

                if text_area:
                    await text_area.click()
                    await asyncio.sleep(1)

                    # Type the caption
                    await text_area.fill(caption)
                    await asyncio.sleep(2)

                    # Upload image if available
                    if image_path and os.path.exists(image_path):
                        # Find photo/video upload button
                        photo_btn = await self.page.query_selector(
                            '[aria-label*="Photo"], [aria-label*="photo"], '
                            '[aria-label*="Add photos"]'
                        )
                        if photo_btn:
                            await photo_btn.click()
                            await asyncio.sleep(2)

                            # Find file input and upload
                            file_input = await self.page.query_selector('input[type="file"]')
                            if file_input:
                                await file_input.set_input_files(image_path)
                                await asyncio.sleep(5)

                    # Click Post button
                    post_btn = await self.page.query_selector(
                        '[aria-label="Post"], [role="button"]:has-text("Post")'
                    )
                    if post_btn:
                        await post_btn.click()
                        await asyncio.sleep(5)
                        print(f"  [FB] Posted successfully", flush=True)

                        # Record for performance tracking
                        self.brain.record_post({
                            "id": f"fb_{int(datetime.now().timestamp())}",
                            "platform": "facebook",
                            "content_type": decision.get("content_type", "text"),
                            "topic": decision.get("topic", ""),
                            "audience": decision.get("audience", ""),
                            "caption": caption,
                            "wrappable_target": decision.get("wrappable_target", ""),
                            "campaign": decision.get("campaign", ""),
                            "had_image": bool(image_path),
                        })

                        self._log_post(decision, caption, image_path)
                        return True

            print(f"  [FB] Could not find post creation UI", flush=True)
            return False

        except Exception as e:
            print(f"  [FB] Post error: {e}", flush=True)
            return False

    # ─────────────────────────────────────────
    # ENGAGEMENT: Comment on others' posts
    # ─────────────────────────────────────────

    async def _engage_with_posts(self, trends: dict) -> int:
        """Find and engage with relevant posts."""
        comments_posted = 0
        max_comments = min(3, FB_MAX_COMMENTS_PER_DAY - self.comments_today)

        # Search for relevant posts
        search_terms = [
            "car wrap", "vehicle wrap", "fleet branding", "vinyl wrap",
            "truck wrap chicago", "EV wrap", "color change wrap",
            "food truck wrap", "van wrap", "fleet graphics",
        ]
        search_term = random.choice(search_terms)

        try:
            await self.page.goto(
                f"https://www.facebook.com/search/posts/?q={search_term.replace(' ', '%20')}",
                wait_until="domcontentloaded", timeout=30000
            )
            await asyncio.sleep(5)

            # Scroll to load posts
            await self.page.evaluate("window.scrollBy(0, 800)")
            await asyncio.sleep(3)

            # Find posts
            post_elements = await self.page.query_selector_all('[role="article"]')

            for elem in post_elements[:max_comments + 2]:
                if comments_posted >= max_comments:
                    break

                try:
                    text = await elem.inner_text()
                    if not text or len(text) < 30:
                        continue

                    # Get comment strategy from the brain
                    strategy = self.brain.decide_comment_strategy(
                        {"text": text[:500]}, "facebook"
                    )

                    if not strategy.get("should_comment"):
                        continue

                    # Generate comment using AI
                    comment_text = self._generate_comment(text[:400], strategy)
                    if not comment_text:
                        continue

                    # Post the comment
                    success = await self._post_comment_on_element(elem, comment_text)
                    if success:
                        comments_posted += 1
                        self._log_comment(text[:200], comment_text, strategy.get("mention_cfw", False))

                        delay = random.randint(FB_MIN_DELAY_SECONDS, FB_MAX_DELAY_SECONDS)
                        print(f"  [FB] Waiting {delay}s...", flush=True)
                        await asyncio.sleep(delay)

                except Exception as e:
                    print(f"  [FB] Comment error: {e}", flush=True)
                    continue

        except Exception as e:
            print(f"  [FB] Engagement error: {e}", flush=True)

        return comments_posted

    def _generate_comment(self, post_text: str, strategy: dict) -> str:
        """Generate a comment using AI based on the brain's strategy."""
        from openai import OpenAI
        from config import OPENAI_MODEL, BUSINESS_CONTEXT

        base_url = os.environ.get("OPENAI_BASE_URL", None)
        ai_client = OpenAI(base_url=base_url) if base_url else OpenAI()

        mention_cfw = strategy.get("mention_cfw", False)
        campaign = strategy.get("campaign")
        target = strategy.get("wrappable_target")

        if mention_cfw:
            system = f"""You're commenting as Chicago Fleet Wraps on Facebook.
Be helpful first, promotional second. Answer their question, then mention CFW naturally.
BUSINESS: {BUSINESS_CONTEXT[:200]}
Keep under 50 words. Sound real, not salesy. Include one specific detail."""
        else:
            system = """You're a car/wrap industry professional commenting on Facebook.
Be helpful and knowledgeable. Do NOT mention any business name.
Keep under 40 words. Sound like a real person."""

        campaign_context = ""
        if campaign:
            campaign_context = f"\nRelevant angle: {campaign.get('response_angle', '')}"

        target_context = ""
        if target:
            target_context = f"\nVehicle type: {target.get('item', '')}, angle: {', '.join(target.get('angles', [])[:2])}"

        prompt = f"""Post: {post_text[:300]}
{campaign_context}{target_context}

Write a comment. ONLY the comment text."""

        try:
            response = ai_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.9,
                max_tokens=100,
            )
            return response.choices[0].message.content.strip().strip('"').strip("'")
        except Exception as e:
            print(f"  [FB] AI error: {e}", flush=True)
            return ""

    async def _post_comment_on_element(self, elem, comment_text: str) -> bool:
        """Post a comment on a Facebook post element."""
        try:
            # Click comment button
            comment_btn = await elem.query_selector(
                '[aria-label*="Leave a comment"], [aria-label*="Comment"], '
                '[role="button"]:has-text("Comment")'
            )
            if comment_btn:
                await comment_btn.click()
                await asyncio.sleep(2)

            # Find comment input
            comment_box = await elem.query_selector(
                '[aria-label*="Write a comment"], [aria-label*="write a comment"], '
                '[contenteditable="true"][role="textbox"]'
            )

            if not comment_box:
                # Try page-level search
                comment_box = await self.page.query_selector(
                    '[aria-label*="Write a comment"][contenteditable="true"]'
                )

            if comment_box:
                await comment_box.click()
                await asyncio.sleep(1)
                await comment_box.fill(comment_text)
                await asyncio.sleep(1)
                await comment_box.press("Enter")
                await asyncio.sleep(3)
                print(f"  [FB] Commented: {comment_text[:60]}...", flush=True)
                return True

            return False
        except Exception as e:
            print(f"  [FB] Post comment error: {e}", flush=True)
            return False

    # ─────────────────────────────────────────
    # LOGGING
    # ─────────────────────────────────────────

    def _log_post(self, decision: dict, caption: str, image_path: str = None):
        os.makedirs(DATA_DIR, exist_ok=True)
        log = []
        if os.path.exists(FB_POST_LOG):
            try:
                with open(FB_POST_LOG, "r") as f:
                    log = json.load(f)
            except Exception:
                log = []

        log.append({
            "date": datetime.now().isoformat(),
            "platform": "facebook",
            "topic": decision.get("topic", ""),
            "caption": caption[:300],
            "audience": decision.get("audience", ""),
            "campaign": decision.get("campaign", ""),
            "had_image": bool(image_path),
            "content_type": decision.get("content_type", "text"),
        })
        log = log[-500:]
        with open(FB_POST_LOG, "w") as f:
            json.dump(log, f, indent=2)

    def _log_comment(self, post_text: str, comment: str, is_promo: bool):
        os.makedirs(DATA_DIR, exist_ok=True)
        log = []
        if os.path.exists(FB_COMMENT_LOG):
            try:
                with open(FB_COMMENT_LOG, "r") as f:
                    log = json.load(f)
            except Exception:
                log = []

        log.append({
            "date": datetime.now().isoformat(),
            "platform": "facebook",
            "post_text": post_text[:200],
            "comment": comment,
            "is_promo": is_promo,
        })
        log = log[-500:]
        with open(FB_COMMENT_LOG, "w") as f:
            json.dump(log, f, indent=2)

    def get_dashboard_data(self) -> dict:
        posts = []
        if os.path.exists(FB_POST_LOG):
            try:
                with open(FB_POST_LOG, "r") as f:
                    posts = json.load(f)
            except Exception:
                posts = []

        comments = []
        if os.path.exists(FB_COMMENT_LOG):
            try:
                with open(FB_COMMENT_LOG, "r") as f:
                    comments = json.load(f)
            except Exception:
                comments = []

        return {
            "platform": "facebook",
            "total_posts": len(posts),
            "total_comments": len(comments),
            "today_posts": self.posts_today,
            "today_comments": self.comments_today,
            "recent_posts": posts[-5:],
            "recent_comments": comments[-5:],
        }


    def create_post(self, caption: str = "", hashtags: list = None,
                    image_path: str = None) -> dict:
        """Synchronous wrapper to create a post — called by master.py."""
        async def _do_post():
            await self.start()
            try:
                decision = {
                    "topic": caption[:50],
                    "caption": caption,
                    "hashtags": hashtags or [],
                    "content_type": "image" if image_path else "text",
                    "audience": "general",
                    "wrappable_target": "",
                    "campaign": "organic",
                    "cta_style": "none",
                }
                result = await self._post_content(
                    trends={"content_ideas": []},
                    image_path=image_path,
                )
                return {"posted": result, "caption": caption}
            finally:
                await self.stop()

        try:
            return asyncio.run(_do_post())
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(_do_post())
            finally:
                loop.close()

    def engage_with_posts(self, max_comments: int = 3) -> dict:
        """Synchronous wrapper to engage with posts — called by master.py."""
        async def _do_engage():
            await self.start()
            try:
                count = await self._engage_with_posts(trends={})
                return {"status": "completed", "comments_posted": count}
            finally:
                await self.stop()

        try:
            return asyncio.run(_do_engage())
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(_do_engage())
            finally:
                loop.close()


async def run_facebook_cycle(trends: dict = None, image_path: str = None):
    bot = FacebookBot()
    try:
        await bot.start()
        return await bot.run_cycle(trends, image_path)
    finally:
        await bot.stop()
