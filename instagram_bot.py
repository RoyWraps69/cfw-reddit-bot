"""
Chicago Fleet Wraps — Instagram Bot v1.0
FULL CONTENT MACHINE: Posts, stories, reels, comments, engagement.

Every hour:
1. Gets content decision from the brain
2. Posts to the CFW Instagram feed (with AI-generated image)
3. Engages with relevant posts (comments on hashtag feeds)
4. Tracks engagement for self-improvement

Uses Playwright browser automation via Instagram web.
"""
import os
import json
import random
import asyncio
from datetime import datetime
from config import DATA_DIR, OPENAI_MODEL, BUSINESS_CONTEXT
from content_brain import get_brain

IG_POST_LOG = os.path.join(DATA_DIR, "ig_post_history.json")
IG_COMMENT_LOG = os.path.join(DATA_DIR, "ig_comment_history.json")
IG_DAILY_LOG = os.path.join(DATA_DIR, "ig_daily_activity.json")

IG_MAX_POSTS_PER_DAY = 6
IG_MAX_COMMENTS_PER_DAY = 20
IG_MIN_DELAY_SECONDS = 90
IG_MAX_DELAY_SECONDS = 240

# Hashtag sets for engagement (rotate to avoid patterns)
ENGAGE_HASHTAGS = [
    "carwrap", "vinylwrap", "colorchangewrap", "wrappedcars", "wraplife",
    "vehiclewrap", "fleetwrap", "truckwrap", "vanwrap", "ppf",
    "ceramiccoating", "autodetailing", "customcars", "carsofinstagram",
    "rivian", "tesla", "cybertruck", "electricvehicle", "evlife",
    "smallbusiness", "entrepreneur", "foodtruck", "fleetmanagement",
    "chicagocars", "chicago", "chicagobusiness",
    "matteblack", "satinwrap", "chromedelete", "paintprotection",
]


class InstagramBot:
    """Instagram content machine using Playwright browser automation."""

    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.brain = get_brain()
        self.posts_today = 0
        self.comments_today = 0
        self._load_daily_state()

    def _load_daily_state(self):
        if os.path.exists(IG_DAILY_LOG):
            try:
                with open(IG_DAILY_LOG, "r") as f:
                    data = json.load(f)
                if data.get("date") == datetime.now().strftime("%Y-%m-%d"):
                    self.posts_today = data.get("posts", 0)
                    self.comments_today = data.get("comments", 0)
            except Exception:
                pass

    def _save_daily_state(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(IG_DAILY_LOG, "w") as f:
            json.dump({
                "date": datetime.now().strftime("%Y-%m-%d"),
                "posts": self.posts_today,
                "comments": self.comments_today,
            }, f)

    async def start(self):
        from playwright.async_api import async_playwright
        pw = await async_playwright().start()

        try:
            self.browser = await pw.chromium.connect_over_cdp("http://localhost:9222")
            contexts = self.browser.contexts
            if contexts:
                self.context = contexts[0]
                self.page = await self.context.new_page()
            else:
                self.context = await self.browser.new_context()
                self.page = await self.context.new_page()
            print("  [IG] Connected to browser session", flush=True)
        except Exception as e:
            print(f"  [IG] CDP failed, launching fresh: {e}", flush=True)
            self.browser = await pw.chromium.launch(headless=True)
            self.context = await self.browser.new_context(
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
                viewport={"width": 430, "height": 932},
                is_mobile=True,
            )
            self.page = await self.context.new_page()

    async def stop(self):
        if self.page:
            await self.page.close()

    # ─────────────────────────────────────────
    # MAIN CYCLE
    # ─────────────────────────────────────────

    async def run_cycle(self, trends: dict = None, generated_image_path: str = None):
        """Run one full Instagram cycle."""
        print(f"\n{'='*50}", flush=True)
        print(f"  [IG] Starting cycle — Posts: {self.posts_today}/{IG_MAX_POSTS_PER_DAY}, "
              f"Comments: {self.comments_today}/{IG_MAX_COMMENTS_PER_DAY}", flush=True)

        results = {"posts": 0, "comments": 0, "status": "complete"}

        try:
            await self.page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(4)

            # Check login
            page_text = await self.page.inner_text("body")
            if "Log in" in page_text and "Sign up" in page_text:
                print("  [IG] Not logged in. Skipping.", flush=True)
                results["status"] = "not_logged_in"
                return results

            # PHASE 1: Post content
            if self.posts_today < IG_MAX_POSTS_PER_DAY and generated_image_path:
                post_result = await self._post_content(trends, generated_image_path)
                if post_result:
                    results["posts"] = 1
                    self.posts_today += 1
                    self._save_daily_state()

            # PHASE 2: Engage with hashtag feeds
            if self.comments_today < IG_MAX_COMMENTS_PER_DAY:
                comments = await self._engage_with_hashtags()
                results["comments"] = comments
                self.comments_today += comments
                self._save_daily_state()

        except Exception as e:
            print(f"  [IG] Cycle error: {e}", flush=True)
            results["status"] = f"error: {str(e)[:100]}"

        print(f"  [IG] Cycle done. Posted {results['posts']}, commented {results['comments']}", flush=True)
        return results

    # ─────────────────────────────────────────
    # POSTING
    # ─────────────────────────────────────────

    async def _post_content(self, trends: dict, image_path: str) -> bool:
        """Post content to Instagram feed."""
        try:
            decision = self.brain.decide_next_post("instagram", trends)
            caption = decision.get("caption", "")
            hashtags = decision.get("hashtags", [])

            # Instagram hashtag strategy: put in caption
            if hashtags:
                caption += "\n.\n.\n.\n" + " ".join(f"#{tag}" for tag in hashtags[:30])

            print(f"  [IG] Posting: {caption[:80]}...", flush=True)

            # Navigate to Instagram and find the create post button
            await self.page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            # Find the "+" or "Create" button
            create_btn = await self.page.query_selector(
                '[aria-label="New post"], [aria-label="Create"], '
                'svg[aria-label="New post"], a[href="/create/"]'
            )

            if not create_btn:
                # Try finding by text content
                buttons = await self.page.query_selector_all('[role="button"], a, button')
                for btn in buttons:
                    label = await btn.get_attribute("aria-label") or ""
                    if "new" in label.lower() or "create" in label.lower():
                        create_btn = btn
                        break

            if create_btn:
                await create_btn.click()
                await asyncio.sleep(3)

                # Upload the image
                file_input = await self.page.query_selector('input[type="file"]')
                if file_input and image_path and os.path.exists(image_path):
                    await file_input.set_input_files(image_path)
                    await asyncio.sleep(5)

                    # Click Next (crop screen)
                    next_btn = await self.page.query_selector(
                        'button:has-text("Next"), [aria-label="Next"]'
                    )
                    if next_btn:
                        await next_btn.click()
                        await asyncio.sleep(3)

                    # Click Next again (filter screen)
                    next_btn = await self.page.query_selector(
                        'button:has-text("Next"), [aria-label="Next"]'
                    )
                    if next_btn:
                        await next_btn.click()
                        await asyncio.sleep(3)

                    # Find caption textarea and type
                    caption_area = await self.page.query_selector(
                        'textarea[aria-label*="caption"], textarea[placeholder*="caption"], '
                        '[contenteditable="true"], textarea'
                    )
                    if caption_area:
                        await caption_area.click()
                        await caption_area.fill(caption)
                        await asyncio.sleep(2)

                    # Click Share
                    share_btn = await self.page.query_selector(
                        'button:has-text("Share"), [aria-label="Share"]'
                    )
                    if share_btn:
                        await share_btn.click()
                        await asyncio.sleep(8)
                        print(f"  [IG] Posted successfully", flush=True)

                        self.brain.record_post({
                            "id": f"ig_{int(datetime.now().timestamp())}",
                            "platform": "instagram",
                            "content_type": decision.get("content_type", "image"),
                            "topic": decision.get("topic", ""),
                            "audience": decision.get("audience", ""),
                            "caption": caption[:200],
                            "wrappable_target": decision.get("wrappable_target", ""),
                            "campaign": decision.get("campaign", ""),
                        })

                        self._log_post(decision, caption)
                        return True

            print(f"  [IG] Could not find create post UI", flush=True)
            return False

        except Exception as e:
            print(f"  [IG] Post error: {e}", flush=True)
            return False

    # ─────────────────────────────────────────
    # ENGAGEMENT: Comment on hashtag feeds
    # ─────────────────────────────────────────

    async def _engage_with_hashtags(self) -> int:
        """Browse hashtag feeds and comment on relevant posts."""
        comments_posted = 0
        max_comments = min(4, IG_MAX_COMMENTS_PER_DAY - self.comments_today)

        # Pick random hashtags to browse
        hashtags = random.sample(ENGAGE_HASHTAGS, min(3, len(ENGAGE_HASHTAGS)))

        for tag in hashtags:
            if comments_posted >= max_comments:
                break

            try:
                await self.page.goto(f"https://www.instagram.com/explore/tags/{tag}/",
                                    wait_until="domcontentloaded", timeout=20000)
                await asyncio.sleep(4)

                # Click on a recent post (not top posts)
                posts = await self.page.query_selector_all('article a[href*="/p/"]')
                recent_posts = posts[9:18] if len(posts) > 9 else posts  # Skip top 9 (top posts)

                for post_link in random.sample(list(recent_posts), min(2, len(recent_posts))):
                    if comments_posted >= max_comments:
                        break

                    try:
                        await post_link.click()
                        await asyncio.sleep(4)

                        # Read the post caption
                        caption_elem = await self.page.query_selector(
                            'div[class*="Caption"] span, article span[dir="auto"]'
                        )
                        caption_text = ""
                        if caption_elem:
                            caption_text = await caption_elem.inner_text()

                        if not caption_text or len(caption_text) < 10:
                            # Close and continue
                            await self.page.keyboard.press("Escape")
                            await asyncio.sleep(1)
                            continue

                        # Get comment strategy
                        strategy = self.brain.decide_comment_strategy(
                            {"text": caption_text[:300]}, "instagram"
                        )

                        # Generate comment
                        comment_text = self._generate_ig_comment(caption_text[:300], strategy, tag)
                        if not comment_text:
                            await self.page.keyboard.press("Escape")
                            await asyncio.sleep(1)
                            continue

                        # Find comment input and post
                        comment_input = await self.page.query_selector(
                            'textarea[aria-label*="comment"], textarea[placeholder*="comment"], '
                            'form textarea'
                        )

                        if comment_input:
                            await comment_input.click()
                            await asyncio.sleep(1)
                            await comment_input.fill(comment_text)
                            await asyncio.sleep(1)

                            # Find and click post button
                            post_btn = await self.page.query_selector(
                                'button:has-text("Post"), [type="submit"]'
                            )
                            if post_btn:
                                await post_btn.click()
                                await asyncio.sleep(3)
                                comments_posted += 1
                                print(f"  [IG] Commented on #{tag}: {comment_text[:50]}...", flush=True)
                                self._log_comment(tag, caption_text[:100], comment_text, strategy.get("mention_cfw", False))

                        # Close post modal
                        await self.page.keyboard.press("Escape")
                        await asyncio.sleep(1)

                        # Delay
                        delay = random.randint(IG_MIN_DELAY_SECONDS, IG_MAX_DELAY_SECONDS)
                        await asyncio.sleep(delay)

                    except Exception as e:
                        print(f"  [IG] Comment error: {e}", flush=True)
                        try:
                            await self.page.keyboard.press("Escape")
                        except Exception:
                            pass
                        continue

            except Exception as e:
                print(f"  [IG] Hashtag browse error: {e}", flush=True)
                continue

        return comments_posted

    def _generate_ig_comment(self, caption: str, strategy: dict, hashtag: str) -> str:
        """Generate an Instagram comment."""
        from openai import OpenAI
        base_url = os.environ.get("OPENAI_BASE_URL", None)
        ai_client = OpenAI(base_url=base_url) if base_url else OpenAI()

        mention_cfw = strategy.get("mention_cfw", False)

        if mention_cfw:
            system = f"""You're commenting as @chicagofleetwraps on Instagram.
Be genuine and helpful. If they're looking for a wrap shop in Chicago, mention you're based in Portage Park.
Keep under 30 words. Sound like a real business, not a bot.
No emojis. No "DM us!" No "check out our page!"."""
        else:
            system = """You're commenting on an Instagram post about cars/wraps/vehicles.
Be genuine and specific. Comment on something specific in the photo or caption.
Keep under 25 words. Sound like a real person.
No emojis. No generic "nice!" or "fire!" comments.
Add value — a specific compliment, a question, or a relevant observation."""

        prompt = f"""Post caption: {caption[:200]}
Hashtag context: #{hashtag}

Write a comment. ONLY the comment text."""

        try:
            response = ai_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.9,
                max_tokens=60,
            )
            return response.choices[0].message.content.strip().strip('"').strip("'")
        except Exception as e:
            print(f"  [IG] AI error: {e}", flush=True)
            return ""

    # ─────────────────────────────────────────
    # LOGGING
    # ─────────────────────────────────────────

    def _log_post(self, decision: dict, caption: str):
        os.makedirs(DATA_DIR, exist_ok=True)
        log = []
        if os.path.exists(IG_POST_LOG):
            try:
                with open(IG_POST_LOG, "r") as f:
                    log = json.load(f)
            except Exception:
                log = []

        log.append({
            "date": datetime.now().isoformat(),
            "platform": "instagram",
            "topic": decision.get("topic", ""),
            "caption": caption[:300],
            "audience": decision.get("audience", ""),
            "campaign": decision.get("campaign", ""),
        })
        log = log[-500:]
        with open(IG_POST_LOG, "w") as f:
            json.dump(log, f, indent=2)

    def _log_comment(self, hashtag: str, post_caption: str, comment: str, is_promo: bool):
        os.makedirs(DATA_DIR, exist_ok=True)
        log = []
        if os.path.exists(IG_COMMENT_LOG):
            try:
                with open(IG_COMMENT_LOG, "r") as f:
                    log = json.load(f)
            except Exception:
                log = []

        log.append({
            "date": datetime.now().isoformat(),
            "platform": "instagram",
            "hashtag": hashtag,
            "post_caption": post_caption[:100],
            "comment": comment,
            "is_promo": is_promo,
        })
        log = log[-500:]
        with open(IG_COMMENT_LOG, "w") as f:
            json.dump(log, f, indent=2)

    def get_dashboard_data(self) -> dict:
        posts, comments = [], []
        if os.path.exists(IG_POST_LOG):
            try:
                with open(IG_POST_LOG, "r") as f:
                    posts = json.load(f)
            except Exception:
                pass
        if os.path.exists(IG_COMMENT_LOG):
            try:
                with open(IG_COMMENT_LOG, "r") as f:
                    comments = json.load(f)
            except Exception:
                pass

        return {
            "platform": "instagram",
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
                count = await self._engage_with_hashtags()
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


async def run_instagram_cycle(trends: dict = None, image_path: str = None):
    bot = InstagramBot()
    try:
        await bot.start()
        return await bot.run_cycle(trends, image_path)
    finally:
        await bot.stop()
