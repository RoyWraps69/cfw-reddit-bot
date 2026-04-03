"""
Chicago Fleet Wraps Reddit Bot — AI Response Generator v2.0
Optimized for higher-quality warming comments that actually get upvotes,
plus persona variety and smarter response generation.
"""
import os
import json
import random
from openai import OpenAI
from config import OPENAI_MODEL, BUSINESS_CONTEXT, COMPETITORS

# Support custom base URL for API proxy (e.g., Manus proxy)
base_url = os.environ.get("OPENAI_BASE_URL", None)
if base_url:
    client = OpenAI(base_url=base_url)
else:
    client = OpenAI()

WARMING_PERSONAS = [
    "You're a 35-year-old guy from Chicago who works in the trades. You're funny, down to earth, and use casual language. You like cars, sports, and grilling.",
    "You're a 40-year-old small business owner from the Chicago suburbs. You're practical, straightforward, and occasionally sarcastic in a friendly way.",
    "You're a 30-year-old car enthusiast who spends too much time on Reddit. You're knowledgeable about vehicles and enjoy sharing opinions.",
    "You're a regular Reddit user who gives honest, no-BS answers. You keep it short and real. You're from the Midwest.",
    "You're a friendly, helpful person who genuinely enjoys answering questions on Reddit. You're concise and add a touch of humor when appropriate.",
]

WARMING_STYLES = {
    "witty_short": "Write a short, witty comment (1-2 sentences max). Be clever but not try-hard. The best Reddit comments are the ones that make people exhale through their nose.",
    "helpful_answer": "Give a genuinely helpful, direct answer. Lead with the answer, then add one useful detail. Be the comment people upvote because it actually helped.",
    "relatable": "Say what everyone reading this thread is probably thinking. Be relatable and authentic. Keep it to 1-3 sentences.",
    "add_context": "Add a useful perspective or detail that others in the thread probably missed. Show you know what you're talking about without being a know-it-all. 2-3 sentences max.",
    "personal_story": "Share a very brief personal anecdote (2-3 sentences) that's relevant to the thread. Make it specific enough to feel real, not generic.",
}


def generate_warming_comment(title: str, body: str, subreddit: str) -> str:
    """Generate a casual comment for account warming -- optimized for upvotes."""
    persona = random.choice(WARMING_PERSONAS)
    style_name = random.choice(list(WARMING_STYLES.keys()))
    style_instruction = WARMING_STYLES[style_name]

    prompt = f"""{persona}

You are browsing Reddit and came across this post. Write a comment that feels completely natural.

Subreddit: r/{subreddit}
Title: {title}
Body: {body[:500]}

STYLE: {style_instruction}

CRITICAL RULES:
- Do NOT mention anything about vehicle wraps, cars, or your job unless the thread is specifically about that
- Do NOT be overly positive or enthusiastic -- real Reddit comments are often understated
- Do NOT use exclamation marks more than once (if at all)
- Do NOT start with "I" -- vary your openings
- Do NOT use phrases like "This!", "So much this!", "Came here to say this"
- Do NOT use emojis
- Keep it under 50 words
- Sound like a real person, not an AI
- Match the tone and energy of the subreddit

Write ONLY the comment text. Nothing else."""

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.95,
        max_tokens=120,
    )

    comment = response.choices[0].message.content.strip().strip('"').strip("'")
    comment = comment.replace("As someone who", "Someone who")
    if comment.startswith("Honestly, ") and random.random() > 0.3:
        comment = comment[10:]
    return comment


def classify_thread(title: str, body: str, subreddit: str) -> dict:
    """Classify a thread to determine response type and whether to mention CFW."""
    prompt = f"""You are analyzing a Reddit thread to decide how a vehicle wrap expert should respond.

Thread title: {title}
Thread body: {body[:500]}
Subreddit: r/{subreddit}

Classify this thread into one of these categories:
1. "direct_recommendation" -- User is explicitly asking for a wrap shop recommendation (especially in Chicago area)
2. "competitor_mention" -- User or comments mention one of these competitors: {', '.join(COMPETITORS)}
3. "general_wrap_question" -- User is asking a general question about wraps (cost, durability, care, etc.)
4. "vehicle_specific" -- User is discussing wrapping a specific vehicle (Rivian, Tesla, etc.)
5. "irrelevant" -- Thread is not related to vehicle wraps at all

Also determine:
- should_mention_cfw: true/false (only true for direct_recommendation or competitor_mention)
- confidence: 0-100 (how confident you are this is a good thread to respond to)
- reasoning: brief explanation

Return ONLY valid JSON, no markdown:
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


PROMO_VOICES = {
    "casual_customer": "You are someone who got their vehicle wrapped at Chicago Fleet Wraps and had a great experience. You're recommending them casually, like telling a friend. Use first-person. Include ONE specific detail from your experience.",
    "industry_insider": "You are Roy, the owner of Chicago Fleet Wraps. You're active on Reddit and genuinely enjoy helping people. Be transparent -- say 'full disclosure, this is my shop' or 'I'm biased obviously.' Be humble and helpful first, promotional second.",
    "local_expert": "You are someone from the Chicago area who has researched wrap shops extensively. You're recommending Chicago Fleet Wraps as one of the good options. Mention ONE specific thing that sets them apart (pricing transparency, Rivian experience, etc.).",
}


def generate_comment(title: str, body: str, subreddit: str, category: str, should_mention_cfw: bool, existing_comments: list = None) -> str:
    """Generate a human-sounding Reddit comment based on thread context."""

    if should_mention_cfw:
        voice = random.choice(list(PROMO_VOICES.keys()))
        system_prompt = f"""{PROMO_VOICES[voice]}

BUSINESS FACTS (use naturally, pick ONE or TWO max):
{BUSINESS_CONTEXT}

RULES:
- Write like a real person on Reddit. Casual language. Short sentences. No corporate speak.
- NEVER include a URL or link. Just mention the business name naturally.
- NEVER use exclamation marks excessively, emojis, or superlatives like "amazing" or "incredible"
- Keep it under 100 words. Reddit comments that are too long get skipped.
- If other comments already recommended competitors, acknowledge them positively before suggesting CFW
- NEVER sound like an ad. If it reads like marketing copy, rewrite it.
- Vary your opening -- don't start with "I" every time
- Include ONE specific detail that proves authenticity (a price, a material, a timeline)"""
    else:
        system_prompt = """You are an experienced vehicle wrap installer who has been in the industry for over 10 years in the Chicago area. You're active on Reddit and genuinely enjoy helping people with wrap questions. You are NOT promoting any business -- you are just sharing your expertise.

RULES:
- Write like a real person on Reddit. Casual language. Short sentences.
- Do NOT mention any specific shop or business name. This is a pure value comment.
- Include specific technical details that show real expertise (vinyl brands, techniques, price ranges, durability facts)
- Keep it under 80 words. Be concise and helpful.
- Vary your opening -- don't always start the same way
- NEVER use exclamation marks excessively, emojis, or superlatives
- Answer the question directly, then add one useful tip they didn't ask about"""

    existing_context = ""
    if existing_comments:
        existing_context = "\n\nOther comments already posted in this thread:\n" + "\n".join([f"- {c[:100]}" for c in existing_comments[:5]])

    user_prompt = f"""Write a Reddit comment replying to this thread:

Subreddit: r/{subreddit}
Title: {title}
Body: {body[:500]}
Category: {category}
{existing_context}

Write ONLY the comment text. No quotes, no "Here's my response:", just the raw comment."""

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.85,
        max_tokens=250,
    )

    comment = response.choices[0].message.content.strip().strip('"').strip("'")
    return comment


def generate_dm_message(username: str, their_comment: str, original_thread_title: str) -> str:
    """Generate a friendly follow-up DM when someone responds positively."""
    prompt = f"""Write a very brief, friendly Reddit DM to someone who showed interest in getting a vehicle wrap in Chicago. They replied positively in a thread.

Their username: u/{username}
Thread title: {original_thread_title}
Their reply: {their_comment}

Include the pricing calculator link: chicagofleetwraps.com/calculator
Keep it under 50 words. Sound like a real person, not a salesperson.

Write ONLY the DM text."""

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
        max_tokens=120,
    )
    return response.choices[0].message.content.strip().strip('"')


def generate_thread_post(subreddit: str, thread_type: str) -> dict:
    """Generate a thread title and body for proactive posting."""
    type_prompts = {
        "educational": "Write a helpful educational post about vehicle wraps. Share practical tips that most people don't know. Don't mention any specific shop.",
        "experience": "Write a post sharing your experience getting a vehicle wrapped. Include specific details about the process, what surprised you, and tips for others. You can casually mention Chicago Fleet Wraps as where you got it done, but the post should be 90% educational.",
        "discussion": "Write a discussion post asking other vehicle owners about their wrap experiences. Ask a specific question that will generate good responses.",
    }

    prompt = f"""You are writing a Reddit post for r/{subreddit}.
{type_prompts.get(thread_type, type_prompts['educational'])}

RULES:
- Title should be engaging and specific (not clickbait)
- Body should be 100-200 words
- Write like a real Reddit user, not a marketer
- Include specific details (costs, materials, timeframes)

Return ONLY valid JSON:
{{"title": "...", "body": "..."}}"""

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.85,
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


def check_positive_reply(comment_text: str) -> bool:
    """Check if a reply to our comment is positive/interested."""
    prompt = f"""Is this Reddit reply expressing positive interest or gratitude? Reply ONLY "yes" or "no".

Reply: {comment_text}"""

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=5,
    )
    return response.choices[0].message.content.strip().lower() == "yes"
