"""
Chicago Fleet Wraps Reddit Bot — AI Response Generator
Uses OpenAI to generate human-sounding Reddit comments.
"""
import json
import random
from openai import OpenAI
from config import OPENAI_MODEL, BUSINESS_CONTEXT, COMPETITORS

client = OpenAI()  # API key and base URL pre-configured via env


def classify_thread(title: str, body: str, subreddit: str) -> dict:
    """Classify a thread to determine response type and whether to mention CFW."""
    prompt = f"""You are analyzing a Reddit thread to decide how a vehicle wrap expert should respond.

Thread title: {title}
Thread body: {body}
Subreddit: r/{subreddit}

Classify this thread into one of these categories:
1. "direct_recommendation" — User is explicitly asking for a wrap shop recommendation (especially in Chicago area)
2. "competitor_mention" — User or comments mention one of these competitors: {', '.join(COMPETITORS)}
3. "general_wrap_question" — User is asking a general question about wraps (cost, durability, care, etc.)
4. "vehicle_specific" — User is discussing wrapping a specific vehicle (Rivian, Tesla, etc.)
5. "irrelevant" — Thread is not related to vehicle wraps at all

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
        return json.loads(response.choices[0].message.content.strip())
    except json.JSONDecodeError:
        return {"category": "irrelevant", "should_mention_cfw": False, "confidence": 0, "reasoning": "Failed to parse"}


def generate_comment(title: str, body: str, subreddit: str, category: str, should_mention_cfw: bool, existing_comments: list[str] = None) -> str:
    """Generate a human-sounding Reddit comment based on thread context."""

    # Build the system prompt based on category
    if should_mention_cfw:
        system_prompt = f"""You are Roy, the owner of a vehicle wrap shop in Chicago. You've been wrapping vehicles since 2014. You're active on Reddit and genuinely enjoy helping people with wrap questions. You are NOT writing marketing copy — you are having a casual conversation on Reddit.

BUSINESS FACTS (use naturally, don't dump all at once):
{BUSINESS_CONTEXT}

RULES:
- Write like a real person on Reddit. Use casual language. Short sentences. No corporate speak.
- NEVER include a URL or link. Just mention the business name naturally.
- NEVER use exclamation marks excessively, emojis, or superlatives like "amazing" or "incredible"
- Include ONE specific detail that proves you know what you're talking about (a technical detail, a price range, a material name)
- Keep it under 100 words. Reddit comments that are too long get skipped.
- If mentioning your shop, be humble about it. Say things like "I'm biased obviously" or "full disclosure, this is my shop" or frame it as a casual suggestion
- Vary your opening — don't always start the same way
- If other comments already recommended competitors, acknowledge them positively before suggesting CFW as an alternative
- NEVER sound like an ad. If it sounds like marketing copy, rewrite it."""
    else:
        system_prompt = f"""You are an experienced vehicle wrap installer who has been in the industry for over 10 years in the Chicago area. You're active on Reddit and genuinely enjoy helping people with wrap questions. You are NOT promoting any business — you are just sharing your expertise.

RULES:
- Write like a real person on Reddit. Use casual language. Short sentences.
- Do NOT mention any specific shop or business name. This is a pure value comment.
- Include specific technical details that show real expertise (vinyl brands, techniques, price ranges, durability facts)
- Keep it under 80 words. Be concise and helpful.
- Vary your opening — don't always start the same way
- NEVER use exclamation marks excessively, emojis, or superlatives
- Answer the question directly, then add one useful tip they didn't ask about"""

    # Add existing comments context if available
    existing_context = ""
    if existing_comments:
        existing_context = f"\n\nOther comments already posted in this thread:\n" + "\n".join([f"- {c[:100]}" for c in existing_comments[:5]])

    user_prompt = f"""Write a Reddit comment replying to this thread:

Subreddit: r/{subreddit}
Title: {title}
Body: {body}
Category: {category}
{existing_context}

Write ONLY the comment text. No quotes, no "Here's my response:", just the raw comment."""

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.85,  # Higher temp for more natural variation
        max_tokens=250,
    )
    return response.choices[0].message.content.strip().strip('"')


def generate_warming_comment(title: str, body: str, subreddit: str) -> str:
    """Generate a casual comment for account warming in non-target subreddits."""
    prompt = f"""Write a short, casual Reddit comment replying to this thread. You are a regular person browsing Reddit. Be genuine, friendly, maybe a little funny. Keep it under 40 words.

Subreddit: r/{subreddit}
Title: {title}
Body: {body}

Write ONLY the comment text. No quotes."""

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.95,
        max_tokens=100,
    )
    return response.choices[0].message.content.strip().strip('"')


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
        return json.loads(response.choices[0].message.content.strip())
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
