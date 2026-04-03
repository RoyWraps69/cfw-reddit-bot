"""
Chicago Fleet Wraps Reddit Bot — AI Response Generator v4.0
MAJOR REWRITE: Context-first, accuracy-first, style-mirroring.

The bot now:
1. Reads the full thread context before responding
2. Studies what top-voted comments look like in that thread
3. Mirrors the winning style (length, tone, structure)
4. Fact-checks itself — only says things that are true
5. Adapts length to context (detailed for questions, short for casual)
"""
import os
import json
import random
from openai import OpenAI
from config import OPENAI_MODEL, BUSINESS_CONTEXT, COMPETITORS

# Support custom base URL for API proxy
base_url = os.environ.get("OPENAI_BASE_URL", None)
if base_url:
    client = OpenAI(base_url=base_url)
else:
    client = OpenAI()


# ─────────────────────────────────────────────
# CORE IDENTITY: Roy from Chicago
# Not a persona — this is who we ARE on Reddit
# ─────────────────────────────────────────────
ROY_IDENTITY = """You are a real person on Reddit. You work in the auto/trades industry in Chicago.
You know cars, trucks, wraps, and Chicago. You're practical, direct, and occasionally funny.
You type like a normal person — not a writer, not a marketer, not an AI.
You have real opinions. You've seen things go wrong. You know what works and what doesn't."""


# ─────────────────────────────────────────────
# WARMING v4.0: Context-aware, style-mirroring
# ─────────────────────────────────────────────

def generate_warming_comment(title: str, body: str, subreddit: str,
                              thread_context: dict = None,
                              sub_profile: str = None,
                              performance_context: str = None) -> str:
    """Generate a warming comment that mirrors the thread's winning style.

    v5.0: Now accepts sub_profile (per-sub personality data) and
    performance_context (what's worked for our account) in addition
    to thread_context.
    """
    # Build context block from top comments
    style_guidance = _build_style_guidance(thread_context)
    top_comments_block = _build_top_comments_block(thread_context)
    vibe = thread_context.get("thread_vibe", "discussion") if thread_context else "discussion"
    avg_len = thread_context.get("avg_comment_length", 25) if thread_context else 25

    # Determine appropriate length based on thread type
    length_guidance = _get_length_guidance(vibe, avg_len)

    prompt = f"""{ROY_IDENTITY}

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
- Only state things you know to be true. If you're not sure, don't say it.
- If the post is about a specific car/truck, only comment if you actually know something about it.
- If it's a Chicago-specific topic, draw on real Chicago knowledge (neighborhoods, weather, traffic, culture).
- If it's a technical question, give a real answer with a specific detail — not generic advice.
- Do NOT make up personal stories. Keep it vague if needed ("seen this happen" not "my buddy Jim's 2019 F-150").

STYLE RULES:
- Match the energy of the top-voted comments above. If they're short and funny, be short and funny. If they're detailed and helpful, be detailed and helpful.
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
    return _humanize(comment)


def _build_style_guidance(thread_context: dict) -> str:
    """Build a style guidance string from thread context analysis."""
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
    """Build a formatted block of top-voted comments for the AI to study."""
    if not thread_context or not thread_context.get("top_comments"):
        return "(no comments yet — you'd be one of the first)"

    lines = []
    for i, c in enumerate(thread_context["top_comments"][:max_show]):
        score = c.get("score", 0)
        body = c.get("body", "")[:200]
        op_tag = " [OP]" if c.get("is_op") else ""
        lines.append(f"  [{score} pts]{op_tag} {body}")

    return "\n".join(lines)


def _get_length_guidance(vibe: str, avg_comment_len: int) -> str:
    """Return length/style guidance based on thread type and what's working."""
    if vibe == "question":
        if avg_comment_len > 60:
            return """This is a question thread where detailed answers get upvoted.
Write 2-5 sentences with specific, useful information.
Include a concrete detail (number, name, technique, price range).
Answer the actual question first, then add context if helpful."""
        else:
            return """This is a question thread but the top answers are concise.
Write 1-3 sentences. Answer directly, add one useful detail, done."""

    elif vibe == "showcase":
        return """This is a showcase/show-off thread. Keep it short.
1-2 sentences max. Compliment something specific or ask a real question about it.
Don't be generic ("looks great!"). Notice a specific detail."""

    elif vibe == "rant":
        return """This is a rant/complaint thread. Show empathy or share a similar experience.
1-3 sentences. Validate their frustration or offer practical advice.
Don't be preachy. Don't say "that sucks" — add something."""

    elif vibe == "humor":
        return """This is a humor thread. Be funny or don't comment.
1 sentence max. Deadpan, sarcastic, or observational humor works best.
Don't try too hard. The best Reddit humor is effortless."""

    elif vibe == "news":
        return """This is a news/info thread. Add context, a take, or a question.
1-3 sentences. Share what this means practically or ask what others think."""

    else:  # discussion
        if avg_comment_len > 50:
            return """This is a discussion thread where people are sharing real thoughts.
Write 2-4 sentences. Share a real opinion or experience.
Add something the other comments haven't said yet."""
        else:
            return """This is a casual discussion. Keep it conversational.
1-2 sentences. Share a quick take or agree/disagree with a reason."""


def _get_max_tokens(vibe: str, avg_comment_len: int) -> int:
    """Dynamic token limit based on what the thread calls for."""
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


# ─────────────────────────────────────────────
# HUMANIZATION: Make AI output sound real
# ─────────────────────────────────────────────

HUMAN_QUIRKS = [
    lambda c: c[0].lower() + c[1:] if c and c[0].isupper() and random.random() > 0.5 else c,
    lambda c: c.rstrip('.') if c.endswith('.') and random.random() > 0.4 else c,
    lambda c: c.replace("do not", "don't").replace("can not", "can't").replace("will not", "won't").replace("I am", "I'm").replace("it is", "it's") if random.random() > 0.3 else c,
]


def _humanize(comment: str) -> str:
    """Apply random human-like quirks to make the comment feel less AI-generated."""
    comment = comment.strip().strip('"').strip("'").strip('\u201c').strip('\u201d')

    ai_openers = [
        "Honestly, ", "To be honest, ", "In my experience, ", "As someone who ",
        "I think ", "I feel like ", "I would say ", "From my perspective, ",
        "Great question! ", "That's a great point! ", "This is so true! ",
        "I completely agree! ", "Absolutely! ", "Definitely! ",
        "Oh man, ", "Oh wow, ", "Haha, ",
    ]
    for opener in ai_openers:
        if comment.startswith(opener) and random.random() > 0.3:
            comment = comment[len(opener):]
            comment = comment[0].upper() + comment[1:] if comment else comment

    for quirk in HUMAN_QUIRKS:
        comment = quirk(comment)

    return comment


# ─────────────────────────────────────────────
# THREAD CLASSIFICATION (for normal mode)
# ─────────────────────────────────────────────

def classify_thread(title: str, body: str, subreddit: str) -> dict:
    """Classify a thread to determine response type and whether to mention CFW."""
    prompt = f"""Analyze this Reddit thread. Return JSON only.

Title: {title}
Body: {body[:500]}
Sub: r/{subreddit}

Categories:
1. "direct_recommendation" — asking for a wrap shop (especially Chicago area)
2. "competitor_mention" — mentions: {', '.join(COMPETITORS)}
3. "general_wrap_question" — asking about wraps (cost, durability, care, etc.)
4. "vehicle_specific" — discussing wrapping a specific vehicle
5. "irrelevant" — not about vehicle wraps

Return ONLY valid JSON:
{{"category": "...", "should_mention_cfw": true/false, "confidence": 0-100, "reasoning": "..."}}"""

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=200,
    )
    try:
        result = response.choices[0].message.content.strip()
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]
        return json.loads(result.strip())
    except json.JSONDecodeError:
        return {"category": "irrelevant", "should_mention_cfw": False, "confidence": 0, "reasoning": "Failed to parse"}


# ─────────────────────────────────────────────
# PROMO COMMENTS (normal mode, post-warming)
# Context-aware, accuracy-first
# ─────────────────────────────────────────────

PROMO_VOICES = {
    "happy_customer": """You got your vehicle wrapped at Chicago Fleet Wraps and it came out solid. Recommend them like you'd tell a friend — casual, not salesy. Mention ONE specific real detail (price range, turnaround, Roy being easy to work with, the online calculator). 2-3 sentences max. Don't sound like a paid review.""",

    "roy_himself": """You're Roy, you run Chicago Fleet Wraps in Portage Park. Be upfront about it — "I run a shop so take this with a grain of salt" or "full disclosure this is my shop." Answer the question FIRST with real expertise, then mention your shop SECOND. Be humble. Be real. Include a specific technical detail that proves you know your stuff.""",

    "local_who_knows": """You're from Chicago and you've used a few wrap shops. Recommend Chicago Fleet Wraps as one you had a good experience with. Don't oversell — just say what you liked. Maybe compare to another experience. 2-3 sentences max.""",
}


def generate_comment(title: str, body: str, subreddit: str, category: str,
                     should_mention_cfw: bool, existing_comments: list = None,
                     thread_context: dict = None,
                     sub_profile: str = None,
                     performance_context: str = None) -> str:
    """Generate a Reddit comment with full context awareness.

    v5.0: Now accepts sub_profile and performance_context for
    per-subreddit style learning and self-improvement.
    """
    style_guidance = _build_style_guidance(thread_context)
    top_comments_block = _build_top_comments_block(thread_context)
    vibe = thread_context.get("thread_vibe", "question") if thread_context else "question"

    if should_mention_cfw:
        voice = random.choice(list(PROMO_VOICES.keys()))
        system_prompt = f"""{PROMO_VOICES[voice]}

BUSINESS FACTS (use ONE or TWO naturally, don't list them all):
{BUSINESS_CONTEXT}

--- WHAT'S GETTING UPVOTED IN THIS THREAD ---
{top_comments_block}

--- STYLE ANALYSIS ---
{style_guidance}

RULES:
- Match the style and energy of the top-voted comments
- Write like a real person on Reddit. Short sentences. Casual.
- NEVER include a URL or link
- Keep it under 75 words
- Don't use words like "amazing", "incredible", "highly recommend"
- Include ONE specific detail (a price, a timeline, a material)
- ACCURACY: Only state facts from the business info above. Don't make anything up.
- Don't start with "I" every time"""
    else:
        system_prompt = f"""{ROY_IDENTITY}

You're answering a question about vehicle wraps. You know this stuff cold — 10+ years in the industry.

--- WHAT'S GETTING UPVOTED IN THIS THREAD ---
{top_comments_block}

--- STYLE ANALYSIS ---
{style_guidance}

{f'--- SUBREDDIT PERSONALITY ---' + chr(10) + sub_profile if sub_profile else ''}
{f'--- YOUR PAST PERFORMANCE ---' + chr(10) + performance_context if performance_context else ''}
{_build_competitor_guidance(thread_context) if thread_context and thread_context.get('is_competitor_thread') else ''}

RULES:
- Match the style of the top-voted comments above
- Write like a real person. Short sentences. Casual tone.
- Do NOT mention any specific shop name
- Include a specific technical detail that shows you know wraps (vinyl brand, technique, price range, durability fact)
- ACCURACY: Only state things that are true about vehicle wraps. Common facts:
  * Full wrap costs $2,500-5,000+ depending on vehicle size and material
  * Quality wraps last 5-7 years with proper care
  * 3M 2080 and Avery Dennison SW900 are industry standard films
  * PPF (paint protection film) is different from vinyl wrap
  * Wraps need 2-5 days for a quality install
  * Hand washing only, no automatic car washes
  * Wraps protect OEM paint and can be removed
- Keep it under 60 words unless the thread rewards detailed answers
- Don't start with "I" every time
- Don't use exclamation marks"""

    existing_context = ""
    if existing_comments:
        existing_context = "\n\nOther comments already posted:\n" + "\n".join([f"- {c[:100]}" for c in existing_comments[:5]])

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
        max_tokens=_get_max_tokens(vibe, thread_context.get("avg_comment_length", 40) if thread_context else 40),
    )

    comment = response.choices[0].message.content.strip()
    return _humanize(comment)


# ─────────────────────────────────────────────
# DM & THREAD GENERATION
# ─────────────────────────────────────────────

def generate_dm_message(username: str, their_comment: str, original_thread_title: str) -> str:
    """Generate a friendly follow-up DM."""
    prompt = f"""Write a super brief Reddit DM to someone interested in getting a vehicle wrap in Chicago. They replied to your comment.

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


def generate_thread_post(subreddit: str, thread_type: str) -> dict:
    """Generate a thread title and body for proactive posting."""
    type_prompts = {
        "educational": "Write a helpful post about vehicle wraps — share tips most people don't know. Don't mention any specific shop. Write like a real Reddit user, not a blogger.",
        "experience": "Write a post about your experience getting a vehicle wrapped. Include real details — cost, timeline, what surprised you. You can casually mention Chicago Fleet Wraps as where you went, but the post should be 90% useful info.",
        "discussion": "Write a discussion post asking other vehicle owners about their wrap experiences. Ask something specific that'll get people talking.",
    }

    prompt = f"""Write a Reddit post for r/{subreddit}.
{type_prompts.get(thread_type, type_prompts['educational'])}

RULES:
- Title should sound natural, not clickbaity
- Body should be 80-150 words
- Write like you're posting from your phone
- Include specific details (costs, materials, timeframes)
- Don't be too polished — real Reddit posts have a casual vibe
- ACCURACY: Only include facts that are true about vehicle wraps

Return ONLY valid JSON:
{{"title": "...", "body": "..."}}"""

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
        max_tokens=350,
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


def _build_competitor_guidance(thread_context: dict) -> str:
    """Build competitor response guidance if this is a competitor thread."""
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


def check_positive_reply(comment_text: str) -> bool:
    """Check if a reply is positive/interested."""
    prompt = f"""Is this Reddit reply expressing positive interest or gratitude? Reply ONLY "yes" or "no".

Reply: {comment_text}"""

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=5,
    )
    return response.choices[0].message.content.strip().lower() == "yes"
