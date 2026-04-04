"""
Chicago Fleet Wraps Reddit Bot — Configuration v6.0

Additions from v3.0:
- AI content creation API keys (Runway, HeyGen, ElevenLabs, Pika)
- Platform-specific settings
- Expanded competitor list with threat levels
- Self-optimizer settings
- Autonomous runner settings
"""

import os
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────
# AI APIs
# ─────────────────────────────────────────────────────────────────────

# ─── GLOBAL KILL SWITCH ───────────────────────────────────────────────
# Set to False to immediately stop ALL posting across ALL platforms.
# The bot will still run but will skip every post/comment action.
POSTING_ENABLED = False
# ──────────────────────────────────────────────────────────────────────

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-4.1-mini"           # Warming/commenting (fast + cheap)
OPENAI_MODEL_PREMIUM = "gpt-4o"         # Content creation + strategy (smart + creative)

# AI Content Creation APIs
RUNWAY_API_KEY = os.environ.get("RUNWAY_API_KEY", "")
HEYGEN_API_KEY = os.environ.get("HEYGEN_API_KEY", "")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
PIKA_API_KEY = os.environ.get("PIKA_API_KEY", "")

# ElevenLabs — for cloning Roy's actual voice
ELEVENLABS_ROY_VOICE_ID = os.environ.get("ELEVENLABS_ROY_VOICE_ID", "")

# ─────────────────────────────────────────────────────────────────────
# Reddit Account
# ─────────────────────────────────────────────────────────────────────

REDDIT_USERNAME = os.environ.get("REDDIT_USERNAME", "AddressRadiant8768")

# ─────────────────────────────────────────────────────────────────────
# Social Media Platform Settings (for content creation)
# ─────────────────────────────────────────────────────────────────────

# Instagram
INSTAGRAM_USERNAME = os.environ.get("INSTAGRAM_USERNAME", "")
INSTAGRAM_PASSWORD = os.environ.get("INSTAGRAM_PASSWORD", "")

# TikTok
TIKTOK_SESSION_ID = os.environ.get("TIKTOK_SESSION_ID", "")

# Facebook
FACEBOOK_PAGE_TOKEN = os.environ.get("FACEBOOK_PAGE_TOKEN", "")
FACEBOOK_PAGE_ID = os.environ.get("FACEBOOK_PAGE_ID", "")

# YouTube
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")
YOUTUBE_CHANNEL_ID = os.environ.get("YOUTUBE_CHANNEL_ID", "")

# ─────────────────────────────────────────────────────────────────────
# Anti-Ban Operational Parameters (unchanged — these work)
# ─────────────────────────────────────────────────────────────────────

MAX_THREAD_AGE_HOURS = 12
MAX_THREAD_COMMENTS = 50
MAX_COMMENTS_PER_DAY = 8
MAX_COMMENTS_PER_SUB_PER_DAY = 1
PROMO_RATIO = 0.10
MIN_DELAY_BETWEEN_COMMENTS = 120
MAX_DELAY_BETWEEN_COMMENTS = 420

# ─────────────────────────────────────────────────────────────────────
# Account Warming Parameters
# ─────────────────────────────────────────────────────────────────────

WARMING_KARMA_THRESHOLD = 50
WARMING_COMMENTS_PER_CYCLE = 5
WARMING_MAX_PER_DAY = 15

WARMING_SUBREDDITS = [
    # Tier A: Car enthusiast subs
    "cars", "Autos", "carporn", "IdiotsInCars", "Justrolledintotheshop",
    "Cartalk", "MechanicAdvice", "projectcar", "AutoDetailing",
    # Tier B: Specific vehicle subs
    "Trucks", "f150", "ram_trucks", "Rivian", "TeslaMotors",
    "BMW", "Porsche", "Mustang", "Corvette", "WRX", "Charger",
    # Tier C: Chicago local
    "chicago", "ChicagoSuburbs", "ChicagoList",
    # Tier D: Business/fleet owners
    "smallbusiness", "Entrepreneur", "foodtrucks", "vandwellers", "sweatystartup",
]

WARMING_MIN_SCORE = 5
WARMING_MAX_EXISTING_COMMENTS = 100
WARMING_PREFER_RISING = True

# ─────────────────────────────────────────────────────────────────────
# Target Subreddits — Tiered
# ─────────────────────────────────────────────────────────────────────

TIER1_LOCAL = [
    "chicago", "ChicagoSuburbs", "Naperville", "ChicagoMotorcycles", "ChicagoList",
]

TIER2_VEHICLE = [
    "Rivian", "TeslaModel3", "TeslaModelY", "TeslaMotors",
    "GolfGTI", "Porsche", "BMW", "mercedes_benz", "Corvette",
    "Mustang", "Camaro", "WRX", "Charger", "Challenger",
    "f150", "ram_trucks", "Trucks", "vandwellers",
]

TIER3_COMMERCIAL = [
    "smallbusiness", "Entrepreneur", "foodtrucks", "sweatystartup",
    "logistics", "USPS", "AmazonDSPDrivers",
]

INDUSTRY_SUBS = [
    "CarWraps", "VinylWrap", "AutoDetailing", "ppf", "Detailing",
]

ALL_TARGET_SUBS = TIER1_LOCAL + TIER2_VEHICLE + TIER3_COMMERCIAL + INDUSTRY_SUBS

# ─────────────────────────────────────────────────────────────────────
# Keywords — Tiered (unchanged + new additions)
# ─────────────────────────────────────────────────────────────────────

PRIMARY_KEYWORDS = [
    "wrap shop chicago", "car wrap chicago", "vehicle wrap chicago",
    "fleet wrap chicago", "vinyl wrap chicago", "ppf chicago",
    "color change wrap chicago", "wrap recommendation chicago",
    "wrap my car chicago", "wrap shop near me", "best wrap shop",
    "wrap shop recommendation", "who wraps", "where to get wrapped",
    "need a wrap",
]

SECONDARY_KEYWORDS = [
    "rivian wrap", "tesla wrap", "sprinter van wrap", "box truck wrap",
    "food truck wrap", "commercial vehicle graphics", "fleet graphics",
    "cargo van wrap", "truck wrap", "van wrap", "trailer wrap",
    "color change wrap", "ppf near me", "ceramic coating and wrap",
]

TERTIARY_KEYWORDS = [
    "how much does a wrap cost", "wrap vs paint", "how long does a wrap last",
    "wrap care tips", "best vinyl wrap brand", "3m vs avery",
    "vehicle wrap price", "is wrapping a car worth it", "wrap durability",
    "wrap maintenance", "partial wrap cost", "full wrap cost",
]

# NEW v6.0 business keywords
BUSINESS_KEYWORDS = [
    "fleet marketing ideas", "van advertising", "mobile billboard",
    "business vehicle branding", "section 179 vehicle", "tax deduction wrap",
    "fleet graphics chicago", "company truck decals", "delivery van wrap",
    "moving company truck wrap", "hvac truck wrap", "plumber truck wrap",
    "food truck branding", "food truck wrap",
]

ALL_KEYWORDS = PRIMARY_KEYWORDS + SECONDARY_KEYWORDS + TERTIARY_KEYWORDS + BUSINESS_KEYWORDS

# ─────────────────────────────────────────────────────────────────────
# Competitor Monitoring — Now with Threat Levels
# ─────────────────────────────────────────────────────────────────────

COMPETITORS = [
    "chicago auto pros",
    "xtreme graphics",
    "ghost industries",
    "electric auto finish",
    "pgc wrap",
    "top shop chicago wraps",
    "wrapstar",
    "wrap city",
    "wraps by design chicago",
    "chicago vinyl wraps",
]

# Threat level: high = respond immediately, medium = respond if convenient, low = monitor only
COMPETITOR_THREAT_LEVELS = {
    "chicago auto pros": "high",
    "xtreme graphics": "high",
    "ghost industries": "medium",
    "electric auto finish": "medium",
    "pgc wrap": "low",
    "top shop chicago wraps": "medium",
    "wrapstar": "low",
    "wrap city": "low",
    "wraps by design chicago": "medium",
    "chicago vinyl wraps": "low",
}

# ─────────────────────────────────────────────────────────────────────
# Self-Optimizer Settings
# ─────────────────────────────────────────────────────────────────────

OPTIMIZER_RUN_HOUR = 6          # 6 AM daily
OPTIMIZER_ENABLED = True
OPTIMIZER_MIN_DATA_DAYS = 3     # Don't optimize until 3 days of data

# ─────────────────────────────────────────────────────────────────────
# Content Creation Settings
# ─────────────────────────────────────────────────────────────────────

CONTENT_CREATION_ENABLED = True
CONTENT_CREATION_DAYS = ["Tuesday", "Thursday", "Saturday"]
CONTENT_PLATFORMS = ["tiktok", "instagram_reels", "youtube_shorts", "facebook"]
CONTENT_PIECES_PER_RUN = 2      # Generate 2 pieces per content day per platform

# ─────────────────────────────────────────────────────────────────────
# Seasonal Adjustments
# ─────────────────────────────────────────────────────────────────────

def get_seasonal_config():
    """Return adjusted config based on current month."""
    month = datetime.now().month

    if month in (3, 4, 5):  # Spring surge
        return {
            "focus_subs": TIER2_VEHICLE + INDUSTRY_SUBS + TIER1_LOCAL,
            "focus_keywords": PRIMARY_KEYWORDS + SECONDARY_KEYWORDS,
            "max_comments": 8,
            "content_archetype_priority": ["before_after", "rivian_special", "day_in_shop"],
            "urgency_message": "Spring is booking up — March through May runs 3-4 weeks out.",
            "note": "Spring surge — enthusiast subs, color change & PPF focus",
        }
    elif month in (10, 11, 12):  # Q4 tax season
        return {
            "focus_subs": TIER3_COMMERCIAL + TIER1_LOCAL + INDUSTRY_SUBS,
            "focus_keywords": PRIMARY_KEYWORDS + BUSINESS_KEYWORDS + [
                "tax deduction vehicle wrap", "section 179 wrap", "end of year fleet"],
            "max_comments": 8,
            "content_archetype_priority": ["client_story", "price_transparency", "competitor_comparison"],
            "urgency_message": "Section 179 tax write-off deadline is December 31.",
            "note": "Q4 tax season — business subs, fleet & tax deduction focus",
        }
    else:  # Normal
        return {
            "focus_subs": ALL_TARGET_SUBS,
            "focus_keywords": ALL_KEYWORDS,
            "max_comments": MAX_COMMENTS_PER_DAY,
            "content_archetype_priority": ["before_after", "education", "day_in_shop"],
            "urgency_message": "",
            "note": "Normal season — balanced approach",
        }

# ─────────────────────────────────────────────────────────────────────
# Thread Creation
# ─────────────────────────────────────────────────────────────────────

THREAD_CREATION_KARMA_THRESHOLD = 250
THREADS_PER_WEEK = 2

# v6.0: Expanded thread types
THREAD_TYPES = [
    "educational", "experience", "discussion",
    "price_transparency", "before_after",
]

# ─────────────────────────────────────────────────────────────────────
# Business Context (single source of truth)
# ─────────────────────────────────────────────────────────────────────

BUSINESS_CONTEXT = """
Chicago Fleet Wraps (CFW) is a vehicle wrap shop in Portage Park, Chicago (4711 N. Lamon Ave, Chicago, IL 60630).
Owner: Roy (known as "Roy Wraps"). In business since 2014. Over 10 years experience.
Wrapped over 600 Rivians — also has a location in Bloomington, IL near the Rivian plant.
Services: commercial fleet wraps, custom color change wraps, vinyl lettering, decals, wall graphics, signage, EV wraps, PPF (paint protection film).
Has a transparent online price calculator on their website — rare in the industry.
Responds within 2 hours with detailed pricing. No games, no "call for a quote" runaround.
Fleet discounts up to 15%.
Cargo van wrap starts around $3,750. Full color change starts around $3,500-4,500 depending on vehicle.
Uses premium materials: 3M 2080, Avery Dennison SW900, XPEL PPF.
Phone: (312) 597-1286.
Website: chicagofleetwraps.com
Known for: transparency, fast turnaround (3-5 days for most jobs), and not upselling unnecessary services.
Target clients: fleets (HVAC, food trucks, delivery, construction), car enthusiasts, EV owners (especially Rivian).
ROI framing: a wrapped cargo van at $3,750 over 5 years = $62/month for a 24/7 mobile billboard.
"""

# ─────────────────────────────────────────────────────────────────────
# File Paths
# ─────────────────────────────────────────────────────────────────────

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(_BASE_DIR, "data")
LOG_DIR = os.path.join(_BASE_DIR, "logs")
CONTENT_QUEUE_DIR = os.path.join(DATA_DIR, "content_queue")
AUDIO_DIR = os.path.join(DATA_DIR, "audio")

POSTED_THREADS_FILE = f"{DATA_DIR}/posted_threads.json"
DAILY_LOG_FILE = f"{LOG_DIR}/daily_activity.json"
COMMENT_HISTORY_FILE = f"{DATA_DIR}/comment_history.json"
PERSONA_STATS_FILE = f"{DATA_DIR}/persona_stats.json"
CONTENT_LOG_FILE = f"{DATA_DIR}/content_log.json"
STRATEGY_FILE = f"{DATA_DIR}/current_strategy.json"
