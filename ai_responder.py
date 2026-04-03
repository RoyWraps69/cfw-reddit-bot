"""
Chicago Fleet Wraps Reddit Bot — AI Response Generator v6.0

MAJOR UPGRADE from v4.0:
1. 10 evolved personas (up from 3) via persona_engine_v2
2. Sales psychology integration (Cialdini, AIDA, objection handling)
3. Platform-aware comment generation
4. Persona performance tracking — learns which voice gets better results
5. Intent detection (curiosity/warm/hot/spam) — not just positive/negative
6. Self-reflective question generation for each comment decision
7. Video script generation for all 5 content archetypes
"""

import os
import json
import random
from openai import OpenAI
from config import OPENAI_MODEL, BUSINESS_CONTEXT, COMPETITORS

# Import new modules
try:
    from persona_engine_v2 import select_persona, record_persona_result, PERSONAS
    from sales_psychology import (
        get_objection_script, get_dm_sequence_message,
        AIDA_CONTENT_PLAN, get_aida_hook, get_seasonal_urgency,
        CIALDINI_APPLICATIONS,
    )
    ADVANCED_MODULES_LOADED = True
except ImportError:
    ADVANCED_MODULES_LOADED = False

base_url = os.environ.get("OPENAI_BASE_URL", None)
client = OpenAI(base_url=base_url) if base_url else OpenAI()

# ─────────────────────────────────────────────────────────────────────
# CORE IDENTITY (unchanged — this is the authentic Roy voice)
# ─────────────────────────────────────────────────────────────────────

ROY_IDENTITY = """You are a real person on Reddit. You work in the auto/trades industry in Chicago.
You know cars, trucks, wraps, and Chicago. You're practical, direct, and occasionally funny.
You type like a normal person — not a writer, not a marketer, not an AI.
You have real opinions. You've seen things go wrong. You know what works and what doesn't."""

# ─────────────────────────────────────────────────────────────────────
# BACKWARD COMPATIBLE PROMO VOICES (kept for warming mode fallback)
# Now supplemented by persona_engine_v2's 10 personas
# ─────────────────────────────────────────────────────────────────────

PROMO_VOICES = {
    "happy_customer": """You got your vehicle wrapped at Chicago Fleet Wraps and it came out solid.
Recommend them like you'd tell a friend — casual, not salesy.
Mention ONE specific real detail (price range, turnaround, Roy being easy to work with, the online calculator).
2-3 sentences max. Don't sound like a paid review.""",

    "roy_himself": """You're Roy, you run Chicago Fleet Wraps in Portage Park.
Be upfront about it — "I run a shop so take this with a grain of salt" or "full disclosure this is my shop."
Answer the question FIRST with real expertise, then mention your shop SECOND.
Be humble. Be real. Include a specific technical detail that proves you know your stuff.""",

    "local_who_knows": """You're from Chicago and you've used a few wrap shops.
Recommend Chicago Fleet Wraps as one you had a good experience with.
Don't oversell — just say what you liked. Maybe compare to another experience. 2-3 sentences max.""",

    # NEW v6.0 voices (simplified versions of the full persona_engine_v2 personas)
    "fleet_manager_voice": """You manage a Chicago fleet and you've done the ROI math on wraps.
You talk business: cost-per-vehicle, brand impressions, what bad installs cost you.
You mention CFW's fleet discount (up to 15%) only if it fits. Max 70 words. No enthusiasm. Just math.""",

    "budget_realist_voice": """You position the cost as math: $3,750 ÷ 5 years = $750/year = $62/month for a billboard.
Compare to Facebook ads, yard signs, Yelp packages. Wraps win.
Mention the online calculator as the no-hassle way to get a real number. Max 65 words.""",

    "converted_skeptic_voice": """You were convinced wraps were a ripoff until you priced a respray.
The math surprised you. You got it done at CFW and it came out solid.
Handle the main objection upfront — show you had it too. 2-3 sentences. No cheerleading.""",
}


# ─────────────────────────────────────────────────────────────────────
# WARMING v6.0: Context + Persona + Psychology
# ─────────────────────────────────────────────────────────────────────

def generate_warming_comment(title: str, body: str, subreddit: str,
                              thread_context: dict = None,
                              sub_profile: str = None,
                              performance_context: str = None) -> str:
    """Generate a warming comment with full context and persona selection."""

    style_guidance = _build_style_guidance(thread_context)
    top_comments_block = _build_top_comments_block(thread_context)
    vibe = thread_context.get("thread_vibe", "discussion") if thread_context else "discussion"
    avg_len = thread_context.get("avg_comment_length", 25) if thread_context else 25
    length_guidance = _get_length_guidance(vibe, avg_len)

    # v6.0: Use persona engine if available
    if ADVANCED_MODULES_LOADED:
        persona = select_persona(
            subreddit=subreddit,
            thread_category="general",
            platform="reddit",
        )
        persona_voice = persona.get("voice_prompt", ROY_IDENTITY)
        persona_key = persona.get("persona_key", "roy_craftsman")
    else:
        persona_voice = ROY_IDENTITY
        persona_key = "default"

    prompt = f"""{persona_voice}

You're scrolling r/{subreddit} and see this post. Write a comment.

POST: {title}
{body[:400] if body else '(no body text)'}

--- WHAT'S GETTING UPVOTED IN THIS THREAD ---
{top_comments_block}

--- STYLE ANALYSIS ---
{style_guidance}
Thread type: {vibe}

--- YOUR RESPONSE RULES ---
{length_guidance}

{f'--- SUBREDDIT PERSONALITY ---' + chr(10) + sub_profile if sub_profile else ''}
{f'--- YOUR PAST PERFORMANCE ---' + chr(10) + performance_context if performance_context else ''}
{_build_competitor_guidance(thread_context) if thread_context and thread_context.get('is_competitor_thread') else ''}

ACCURACY RULES:
- Only state things you know to be true
- If it's a Chicago-specific topic, draw on real Chicago knowledge
- If it's a technical question, give a real answer with a specific detail
- Do NOT make up personal stories

STYLE RULES:
- Match the energy of the top-voted comments above
- Do NOT mention vehicle wraps, your job, or anything promotional
- Do NOT use exclamation marks
- Do NOT use emojis  
- Do NOT start with "I" if you can avoid it
- No "Great question!" or "Honestly," or "As someone who"
- Write like you're on your phone between jobs

Write ONLY the comment. Nothing else."""

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=1.0,
        max_tokens=_get_max_tokens(vibe, avg_len),
    )

    comment = response.choices[0].message.content.strip()
    return _humanize(comment), persona_key  # Return persona_key for tracking


# ─────────────────────────────────────────────────────────────────────
# THREAD CLASSIFICATION v6.0
# Now detects intent level and buyer stage
# ─────────────────────────────────────────────────────────────────────

def classify_thread(title: str, body: str, subreddit: str) -> dict:
    """Classify a thread with intent level detection."""

    prompt = f"""Analyze this Reddit thread for a vehicle wrap business. Return JSON only.

Title: {title}
Body: {body[:500]}
Sub: r/{subreddit}

Categories:
1. "direct_recommendation" — asking for a wrap shop (especially Chicago area)
2. "competitor_mention" — mentions: {', '.join(COMPETITORS)}
3. "general_wrap_question" — asking about wraps (cost, durability, care, etc.)
4. "vehicle_specific" — discussing wrapping a specific vehicle
5. "irrelevant" — not about vehicle wraps

Buyer stages:
- "awareness" — just learning about wraps
- "consideration" — actively researching options
- "decision" — ready to buy, needs a specific shop

Return ONLY valid JSON:
{{
    "category": "...",
    "buyer_stage": "awareness|consideration|decision",
    "should_mention_cfw": true/false,
    "confidence": 0-100,
    "intent_level": "cold|curious|warm|hot",
    "objection_detected": "too_expensive|durability|competitor|none",
    "reasoning": "..."
}}"""

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=250,
    )

    try:
        result = response.choices[0].message.content.strip()
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]
        return json.loads(result.strip())
    except json.JSONDecodeError:
        return {
            "category": "irrelevant",
            "buyer_stage": "awareness",
            "should_mention_cfw": False,
            "confidence": 0,
            "intent_level": "cold",
            "objection_detected": "none",
            "reasoning": "Failed to parse",
        }


# ─────────────────────────────────────────────────────────────────────
# PROMO COMMENT GENERATION v6.0
# Persona + sales psychology + objection handling
# ─────────────────────────────────────────────────────────────────────

def generate_comment(title: str, body: str, subreddit: str, category: str,
                     should_mention_cfw: bool, existing_comments: list = None,
                     thread_context: dict = None,
                     sub_profile: str = None,
                     performance_context: str = None,
                     buyer_stage: str = "consideration",
                     objection_detected: str = "none") -> str:
    """Generate a Reddit comment with full persona + psychology + context."""

    style_guidance = _build_style_guidance(thread_context)
    top_comments_block = _build_top_comments_block(thread_context)
    vibe = thread_context.get("thread_vibe", "question") if thread_context else "question"
    avg_len = thread_context.get("avg_comment_length", 40) if thread_context else 40

    # Select persona
    if ADVANCED_MODULES_LOADED:
        is_neg = thread_context.get("is_negative", False) if thread_context else False
        is_comp = thread_context.get("is_competitor_thread", False) if thread_context else False
        persona = select_persona(
            subreddit=subreddit,
            thread_category=category,
            is_competitor_thread=is_comp,
            is_negative_thread=is_neg,
            buyer_stage_hint=buyer_stage,
        )
        voice = persona.get("voice_prompt", ROY_IDENTITY)
        persona_key = persona.get("persona_key", "default")
    else:
        voice = random.choice(list(PROMO_VOICES.values())) if should_mention_cfw else ROY_IDENTITY
        persona_key = "default"

    # Get objection script if needed
    objection_script = ""
    if ADVANCED_MODULES_LOADED and objection_detected and objection_detected != "none":
        full_text = f"{title} {body}"
        objection_script = get_objection_script(full_text, platform="reddit")

    # Get seasonal urgency if at decision stage
    seasonal = ""
    if ADVANCED_MODULES_LOADED and buyer_stage == "decision" and should_mention_cfw:
        seasonal = get_seasonal_urgency()

    # Build system prompt
    if should_mention_cfw:
        system_prompt = f"""{voice}

BUSINESS FACTS (use ONE or TWO naturally, don't list them all):
{BUSINESS_CONTEXT}

--- WHAT'S GETTING UPVOTED IN THIS THREAD ---
{top_comments_block}

--- STYLE ANALYSIS ---
{style_guidance}

{f'OBJECTION TO ADDRESS: {objection_script}' if objection_script else ''}
{f'SEASONAL CONTEXT: {seasonal}' if seasonal else ''}

RULES:
- Match the style and energy of the top-voted comments
- Write like a real person on Reddit. Short sentences. Casual.
- NEVER include a URL or link (DMs only)
- Keep it under 75 words
- Don't use words like "amazing", "incredible", "highly recommend"
- Include ONE specific detail (a price, a timeline, a material name)
- ACCURACY: Only state facts from the business info above
- Don't start with "I" every time
- The goal is to be HELPFUL first, promotional second"""

    else:
        system_prompt = f"""{ROY_IDENTITY}

You're answering a question about vehicle wraps. You know this cold — 10+ years in the industry.

--- WHAT'S GETTING UPVOTED IN THIS THREAD ---
{top_comments_block}

--- STYLE ANALYSIS ---
{style_guidance}

{f'--- SUBREDDIT PERSONALITY ---' + chr(10) + sub_profile if sub_profile else ''}
{f'--- YOUR PAST PERFORMANCE ---' + chr(10) + performance_context if performance_context else ''}
{_build_competitor_guidance(thread_context) if thread_context and thread_context.get('is_competitor_thread') else ''}

WRAP FACTS YOU KNOW (accurate, use naturally):
- Full wrap: $2,500-5,000+ depending on vehicle size and material
- Quality wraps last 5-7 years with proper care
- 3M 2080 and Avery Dennison SW900 are industry standard films  
- PPF (paint protection film) is different from vinyl wrap
- Wraps take 2-5 days for quality install
- Hand wash only — no automatic car washes
- Wraps protect OEM paint and can be removed

RULES:
- Match the style of top-voted comments
- Include a specific technical detail that shows expertise
- Keep it under 60 words unless thread rewards detail
- Don't start with "I" every time
- No exclamation marks"""

    existing_context = ""
    if existing_comments:
        existing_context = "\n\nOther comments already posted:\n" + "\n".join(
            [f"- {c[:100]}" for c in existing_comments[:5]])

    user_prompt = f"""Reply to this Reddit thread:

r/{subreddit}: {title}
{body[:500]}
{existing_context}

Write ONLY the comment text. No quotes, no labels, just the raw comment."""

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.9,
        max_tokens=_get_max_tokens(vibe, avg_len),
    )

    comment = response.choices[0].message.content.strip()
    return _humanize(comment), persona_key


# ─────────────────────────────────────────────────────────────────────
# DM GENERATION v6.0 — Multi-day sequences
# ─────────────────────────────────────────────────────────────────────

def generate_dm_message(username: str, their_comment: str, original_thread_title: str,
                         day: int = 1, intent_level: str = "warm") -> str:
    """Generate a DM with the right message for the day and intent level."""

    if ADVANCED_MODULES_LOADED:
        # Use the psychology-optimized sequence
        base_message = get_dm_sequence_message(day, intent_level)
        return base_message

    # Fallback to original prompt-based generation
    prompt = f"""Write a super brief Reddit DM to someone interested in getting a vehicle wrap in Chicago.
Their reply: {their_comment}
Include chicagofleetwraps.com/calculator if it fits naturally.
Keep it under 40 words. Sound like a real person, not a salesperson.
Don't start with "Hey there!" or "Hi friend!" — just be normal.
Write ONLY the DM text."""

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
        max_tokens=80,
    )
    return _humanize(response.choices[0].message.content.strip())


# ─────────────────────────────────────────────────────────────────────
# THREAD POST GENERATION v6.0
# ─────────────────────────────────────────────────────────────────────

def generate_thread_post(subreddit: str, thread_type: str) -> dict:
    """Generate a thread title and body."""

    type_prompts = {
        "educational": "Write a helpful post about vehicle wraps — share tips most people don't know. Don't mention any specific shop. Write like a real Reddit user.",
        "experience": "Write a post about your experience getting a vehicle wrapped. Include real details — cost, timeline, what surprised you. You can casually mention Chicago Fleet Wraps as where you went, but the post should be 90% useful info.",
        "discussion": "Write a discussion post asking other vehicle owners about their wrap experiences. Ask something specific that'll get people talking.",
        "price_transparency": "Write a post breaking down the real cost of vehicle wraps — what drives the price, what to watch out for, what questions to ask. Make it genuinely useful.",
        "before_after": "Write a post sharing a before/after wrap experience. Be specific about the vehicle, the cost, the timeline. Include one thing that surprised you.",
    }

    seasonal = get_seasonal_urgency() if ADVANCED_MODULES_LOADED else ""

    prompt = f"""Write a Reddit post for r/{subreddit}.

{type_prompts.get(thread_type, type_prompts['educational'])}

{f'SEASONAL CONTEXT (mention naturally if relevant): {seasonal}' if seasonal else ''}

RULES:
- Title should sound natural, not clickbaity
- Body should be 80-150 words
- Write like you're posting from your phone
- Include specific details (costs, materials, timeframes)
- Don't be too polished
- ACCURACY: Only include facts that are true about vehicle wraps

Return ONLY valid JSON:
{{"title": "...", "body": "..."}}"""

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
        max_tokens=400,
    )

    try:
        result = response.choices[0].message.content.strip()
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]
        return json.loads(result.strip())
    except json.JSONDecodeError:
        return None


# ─────────────────────────────────────────────────────────────────────
# INTENT DETECTION v6.0 (replaces binary check_positive_reply)
# ─────────────────────────────────────────────────────────────────────

def check_positive_reply(comment_text: str) -> bool:
    """Backward compatible: returns True if reply is positive/interested."""
    result = detect_intent(comment_text)
    return result.get("intent_level") in ("warm", "hot")


def detect_intent(comment_text: str) -> dict:
    """Detect intent level and buyer signals in a reply."""

    prompt = f"""Analyze this Reddit reply for purchase intent signals. Return JSON only.

Reply: {comment_text}

Intent levels:
- "hot" — explicitly asking for contact, ready to buy, asking for price/appointment
- "warm" — expressing interest, asking follow-up questions, showing curiosity
- "cold" — polite but not interested
- "spam" — bot, promotional, or irrelevant

Return ONLY valid JSON:
{{
    "intent_level": "hot|warm|cold|spam",
    "buyer_signals": ["list", "of", "signals"],
    "recommended_action": "send_dm|reply_with_info|ignore|block",
    "confidence": 0-100
}}"""

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=150,
    )

    try:
        result = response.choices[0].message.content.strip()
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]
        return json.loads(result.strip())
    except Exception:
        return {"intent_level": "cold", "recommended_action": "ignore", "confidence": 0}


# ─────────────────────────────────────────────────────────────────────
# HUMANIZATION ENGINE (unchanged — it works)
# ─────────────────────────────────────────────────────────────────────

import random as _random

HUMAN_QUIRKS = [
    lambda c: c[0].lower() + c[1:] if c and c[0].isupper() and _random.random() > 0.5 else c,
    lambda c: c.rstrip('.') if c.endswith('.') and _random.random() > 0.4 else c,
    lambda c: c.replace("do not", "don't").replace("can not", "can't").replace(
        "will not", "won't").replace("I am", "I'm").replace("it is", "it's")
        if _random.random() > 0.3 else c,
]

def _humanize(comment: str) -> str:
    comment = comment.strip().strip('"').strip("'").strip('\u201c').strip('\u201d')

    ai_openers = [
        "Honestly, ", "To be honest, ", "In my experience, ", "As someone who ",
        "I think ", "I feel like ", "I would say ", "From my perspective, ",
        "Great question! ", "That's a great point! ", "This is so true! ",
        "I completely agree! ", "Absolutely! ", "Definitely! ",
        "Oh man, ", "Oh wow, ", "Haha, ",
    ]

    for opener in ai_openers:
        if comment.startswith(opener) and _random.random() > 0.3:
            comment = comment[len(opener):]
            comment = comment[0].upper() + comment[1:] if comment else comment

    for quirk in HUMAN_QUIRKS:
        comment = quirk(comment)

    return comment


# ─────────────────────────────────────────────────────────────────────
# INTERNAL HELPERS (unchanged)
# ─────────────────────────────────────────────────────────────────────

def _build_style_guidance(thread_context: dict) -> str:
    if not thread_context:
        return "No context available. Default to short, casual comment (1-2 sentences)."
    style = thread_context.get("top_comment_style", "")
    avg_len = thread_context.get("avg_comment_length", 0)
    parts = []
    if style:
        parts.append(f"Winning comment style: {style}")
    if avg_len:
        parts.append(f"Average top comment length: ~{avg_len} words")
    return "\n".join(parts) if parts else "No style data. Default to short and casual."


def _build_top_comments_block(thread_context: dict, max_show: int = 5) -> str:
    if not thread_context or not thread_context.get("top_comments"):
        return "(no comments yet — you'd be one of the first)"
    lines = []
    for c in thread_context["top_comments"][:max_show]:
        score = c.get("score", 0)
        body = c.get("body", "")[:200]
        op_tag = " [OP]" if c.get("is_op") else ""
        lines.append(f"  [{score} pts]{op_tag} {body}")
    return "\n".join(lines)


def _get_length_guidance(vibe: str, avg_comment_len: int) -> str:
    if vibe == "question":
        if avg_comment_len > 60:
            return "Detailed thread. Write 2-5 sentences with specific, useful info. Answer first, context second."
        else:
            return "Concise question thread. 1-3 sentences. Answer directly, one useful detail, done."
    elif vibe == "showcase":
        return "Showcase thread. 1-2 sentences. Notice a specific detail, don't be generic."
    elif vibe == "rant":
        return "Rant thread. Validate or offer practical advice. 1-3 sentences. Don't be preachy."
    elif vibe == "humor":
        return "Humor thread. Be funny or don't comment. 1 sentence max. Deadpan works."
    elif vibe == "news":
        return "News thread. Add context or a take. 1-3 sentences."
    else:
        if avg_comment_len > 50:
            return "Discussion thread. 2-4 sentences. Add something not yet said."
        else:
            return "Casual discussion. 1-2 sentences. Quick take or agree/disagree with a reason."


def _get_max_tokens(vibe: str, avg_comment_len: int) -> int:
    if vibe == "question" and avg_comment_len > 60:
        return 150
    elif vibe in ("question", "rant", "discussion") and avg_comment_len > 40:
        return 120
    elif vibe == "humor":
        return 40
    elif vibe == "showcase":
        return 60
    else:
        return 80


def _build_competitor_guidance(thread_context: dict) -> str:
    if not thread_context or not thread_context.get("is_competitor_thread"):
        return ""
    strategy = thread_context.get("competitor_strategy", {})
    guidance = strategy.get("ai_guidance", "")
    approach = strategy.get("approach", "helpful")
    tone = strategy.get("tone", "casual")
    mention = strategy.get("mention_cfw", False)

    parts = ["--- COMPETITOR THREAD STRATEGY ---"]
    parts.append(f"Approach: {approach}")
    parts.append(f"Tone: {tone}")
    if mention:
        parts.append("You CAN mention Chicago Fleet Wraps naturally if it fits.")
    else:
        parts.append("Do NOT mention any specific shop. Just be helpful.")
    if guidance:
        parts.append(f"Strategy: {guidance}")
    return "\n".join(parts)
