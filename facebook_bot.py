"""
Chicago Fleet Wraps — Facebook Bot v3.0
ROBUST CONTENT MACHINE: Posts original content + engages with comments.

v3.0 Changes:
- Multiple fallback selector strategies for post creation
- Text-only posting when images fail
- Screenshot debugging on failure
- Better anti-detection measures
- Graceful degradation at every step

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

# CFW Facebook page URL
CFW_PAGE_URL = "https://www.facebook.com/chicagofleetwraps"


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
        # Add stealth: randomize viewport slightly
        await self.page.set_viewport_size({
            "width": 1280 + random.randint(-20, 20),
            "height": 720 + random.randint(-20, 20),
        })
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

    async def _save_debug_screenshot(self, name: str):
        """Save a screenshot for debugging when something fails."""
        try:
            os.makedirs(LOG_DIR, exist_ok=True)
            path = os.path.join(LOG_DIR, f"fb_debug_{name}_{int(time.time())}.png")
            await self.page.screenshot(path=path)
            print(f"  [FB] Debug screenshot saved: {path}", flush=True)
        except Exception:
            pass

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
            # Navigate to Facebook and check login
            await self.page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(5)

            # Check if logged in by looking for key elements
            page_content = await self.page.content()
            is_logged_in = (
                "login" not in self.page.url.lower() or
                "feed" in page_content.lower() or
                await self.page.query_selector('[aria-label="Your profile"]') is not None or
                await self.page.query_selector('[aria-label="Account"]') is not None
            )

            if not is_logged_in:
                print("  [FB] Not logged in. Skipping.", flush=True)
                await self._save_debug_screenshot("not_logged_in")
                results["status"] = "not_logged_in"
                return results

            print("  [FB] Logged in successfully", flush=True)

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

    async def _post_content(self, trends: dict, image_path: str = None,
                            override_caption: str = "", override_hashtags: list = None) -> bool:
        """Post original content to the CFW Facebook page using multiple strategies."""
        try:
            # Use override caption if provided (from master orchestrator), otherwise ask brain
            if override_caption:
                caption = override_caption
                hashtags = override_hashtags or []
            else:
                decision = self.brain.decide_next_post("facebook", trends)
                caption = decision.get("caption", "")
                hashtags = decision.get("hashtags", [])

            if hashtags:
                caption += "\n\n" + " ".join(f"#{tag}" for tag in hashtags[:5])

            if not caption:
                print("  [FB] No caption generated, skipping post", flush=True)
                return False

            print(f"  [FB] Posting: {caption[:80]}...", flush=True)

            # Navigate to CFW page
            await self.page.goto(CFW_PAGE_URL, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(5)

            # Strategy 1: Try clicking the composer box directly
            posted = await self._try_post_strategy_1(caption, image_path)
            if posted:
                self._log_post(decision, caption, image_path)
                return True

            # Strategy 2: Try the page's "Create post" button
            posted = await self._try_post_strategy_2(caption, image_path)
            if posted:
                self._log_post(decision, caption, image_path)
                return True

            # Strategy 3: Use keyboard shortcut to open composer
            posted = await self._try_post_strategy_3(caption, image_path)
            if posted:
                self._log_post(decision, caption, image_path)
                return True

            # All strategies failed
            await self._save_debug_screenshot("post_failed")
            print("  [FB] All post strategies failed", flush=True)
            return False

        except Exception as e:
            print(f"  [FB] Post error: {e}", flush=True)
            return False

    async def _try_post_strategy_1(self, caption: str, image_path: str = None) -> bool:
        """Strategy 1: Click on 'What's on your mind' or composer area."""
        try:
            # Look for the composer trigger with many possible selectors
            selectors = [
                'div[role="button"]:has-text("What\'s on your mind")',
                '[aria-label*="Create a post"]',
                '[aria-label*="create a post"]',
                '[aria-label*="What\'s on your mind"]',
                'div[role="button"]:has-text("Create post")',
                'div[role="button"]:has-text("Write something")',
                'span:has-text("What\'s on your mind")',
                'span:has-text("Create post")',
            ]

            composer_trigger = None
            for sel in selectors:
                try:
                    elem = await self.page.query_selector(sel)
                    if elem and await elem.is_visible():
                        composer_trigger = elem
                        print(f"  [FB] Found composer via: {sel[:50]}", flush=True)
                        break
                except Exception:
                    continue

            if not composer_trigger:
                print("  [FB] Strategy 1: No composer trigger found", flush=True)
                return False

            await composer_trigger.click()
            await asyncio.sleep(3)

            return await self._fill_and_submit_post(caption, image_path)

        except Exception as e:
            print(f"  [FB] Strategy 1 error: {e}", flush=True)
            return False

    async def _try_post_strategy_2(self, caption: str, image_path: str = None) -> bool:
        """Strategy 2: Navigate directly to the page's post creation URL."""
        try:
            # Try navigating to the page's post creation dialog
            await self.page.goto(
                f"{CFW_PAGE_URL}?sk=wall",
                wait_until="domcontentloaded", timeout=30000
            )
            await asyncio.sleep(5)

            # Click any visible text input or composer area
            all_buttons = await self.page.query_selector_all('div[role="button"]')
            for btn in all_buttons:
                try:
                    text = await btn.inner_text()
                    if any(kw in text.lower() for kw in ["what's on your mind", "create post", "write something"]):
                        await btn.click()
                        await asyncio.sleep(3)
                        return await self._fill_and_submit_post(caption, image_path)
                except Exception:
                    continue

            print("  [FB] Strategy 2: No post button found", flush=True)
            return False

        except Exception as e:
            print(f"  [FB] Strategy 2 error: {e}", flush=True)
            return False

    async def _try_post_strategy_3(self, caption: str, image_path: str = None) -> bool:
        """Strategy 3: Use Tab navigation and keyboard to find the composer."""
        try:
            # Go back to the page
            await self.page.goto(CFW_PAGE_URL, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(5)

            # Try pressing Tab multiple times to reach the composer
            for _ in range(10):
                await self.page.keyboard.press("Tab")
                await asyncio.sleep(0.3)

            # Try pressing Enter on whatever is focused
            await self.page.keyboard.press("Enter")
            await asyncio.sleep(3)

            # Check if a dialog/modal opened with a text area
            text_area = await self.page.query_selector(
                '[contenteditable="true"][role="textbox"]'
            )
            if text_area:
                return await self._fill_and_submit_post(caption, image_path)

            print("  [FB] Strategy 3: No composer opened via keyboard", flush=True)
            return False

        except Exception as e:
            print(f"  [FB] Strategy 3 error: {e}", flush=True)
            return False

    async def _fill_and_submit_post(self, caption: str, image_path: str = None) -> bool:
        """Fill the post composer and submit. Called after the composer is opened."""
        try:
            # Find the text input area (contenteditable div)
            text_area = None
            text_selectors = [
                '[contenteditable="true"][role="textbox"]',
                '[contenteditable="true"][data-lexical-editor="true"]',
                '[aria-label*="What\'s on your mind"][contenteditable="true"]',
                '[aria-label*="Create a public post"][contenteditable="true"]',
                'div[contenteditable="true"]',
            ]

            for sel in text_selectors:
                try:
                    elems = await self.page.query_selector_all(sel)
                    for elem in elems:
                        if await elem.is_visible():
                            text_area = elem
                            break
                    if text_area:
                        break
                except Exception:
                    continue

            if not text_area:
                print("  [FB] No text area found in composer", flush=True)
                await self._save_debug_screenshot("no_textarea")
                return False

            # Click and type the caption
            await text_area.click()
            await asyncio.sleep(1)

            # Type character by character for more natural behavior
            # But use fill for speed in headless mode
            await text_area.fill("")  # Clear first
            await asyncio.sleep(0.5)

            # Type in chunks to look more natural
            chunks = [caption[i:i+50] for i in range(0, len(caption), 50)]
            for chunk in chunks:
                await self.page.keyboard.type(chunk, delay=20)
                await asyncio.sleep(0.3)

            await asyncio.sleep(2)

            # Upload image if available
            if image_path and os.path.exists(image_path):
                try:
                    # Look for photo/video button
                    photo_selectors = [
                        '[aria-label*="Photo"]',
                        '[aria-label*="photo"]',
                        '[aria-label*="Add photos"]',
                        '[aria-label*="Add Photos"]',
                    ]
                    for sel in photo_selectors:
                        photo_btn = await self.page.query_selector(sel)
                        if photo_btn and await photo_btn.is_visible():
                            await photo_btn.click()
                            await asyncio.sleep(2)
                            break

                    file_input = await self.page.query_selector('input[type="file"][accept*="image"]')
                    if not file_input:
                        file_input = await self.page.query_selector('input[type="file"]')
                    if file_input:
                        await file_input.set_input_files(image_path)
                        await asyncio.sleep(5)
                        print("  [FB] Image uploaded", flush=True)
                except Exception as e:
                    print(f"  [FB] Image upload failed (posting text-only): {e}", flush=True)

            # Find and click the Post button
            post_selectors = [
                '[aria-label="Post"][role="button"]',
                'div[role="button"]:has-text("Post")',
                'span:has-text("Post")',
                '[aria-label="Publish"]',
            ]

            for sel in post_selectors:
                try:
                    btns = await self.page.query_selector_all(sel)
                    for btn in btns:
                        if await btn.is_visible():
                            text = await btn.inner_text()
                            # Make sure it says "Post" not "Repost" or "Boost post"
                            if text.strip().lower() in ["post", "publish", "share"]:
                                await btn.click()
                                await asyncio.sleep(5)
                                print("  [FB] Post submitted!", flush=True)
                                return True
                except Exception:
                    continue

            # Last resort: press Ctrl+Enter to submit
            try:
                await self.page.keyboard.press("Control+Enter")
                await asyncio.sleep(5)
                print("  [FB] Post submitted via Ctrl+Enter", flush=True)
                return True
            except Exception:
                pass

            print("  [FB] Could not find Post button", flush=True)
            await self._save_debug_screenshot("no_post_button")
            return False

        except Exception as e:
            print(f"  [FB] Fill and submit error: {e}", flush=True)
            return False

    # ─────────────────────────────────────────
    # ENGAGEMENT: Comment on others' posts
    # ─────────────────────────────────────────

    async def _engage_with_posts(self, trends: dict) -> int:
        """Find and engage with relevant posts."""
        comments_posted = 0
        max_comments = min(3, FB_MAX_COMMENTS_PER_DAY - self.comments_today)

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
                comment_box = await self.page.query_selector(
                    '[aria-label*="Write a comment"][contenteditable="true"]'
                )

            if comment_box:
                await comment_box.click()
                await asyncio.sleep(1)
                await self.page.keyboard.type(comment_text, delay=30)
                await asyncio.sleep(1)
                await self.page.keyboard.press("Enter")
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
                result = await self._post_content(
                    trends={"content_ideas": []},
                    image_path=image_path,
                    override_caption=caption,
                    override_hashtags=hashtags or [],
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
