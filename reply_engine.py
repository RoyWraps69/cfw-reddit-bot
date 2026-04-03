"""
Chicago Fleet Wraps Reddit Bot — Reply Engine v1.0
Detects when someone replies to our comments and responds naturally
to keep the conversation going (builds karma + visibility).

Safety rules:
- Max 3 reply-backs per cycle (don't spam)
- Only reply to comments that are genuine engagement (not trolls)
- Never reply to the same person twice in one thread
- Match the energy of their reply
- If they're asking a question, answer it
- If they're agreeing, acknowledge briefly
- If they're hostile, don't engage
"""
import json
import os
import time
import random
from datetime import datetime
from openai import OpenAI
from config import DATA_DIR, REDDIT_USERNAME, OPENAI_MODEL, BUSINESS_CONTEXT

# Support custom base URL for API proxy
base_url = os.environ.get("OPENAI_BASE_URL", None)
if base_url:
    client = OpenAI(base_url=base_url)
else:
    client = OpenAI()

REPLIES_SENT_FILE = os.path.join(DATA_DIR, "replies_sent.json")
MAX_REPLIES_PER_CYCLE = 3
MAX_REPLIES_PER_DAY = 8


def _load_replies_sent() -> dict:
    """Load the record of replies we've already sent."""
    if os.path.exists(REPLIES_SENT_FILE):
        try:
            with open(REPLIES_SENT_FILE, "r") as f:
                data = json.load(f)
                # Reset if it's a new day
                if data.get("date") != str(datetime.now().date()):
                    return {"date": str(datetime.now().date()), "count": 0, "replied_to": []}
                return data
        except (json.JSONDecodeError, Exception):
            pass
    return {"date": str(datetime.now().date()), "count": 0, "replied_to": []}


def _save_replies_sent(data: dict):
    """Save the replies sent record."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(REPLIES_SENT_FILE, "w") as f:
        json.dump(data, f, indent=2)


def classify_reply(reply_text: str) -> dict:
    """Classify a reply to determine if and how we should respond.

    Returns:
        {"should_reply": bool, "reply_type": str, "reasoning": str}
        reply_type: "question", "agreement", "disagreement", "followup", "hostile", "spam"
    """
    prompt = f"""Classify this Reddit reply to determine if it warrants a response.

Reply: "{reply_text}"

Categories:
- "question" — they're asking a genuine question (ALWAYS reply)
- "agreement" — they agree or add to what we said (reply briefly ~50% of the time)
- "disagreement" — they respectfully disagree (reply if we can add value)
- "followup" — they're continuing the conversation (reply naturally)
- "hostile" — they're being rude/trolling (DO NOT reply)
- "spam" — irrelevant or bot-like (DO NOT reply)

Return ONLY valid JSON:
{{"should_reply": true/false, "reply_type": "...", "reasoning": "..."}}"""

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=100,
        )
        result = response.choices[0].message.content.strip()
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]
        return json.loads(result.strip())
    except Exception:
        return {"should_reply": False, "reply_type": "unknown", "reasoning": "Failed to classify"}


def generate_reply(our_comment: str, their_reply: str, reply_type: str,
                   subreddit: str, is_promo_thread: bool = False) -> str:
    """Generate a natural reply to someone who responded to our comment.

    The reply should:
    - Be shorter than our original comment (replies get shorter)
    - Answer their question if they asked one
    - Not repeat what we already said
    - Sound natural and conversational
    - Only mention CFW if they're directly asking for a recommendation
    """
    promo_context = ""
    if is_promo_thread:
        promo_context = f"""
If they're asking a follow-up about the shop/service, you can share more details:
{BUSINESS_CONTEXT}
But ONLY if they asked. Don't volunteer it."""

    type_guidance = {
        "question": "They asked a question. Answer it directly and concisely. 1-2 sentences max.",
        "agreement": "They agreed with you. Acknowledge briefly. 1 sentence max. Don't over-explain.",
        "disagreement": "They disagree. Acknowledge their point, share your perspective briefly. 1-2 sentences. Don't argue.",
        "followup": "They're continuing the conversation. Keep it going naturally. 1-2 sentences.",
    }

    guidance = type_guidance.get(reply_type, "Reply naturally. 1-2 sentences max.")

    prompt = f"""You're replying to someone who responded to your Reddit comment in r/{subreddit}.

YOUR ORIGINAL COMMENT: "{our_comment[:300]}"

THEIR REPLY: "{their_reply[:300]}"

{guidance}
{promo_context}

RULES:
- Be SHORTER than your original comment. Replies should get more concise.
- Don't repeat anything from your original comment
- Don't start with "Thanks" or "Appreciate it" or "Great point"
- Sound like a real person texting back quickly
- No exclamation marks
- No emojis
- If you don't have anything meaningful to add, just write "fair point" or similar

Write ONLY the reply text. Nothing else."""

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,
            max_tokens=60,
        )
        reply = response.choices[0].message.content.strip().strip('"').strip("'")
        # Remove AI-isms
        for opener in ["Honestly, ", "To be honest, ", "Great point! ", "That's a great question! "]:
            if reply.startswith(opener):
                reply = reply[len(opener):]
                reply = reply[0].upper() + reply[1:] if reply else reply
        return reply
    except Exception as e:
        print(f"  [REPLY ENGINE] Error generating reply: {e}", flush=True)
        return ""


def run_reply_cycle(reddit_session) -> dict:
    """Main reply cycle: check for replies to our comments and respond.

    Returns a summary dict.
    """
    print(f"\n  [REPLY ENGINE] Checking for replies to our comments...", flush=True)

    replies_data = _load_replies_sent()

    # Check daily limit
    if replies_data["count"] >= MAX_REPLIES_PER_DAY:
        print(f"  [REPLY ENGINE] Daily reply limit ({MAX_REPLIES_PER_DAY}) reached.", flush=True)
        return {"replies_sent": 0, "replies_found": 0}

    # Fetch our recent comments
    my_comments = reddit_session.get_my_comments(limit=25)
    if not my_comments:
        print(f"  [REPLY ENGINE] No comments found.", flush=True)
        return {"replies_sent": 0, "replies_found": 0}

    replies_found = 0
    replies_sent = 0
    already_replied_to = set(replies_data.get("replied_to", []))

    for comment in my_comments:
        if replies_sent >= MAX_REPLIES_PER_CYCLE:
            break

        permalink = comment.get("permalink", "")
        if not permalink:
            continue

        # Fetch replies to this comment
        try:
            replies = reddit_session.get_comment_replies(permalink)
        except Exception as e:
            print(f"  [REPLY ENGINE] Error fetching replies: {e}", flush=True)
            continue

        for reply in replies:
            if replies_sent >= MAX_REPLIES_PER_CYCLE:
                break

            author = reply.get("author", "")
            reply_body = reply.get("body", "")

            # Skip if already replied to this person in this thread
            reply_key = f"{comment.get('id', '')}:{author}"
            if reply_key in already_replied_to:
                continue

            # Skip bots and deleted
            if not author or author in ("[deleted]", "AutoModerator", REDDIT_USERNAME):
                continue

            replies_found += 1

            # Classify the reply
            classification = classify_reply(reply_body)
            should_reply = classification.get("should_reply", False)
            reply_type = classification.get("reply_type", "unknown")

            print(f"  [REPLY ENGINE] Reply from u/{author} in r/{comment.get('subreddit', '')}: "
                  f"type={reply_type}, should_reply={should_reply}", flush=True)
            print(f"    Their reply: \"{reply_body[:80]}...\"", flush=True)

            if not should_reply:
                print(f"    Skipping (classified as {reply_type})", flush=True)
                continue

            # For agreements, only reply ~50% of the time
            if reply_type == "agreement" and random.random() > 0.5:
                print(f"    Skipping agreement (coin flip)", flush=True)
                continue

            # Check if this was a promo thread
            is_promo = "chicagofleetwraps" in comment.get("body", "").lower() or \
                       "cfw" in comment.get("body", "").lower() or \
                       "chicago fleet" in comment.get("body", "").lower()

            # Generate reply
            reply_text = generate_reply(
                our_comment=comment.get("body", ""),
                their_reply=reply_body,
                reply_type=reply_type,
                subreddit=comment.get("subreddit", ""),
                is_promo_thread=is_promo,
            )

            if not reply_text:
                continue

            print(f"    Generated reply: \"{reply_text[:80]}\"", flush=True)

            # Post the reply (reply to their comment, not the thread)
            # We need the fullname of their reply comment
            # The reply's fullname would be t1_{reply_id}
            # But get_comment_replies doesn't return the reply ID
            # We need to post as a reply to the thread, targeting their comment

            # For now, post as a reply to the original thread, mentioning context
            # TODO: Need to get reply comment IDs from get_comment_replies
            try:
                # Post reply to the thread (as a new comment referencing the conversation)
                # Actually, we should reply to THEIR comment, not the thread
                # Let's use the thread fullname from our comment's link_id
                thread_id = comment.get("link_id", "")

                # We need to reply to their specific comment
                # Let's fetch the reply ID from the permalink
                reply_permalink = permalink
                url = f"https://old.reddit.com{reply_permalink}.json"
                resp = reddit_session.session.get(url, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list) and len(data) > 1:
                        for child in data[1].get("data", {}).get("children", []):
                            cd = child.get("data", {})
                            if cd.get("author") == author and cd.get("body", "")[:50] == reply_body[:50]:
                                reply_fullname = f"t1_{cd['id']}"
                                success = reddit_session.post_comment(reply_fullname, reply_text)
                                if success:
                                    replies_sent += 1
                                    replies_data["count"] += 1
                                    already_replied_to.add(reply_key)
                                    print(f"    REPLIED! ({replies_sent}/{MAX_REPLIES_PER_CYCLE})", flush=True)

                                    # Wait between replies
                                    delay = random.randint(30, 90)
                                    print(f"    Waiting {delay}s...", flush=True)
                                    time.sleep(delay)
                                break
            except Exception as e:
                print(f"    Error posting reply: {e}", flush=True)

        time.sleep(2)  # Rate limit between checking comments

    # Save state
    replies_data["replied_to"] = list(already_replied_to)[-100:]  # Keep last 100
    _save_replies_sent(replies_data)

    result = {"replies_sent": replies_sent, "replies_found": replies_found}
    print(f"  [REPLY ENGINE] Found {replies_found} replies, sent {replies_sent} responses.", flush=True)
    return result
