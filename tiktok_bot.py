"""
Chicago Fleet Wraps — TikTok Bot v1.0
FULL CONTENT MACHINE: Posts videos, comments on trending content, tracks engagement.

Every hour:
1. Gets content decision from the brain
2. Posts video content (AI-generated) to CFW TikTok
3. Engages with relevant videos (comments)
4. Tracks engagement for self-improvement

Uses Playwright browser automation via TikTok web.
"""
import os
import json
import random
import asyncio
from datetime import datetime
from config import DATA_DIR, OPENAI_MODEL, BUSINESS_CONTEXT
from content_brain import get_brain

TT_POST_LOG = os.path.join(DATA_DIR, "tt_post_history.json")
TT_COMMENT_LOG = os.path.join(DATA_DIR, "tt_comment_history.json")
TT_DAILY_LOG = os.path.join(DATA_DIR, "tt_daily_activity.json")

TT_MAX_POSTS_PER_DAY = 4
TT_MAX_COMMENTS_PER_DAY = 25
TT_MIN_DELAY_SECONDS = 60
TT_MAX_DELAY_SECONDS = 180

# Search terms for finding relevant videos to comment on
TT_SEARCH_TERMS = [
    "car wrap", "vinyl wrap", "vehicle wrap", "color change wrap",
    "truck wrap", "van wrap", "fleet wrap", "matte black car",
    "satin wrap", "chrome delete", "ppf", "paint protection film",
    "Rivian", "Tesla wrap", "Cybertruck wrap", "new car delivery",
    "food truck", "small business vehicle", "fleet branding",
    "car transformation", "wrap reveal", "before and after wrap",
    "Chicago cars", "car detailing", "auto body",
    "EV wrap", "electric vehicle", "car mod",
]


class TikTokBot:
    """TikTok content machine using Playwright browser automation."""

    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.brain = get_brain()
        self.posts_today = 0
        self.comments_today = 0
        self._load_daily_state()

    def _load_daily_state(self):
        if os.path.exists(TT_DAILY_LOG):
            try:
                with open(TT_DAILY_LOG, "r") as f:
                    data = json.load(f)
                if data.get("date") == datetime.now().strftime("%Y-%m-%d"):
                    self.posts_today = data.get("posts", 0)
                    self.comments_today = data.get("comments", 0)
            except Exception:
                pass

    def _save_daily_state(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(TT_DAILY_LOG, "w") as f:
            json.dump({
                "date": datetime.now().strftime("%Y-%m-%d"),
                "posts": self.posts_today,
                "comments": self.comments_today,
            }, f)

    async def start(self):
        """Launch browser with restored TikTok session cookies."""
        from browser_launcher import launch_browser
        self._pw, self.browser, self.context, self.page = await launch_browser("tiktok")
        print("  [TT] Browser started with restored session", flush=True)

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
    # MAIN CYCLE
    # ─────────────────────────────────────────

    async def run_cycle(self, trends: dict = None, generated_video_path: str = None):
        """Run one full TikTok cycle."""
        print(f"\n{'='*50}", flush=True)
        print(f"  [TT] Starting cycle — Posts: {self.posts_today}/{TT_MAX_POSTS_PER_DAY}, "
              f"Comments: {self.comments_today}/{TT_MAX_COMMENTS_PER_DAY}", flush=True)

        results = {"posts": 0, "comments": 0, "status": "complete"}

        try:
            await self.page.goto("https://www.tiktok.com/", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(5)

            # Dismiss any popups
            try:
                cookie_btn = await self.page.query_selector('button:has-text("Accept")')
                if cookie_btn:
                    await cookie_btn.click()
                    await asyncio.sleep(1)
            except Exception:
                pass

            # PHASE 1: Post video content
            if self.posts_today < TT_MAX_POSTS_PER_DAY and generated_video_path:
                post_result = await self._post_content(trends, generated_video_path)
                if post_result:
                    results["posts"] = 1
                    self.posts_today += 1
                    self._save_daily_state()

            # PHASE 2: Engage with relevant videos
            if self.comments_today < TT_MAX_COMMENTS_PER_DAY:
                comments = await self._engage_with_videos()
                results["comments"] = comments
                self.comments_today += comments
                self._save_daily_state()

        except Exception as e:
            print(f"  [TT] Cycle error: {e}", flush=True)
            results["status"] = f"error: {str(e)[:100]}"

        print(f"  [TT] Cycle done. Posted {results['posts']}, commented {results['comments']}", flush=True)
        return results

    # ─────────────────────────────────────────
    # POSTING
    # ─────────────────────────────────────────

    async def _post_content(self, trends: dict, video_path: str,
                            override_caption: str = "", override_hashtags: list = None) -> bool:
        """Post video content to TikTok."""
        try:
            if override_caption:
                caption = override_caption
                hashtags = override_hashtags or []
            else:
                decision = self.brain.decide_next_post("tiktok", trends)
                caption = decision.get("caption", "")
                hashtags = decision.get("hashtags", [])

            # TikTok: hashtags go in the caption
            if hashtags:
                caption += " " + " ".join(f"#{tag}" for tag in hashtags[:10])

            print(f"  [TT] Posting: {caption[:80]}...", flush=True)

            # Navigate to TikTok upload page
            await self.page.goto("https://www.tiktok.com/upload", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(5)

            # Find file input for video upload
            file_input = await self.page.query_selector('input[type="file"]')
            if file_input and video_path and os.path.exists(video_path):
                await file_input.set_input_files(video_path)
                await asyncio.sleep(10)  # Wait for upload

                # Find caption/description input
                caption_area = await self.page.query_selector(
                    '[contenteditable="true"], textarea[placeholder*="caption"], '
                    'div[data-placeholder*="caption"]'
                )
                if caption_area:
                    await caption_area.click()
                    # Clear existing text
                    await self.page.keyboard.press("Control+a")
                    await asyncio.sleep(0.5)
                    await caption_area.fill(caption)
                    await asyncio.sleep(2)

                # Click Post button
                post_btn = await self.page.query_selector(
                    'button:has-text("Post"), button[data-e2e="post-button"]'
                )
                if post_btn:
                    await post_btn.click()
                    await asyncio.sleep(8)
                    print(f"  [TT] Posted successfully", flush=True)

                    self.brain.record_post({
                        "id": f"tt_{int(datetime.now().timestamp())}",
                        "platform": "tiktok",
                        "content_type": "video",
                        "topic": decision.get("topic", ""),
                        "audience": decision.get("audience", ""),
                        "caption": caption[:200],
                        "wrappable_target": decision.get("wrappable_target", ""),
                        "campaign": decision.get("campaign", ""),
                    })

                    self._log_post(decision, caption)
                    return True

            print(f"  [TT] Could not upload video", flush=True)
            return False

        except Exception as e:
            print(f"  [TT] Post error: {e}", flush=True)
            return False

    # ─────────────────────────────────────────
    # ENGAGEMENT: Comment on relevant videos
    # ─────────────────────────────────────────

    async def _engage_with_videos(self) -> int:
        """Search for relevant videos and comment on them."""
        comments_posted = 0
        max_comments = min(5, TT_MAX_COMMENTS_PER_DAY - self.comments_today)

        # Pick search terms
        search_terms = random.sample(TT_SEARCH_TERMS, min(3, len(TT_SEARCH_TERMS)))

        for term in search_terms:
            if comments_posted >= max_comments:
                break

            try:
                # Search for videos
                search_url = f"https://www.tiktok.com/search?q={term.replace(' ', '%20')}"
                await self.page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
                await asyncio.sleep(5)

                # Find video cards
                video_cards = await self.page.query_selector_all(
                    '[data-e2e="search_top-item"], [class*="DivItemCard"], '
                    'div[class*="video-feed"] > div'
                )

                for card in random.sample(list(video_cards[:10]), min(2, len(video_cards))):
                    if comments_posted >= max_comments:
                        break

                    try:
                        # Click on the video
                        await card.click()
                        await asyncio.sleep(5)

                        # Read the video description
                        desc_elem = await self.page.query_selector(
                            '[data-e2e="browse-video-desc"], [class*="SpanText"], '
                            'span[class*="tiktok-j2a19r"]'
                        )
                        desc_text = ""
                        if desc_elem:
                            desc_text = await desc_elem.inner_text()

                        # Read existing comments for context
                        existing_comments = []
                        comment_elems = await self.page.query_selector_all(
                            '[data-e2e="comment-level-1"] [data-e2e="comment-text"], '
                            '[class*="CommentText"]'
                        )
                        for ce in comment_elems[:5]:
                            try:
                                ct = await ce.inner_text()
                                if ct:
                                    existing_comments.append(ct[:100])
                            except Exception:
                                continue

                        # Get strategy from brain
                        strategy = self.brain.decide_comment_strategy(
                            {"text": desc_text[:300]}, "tiktok"
                        )

                        # Generate comment
                        comment_text = self._generate_tt_comment(
                            desc_text[:200], existing_comments, strategy, term
                        )

                        if comment_text:
                            # Find comment input
                            comment_input = await self.page.query_selector(
                                '[data-e2e="comment-input"], [contenteditable="true"], '
                                'div[class*="DivInputArea"] [contenteditable]'
                            )

                            if comment_input:
                                await comment_input.click()
                                await asyncio.sleep(1)
                                await comment_input.fill(comment_text)
                                await asyncio.sleep(1)

                                # Post comment
                                post_btn = await self.page.query_selector(
                                    '[data-e2e="comment-post"], button:has-text("Post")'
                                )
                                if post_btn:
                                    await post_btn.click()
                                    await asyncio.sleep(3)
                                    comments_posted += 1
                                    print(f"  [TT] Commented on '{term}': {comment_text[:50]}...", flush=True)
                                    self._log_comment(term, desc_text[:100], comment_text, strategy.get("mention_cfw", False))

                        # Go back
                        await self.page.go_back()
                        await asyncio.sleep(3)

                        # Delay
                        delay = random.randint(TT_MIN_DELAY_SECONDS, TT_MAX_DELAY_SECONDS)
                        await asyncio.sleep(delay)

                    except Exception as e:
                        print(f"  [TT] Video comment error: {e}", flush=True)
                        try:
                            await self.page.go_back()
                            await asyncio.sleep(2)
                        except Exception:
                            pass
                        continue

            except Exception as e:
                print(f"  [TT] Search error: {e}", flush=True)
                continue

        return comments_posted

    def _generate_tt_comment(self, desc: str, existing_comments: list,
                              strategy: dict, search_term: str) -> str:
        """Generate a TikTok comment — short, punchy, platform-native."""
        from openai import OpenAI
        base_url = os.environ.get("OPENAI_BASE_URL", None)
        ai_client = OpenAI(base_url=base_url) if base_url else OpenAI()

        mention_cfw = strategy.get("mention_cfw", False)

        existing_block = ""
        if existing_comments:
            existing_block = "\nTop comments:\n" + "\n".join(f"  - {c}" for c in existing_comments[:3])

        if mention_cfw:
            system = f"""You're @chicagofleetwraps commenting on TikTok.
Be helpful and real. If they're looking for a wrap shop, mention you're in Chicago.
TikTok voice: short, direct, slightly casual.
Max 20 words. No emojis. No "follow us!" No corporate speak."""
        else:
            system = """You're commenting on a TikTok video about cars/wraps/vehicles.
TikTok comments that get likes are: funny, insightful, or ask a good question.
Study the existing comments and match that energy.
Max 15 words. No emojis. Be real, not generic.
Don't say "fire" or "sick" or "W" — those are played out."""

        prompt = f"""Video about: {desc[:150]}
Search context: {search_term}
{existing_block}

Write a TikTok comment. ONLY the comment text."""

        try:
            response = ai_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                temperature=1.0,
                max_tokens=40,
            )
            return response.choices[0].message.content.strip().strip('"').strip("'")
        except Exception as e:
            print(f"  [TT] AI error: {e}", flush=True)
            return ""

    # ─────────────────────────────────────────
    # LOGGING
    # ─────────────────────────────────────────

    def _log_post(self, decision: dict, caption: str):
        os.makedirs(DATA_DIR, exist_ok=True)
        log = []
        if os.path.exists(TT_POST_LOG):
            try:
                with open(TT_POST_LOG, "r") as f:
                    log = json.load(f)
            except Exception:
                log = []

        log.append({
            "date": datetime.now().isoformat(),
            "platform": "tiktok",
            "topic": decision.get("topic", ""),
            "caption": caption[:300],
            "audience": decision.get("audience", ""),
            "campaign": decision.get("campaign", ""),
        })
        log = log[-500:]
        with open(TT_POST_LOG, "w") as f:
            json.dump(log, f, indent=2)

    def _log_comment(self, search_term: str, video_desc: str, comment: str, is_promo: bool):
        os.makedirs(DATA_DIR, exist_ok=True)
        log = []
        if os.path.exists(TT_COMMENT_LOG):
            try:
                with open(TT_COMMENT_LOG, "r") as f:
                    log = json.load(f)
            except Exception:
                log = []

        log.append({
            "date": datetime.now().isoformat(),
            "platform": "tiktok",
            "search_term": search_term,
            "video_desc": video_desc[:100],
            "comment": comment,
            "is_promo": is_promo,
        })
        log = log[-500:]
        with open(TT_COMMENT_LOG, "w") as f:
            json.dump(log, f, indent=2)

    def get_dashboard_data(self) -> dict:
        posts, comments = [], []
        if os.path.exists(TT_POST_LOG):
            try:
                with open(TT_POST_LOG, "r") as f:
                    posts = json.load(f)
            except Exception:
                pass
        if os.path.exists(TT_COMMENT_LOG):
            try:
                with open(TT_COMMENT_LOG, "r") as f:
                    comments = json.load(f)
            except Exception:
                pass

        return {
            "platform": "tiktok",
            "total_posts": len(posts),
            "total_comments": len(comments),
            "today_posts": self.posts_today,
            "today_comments": self.comments_today,
            "recent_posts": posts[-5:],
            "recent_comments": comments[-5:],
        }


    def create_post(self, caption: str = "", hashtags: list = None,
                    media_path: str = None) -> dict:
        """Synchronous wrapper to create a post — called by master.py."""
        async def _do_post():
            await self.start()
            try:
                # Generate video from branded image if no media provided
                vid = media_path
                if not vid or not os.path.exists(str(vid)):
                    from media_generator import generate_branded_image, _generate_image_content, create_slideshow_video
                    decision = {"topic": "vehicle wraps", "caption": caption}
                    headline, subtext = _generate_image_content(decision)
                    img = generate_branded_image(headline, subtext)
                    if img:
                        vid = create_slideshow_video(img, caption)
                        print(f"  [TT] Generated video from branded image: {vid}", flush=True)
                result = await self._post_content(
                    trends={"content_ideas": []},
                    video_path=vid or "",
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
                count = await self._engage_with_videos()
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


async def run_tiktok_cycle(trends: dict = None, video_path: str = None):
    bot = TikTokBot()
    try:
        await bot.start()
        return await bot.run_cycle(trends, video_path)
    finally:
        await bot.stop()
