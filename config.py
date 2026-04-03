"""
Chicago Fleet Wraps Reddit Bot — Configuration v3.0
Tightened warming to stay on-target: car, Chicago, and business subs only.
No more random subs like r/Showerthoughts.
"""
import os
from datetime import datetime

# ─────────────────────────────────────────────
# OpenAI
# ─────────────────────────────────────────────
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-4.1-mini"

# ─────────────────────────────────────────────
# Reddit Account
# ─────────────────────────────────────────────
REDDIT_USERNAME = os.environ.get("REDDIT_USERNAME", "AddressRadiant8768")

# ─────────────────────────────────────────────
# Anti-Ban Operational Parameters
# ─────────────────────────────────────────────
MAX_THREAD_AGE_HOURS = 12
MAX_THREAD_COMMENTS = 50
MAX_COMMENTS_PER_DAY = 8
MAX_COMMENTS_PER_SUB_PER_DAY = 1
PROMO_RATIO = 0.10
MIN_DELAY_BETWEEN_COMMENTS = 120
MAX_DELAY_BETWEEN_COMMENTS = 420

# ─────────────────────────────────────────────
# Account Warming Parameters
# ─────────────────────────────────────────────
WARMING_KARMA_THRESHOLD = 50
WARMING_COMMENTS_PER_CYCLE = 5
WARMING_MAX_PER_DAY = 15

# WARMING SUBREDDITS — v3.0: Tightened to stay on-target
# Even during warming, we build credibility where our customers are.
# No more random subs. Every comment builds toward our niche.
WARMING_SUBREDDITS = [
    # Tier A: Car enthusiast subs (high traffic, our people)
    "cars",
    "Autos",
    "carporn",
    "IdiotsInCars",
    "Justrolledintotheshop",
    "Cartalk",
    "MechanicAdvice",
    "projectcar",
    "AutoDetailing",
    # Tier B: Specific vehicle subs (future wrap customers)
    "Trucks",
    "f150",
    "ram_trucks",
    "Rivian",
    "TeslaMotors",
    "BMW",
    "Porsche",
    "Mustang",
    "Corvette",
    "WRX",
    "Charger",
    # Tier C: Chicago local (build local presence)
    "chicago",
    "ChicagoSuburbs",
    "ChicagoList",
    # Tier D: Business/fleet owners (commercial customers)
    "smallbusiness",
    "Entrepreneur",
    "foodtrucks",
    "vandwellers",
    "sweatystartup",
]

# Warming thread selection
WARMING_MIN_SCORE = 5
WARMING_MAX_EXISTING_COMMENTS = 100
WARMING_PREFER_RISING = True

# ─────────────────────────────────────────────
# Target Subreddits — Tiered (for normal mode)
# ─────────────────────────────────────────────
TIER1_LOCAL = [
    "chicago",
    "ChicagoSuburbs",
    "Naperville",
    "ChicagoMotorcycles",
    "ChicagoList",
]

TIER2_VEHICLE = [
    "Rivian",
    "TeslaModel3",
    "TeslaModelY",
    "TeslaMotors",
    "GolfGTI",
    "Porsche",
    "BMW",
    "mercedes_benz",
    "Corvette",
    "Mustang",
    "Camaro",
    "WRX",
    "Charger",
    "Challenger",
    "f150",
    "ram_trucks",
    "Trucks",
    "vandwellers",
]

TIER3_COMMERCIAL = [
    "smallbusiness",
    "Entrepreneur",
    "foodtrucks",
    "sweatystartup",
    "logistics",
    "USPS",
    "AmazonDSPDrivers",
]

INDUSTRY_SUBS = [
    "CarWraps",
    "VinylWrap",
    "AutoDetailing",
    "ppf",
    "Detailing",
]

ALL_TARGET_SUBS = TIER1_LOCAL + TIER2_VEHICLE + TIER3_COMMERCIAL + INDUSTRY_SUBS

# ─────────────────────────────────────────────
# Keywords — Tiered
# ─────────────────────────────────────────────
PRIMARY_KEYWORDS = [
    "wrap shop chicago",
    "car wrap chicago",
    "vehicle wrap chicago",
    "fleet wrap chicago",
    "vinyl wrap chicago",
    "ppf chicago",
    "color change wrap chicago",
    "wrap recommendation chicago",
    "wrap my car chicago",
    "wrap shop near me",
    "best wrap shop",
    "wrap shop recommendation",
    "who wraps",
    "where to get wrapped",
    "need a wrap",
]

SECONDARY_KEYWORDS = [
    "rivian wrap",
    "tesla wrap",
    "sprinter van wrap",
    "box truck wrap",
    "food truck wrap",
    "commercial vehicle graphics",
    "fleet graphics",
    "cargo van wrap",
    "truck wrap",
    "van wrap",
    "trailer wrap",
    "color change wrap",
    "ppf near me",
    "ceramic coating and wrap",
]

TERTIARY_KEYWORDS = [
    "how much does a wrap cost",
    "wrap vs paint",
    "how long does a wrap last",
    "wrap care tips",
    "best vinyl wrap brand",
    "3m vs avery",
    "vehicle wrap price",
    "is wrapping a car worth it",
    "wrap durability",
    "wrap maintenance",
    "partial wrap cost",
    "full wrap cost",
]

ALL_KEYWORDS = PRIMARY_KEYWORDS + SECONDARY_KEYWORDS + TERTIARY_KEYWORDS

# ─────────────────────────────────────────────
# Competitor Monitoring
# ─────────────────────────────────────────────
COMPETITORS = [
    "chicago auto pros",
    "xtreme graphics",
    "ghost industries",
    "electric auto finish",
    "pgc wrap",
    "top shop chicago wraps",
    "wrapstar",
    "wrap city",
]

# ─────────────────────────────────────────────
# Seasonal Adjustments
# ─────────────────────────────────────────────
def get_seasonal_config():
    """Return adjusted config based on current month."""
    month = datetime.now().month
    if month in (3, 4, 5):  # Spring surge
        return {
            "focus_subs": TIER2_VEHICLE + INDUSTRY_SUBS + TIER1_LOCAL,
            "focus_keywords": PRIMARY_KEYWORDS + SECONDARY_KEYWORDS,
            "max_comments": 8,
            "note": "Spring surge — enthusiast subs, color change & PPF focus",
        }
    elif month in (10, 11, 12):  # Q4 tax season
        return {
            "focus_subs": TIER3_COMMERCIAL + TIER1_LOCAL + INDUSTRY_SUBS,
            "focus_keywords": PRIMARY_KEYWORDS + ["tax deduction vehicle wrap", "section 179 wrap", "end of year fleet"],
            "max_comments": 8,
            "note": "Q4 tax season — business subs, fleet & tax deduction focus",
        }
    else:  # Normal
        return {
            "focus_subs": ALL_TARGET_SUBS,
            "focus_keywords": ALL_KEYWORDS,
            "max_comments": MAX_COMMENTS_PER_DAY,
            "note": "Normal season — balanced approach",
        }

# ─────────────────────────────────────────────
# Thread Creation (post-warming, 250+ karma)
# ─────────────────────────────────────────────
THREAD_CREATION_KARMA_THRESHOLD = 250
THREADS_PER_WEEK = 2

# ─────────────────────────────────────────────
# Business Facts (for AI prompt)
# ─────────────────────────────────────────────
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
"""

# ─────────────────────────────────────────────
# File Paths
# ─────────────────────────────────────────────
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(_BASE_DIR, "data")
LOG_DIR = os.path.join(_BASE_DIR, "logs")
POSTED_THREADS_FILE = f"{DATA_DIR}/posted_threads.json"
DAILY_LOG_FILE = f"{LOG_DIR}/daily_activity.json"
COMMENT_HISTORY_FILE = f"{DATA_DIR}/comment_history.json"
