"""
Chicago Fleet Wraps Reddit Bot — Configuration
All playbook parameters in one place.
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
MAX_THREAD_AGE_HOURS = 6          # Only reply to threads < 6 hours old
MAX_THREAD_COMMENTS = 20          # Skip threads with 20+ existing comments
MAX_COMMENTS_PER_DAY = 4          # Hard cap on daily comments
MAX_COMMENTS_PER_SUB_PER_DAY = 1  # Never more than 1 comment per sub per day
PROMO_RATIO = 0.10                # 10% of comments mention CFW
MIN_DELAY_BETWEEN_COMMENTS = 300  # 5 minutes minimum between comments
MAX_DELAY_BETWEEN_COMMENTS = 900  # 15 minutes max random delay

# ─────────────────────────────────────────────
# Account Warming Parameters
# ─────────────────────────────────────────────
WARMING_KARMA_THRESHOLD = 100     # Karma needed before entering target subs
WARMING_COMMENTS_PER_DAY = 3      # Comments per day during warming
WARMING_SUBREDDITS = [
    "AskReddit",
    "CasualConversation",
    "mildlyinteresting",
    "NoStupidQuestions",
    "todayilearned",
]

# ─────────────────────────────────────────────
# Target Subreddits — Tiered
# ─────────────────────────────────────────────
TIER1_LOCAL = [
    "chicago",
    "ChicagoSuburbs",
    "Naperville",
    "ChicagoMotorcycles",
]

TIER2_VEHICLE = [
    "Rivian",
    "TeslaModel3",
    "TeslaModelY",
    "GolfGTI",
    "Porsche",
    "BMW",
    "mercedes_benz",
    "Corvette",
    "Mustang",
    "Camaro",
]

TIER3_COMMERCIAL = [
    "smallbusiness",
    "Entrepreneur",
    "foodtrucks",
    "sweatystartup",
    "logistics",
]

INDUSTRY_SUBS = [
    "CarWraps",
    "VinylWrap",
    "AutoDetailing",
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
]

# ─────────────────────────────────────────────
# Seasonal Adjustments
# ─────────────────────────────────────────────
def get_seasonal_config():
    """Return adjusted config based on current month."""
    month = datetime.now().month
    if month in (3, 4, 5):  # Spring surge
        return {
            "focus_subs": TIER2_VEHICLE + INDUSTRY_SUBS,
            "focus_keywords": PRIMARY_KEYWORDS + SECONDARY_KEYWORDS,
            "max_comments": 5,
            "note": "Spring surge — enthusiast subs, color change & PPF focus",
        }
    elif month in (10, 11, 12):  # Q4 tax season
        return {
            "focus_subs": TIER3_COMMERCIAL + TIER1_LOCAL,
            "focus_keywords": PRIMARY_KEYWORDS + ["tax deduction vehicle wrap", "section 179 wrap", "end of year fleet"],
            "max_comments": 5,
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
THREADS_PER_WEEK = 1

# ─────────────────────────────────────────────
# Business Facts (for AI prompt)
# ─────────────────────────────────────────────
BUSINESS_CONTEXT = """
Chicago Fleet Wraps is a vehicle wrap shop located in Portage Park, Chicago (4711 N. Lamon Ave, Chicago, IL 60630).
Owner: Roy (known as "Roy Wraps").
In business since 2014.
Wrapped over 600 Rivians — also has a location in Bloomington, IL near the Rivian plant.
Services: commercial fleet wraps, custom color change wraps, vinyl lettering, decals, wall graphics, signage, EV wraps, PPF.
Has a transparent online price calculator on their website.
Responds within 2 hours with detailed pricing.
Fleet discounts up to 15%.
Cargo van wrap starts around $3,750.
Phone: (312) 597-1286.
Website: chicagofleetwraps.com
"""

# ─────────────────────────────────────────────
# File Paths
# ─────────────────────────────────────────────
# Use relative paths so it works on Railway or any server
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(_BASE_DIR, "data")
LOG_DIR = os.path.join(_BASE_DIR, "logs")
POSTED_THREADS_FILE = f"{DATA_DIR}/posted_threads.json"
DAILY_LOG_FILE = f"{LOG_DIR}/daily_activity.json"
COMMENT_HISTORY_FILE = f"{DATA_DIR}/comment_history.json"
