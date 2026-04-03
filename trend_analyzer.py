"""
Chicago Fleet Wraps — Multi-Platform Trend Analyzer v1.0
Scrapes trending content across Facebook, Instagram, TikTok, and the web
every hour to identify what's hot, what's getting engagement, and what
CFW should post about FIRST.

Targets:
- Car enthusiasts & vehicle owners
- Small business owners
- Fleet managers
- Large corporations with vehicle fleets
- New EV companies (Rivian, Lucid, Polestar, VinFast, Fisker, Scout, etc.)
- New car trends (launches, redesigns, color trends)
- Chicago local trends
"""
import os
import json
import time
import random
import asyncio
import requests
from datetime import datetime
from openai import OpenAI
from config import DATA_DIR, OPENAI_MODEL

base_url = os.environ.get("OPENAI_BASE_URL", None)
client = OpenAI(base_url=base_url) if base_url else OpenAI()

TRENDS_FILE = os.path.join(DATA_DIR, "current_trends.json")
TRENDS_HISTORY_FILE = os.path.join(DATA_DIR, "trends_history.json")

# ─────────────────────────────────────────────
# TARGET AUDIENCES & TOPICS
# ─────────────────────────────────────────────

AUDIENCE_SEGMENTS = {
    "car_enthusiasts": {
        "hashtags": [
            "carwrap", "vinylwrap", "colorchange", "carporn", "carsofinstagram",
            "wrappedcars", "wraplife", "carculture", "stancenation", "modifiedcars",
            "customcars", "carmod", "carlifestyle", "supercars", "exoticcars",
            "musclecar", "jdm", "eurocar", "americanmuscle", "carshow",
        ],
        "keywords": [
            "car wrap", "vinyl wrap", "color change", "custom car", "car mod",
            "vehicle wrap", "paint protection", "ppf", "ceramic coating",
        ],
        "fb_groups": [
            "Car Wrapping Worldwide", "Vinyl Wrap Community", "Wrap Society",
            "Custom Car Culture", "Car Enthusiasts United",
        ],
    },
    "small_business_owners": {
        "hashtags": [
            "smallbusiness", "entrepreneur", "businessowner", "startup",
            "sidehustle", "businessbranding", "vehiclebranding", "mobilebusiness",
            "foodtruck", "deliveryservice", "localBusiness", "chicagobusiness",
            "businessgrowth", "brandingtips", "marketingtips", "fleetmanagement",
        ],
        "keywords": [
            "fleet wrap", "business vehicle", "company van", "work truck",
            "vehicle branding", "mobile advertising", "fleet graphics",
            "commercial wrap", "box truck wrap", "sprinter van wrap",
        ],
        "fb_groups": [
            "Small Business Owners", "Entrepreneur Network",
            "Chicago Small Business Network", "Food Truck Owners",
            "Fleet Management Professionals", "Mobile Business Owners",
        ],
    },
    "fleet_managers": {
        "hashtags": [
            "fleetmanagement", "fleetmanager", "fleetvehicles", "logistics",
            "lastmiledelivery", "commercialvehicles", "fleetbranding",
            "fleetgraphics", "vehiclefleet", "fleetoperations",
            "transportationindustry", "truckfleet", "vanfleet",
        ],
        "keywords": [
            "fleet wrap", "fleet branding", "fleet graphics", "fleet vehicle",
            "fleet management", "vehicle fleet", "commercial fleet",
            "delivery fleet", "fleet discount", "bulk vehicle wrap",
        ],
        "fb_groups": [
            "Fleet Management Professionals", "Fleet Managers Network",
            "Commercial Vehicle Fleet Owners", "Logistics Professionals",
        ],
    },
    "corporate_accounts": {
        "hashtags": [
            "corporatebranding", "corporatefleet", "businessfleet",
            "companybranding", "corporateidentity", "brandedvehicles",
            "corporatevehicles", "businessmarketing", "b2bmarketing",
        ],
        "keywords": [
            "corporate fleet", "company branding", "corporate vehicle",
            "business fleet wrap", "enterprise fleet", "corporate graphics",
        ],
        "fb_groups": [
            "Corporate Fleet Management", "B2B Marketing Professionals",
            "Corporate Branding Strategies",
        ],
    },
    "ev_companies": {
        "hashtags": [
            "electricvehicle", "ev", "rivian", "tesla", "lucidmotors",
            "polestar", "vinfast", "fisker", "scout", "canoo",
            "electriccar", "evlife", "zeroemissions", "evcharging",
            "electrictruck", "evfleet", "electricvan", "evwrap",
            "rivianr1t", "rivianr1s", "cybertruck", "model3", "modely",
            "hummer_ev", "f150lightning", "chevyequinox", "ioniq5",
            "ioniq6", "ev6", "id4", "machE", "ariya",
        ],
        "keywords": [
            "rivian wrap", "tesla wrap", "ev wrap", "electric vehicle wrap",
            "cybertruck wrap", "lucid wrap", "polestar wrap", "ev fleet",
            "electric truck", "electric van", "ev delivery", "ev company",
        ],
        "fb_groups": [
            "Rivian Owners Club", "Rivian R1T R1S Owners",
            "Tesla Owners Club", "Electric Vehicle Owners",
            "EV Fleet Management", "Cybertruck Owners Club",
        ],
    },
    "new_car_trends": {
        "hashtags": [
            "newcar", "2025cars", "2026cars", "carlaunch", "newrelease",
            "automotivetrends", "cartrends", "colortrends", "mattewrap",
            "satinwrap", "chromelete", "pearlwrap", "colorshift",
            "iridescent", "matteblack", "satinblack", "nardogray",
            "miamiblue", "urbanautomotive", "cardesign",
        ],
        "keywords": [
            "new car 2026", "car launch", "new model", "redesign",
            "color trend", "matte wrap", "satin wrap", "chrome delete",
            "new vehicle", "concept car", "auto show",
        ],
        "fb_groups": [
            "New Car Releases", "Automotive News & Trends",
            "Car Design & Trends", "Auto Show Enthusiasts",
        ],
    },
    "chicago_local": {
        "hashtags": [
            "chicago", "chicagoland", "chitown", "windycity",
            "chicagocars", "chicagocarscene", "chicagoauto",
            "chicagobusiness", "chicagoentrepreneur", "portagepark",
            "chicagolife", "explorechicago", "chicagoevents",
        ],
        "keywords": [
            "chicago car", "chicago wrap", "chicago business",
            "chicago fleet", "chicago auto", "chicagoland",
        ],
        "fb_groups": [
            "Chicago Car Enthusiasts", "Cars of Chicago",
            "Chicago Small Business Network", "Chicago Area Car Club",
        ],
    },
}

# Accounts to monitor for trends on each platform
MONITOR_ACCOUNTS = {
    "instagram": [
        "rivian", "teslamotors", "lucidmotors", "polestar",
        "3mautofilm", "averydennison", "xpeltech",
        "wrapstronaut", "ckwraps", "inozetek",
        "chicagofleetwraps",  # monitor ourselves too
    ],
    "tiktok": [
        "rivian", "tesla", "carwraptok", "wraplife",
        "chicagofleetwraps",
    ],
}

# News sources to check for trending car/EV/business news
NEWS_SEARCH_QUERIES = [
    "new electric vehicle launch 2026",
    "new car model reveal",
    "vehicle wrap industry trends",
    "fleet management news",
    "Rivian news",
    "Tesla news",
    "Chicago business news",
    "commercial vehicle trends",
    "EV delivery fleet",
    "car color trends 2026",
    "auto show news",
    "vehicle branding trends",
]


class TrendAnalyzer:
    """Analyzes trends across platforms to determine what to post about."""

    def __init__(self):
        self.current_trends = self._load_trends()
        self.browser = None
        self.page = None

    def _load_trends(self) -> dict:
        """Load current trends from file."""
        if os.path.exists(TRENDS_FILE):
            try:
                with open(TRENDS_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"last_updated": None, "trends": [], "hot_topics": [], "content_ideas": []}

    def _save_trends(self):
        """Save current trends to file."""
        os.makedirs(DATA_DIR, exist_ok=True)
        self.current_trends["last_updated"] = datetime.now().isoformat()
        with open(TRENDS_FILE, "w") as f:
            json.dump(self.current_trends, f, indent=2)

        # Also append to history
        history = []
        if os.path.exists(TRENDS_HISTORY_FILE):
            try:
                with open(TRENDS_HISTORY_FILE, "r") as f:
                    history = json.load(f)
            except Exception:
                history = []

        history.append({
            "timestamp": datetime.now().isoformat(),
            "top_trends": self.current_trends.get("trends", [])[:5],
            "content_ideas_count": len(self.current_trends.get("content_ideas", [])),
        })
        history = history[-168:]  # Keep 7 days of hourly snapshots
        with open(TRENDS_HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=2)

    async def run_full_analysis(self):
        """Run a complete trend analysis across all sources."""
        print(f"\n{'='*60}", flush=True)
        print(f"  [TRENDS] Starting hourly trend analysis — {datetime.now().strftime('%I:%M %p')}", flush=True)

        all_signals = []

        # 1. Scrape Instagram trending hashtags and posts
        ig_signals = await self._analyze_instagram_trends()
        all_signals.extend(ig_signals)

        # 2. Scrape TikTok trending content
        tt_signals = await self._analyze_tiktok_trends()
        all_signals.extend(tt_signals)

        # 3. Scrape Facebook group activity
        fb_signals = await self._analyze_facebook_trends()
        all_signals.extend(fb_signals)

        # 4. Check news for trending car/EV/business stories
        news_signals = await self._analyze_news_trends()
        all_signals.extend(news_signals)

        # 5. Use AI to synthesize all signals into actionable content ideas
        content_plan = await self._synthesize_trends(all_signals)

        # Save everything
        self.current_trends = {
            "last_updated": datetime.now().isoformat(),
            "trends": all_signals[:50],
            "hot_topics": content_plan.get("hot_topics", []),
            "content_ideas": content_plan.get("content_ideas", []),
            "platform_specific": content_plan.get("platform_specific", {}),
            "audience_opportunities": content_plan.get("audience_opportunities", []),
        }
        self._save_trends()

        print(f"  [TRENDS] Analysis complete. Found {len(all_signals)} signals, "
              f"generated {len(content_plan.get('content_ideas', []))} content ideas.", flush=True)

        return self.current_trends

    async def _analyze_instagram_trends(self) -> list:
        """Analyze trending content on Instagram."""
        signals = []
        print(f"  [TRENDS] Analyzing Instagram trends...", flush=True)

        try:
            from playwright.async_api import async_playwright
            pw = await async_playwright().start()

            try:
                browser = await pw.chromium.connect_over_cdp("http://localhost:9222")
                context = browser.contexts[0] if browser.contexts else await browser.new_context()
                page = await context.new_page()
            except Exception:
                browser = await pw.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
                )
                page = await context.new_page()

            # Check trending hashtags from each audience segment
            for segment_name, segment in list(AUDIENCE_SEGMENTS.items())[:4]:
                hashtags = random.sample(segment["hashtags"], min(3, len(segment["hashtags"])))
                for tag in hashtags:
                    try:
                        await page.goto(f"https://www.instagram.com/explore/tags/{tag}/",
                                       wait_until="domcontentloaded", timeout=15000)
                        await asyncio.sleep(3)

                        # Extract post count and top post data
                        content = await page.content()
                        text = await page.inner_text("body")

                        if text and len(text) > 50:
                            signals.append({
                                "platform": "instagram",
                                "type": "hashtag_trend",
                                "topic": tag,
                                "audience": segment_name,
                                "content_preview": text[:300],
                                "timestamp": datetime.now().isoformat(),
                            })
                    except Exception:
                        continue

            # Check monitored accounts for recent posts
            for account in random.sample(MONITOR_ACCOUNTS["instagram"], min(3, len(MONITOR_ACCOUNTS["instagram"]))):
                try:
                    await page.goto(f"https://www.instagram.com/{account}/",
                                   wait_until="domcontentloaded", timeout=15000)
                    await asyncio.sleep(3)
                    text = await page.inner_text("body")
                    if text:
                        signals.append({
                            "platform": "instagram",
                            "type": "account_activity",
                            "account": account,
                            "content_preview": text[:300],
                            "timestamp": datetime.now().isoformat(),
                        })
                except Exception:
                    continue

            await page.close()

        except Exception as e:
            print(f"  [TRENDS] Instagram analysis error: {e}", flush=True)

        print(f"  [TRENDS] Instagram: {len(signals)} signals", flush=True)
        return signals

    async def _analyze_tiktok_trends(self) -> list:
        """Analyze trending content on TikTok."""
        signals = []
        print(f"  [TRENDS] Analyzing TikTok trends...", flush=True)

        try:
            from playwright.async_api import async_playwright
            pw = await async_playwright().start()

            try:
                browser = await pw.chromium.connect_over_cdp("http://localhost:9222")
                context = browser.contexts[0] if browser.contexts else await browser.new_context()
                page = await context.new_page()
            except Exception:
                browser = await pw.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
                )
                page = await context.new_page()

            # Check trending topics on TikTok
            for segment_name, segment in list(AUDIENCE_SEGMENTS.items())[:3]:
                keywords = random.sample(segment["keywords"], min(2, len(segment["keywords"])))
                for kw in keywords:
                    try:
                        search_url = f"https://www.tiktok.com/search?q={kw.replace(' ', '%20')}"
                        await page.goto(search_url, wait_until="domcontentloaded", timeout=15000)
                        await asyncio.sleep(5)

                        text = await page.inner_text("body")
                        if text and len(text) > 50:
                            signals.append({
                                "platform": "tiktok",
                                "type": "search_trend",
                                "topic": kw,
                                "audience": segment_name,
                                "content_preview": text[:300],
                                "timestamp": datetime.now().isoformat(),
                            })
                    except Exception:
                        continue

            # Check TikTok explore/trending
            try:
                await page.goto("https://www.tiktok.com/explore", wait_until="domcontentloaded", timeout=15000)
                await asyncio.sleep(5)
                text = await page.inner_text("body")
                if text:
                    signals.append({
                        "platform": "tiktok",
                        "type": "explore_trending",
                        "content_preview": text[:500],
                        "timestamp": datetime.now().isoformat(),
                    })
            except Exception:
                pass

            await page.close()

        except Exception as e:
            print(f"  [TRENDS] TikTok analysis error: {e}", flush=True)

        print(f"  [TRENDS] TikTok: {len(signals)} signals", flush=True)
        return signals

    async def _analyze_facebook_trends(self) -> list:
        """Analyze trending content on Facebook groups."""
        signals = []
        print(f"  [TRENDS] Analyzing Facebook trends...", flush=True)

        try:
            from playwright.async_api import async_playwright
            pw = await async_playwright().start()

            try:
                browser = await pw.chromium.connect_over_cdp("http://localhost:9222")
                context = browser.contexts[0] if browser.contexts else await browser.new_context()
                page = await context.new_page()
            except Exception:
                browser = await pw.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()

            # Check Facebook for trending topics
            for segment_name, segment in list(AUDIENCE_SEGMENTS.items())[:3]:
                keywords = random.sample(segment["keywords"], min(2, len(segment["keywords"])))
                for kw in keywords:
                    try:
                        search_url = f"https://www.facebook.com/search/posts/?q={kw.replace(' ', '%20')}"
                        await page.goto(search_url, wait_until="domcontentloaded", timeout=15000)
                        await asyncio.sleep(5)

                        text = await page.inner_text("body")
                        if text and len(text) > 50:
                            signals.append({
                                "platform": "facebook",
                                "type": "search_trend",
                                "topic": kw,
                                "audience": segment_name,
                                "content_preview": text[:300],
                                "timestamp": datetime.now().isoformat(),
                            })
                    except Exception:
                        continue

            await page.close()

        except Exception as e:
            print(f"  [TRENDS] Facebook analysis error: {e}", flush=True)

        print(f"  [TRENDS] Facebook: {len(signals)} signals", flush=True)
        return signals

    async def _analyze_news_trends(self) -> list:
        """Check news sources for trending car/EV/business stories."""
        signals = []
        print(f"  [TRENDS] Analyzing news trends...", flush=True)

        # Use Google News RSS or search for trending stories
        queries = random.sample(NEWS_SEARCH_QUERIES, min(4, len(NEWS_SEARCH_QUERIES)))

        for query in queries:
            try:
                # Use Google News search
                url = f"https://news.google.com/search?q={query.replace(' ', '%20')}&hl=en-US&gl=US&ceid=US:en"
                headers = {
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
                }
                resp = requests.get(url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    # Extract headlines from the page
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(resp.text, "html.parser")
                    articles = soup.find_all("article")
                    for article in articles[:3]:
                        headline = article.get_text()[:200]
                        if headline:
                            signals.append({
                                "platform": "news",
                                "type": "news_headline",
                                "topic": query,
                                "headline": headline,
                                "timestamp": datetime.now().isoformat(),
                            })
            except Exception:
                continue

        print(f"  [TRENDS] News: {len(signals)} signals", flush=True)
        return signals

    async def _synthesize_trends(self, signals: list) -> dict:
        """Use AI to synthesize all trend signals into actionable content ideas."""
        if not signals:
            return self._get_default_content_plan()

        # Build a summary of all signals for the AI
        signal_summary = []
        for s in signals[:30]:
            platform = s.get("platform", "")
            topic = s.get("topic", s.get("headline", s.get("account", "")))
            audience = s.get("audience", "general")
            preview = s.get("content_preview", "")[:100]
            signal_summary.append(f"[{platform}] ({audience}) {topic}: {preview}")

        signals_text = "\n".join(signal_summary)

        prompt = f"""You are a social media strategist for Chicago Fleet Wraps, a vehicle wrap shop in Chicago.

Analyze these trending signals from across social media and news:

{signals_text}

Based on these trends, generate a content plan. Return ONLY valid JSON:

{{
    "hot_topics": [
        "topic 1 that's trending right now",
        "topic 2",
        "topic 3"
    ],
    "content_ideas": [
        {{
            "title": "Post title/hook",
            "platform": "instagram|facebook|tiktok|all",
            "content_type": "image|video|carousel|text",
            "caption": "The caption/text for the post",
            "image_prompt": "Detailed prompt for AI image generation — describe the exact image to create",
            "audience": "car_enthusiasts|small_business|fleet_managers|corporate|ev_owners|chicago_local",
            "urgency": "high|medium|low",
            "hashtags": ["tag1", "tag2", "tag3"],
            "reasoning": "Why this will perform well right now"
        }}
    ],
    "platform_specific": {{
        "instagram": "What type of content is trending on IG right now",
        "facebook": "What type of content is trending on FB right now",
        "tiktok": "What type of content is trending on TikTok right now"
    }},
    "audience_opportunities": [
        "Specific opportunity to reach fleet managers",
        "Specific opportunity to reach EV owners"
    ]
}}

RULES:
- Generate 6-10 content ideas covering different audiences and platforms
- At least 2 ideas should target small business owners or fleet managers
- At least 2 ideas should be about EVs or new car trends
- At least 1 idea should be Chicago-specific
- Image prompts should be detailed and specific — describe the vehicle, wrap style, setting, lighting
- Captions should sound natural, not corporate. Use the platform's native voice.
- For TikTok, think short-form video concepts
- For Instagram, think visually stunning images and carousels
- For Facebook, think informative posts that spark discussion
- Include trending topics that CFW can ride the wave of
- HIGH urgency = post within the hour (breaking news, viral trend)
- MEDIUM urgency = post today
- LOW urgency = can wait, evergreen content"""

        try:
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                max_tokens=2000,
            )
            result = response.choices[0].message.content.strip()
            if result.startswith("```"):
                result = result.split("```")[1]
                if result.startswith("json"):
                    result = result[4:]
            return json.loads(result.strip())
        except Exception as e:
            print(f"  [TRENDS] AI synthesis error: {e}", flush=True)
            return self._get_default_content_plan()

    def _get_default_content_plan(self) -> dict:
        """Fallback content plan when trend analysis fails."""
        return {
            "hot_topics": ["vehicle wraps", "fleet branding", "EV wraps"],
            "content_ideas": [
                {
                    "title": "Transform your fleet's image",
                    "platform": "all",
                    "content_type": "image",
                    "caption": "Your fleet is your billboard. Make it count.",
                    "image_prompt": "Professional fleet of white commercial vans with sleek blue and orange branded wraps, parked in a row in front of a modern Chicago building, golden hour lighting, cinematic composition",
                    "audience": "fleet_managers",
                    "urgency": "medium",
                    "hashtags": ["fleetwrap", "vehiclebranding", "chicago"],
                    "reasoning": "Evergreen fleet content always performs",
                },
            ],
            "platform_specific": {
                "instagram": "Visual transformation content",
                "facebook": "Informative business content",
                "tiktok": "Short-form video trends",
            },
            "audience_opportunities": [
                "Fleet managers looking for Q2 branding refresh",
                "EV owners wanting to personalize their vehicles",
            ],
        }

    def get_next_content_idea(self, platform: str = None) -> dict:
        """Get the next content idea to post, optionally filtered by platform."""
        ideas = self.current_trends.get("content_ideas", [])
        if not ideas:
            self.current_trends = self._load_trends()
            ideas = self.current_trends.get("content_ideas", [])

        if not ideas:
            return self._get_default_content_plan()["content_ideas"][0]

        # Filter by platform if specified
        if platform:
            platform_ideas = [i for i in ideas if i.get("platform") in (platform, "all")]
            if platform_ideas:
                # Prioritize by urgency
                high = [i for i in platform_ideas if i.get("urgency") == "high"]
                if high:
                    return high[0]
                medium = [i for i in platform_ideas if i.get("urgency") == "medium"]
                if medium:
                    return random.choice(medium)
                return random.choice(platform_ideas)

        # No platform filter — return highest urgency
        high = [i for i in ideas if i.get("urgency") == "high"]
        if high:
            return high[0]
        return random.choice(ideas)

    def analyze_all(self) -> dict:
        """Synchronous wrapper for run_full_analysis() — called by master.py."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    result = pool.submit(asyncio.run, self.run_full_analysis()).result()
                return result
            else:
                return loop.run_until_complete(self.run_full_analysis())
        except RuntimeError:
            return asyncio.run(self.run_full_analysis())

    def get_dashboard_data(self) -> dict:
        """Get trend data for the dashboard."""
        return {
            "last_updated": self.current_trends.get("last_updated"),
            "hot_topics": self.current_trends.get("hot_topics", []),
            "content_ideas_count": len(self.current_trends.get("content_ideas", [])),
            "platform_insights": self.current_trends.get("platform_specific", {}),
            "audience_opportunities": self.current_trends.get("audience_opportunities", []),
        }


async def run_trend_analysis():
    """Entry point for running a trend analysis cycle."""
    analyzer = TrendAnalyzer()
    result = await analyzer.run_full_analysis()
    return result


if __name__ == "__main__":
    result = asyncio.run(run_trend_analysis())
    print(f"\nTrends found: {len(result.get('trends', []))}")
    print(f"Content ideas: {len(result.get('content_ideas', []))}")
    for idea in result.get("content_ideas", [])[:3]:
        print(f"  - [{idea.get('urgency')}] {idea.get('title')} ({idea.get('platform')})")
