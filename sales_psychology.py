"""
Chicago Fleet Wraps — Sales Psychology Engine v1.0

6 Cialdini Principles applied to CFW's exact sales situation.
AIDA framework for content sequencing.
Specific objection scripts by platform and buyer type.
DM follow-up sequences (day 1, 3, 7).
Price anchoring and urgency triggers.

This module generates psychologically-optimized language for every
touchpoint: Reddit comments, DMs, TikTok captions, video scripts, FB posts.
"""

import random
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────
# CIALDINI'S 6 PRINCIPLES — CFW-SPECIFIC APPLICATIONS
# ─────────────────────────────────────────────────────────────────────

CIALDINI_APPLICATIONS = {

    "reciprocity": {
        "principle": "Give value first. People feel obligated to return a favor.",
        "cfw_tactics": [
            "Free educational content about wrap care, film selection, install process",
            "Answer the question FULLY before even hinting at CFW",
            "Share the price calculator freely — no gate, no 'call for a quote'",
            "Post genuine wrap tips on TikTok/Reels — give away the knowledge",
        ],
        "sample_language": [
            "Here's how to tell if a wrap install was done right — check the door jambs.",
            "Most shops won't tell you this: cheap film starts peeling at 18 months. Ask what brand they use before you book.",
            "The calculator on our site shows prices without you having to talk to anyone first. That's on purpose.",
        ],
    },

    "social_proof": {
        "principle": "People follow what others are doing, especially people like them.",
        "cfw_tactics": [
            "600+ Rivians wrapped — specific number beats 'many clients'",
            "Fleet customers: name the industry ('HVAC company in Schaumburg') not the company",
            "Before/after content shows the crowd has already decided",
            "Mention the 2-hour response time — shows volume of people reaching out",
        ],
        "sample_language": [
            "600+ Rivians isn't a typo. There's a reason Rivian owners in Chicago talk about them.",
            "I've seen HVAC fleets, food trucks, Amazon DSP routes, even a law firm's cars — all wrapped there.",
            "They respond in 2 hours with real pricing. Not because they're slow, because they're busy.",
        ],
    },

    "authority": {
        "principle": "Expertise and credentials drive trust.",
        "cfw_tactics": [
            "Since 2014 + 600 Rivians + location near Rivian plant = specific credibility",
            "3M 2080 / Avery Dennison / XPEL — material names prove knowledge",
            "Roy's 10+ years: specific beats vague ('decade' sounds like AI, '2014' sounds real)",
            "Industry language in comments builds authority even without naming CFW",
        ],
        "sample_language": [
            "After 10 years doing this, you can feel when a film is prepped right. It's in the edges.",
            "They use 3M 2080 and Avery SW900 — not the gray-market roll-end stuff some shops push.",
            "Since 2014 means they've seen Chicago winters test every install they've done.",
        ],
    },

    "liking": {
        "principle": "People say yes to people they like and feel similar to.",
        "cfw_tactics": [
            "Chicago-specific language and references build local affinity",
            "Roy's blue-collar, no-BS voice is inherently likeable vs corporate speak",
            "Car enthusiasm is a shared identity — speak the language",
            "Humor and self-deprecation ('take this with a grain of salt, it's my shop') build liking",
        ],
        "sample_language": [
            "Full disclosure: my shop. Take it with a grain of salt. But here's the honest answer to your question.",
            "Chicago winters are brutal on wraps. UV in summer too. Not every shop accounts for that in the install.",
            "I'm biased obviously, but you can get pricing without talking to anyone at chicagofleetwraps.com/calculator.",
        ],
    },

    "scarcity": {
        "principle": "People want what they can't easily have.",
        "cfw_tactics": [
            "Spring booking surge: 'March-May books out 3-4 weeks' (true)",
            "Q4 tax window: 'Section 179 deadline is December 31' (real urgency)",
            "Slot language: 'they cap new fleet accounts per month' (frames exclusivity)",
            "Rivian specialty: 'one of few shops with real Rivian experience in the Midwest'",
        ],
        "sample_language": [
            "Spring is brutal for booking — March through May typically runs 3-4 weeks out in Chicago.",
            "If it's a business vehicle, the Section 179 tax write-off ends December 31. That's real money.",
            "They're one of maybe 3 shops in the Midwest with actual Rivian experience at scale.",
        ],
    },

    "commitment_consistency": {
        "principle": "People follow through on things they've already said yes to.",
        "cfw_tactics": [
            "Get the micro-commitment: 'have you used the online calculator yet?'",
            "DM follow-up sequence: each message builds on the last yes",
            "Progress language: 'sounds like you're already leaning toward the wrap' → mirrors back their intent",
            "Content that makes people say 'that's exactly my situation' → they're halfway sold",
        ],
        "sample_language": [
            "Sounds like you've already decided wraps make sense — what's the vehicle?",
            "Did you run it through the calculator? Takes 60 seconds and gives you a real number.",
            "You mentioned budget earlier — cargo van wraps start around $3,750. Does that work?",
        ],
    },
}

# ─────────────────────────────────────────────────────────────────────
# OBJECTION HANDLING SCRIPTS
# ─────────────────────────────────────────────────────────────────────

OBJECTION_SCRIPTS = {

    "too_expensive": {
        "trigger_phrases": ["too expensive", "can't afford", "costs too much", "that's a lot", "cheaper option", "budget", "price"],
        "scripts": [
            # Script A: ROI reframe
            """The way I think about it: $3,750 over 5 years = $750/year = $62/month.
A Yelp ad package runs $300-500/month. Your wrapped van is a billboard 24/7, parked at every job site.
Most business owners who do it say they should've done it 3 years earlier.""",

            # Script B: Compare to paint
            """Compared to a quality respray ($4,000-8,000+), wraps come out cheaper and you get your OEM paint back when you're done.
It also protects that paint while it's on. The math isn't obvious until you run it.""",

            # Script C: Calculator nudge
            """Pricing depends a lot on the vehicle — they have a calculator at chicagofleetwraps.com/calculator
that gives you a real number without talking to anyone. Might be closer to your budget than you think,
especially if it's a business vehicle (Section 179 write-off applies).""",
        ],
    },

    "competitor_mention": {
        "trigger_phrases": ["other shop", "another place", "competitor name", "cheaper shop", "found one for less"],
        "scripts": [
            # Script A: Quality distinction
            """Price gap between shops usually comes down to film brand and prep time.
Ask any shop: what film brand? How long does prep take? What's the warranty?
If they can't answer quickly and specifically, that's your answer.""",

            # Script B: The real cost of bad installs
            """Cheap installs look fine for 6 months. Then the edges start lifting in Chicago winter.
Then it peels. Then you're paying for a removal + re-wrap.
The $500 you saved on the first one costs you $800 to fix. Seen it plenty of times.""",

            # Script C: Soft redirect
            """Worth getting 2-3 quotes. Just make sure you're comparing apples to apples — same film brand,
same warranty, similar timeline. CFW's pricing is on their website so you can actually compare.""",
        ],
    },

    "ill_think_about_it": {
        "trigger_phrases": ["think about it", "not sure", "maybe", "considering", "later", "not yet"],
        "scripts": [
            # Script A: Identify the hesitation
            """Totally fair. What's the main thing giving you pause — budget, timing, not sure if it's worth it?
Happy to give you a straight answer on whatever it is.""",

            # Script B: Soft scarcity (spring/fall specific)
            """No rush at all. Just heads up that March-May typically runs 3-4 weeks out for booking in Chicago.
Worth knowing if you have a timeline.""",

            # Script C: Low-commitment next step
            """Makes sense. If you want a real number without any commitment, their online calculator gives you
pricing in about 60 seconds. No phone call required.""",
        ],
    },

    "wrap_durability_concern": {
        "trigger_phrases": ["peeling", "fading", "how long", "durability", "last", "winter", "sun damage"],
        "scripts": [
            # Script A: Film quality answer
            """Quality wraps (3M 2080, Avery SW900) last 5-7 years. The ones that peel in 2 years are using
gray-market film or rushing the prep. You can feel the difference in quality when it's done right.""",

            # Script B: Chicago specific
            """Chicago is actually a good stress test — UV in summer, freeze/thaw in winter, road salt.
A properly done wrap with quality film handles it. You'll see peeling on cheap installs by year 2.""",

            # Script C: Care instructions close
            """Lifespan is mostly film quality + prep. Hand wash only (no auto car washes), 
keep it out of direct sun when possible. Most quality installs hit the 5-year mark easy.
Some do 7+ with good care.""",
        ],
    },

    "diy_wrap_interest": {
        "trigger_phrases": ["diy", "do it myself", "wrap it myself", "how hard is it", "tutorial"],
        "scripts": [
            # Script A: Honest answer (builds trust)
            """Small panels? Totally doable with practice. Full vehicle? The bumper curves, door handles,
mirrors — that's where people get stuck and end up with bubbles and lifting edges.
Most shops charge for removals from failed DIY. Not discouraging, just real talk.""",

            # Script B: Middle ground
            """Partial DIY is a thing — some people do their hood or roof themselves and have the rest
professionally done. Saves money, keeps the complex panels to the pros.""",
        ],
    },
}


def get_objection_script(comment_text: str, platform: str = "reddit") -> str:
    """Detect objection type and return an appropriate script."""
    comment_lower = comment_text.lower()

    for objection_type, data in OBJECTION_SCRIPTS.items():
        for phrase in data["trigger_phrases"]:
            if phrase in comment_lower:
                script = random.choice(data["scripts"])
                # Platform adapt
                if platform in ("tiktok", "instagram"):
                    # Shorten for social
                    script = _shorten_for_social(script)
                return script

    return ""


def _shorten_for_social(script: str, max_words: int = 50) -> str:
    """Truncate a script for social media contexts."""
    words = script.split()
    if len(words) <= max_words:
        return script
    return " ".join(words[:max_words]) + "..."


# ─────────────────────────────────────────────────────────────────────
# DM FOLLOW-UP SEQUENCES
# 3-touch sequence for interested prospects
# ─────────────────────────────────────────────────────────────────────

DM_SEQUENCES = {

    "day_1_warm": """Hey — saw your comment on the wrap thread. To give you a real price fast,
the calculator at chicagofleetwraps.com/calculator takes 60 seconds and no phone call needed.
Or just reply here with the vehicle and I can give you a ballpark.""",

    "day_3_followup": """Following up from earlier — did you get a chance to check the calculator?
If budget was the concern, worth knowing there's a fleet discount (up to 15%) if you have multiple vehicles,
and it's a business write-off under Section 179.""",

    "day_7_last": """Last message — I don't want to be annoying. If timing wasn't right, totally fine.
Whenever you're ready, (312) 597-1286 or chicagofleetwraps.com. Ask for Roy.""",

    "hot_lead_fast": """Sounds like you're ready to move. Best next step: call (312) 597-1286 or
drop your vehicle info at chicagofleetwraps.com. They respond same day with actual pricing.
Spring books up fast — worth grabbing a slot sooner than later.""",
}


def get_dm_sequence_message(day: int, lead_temperature: str = "warm") -> str:
    """Get the right DM for the right day and lead temperature."""
    if lead_temperature == "hot":
        return DM_SEQUENCES["hot_lead_fast"]
    if day == 1:
        return DM_SEQUENCES["day_1_warm"]
    if day == 3:
        return DM_SEQUENCES["day_3_followup"]
    if day >= 7:
        return DM_SEQUENCES["day_7_last"]
    return DM_SEQUENCES["day_1_warm"]


# ─────────────────────────────────────────────────────────────────────
# AIDA FRAMEWORK — Content Planning
# ─────────────────────────────────────────────────────────────────────

AIDA_CONTENT_PLAN = {
    "Attention": {
        "goal": "Stop the scroll. Create pattern interrupts.",
        "tactics": [
            "Bold stat: 'Your van sits at job sites 8 hours a day and nobody knows your name'",
            "Contrast: 'Before: generic white van. After: 3,000 impressions per day'",
            "Question: 'What does it cost you every month your van isn't wrapped?'",
            "Before/after visuals — the fastest attention grabber in the wrap industry",
        ],
        "hooks": [
            "Your truck is driving past 10,000 people a week. Are they remembering you?",
            "The cheapest billboard in Chicago is your vehicle.",
            "We wrapped 600+ Rivians. Here's what most shops get wrong.",
            "A $62/month billboard. Let me show you the math.",
            "Chicago fleet wraps vs the white van. The difference is just a phone call.",
        ],
    },
    "Interest": {
        "goal": "Educate. Show you understand their world.",
        "tactics": [
            "Show the install process — demystify it",
            "Explain film brands, durability, care — give real information",
            "Chicago-specific context: winters, UV, salt",
            "Industry comparisons: wrap vs paint vs vinyl lettering",
        ],
    },
    "Desire": {
        "goal": "Make them picture themselves with the wrap.",
        "tactics": [
            "Before/after with their exact vehicle type",
            "Social proof from their industry ('HVAC company saw X calls/month increase')",
            "Price transparency — the calculator removes the fear of 'how much is this going to cost?'",
            "Short timeline: 3-5 days turnaround (faster than paint, faster than they expect)",
        ],
    },
    "Action": {
        "goal": "Make the next step obvious and low-friction.",
        "tactics": [
            "Calculator link: no phone call required",
            "Phone number in every action CTA: (312) 597-1286",
            "Website: chicagofleetwraps.com",
            "DM: 'Reply with your vehicle and I'll give you a ballpark'",
        ],
        "ctas": [
            "Get a price in 60 seconds: chicagofleetwraps.com/calculator",
            "Call or text Roy at (312) 597-1286. He responds same day.",
            "Drop your vehicle in the comments and I'll give you a real number.",
            "Spring slots are filling. Worth booking early: chicagofleetwraps.com",
        ],
    },
}


def get_aida_hook(vehicle_type: str = None, platform: str = "tiktok") -> str:
    """Get an attention-grabbing hook optimized for the platform."""
    hooks = AIDA_CONTENT_PLAN["Attention"]["hooks"]

    if vehicle_type and "rivian" in vehicle_type.lower():
        hooks = [h for h in hooks if "rivian" in h.lower() or "600" in h.lower()] or hooks

    hook = random.choice(hooks)

    if platform == "tiktok":
        # TikTok wants FAST hooks — first 2 words matter most
        return hook.upper() if len(hook) < 40 else hook
    return hook


def get_seasonal_urgency() -> str:
    """Return a seasonally relevant urgency message."""
    month = datetime.now().month
    if month in (3, 4, 5):
        return "Spring is booking up — March through May typically runs 3-4 weeks out."
    elif month == 12:
        return "Section 179 tax write-off deadline is December 31. Business vehicles qualify."
    elif month in (10, 11):
        return "Q4 is peak fleet season. Get in before December pricing locks."
    elif month in (1, 2):
        return "Winter's actually a great time to wrap — shops have more availability and quicker turnaround."
    else:
        return "Summer UV is brutal on unwrapped vehicles. Quality film protects your paint."
