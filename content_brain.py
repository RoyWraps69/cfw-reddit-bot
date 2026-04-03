"""
Chicago Fleet Wraps — Content Strategy Brain v1.0
THE ENGAGEMENT TASK FORCE

This is the brain that decides:
1. WHAT to post (based on trend analysis + performance data)
2. WHERE to post (which platform, which audience)
3. HOW to post (what style, length, media type)
4. WHEN to pivot (if something isn't working, change it up NEXT post)

Self-improving loop:
- Every post gets tracked for engagement (likes, comments, shares, views)
- After each cycle, the brain reviews what worked and what didn't
- If a targeting strategy is working → double down
- If it's NOT working → change up with the NEXT post
- Learns which audiences, topics, formats, and times perform best

WRAPPABLE TARGETS — everything that can be wrapped, we target:
- Cars, trucks, SUVs, vans, buses
- Commercial fleets (delivery, service, sales)
- Food trucks, ice cream trucks, mobile businesses
- Boats, jet skis, ATVs, motorcycles
- Trailers, box trucks, semi trucks
- Electric vehicles (Rivian, Tesla, Lucid, etc.)
- Race cars, show cars, project cars
- Company vehicles, corporate fleets
- Government vehicles, municipal fleets
- Rideshare vehicles (Uber, Lyft)
- RVs, campers, motorhomes
- Construction equipment, heavy machinery
- Ambulances, fire trucks (graphics)
- Airport shuttles, hotel shuttles
- Moving trucks, rental fleets
"""
import os
import json
import random
from datetime import datetime, timedelta
from openai import OpenAI
from config import BUSINESS_CONTEXT, OPENAI_MODEL, DATA_DIR

base_url = os.environ.get("OPENAI_BASE_URL", None)
client = OpenAI(base_url=base_url) if base_url else OpenAI()

STRATEGY_FILE = os.path.join(DATA_DIR, "content_strategy.json")
PERFORMANCE_FILE = os.path.join(DATA_DIR, "post_performance.json")
LEARNING_FILE = os.path.join(DATA_DIR, "strategy_learnings.json")

# ─────────────────────────────────────────────
# WRAPPABLE UNIVERSE — Everything we can target
# ─────────────────────────────────────────────
WRAPPABLE_TARGETS = {
    "personal_vehicles": {
        "items": ["sedan", "coupe", "SUV", "crossover", "hatchback", "convertible",
                  "sports car", "luxury car", "exotic car", "muscle car", "JDM car"],
        "angles": ["color change", "custom design", "paint protection", "resale value",
                   "personalization", "unique look", "head turner"],
        "audiences": ["car_enthusiasts", "new_car_owners"],
    },
    "trucks_suvs": {
        "items": ["pickup truck", "F-150", "RAM", "Silverado", "Tacoma", "Tundra",
                  "Jeep Wrangler", "Bronco", "4Runner", "full-size SUV"],
        "angles": ["rugged look", "off-road style", "matte finish", "camo wrap",
                   "work truck branding", "weekend warrior"],
        "audiences": ["truck_owners", "outdoor_enthusiasts"],
    },
    "electric_vehicles": {
        "items": ["Tesla Model 3", "Tesla Model Y", "Tesla Model S", "Tesla Model X",
                  "Cybertruck", "Rivian R1T", "Rivian R1S", "Rivian delivery van",
                  "Lucid Air", "Polestar 2", "Polestar 3", "BMW iX", "BMW i4",
                  "Mercedes EQS", "Mercedes EQE", "Hyundai Ioniq 5", "Ioniq 6",
                  "Kia EV6", "Kia EV9", "Ford Mustang Mach-E", "F-150 Lightning",
                  "Chevy Equinox EV", "Chevy Blazer EV", "VW ID.4", "Nissan Ariya",
                  "Cadillac Lyriq", "Hummer EV", "Scout Terra", "Scout Traveler",
                  "Fisker Ocean", "Canoo", "Aptera"],
        "angles": ["protect factory paint", "personalize without voiding warranty",
                   "EV color options are limited", "stand out at the charger",
                   "PPF for EV paint", "matte wrap on EV"],
        "audiences": ["ev_owners", "tech_enthusiasts", "early_adopters"],
    },
    "commercial_fleets": {
        "items": ["delivery van", "cargo van", "Sprinter van", "Transit van",
                  "ProMaster van", "box truck", "straight truck", "step van",
                  "service truck", "utility truck", "work van"],
        "angles": ["mobile billboard", "brand visibility", "professional image",
                   "fleet consistency", "tax deduction", "section 179",
                   "fleet discount", "bulk pricing", "ROI of fleet wraps"],
        "audiences": ["small_business", "fleet_managers", "corporate"],
    },
    "food_mobile_business": {
        "items": ["food truck", "ice cream truck", "coffee truck", "taco truck",
                  "mobile kitchen", "catering van", "mobile bar", "pop-up shop vehicle",
                  "mobile pet grooming van", "mobile detailing van", "mobile mechanic"],
        "angles": ["attract customers", "menu display", "brand recognition",
                   "Instagram-worthy", "stand out at events", "food truck wrap cost"],
        "audiences": ["food_truck_owners", "mobile_business", "entrepreneurs"],
    },
    "specialty_vehicles": {
        "items": ["race car", "show car", "project car", "drift car", "track car",
                  "boat", "jet ski", "ATV", "UTV", "motorcycle", "snowmobile",
                  "golf cart", "go-kart"],
        "angles": ["sponsor wraps", "race livery", "custom graphics", "protection",
                   "seasonal wrap", "show quality"],
        "audiences": ["motorsport", "boat_owners", "powersport"],
    },
    "large_commercial": {
        "items": ["semi truck", "trailer", "18-wheeler", "bus", "shuttle bus",
                  "school bus conversion", "RV", "motorhome", "camper van",
                  "moving truck", "refrigerated truck"],
        "angles": ["highway advertising", "national brand exposure", "fleet identity",
                   "long-haul visibility", "trailer wrap ROI"],
        "audiences": ["logistics", "corporate", "fleet_managers"],
    },
    "corporate_government": {
        "items": ["company car", "executive vehicle", "sales fleet", "rental fleet",
                  "municipal vehicle", "police car graphics", "fire truck graphics",
                  "ambulance graphics", "government fleet", "airport shuttle",
                  "hotel shuttle", "rideshare vehicle"],
        "angles": ["professional branding", "fleet standardization", "municipal identity",
                   "corporate image", "employee vehicles"],
        "audiences": ["corporate", "government", "fleet_managers"],
    },
}

# ─────────────────────────────────────────────
# CAMPAIGN MOVEMENTS TO ENGAGE WITH
# ─────────────────────────────────────────────
CAMPAIGN_MOVEMENTS = [
    {
        "name": "EV Revolution",
        "description": "The shift to electric vehicles — every new EV needs a wrap",
        "triggers": ["new EV launch", "EV delivery", "first EV", "switched to electric"],
        "response_angle": "Wraps let you personalize limited EV color options",
    },
    {
        "name": "Small Business Branding",
        "description": "Small businesses discovering vehicle wraps as marketing",
        "triggers": ["started a business", "new business", "side hustle", "branding tips"],
        "response_angle": "Vehicle wraps are the cheapest cost-per-impression advertising",
    },
    {
        "name": "Fleet Electrification",
        "description": "Companies converting fleets to EVs",
        "triggers": ["fleet EV", "electric fleet", "delivery EV", "Amazon Rivian"],
        "response_angle": "New fleet vehicles need new branding — bulk wrap discounts",
    },
    {
        "name": "Car Culture & Shows",
        "description": "Car shows, meets, and enthusiast events",
        "triggers": ["car show", "cars and coffee", "car meet", "SEMA", "auto show"],
        "response_angle": "Stand out at the show with a custom wrap",
    },
    {
        "name": "New Car Launches",
        "description": "When new models drop, owners want to customize",
        "triggers": ["just picked up", "new car", "took delivery", "first mod"],
        "response_angle": "Protect that new paint with PPF, or make it yours with a wrap",
    },
    {
        "name": "Seasonal Campaigns",
        "description": "Seasonal wrap opportunities",
        "triggers": ["spring", "summer", "winter protection", "salt damage", "road trip"],
        "response_angle": "Seasonal wrap specials, winter protection, summer color changes",
    },
    {
        "name": "Tax Season / Year End",
        "description": "Business owners looking for tax deductions",
        "triggers": ["tax deduction", "section 179", "write off", "year end", "Q4"],
        "response_angle": "Fleet wraps are a tax-deductible business expense",
    },
    {
        "name": "Chicago Local",
        "description": "Chicago-specific events, weather, culture",
        "triggers": ["chicago", "chi-town", "lake shore drive", "winter chicago", "pothole"],
        "response_angle": "Local shop, local knowledge, Chicago weather-tested wraps",
    },
    {
        "name": "Wrap vs Paint Debate",
        "description": "People debating whether to wrap or repaint",
        "triggers": ["wrap vs paint", "repaint cost", "should I wrap", "is wrapping worth it"],
        "response_angle": "Expert knowledge on wrap vs paint — cost, durability, reversibility",
    },
    {
        "name": "DIY vs Professional",
        "description": "People considering DIY wraps",
        "triggers": ["DIY wrap", "wrap myself", "how hard is wrapping", "wrap kit"],
        "response_angle": "Honest advice on what you can DIY vs what needs a pro",
    },
]

# ─────────────────────────────────────────────
# PERFORMANCE TRACKING & SELF-IMPROVEMENT
# ─────────────────────────────────────────────

class ContentBrain:
    """The self-improving content strategy engine."""

    def __init__(self):
        self.strategy = self._load_strategy()
        self.performance = self._load_performance()
        self.learnings = self._load_learnings()

    def _load_strategy(self) -> dict:
        if os.path.exists(STRATEGY_FILE):
            try:
                with open(STRATEGY_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "current_focus": [],
            "avoid_topics": [],
            "winning_formats": {},
            "winning_audiences": {},
            "winning_times": {},
            "pivot_history": [],
        }

    def _load_performance(self) -> list:
        if os.path.exists(PERFORMANCE_FILE):
            try:
                with open(PERFORMANCE_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _load_learnings(self) -> list:
        if os.path.exists(LEARNING_FILE):
            try:
                with open(LEARNING_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save_all(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(STRATEGY_FILE, "w") as f:
            json.dump(self.strategy, f, indent=2)
        with open(PERFORMANCE_FILE, "w") as f:
            json.dump(self.performance[-1000:], f, indent=2)
        with open(LEARNING_FILE, "w") as f:
            json.dump(self.learnings[-200:], f, indent=2)

    # ─────────────────────────────────────────
    # RECORD & REVIEW PERFORMANCE
    # ─────────────────────────────────────────

    def record_post(self, post_data: dict):
        """Record a post we made for later performance review."""
        self.performance.append({
            "id": post_data.get("id", f"post_{int(datetime.now().timestamp())}"),
            "platform": post_data.get("platform", ""),
            "content_type": post_data.get("content_type", ""),
            "topic": post_data.get("topic", ""),
            "audience": post_data.get("audience", ""),
            "caption": post_data.get("caption", "")[:200],
            "wrappable_target": post_data.get("wrappable_target", ""),
            "campaign": post_data.get("campaign", ""),
            "posted_at": datetime.now().isoformat(),
            "engagement": {
                "likes": 0,
                "comments": 0,
                "shares": 0,
                "views": 0,
                "checked_at": None,
            },
            "performance_score": None,
            "reviewed": False,
        })
        self._save_all()

    def update_engagement(self, post_id: str, engagement: dict):
        """Update engagement metrics for a post after checking back."""
        for post in self.performance:
            if post.get("id") == post_id:
                post["engagement"] = engagement
                post["engagement"]["checked_at"] = datetime.now().isoformat()
                post["performance_score"] = self._calculate_score(engagement)
                post["reviewed"] = True
                break
        self._save_all()

    def _calculate_score(self, engagement: dict) -> float:
        """Calculate a normalized performance score for a post."""
        likes = engagement.get("likes", 0)
        comments = engagement.get("comments", 0)
        shares = engagement.get("shares", 0)
        views = engagement.get("views", 0)

        # Weighted score: comments > shares > likes > views
        score = (comments * 5) + (shares * 3) + (likes * 1) + (views * 0.01)
        return round(score, 2)

    # ─────────────────────────────────────────
    # SELF-IMPROVEMENT: LEARN & PIVOT
    # ─────────────────────────────────────────

    def review_and_pivot(self):
        """Review recent performance and adjust strategy.
        
        This is the core self-improvement loop:
        - Look at last 20 posts
        - Find what's working (high scores) → double down
        - Find what's NOT working (low scores) → pivot away
        - Update strategy for next cycle
        """
        reviewed = [p for p in self.performance if p.get("reviewed") and p.get("performance_score") is not None]
        if len(reviewed) < 3:
            print("  [BRAIN] Not enough reviewed posts to learn from yet", flush=True)
            return

        recent = reviewed[-20:]
        avg_score = sum(p["performance_score"] for p in recent) / len(recent)

        # Analyze by dimension
        by_platform = self._analyze_dimension(recent, "platform")
        by_audience = self._analyze_dimension(recent, "audience")
        by_content_type = self._analyze_dimension(recent, "content_type")
        by_topic = self._analyze_dimension(recent, "topic")
        by_target = self._analyze_dimension(recent, "wrappable_target")
        by_campaign = self._analyze_dimension(recent, "campaign")

        # Find winners and losers
        winners = {
            "platforms": [k for k, v in by_platform.items() if v["avg"] > avg_score * 1.2],
            "audiences": [k for k, v in by_audience.items() if v["avg"] > avg_score * 1.2],
            "content_types": [k for k, v in by_content_type.items() if v["avg"] > avg_score * 1.2],
            "topics": [k for k, v in by_topic.items() if v["avg"] > avg_score * 1.2],
            "targets": [k for k, v in by_target.items() if v["avg"] > avg_score * 1.2],
            "campaigns": [k for k, v in by_campaign.items() if v["avg"] > avg_score * 1.2],
        }

        losers = {
            "platforms": [k for k, v in by_platform.items() if v["avg"] < avg_score * 0.5 and v["count"] >= 2],
            "audiences": [k for k, v in by_audience.items() if v["avg"] < avg_score * 0.5 and v["count"] >= 2],
            "content_types": [k for k, v in by_content_type.items() if v["avg"] < avg_score * 0.5 and v["count"] >= 2],
            "topics": [k for k, v in by_topic.items() if v["avg"] < avg_score * 0.5 and v["count"] >= 2],
        }

        # Update strategy
        self.strategy["winning_formats"] = by_content_type
        self.strategy["winning_audiences"] = by_audience
        self.strategy["current_focus"] = winners.get("topics", []) + winners.get("targets", [])
        self.strategy["avoid_topics"] = losers.get("topics", [])

        # Record the pivot
        pivot = {
            "timestamp": datetime.now().isoformat(),
            "avg_score": avg_score,
            "posts_reviewed": len(recent),
            "winners": winners,
            "losers": losers,
            "action": self._determine_pivot_action(winners, losers, avg_score),
        }
        self.strategy["pivot_history"].append(pivot)
        self.strategy["pivot_history"] = self.strategy["pivot_history"][-50:]

        # Record learning
        self.learnings.append({
            "timestamp": datetime.now().isoformat(),
            "insight": pivot["action"],
            "data": {"avg_score": avg_score, "winners": winners, "losers": losers},
        })

        self._save_all()

        print(f"  [BRAIN] Review complete. Avg score: {avg_score:.1f}", flush=True)
        print(f"  [BRAIN] Winners: {winners}", flush=True)
        print(f"  [BRAIN] Pivot action: {pivot['action']}", flush=True)

    def _analyze_dimension(self, posts: list, key: str) -> dict:
        """Analyze performance by a specific dimension."""
        buckets = {}
        for p in posts:
            val = p.get(key, "unknown")
            if not val:
                val = "unknown"
            if val not in buckets:
                buckets[val] = {"scores": [], "count": 0}
            buckets[val]["scores"].append(p.get("performance_score", 0))
            buckets[val]["count"] += 1

        for k, v in buckets.items():
            v["avg"] = sum(v["scores"]) / len(v["scores"]) if v["scores"] else 0
            v["best"] = max(v["scores"]) if v["scores"] else 0
            del v["scores"]  # Don't store raw scores

        return buckets

    def _determine_pivot_action(self, winners: dict, losers: dict, avg_score: float) -> str:
        """Determine what strategic action to take based on performance data."""
        actions = []

        if winners.get("audiences"):
            actions.append(f"DOUBLE DOWN on audiences: {', '.join(winners['audiences'][:3])}")
        if winners.get("content_types"):
            actions.append(f"MORE of content type: {', '.join(winners['content_types'][:2])}")
        if winners.get("campaigns"):
            actions.append(f"RIDE the wave: {', '.join(winners['campaigns'][:2])}")
        if losers.get("topics"):
            actions.append(f"STOP posting about: {', '.join(losers['topics'][:3])}")
        if losers.get("audiences"):
            actions.append(f"REDUCE targeting: {', '.join(losers['audiences'][:2])}")

        if not actions:
            if avg_score > 10:
                actions.append("MAINTAIN current strategy — performing well")
            else:
                actions.append("EXPERIMENT with new topics and audiences — need more data")

        return " | ".join(actions)

    # ─────────────────────────────────────────
    # CONTENT DECISION ENGINE
    # ─────────────────────────────────────────

    def decide_next_post(self, platform: str, trends: dict = None) -> dict:
        """Decide what to post next based on trends, performance data, and strategy.
        
        This is the main decision function called every hour.
        It considers:
        1. Current trends (from trend_analyzer)
        2. What's been working (from performance data)
        3. What to avoid (from pivot decisions)
        4. What wrappable targets haven't been covered recently
        5. Which campaigns/movements are active
        6. What audience segment to target
        """
        # Get trend-based content idea
        trend_idea = None
        if trends and trends.get("content_ideas"):
            platform_ideas = [i for i in trends["content_ideas"]
                            if i.get("platform") in (platform, "all")]
            if platform_ideas:
                # Prioritize high urgency
                high = [i for i in platform_ideas if i.get("urgency") == "high"]
                trend_idea = high[0] if high else random.choice(platform_ideas)

        # Get a wrappable target we haven't posted about recently
        recent_targets = [p.get("wrappable_target", "") for p in self.performance[-20:]]
        fresh_target = self._get_fresh_wrappable_target(recent_targets)

        # Get an active campaign/movement
        campaign = self._get_relevant_campaign(trends)

        # Check what's been winning
        winning_audiences = list(self.strategy.get("winning_audiences", {}).keys())
        winning_formats = list(self.strategy.get("winning_formats", {}).keys())
        avoid_topics = self.strategy.get("avoid_topics", [])

        # Use AI to make the final decision
        decision = self._ai_decide(
            platform=platform,
            trend_idea=trend_idea,
            fresh_target=fresh_target,
            campaign=campaign,
            winning_audiences=winning_audiences,
            winning_formats=winning_formats,
            avoid_topics=avoid_topics,
            recent_posts=self.performance[-5:],
        )

        return decision

    def _get_fresh_wrappable_target(self, recent_targets: list) -> dict:
        """Get a wrappable target category that hasn't been posted about recently."""
        all_categories = list(WRAPPABLE_TARGETS.keys())
        # Prefer categories not recently used
        fresh = [c for c in all_categories if c not in recent_targets]
        if not fresh:
            fresh = all_categories

        category = random.choice(fresh)
        target = WRAPPABLE_TARGETS[category]
        item = random.choice(target["items"])
        angle = random.choice(target["angles"])

        return {
            "category": category,
            "item": item,
            "angle": angle,
            "audiences": target["audiences"],
        }

    def _get_relevant_campaign(self, trends: dict = None) -> dict:
        """Get a relevant campaign/movement to engage with."""
        # Check if any campaign triggers match current trends
        if trends:
            hot_topics = " ".join(trends.get("hot_topics", [])).lower()
            for campaign in CAMPAIGN_MOVEMENTS:
                for trigger in campaign["triggers"]:
                    if trigger.lower() in hot_topics:
                        return campaign

        # Default: pick a seasonal or evergreen campaign
        month = datetime.now().month
        if month in (3, 4, 5):
            seasonal = [c for c in CAMPAIGN_MOVEMENTS if c["name"] in ("New Car Launches", "Car Culture & Shows")]
        elif month in (10, 11, 12):
            seasonal = [c for c in CAMPAIGN_MOVEMENTS if c["name"] in ("Tax Season / Year End", "Fleet Electrification")]
        elif month in (6, 7, 8):
            seasonal = [c for c in CAMPAIGN_MOVEMENTS if c["name"] in ("Car Culture & Shows", "Seasonal Campaigns")]
        else:
            seasonal = CAMPAIGN_MOVEMENTS

        return random.choice(seasonal) if seasonal else random.choice(CAMPAIGN_MOVEMENTS)

    def _ai_decide(self, platform: str, trend_idea: dict, fresh_target: dict,
                   campaign: dict, winning_audiences: list, winning_formats: list,
                   avoid_topics: list, recent_posts: list) -> dict:
        """Use AI to synthesize all inputs into a final content decision."""

        recent_summary = ""
        if recent_posts:
            recent_summary = "\n".join([
                f"  - [{p.get('platform')}] {p.get('topic', '')} → score: {p.get('performance_score', 'pending')}"
                for p in recent_posts[-5:]
            ])

        prompt = f"""You are the content strategy brain for Chicago Fleet Wraps, a vehicle wrap shop in Chicago.

BUSINESS: {BUSINESS_CONTEXT[:300]}

PLATFORM: {platform}

CURRENT TREND IDEA:
{json.dumps(trend_idea, indent=2) if trend_idea else "No trending idea available"}

FRESH WRAPPABLE TARGET (hasn't been posted about recently):
Vehicle: {fresh_target.get('item', 'N/A')}
Angle: {fresh_target.get('angle', 'N/A')}
Target audience: {', '.join(fresh_target.get('audiences', []))}

ACTIVE CAMPAIGN/MOVEMENT:
{campaign.get('name', 'N/A')}: {campaign.get('description', '')}
Response angle: {campaign.get('response_angle', '')}

WHAT'S BEEN WINNING:
Audiences: {', '.join(winning_audiences[:5]) if winning_audiences else 'Not enough data yet'}
Formats: {', '.join(winning_formats[:3]) if winning_formats else 'Not enough data yet'}

AVOID THESE (not performing):
{', '.join(avoid_topics[:5]) if avoid_topics else 'Nothing to avoid yet'}

RECENT POSTS (don't repeat):
{recent_summary if recent_summary else 'No recent posts'}

DECIDE what to post next. Return ONLY valid JSON:
{{
    "topic": "What this post is about",
    "caption": "The actual caption/text for the post (platform-native voice, not corporate)",
    "image_prompt": "Detailed AI image generation prompt — describe the exact vehicle, wrap style, colors, setting, lighting, camera angle. Be VERY specific.",
    "content_type": "image|video|carousel|text",
    "audience": "Who this targets",
    "wrappable_target": "The vehicle/item category being featured",
    "campaign": "Which campaign/movement this ties into (or 'organic')",
    "hashtags": ["relevant", "hashtags", "for", "the", "platform"],
    "reasoning": "Why this will perform well right now — be specific",
    "cta_style": "none|soft|direct"
}}

RULES:
- Caption must sound like a REAL person/business, not a marketing agency
- For Instagram: visual-first, use relevant hashtags, engaging caption
- For Facebook: informative, spark discussion, ask a question
- For TikTok: hook in first 3 words, trendy, short
- Image prompt must be PHOTOREALISTIC and SPECIFIC — describe the exact vehicle model, wrap color/finish, Chicago backdrop if relevant
- Don't repeat what was recently posted
- If something is trending, ride that wave
- If winning audiences exist, lean into them
- If avoid topics exist, stay away from them
- Mix between promotional (showing CFW work) and educational (wrap tips/facts)
- CTA: "none" for pure engagement, "soft" for subtle mention, "direct" for clear CFW plug"""

        try:
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.9,
                max_tokens=800,
            )
            result = response.choices[0].message.content.strip()
            if result.startswith("```"):
                result = result.split("```")[1]
                if result.startswith("json"):
                    result = result[4:]
            decision = json.loads(result.strip())
            decision["platform"] = platform
            decision["decided_at"] = datetime.now().isoformat()
            return decision
        except Exception as e:
            print(f"  [BRAIN] AI decision error: {e}", flush=True)
            # Fallback decision
            return {
                "topic": f"{fresh_target.get('item', 'vehicle')} wrap",
                "caption": f"Another day, another wrap. {fresh_target.get('angle', 'Custom look')} on this {fresh_target.get('item', 'vehicle')}.",
                "image_prompt": f"Photorealistic image of a {fresh_target.get('item', 'car')} with a matte black vinyl wrap, parked in front of a modern Chicago building, golden hour lighting, cinematic composition, 4K quality",
                "content_type": "image",
                "audience": fresh_target.get("audiences", ["car_enthusiasts"])[0],
                "wrappable_target": fresh_target.get("category", "personal_vehicles"),
                "campaign": campaign.get("name", "organic"),
                "hashtags": ["carwrap", "vinylwrap", "chicago", "chicagofleetwraps"],
                "reasoning": "Fallback content — fresh target with proven angle",
                "cta_style": "none",
                "platform": platform,
                "decided_at": datetime.now().isoformat(),
            }

    # ─────────────────────────────────────────
    # MASTER ORCHESTRATOR INTERFACE
    # ─────────────────────────────────────────

    def decide_content(self, trends: dict = None, cross_platform_recs: dict = None,
                       avoid_topics: list = None) -> dict:
        """Main entry point called by master.py to decide what to post across ALL platforms.
        
        Returns a unified content decision that gets posted to FB, IG, and TikTok simultaneously.
        Uses CFW's authentic voice — not corporate marketing speak.
        """
        # Merge avoid topics from damage control with strategy avoid topics
        all_avoid = list(set(
            (avoid_topics or []) + self.strategy.get("avoid_topics", [])
        ))

        # Review and pivot based on recent performance
        self.review_and_pivot()

        # Get platform-specific decisions and merge into one unified decision
        # Pick the platform with the best cross-platform recommendation as primary
        primary_platform = "instagram"  # Default
        if cross_platform_recs:
            for plat in ["instagram", "facebook", "tiktok"]:
                recs = cross_platform_recs.get(plat, {})
                if recs.get("amplify"):
                    primary_platform = plat
                    break

        # Get the core decision
        decision = self.decide_next_post(primary_platform, trends)
        if not decision:
            return {}

        # Inject cross-platform intelligence
        if cross_platform_recs:
            decision["cross_platform_recs"] = cross_platform_recs

        # Inject avoid topics
        decision["avoid_topics"] = all_avoid

        # Ensure CFW voice in the caption
        decision = self._ensure_cfw_voice(decision)

        return decision

    def decide_replacement(self, failed_topic: str = "", failed_platform: str = "",
                           failure_details: dict = None) -> dict:
        """Decide replacement content when a post gets deleted for negative reactions.
        
        Called by master.py damage control phase.
        """
        # Add the failed topic to avoid list
        if failed_topic:
            if failed_topic not in self.strategy.get("avoid_topics", []):
                self.strategy.setdefault("avoid_topics", []).append(failed_topic)
                self._save_all()

        # Generate a safe replacement
        safe_targets = ["personal_vehicles", "electric_vehicles", "commercial_fleets"]
        fresh_target = self._get_fresh_wrappable_target([failed_topic])

        # Use a proven campaign
        campaign = self._get_relevant_campaign()

        prompt = f"""You are Chicago Fleet Wraps. A previous post about \"{failed_topic}\" on {failed_platform} \
got negative reactions and was deleted.

Failure details: {json.dumps(failure_details or {})}

Create a SAFE replacement post that:
1. Avoids anything controversial or similar to the failed topic
2. Focuses on something universally positive about vehicle wraps
3. Uses CFW's authentic voice — we're a real Chicago shop, not a marketing agency
4. Features: {fresh_target.get('item', 'vehicle')} with angle: {fresh_target.get('angle', 'custom look')}

Return ONLY valid JSON:
{{{{
    "topic": "safe topic",
    "caption": "the caption in CFW voice",
    "image_prompt": "detailed photorealistic image prompt",
    "content_type": "image",
    "audience": "target audience",
    "wrappable_target": "{fresh_target.get('category', 'personal_vehicles')}",
    "campaign": "{campaign.get('name', 'organic')}",
    "hashtags": ["relevant", "hashtags"],
    "reasoning": "why this is safe and will perform well",
    "cta_style": "none"
}}}}"""

        try:
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=600,
            )
            result = response.choices[0].message.content.strip()
            if result.startswith("```"):
                result = result.split("```")[1]
                if result.startswith("json"):
                    result = result[4:]
            return json.loads(result.strip())
        except Exception as e:
            print(f"  [BRAIN] Replacement decision error: {e}", flush=True)
            return {
                "topic": f"{fresh_target.get('item', 'vehicle')} wrap",
                "caption": f"Clean wrap, clean look. {fresh_target.get('angle', 'Custom style')} done right.",
                "image_prompt": f"Photorealistic image of a {fresh_target.get('item', 'car')} with a satin finish vinyl wrap in deep blue, parked on a Chicago street, golden hour, cinematic",
                "content_type": "image",
                "audience": "car_enthusiasts",
                "wrappable_target": fresh_target.get("category", "personal_vehicles"),
                "campaign": "organic",
                "hashtags": ["carwrap", "vinylwrap", "chicago", "chicagofleetwraps"],
                "cta_style": "none",
            }

    def _ensure_cfw_voice(self, decision: dict) -> dict:
        """Make sure the caption sounds like CFW — a real Chicago wrap shop, not a marketing bot."""
        caption = decision.get("caption", "")
        if not caption:
            return decision

        # Check for corporate-sounding phrases and rewrite if needed
        corporate_flags = [
            "we are proud", "we're excited to announce", "our team of experts",
            "industry-leading", "state-of-the-art", "don't hesitate to",
            "reach out today", "contact us now", "limited time offer",
            "act now", "click the link", "visit our website",
        ]

        needs_rewrite = any(flag in caption.lower() for flag in corporate_flags)
        if not needs_rewrite:
            return decision

        try:
            rewrite_prompt = f"""Rewrite this social media caption to sound like a REAL Chicago vehicle wrap shop owner \
talking to car people. Not corporate. Not salesy. Just a guy who loves wraps sharing cool stuff.

Original: {caption}

Rules:
- Sound like a real person, not a brand
- Chicago personality — direct, no BS, maybe a little humor
- No "click the link" or "contact us" or "limited time"
- Keep it under 200 characters for TikTok compatibility
- If there's a call to action, make it natural like "DM if you want details"

Return ONLY the rewritten caption, nothing else."""

            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": rewrite_prompt}],
                temperature=0.8,
                max_tokens=200,
            )
            decision["caption"] = response.choices[0].message.content.strip().strip('"')
        except Exception:
            pass

        return decision

    # ─────────────────────────────────────────
    # ENGAGEMENT TASK FORCE: Comment Strategy
    # ─────────────────────────────────────────

    def decide_comment_strategy(self, post_context: dict, platform: str) -> dict:
        """Decide how to comment on someone else's post.
        
        Analyzes the post and decides:
        - Should we comment at all?
        - What angle to take?
        - Should we mention CFW?
        - What tone/length?
        """
        post_text = post_context.get("text", "").lower()

        # Check if this matches any campaign triggers
        matched_campaign = None
        for campaign in CAMPAIGN_MOVEMENTS:
            for trigger in campaign["triggers"]:
                if trigger.lower() in post_text:
                    matched_campaign = campaign
                    break
            if matched_campaign:
                break

        # Check if it's about something wrappable
        matched_target = None
        for category, target in WRAPPABLE_TARGETS.items():
            for item in target["items"]:
                if item.lower() in post_text:
                    matched_target = {"category": category, "item": item, "angles": target["angles"]}
                    break
            if matched_target:
                break

        # Determine if we should mention CFW
        mention_cfw = False
        if any(w in post_text for w in ["recommend", "looking for", "who does", "wrap shop",
                                         "where to get", "need a wrap", "wrap near me"]):
            if any(w in post_text for w in ["chicago", "il", "illinois", "midwest", "chi"]):
                mention_cfw = True

        return {
            "should_comment": True,
            "campaign": matched_campaign,
            "wrappable_target": matched_target,
            "mention_cfw": mention_cfw,
            "tone": "helpful" if "?" in post_text else "casual",
            "max_length": 50 if platform == "tiktok" else 80,
        }

    # ─────────────────────────────────────────
    # DASHBOARD DATA
    # ─────────────────────────────────────────

    def get_dashboard_data(self) -> dict:
        """Get strategy data for the unified dashboard."""
        reviewed = [p for p in self.performance if p.get("reviewed")]
        total_posts = len(self.performance)
        avg_score = (sum(p.get("performance_score", 0) for p in reviewed) / len(reviewed)) if reviewed else 0

        # Best performing posts
        best_posts = sorted(reviewed, key=lambda p: p.get("performance_score", 0), reverse=True)[:5]

        # Performance by platform
        by_platform = {}
        for p in reviewed:
            plat = p.get("platform", "unknown")
            if plat not in by_platform:
                by_platform[plat] = {"count": 0, "total_score": 0}
            by_platform[plat]["count"] += 1
            by_platform[plat]["total_score"] += p.get("performance_score", 0)

        for k, v in by_platform.items():
            v["avg_score"] = round(v["total_score"] / v["count"], 1) if v["count"] else 0

        return {
            "total_posts": total_posts,
            "reviewed_posts": len(reviewed),
            "avg_score": round(avg_score, 1),
            "best_posts": best_posts,
            "by_platform": by_platform,
            "current_strategy": {
                "focus_topics": self.strategy.get("current_focus", []),
                "avoid_topics": self.strategy.get("avoid_topics", []),
                "winning_audiences": self.strategy.get("winning_audiences", {}),
            },
            "pivot_history": self.strategy.get("pivot_history", [])[-5:],
            "learnings": self.learnings[-5:],
        }


# ─────────────────────────────────────────────
# CONVENIENCE FUNCTIONS
# ─────────────────────────────────────────────

def get_brain() -> ContentBrain:
    """Get a ContentBrain instance."""
    return ContentBrain()


if __name__ == "__main__":
    brain = ContentBrain()

    # Test decision making
    from trend_analyzer import TrendAnalyzer
    analyzer = TrendAnalyzer()
    trends = analyzer.current_trends

    for platform in ["instagram", "facebook", "tiktok"]:
        decision = brain.decide_next_post(platform, trends)
        print(f"\n{'='*50}")
        print(f"[{platform.upper()}] Next post:")
        print(f"  Topic: {decision.get('topic')}")
        print(f"  Caption: {decision.get('caption', '')[:100]}...")
        print(f"  Audience: {decision.get('audience')}")
        print(f"  Campaign: {decision.get('campaign')}")
        print(f"  CTA: {decision.get('cta_style')}")
