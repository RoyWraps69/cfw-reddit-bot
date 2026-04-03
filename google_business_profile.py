"""
Chicago Fleet Wraps — Google Business Profile Automation v1.0

GBP posts are a direct ranking signal for local search.
Shops that post weekly rank measurably higher for "wrap shop near me."

This module:
1. Posts to GBP weekly (images + offers + updates)
2. Monitors and auto-drafts review responses
3. Manages the Q&A section
4. Tracks GBP insights (views, calls, direction requests)

API: Google My Business API v4.9
Requires: SERVICE_ACCOUNT_KEY_FILE or GBP_ACCESS_TOKEN env var
"""

import os
import json
import random
from datetime import datetime, date, timedelta
from openai import OpenAI

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

GBP_ACCESS_TOKEN = os.environ.get("GBP_ACCESS_TOKEN", "")
GBP_ACCOUNT_ID = os.environ.get("GBP_ACCOUNT_ID", "")
GBP_LOCATION_ID = os.environ.get("GBP_LOCATION_ID", "")  # The specific business location

GBP_LOG = os.path.join(DATA_DIR, "gbp_log.json")
REVIEW_LOG = os.path.join(DATA_DIR, "gbp_reviews.json")

client = OpenAI()

CFW_CONTEXT = """
Chicago Fleet Wraps | 4711 N. Lamon Ave, Chicago IL 60630 | Portage Park neighborhood
Owner: Roy | Since 2014 | 600+ Rivians wrapped | (312) 597-1286 | chicagofleetwraps.com
Services: Fleet wraps, color change, PPF, vinyl lettering, EV wraps
Materials: 3M 2080, Avery Dennison SW900, XPEL PPF
Fleet discount up to 15% | Online price calculator | 3-5 day turnaround
"""

# ─────────────────────────────────────────────────────────────────────
# GBP POST TYPES — Rotated weekly
# ─────────────────────────────────────────────────────────────────────

GBP_POST_TYPES = [
    "what_s_new",      # Standard update post
    "event",           # Seasonal promotion
    "offer",           # Discount or special
    "product",         # Highlight a specific service
]

WEEKLY_POST_THEMES = [
    {"week_mod": 0, "theme": "before_after", "type": "what_s_new"},
    {"week_mod": 1, "theme": "fleet_discount", "type": "offer"},
    {"week_mod": 2, "theme": "education", "type": "what_s_new"},
    {"week_mod": 3, "theme": "rivian_specialty", "type": "product"},
]

# ─────────────────────────────────────────────────────────────────────
# POST GENERATION
# ─────────────────────────────────────────────────────────────────────

def generate_gbp_post(theme: str = None, post_type: str = "what_s_new") -> dict:
    """Generate a Google Business Profile post with AI."""
    from sales_psychology import get_seasonal_urgency

    if not theme:
        week_number = date.today().isocalendar()[1]
        theme_data = WEEKLY_POST_THEMES[week_number % len(WEEKLY_POST_THEMES)]
        theme = theme_data["theme"]
        post_type = theme_data["type"]

    seasonal = get_seasonal_urgency()

    theme_prompts = {
        "before_after": "Write a Google Business Profile post about a recent vehicle wrap transformation. Include the vehicle type and one specific detail about the result. End with a call to action.",
        "fleet_discount": "Write a Google Business Profile OFFER post about CFW's fleet discount (up to 15% off for 3+ vehicles). Include the ROI angle — a wrapped van is a $62/month billboard. Add a CTA.",
        "education": "Write a Google Business Profile post that educates local businesses about vehicle wraps — one specific tip or fact they don't know. Example: how to tell a quality install from a cheap one.",
        "rivian_specialty": "Write a Google Business Profile post about CFW's Rivian wrap specialty. 600+ Rivians wrapped. Location near the Bloomington plant. Rivian owners in Chicago know this shop.",
        "ppf": "Write a Google Business Profile post about paint protection film (PPF) — what it is, why EVs especially benefit, that CFW uses XPEL.",
        "seasonal_spring": "Write a Google Business Profile post about spring wrap season — why spring is ideal (no salt, long UV season ahead). Include spring booking note.",
        "tax_season": "Write a Google Business Profile post about Section 179 tax deductions for business vehicle wraps. Deadline December 31. Direct CTA to get a quote now.",
        "chicago_specific": "Write a Google Business Profile post about why Chicago specifically is a great city to have a wrapped vehicle — traffic, density, parking, impressions per day.",
    }

    prompt = f"""Write a Google Business Profile post for Chicago Fleet Wraps.

BUSINESS CONTEXT:
{CFW_CONTEXT}

THEME: {theme_prompts.get(theme, theme_prompts['before_after'])}

{f'SEASONAL CONTEXT: {seasonal}' if seasonal else ''}

RULES:
- 150-300 words (GBP sweet spot)
- Include the business name at least once naturally
- End with ONE clear call to action (phone, website, or "Get a free quote")
- Sound like a real local business, not a marketing agency
- Include at least one specific fact (price, timeline, material name, number)
- No hashtags (not needed on GBP)

Return ONLY valid JSON:
{{"summary": "150-300 word post text", "call_to_action": {{"actionType": "CALL|LEARN_MORE|SIGN_UP|ORDER", "url": "optional URL"}}, "post_type": "{post_type}"}}"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
        max_tokens=600,
        response_format={"type": "json_object"},
    )

    try:
        result = json.loads(response.choices[0].message.content)
        result["theme"] = theme
        result["generated_at"] = str(datetime.now())
        return result
    except Exception:
        return {
            "summary": "Chicago Fleet Wraps — wrapping vehicles in Portage Park since 2014. Fleet discounts up to 15%. Online price calculator at chicagofleetwraps.com. Call (312) 597-1286.",
            "call_to_action": {"actionType": "CALL"},
            "post_type": post_type,
            "theme": theme,
        }


def publish_gbp_post(post_data: dict) -> dict:
    """Publish a post to Google Business Profile via API."""
    if not GBP_ACCESS_TOKEN or not GBP_LOCATION_ID:
        return {"status": "no_credentials",
                "note": "Set GBP_ACCESS_TOKEN and GBP_LOCATION_ID. See setup guide.",
                "post_preview": post_data.get("summary", "")[:200]}

    url = f"https://mybusiness.googleapis.com/v4/accounts/{GBP_ACCOUNT_ID}/locations/{GBP_LOCATION_ID}/localPosts"
    headers = {
        "Authorization": f"Bearer {GBP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "languageCode": "en-US",
        "summary": post_data.get("summary", ""),
        "topicType": post_data.get("post_type", "STANDARD").upper().replace("what_s_new", "STANDARD"),
    }

    cta = post_data.get("call_to_action", {})
    if cta.get("actionType"):
        payload["callToAction"] = {
            "actionType": cta.get("actionType", "CALL"),
        }
        if cta.get("url"):
            payload["callToAction"]["url"] = cta["url"]

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code in (200, 201):
            result = response.json()
            _log_gbp_action("post_published", {"post_name": result.get("name"), "theme": post_data.get("theme")})
            return {"status": "published", "post_name": result.get("name"), "theme": post_data.get("theme")}
        else:
            return {"status": "error", "code": response.status_code, "body": response.text[:300]}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def run_weekly_gbp_post() -> dict:
    """Generate and publish this week's GBP post."""
    post = generate_gbp_post()
    result = publish_gbp_post(post)
    print(f"[GBP] Weekly post: {result.get('status')} | Theme: {post.get('theme')}", flush=True)
    return {"post": post, "result": result}


# ─────────────────────────────────────────────────────────────────────
# REVIEW MANAGEMENT
# ─────────────────────────────────────────────────────────────────────

def fetch_reviews(min_rating: int = None) -> list:
    """Fetch reviews from GBP API."""
    if not GBP_ACCESS_TOKEN or not GBP_LOCATION_ID:
        return []

    url = f"https://mybusiness.googleapis.com/v4/accounts/{GBP_ACCOUNT_ID}/locations/{GBP_LOCATION_ID}/reviews"
    headers = {"Authorization": f"Bearer {GBP_ACCESS_TOKEN}"}

    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            reviews = response.json().get("reviews", [])
            if min_rating is not None:
                rating_map = {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5}
                reviews = [r for r in reviews
                           if rating_map.get(r.get("starRating", "THREE"), 3) >= min_rating]
            return reviews
    except Exception as e:
        print(f"[GBP] Review fetch error: {e}", flush=True)
    return []


def generate_review_response(review_text: str, star_rating: int, reviewer_name: str = "Customer") -> str:
    """Generate a response to a Google review using AI."""

    if star_rating >= 4:
        tone_instruction = "Warm, grateful, and genuine. Thank them specifically for what they mentioned. Keep it 2-3 sentences."
    elif star_rating == 3:
        tone_instruction = "Appreciative but address their concern directly. Offer to make it right. 3-4 sentences. Include the phone number."
    else:
        tone_instruction = "Empathetic, professional, never defensive. Acknowledge their experience, apologize, offer a direct resolution path. Include Roy's direct line (312) 597-1286. 3-4 sentences."

    prompt = f"""Write a Google review response for Chicago Fleet Wraps.

REVIEWER: {reviewer_name}
RATING: {star_rating}/5 stars
REVIEW: {review_text}

TONE: {tone_instruction}

RULES:
- Start with the reviewer's name
- Sound like Roy, the owner — genuine and direct
- Never copy-paste generic "We value your feedback" language
- If positive: reference something specific from their review
- If negative: don't be defensive, offer a real resolution
- End with an invite to come back or call
- Max 100 words

Write ONLY the response text."""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=200,
    )
    return response.choices[0].message.content.strip()


def reply_to_review(review_name: str, response_text: str) -> dict:
    """Post a reply to a specific review via GBP API."""
    if not GBP_ACCESS_TOKEN:
        return {"status": "no_credentials", "response_preview": response_text[:100]}

    url = f"https://mybusiness.googleapis.com/v4/{review_name}/reply"
    headers = {
        "Authorization": f"Bearer {GBP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.put(url, headers=headers, json={"comment": response_text}, timeout=30)
        if response.status_code == 200:
            _log_gbp_action("review_replied", {"review_name": review_name})
            return {"status": "replied"}
        else:
            return {"status": "error", "code": response.status_code}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def run_review_response_cycle() -> dict:
    """Check for unanswered reviews and generate/post responses."""
    reviews = fetch_reviews()
    results = {"checked": len(reviews), "responded": 0, "flagged": 0}
    rating_map = {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5}

    for review in reviews:
        # Skip if already responded
        if review.get("reviewReply"):
            continue

        reviewer = review.get("reviewer", {}).get("displayName", "Customer")
        review_text = review.get("comment", "")
        star_str = review.get("starRating", "FOUR")
        stars = rating_map.get(star_str, 4)
        review_name = review.get("name", "")

        if not review_text or not review_name:
            continue

        # Flag low reviews for immediate Roy notification
        if stars <= 2:
            from lead_alert import send_hot_lead_alert
            send_hot_lead_alert(
                platform="google_review",
                username=reviewer,
                message_text=f"{stars}★: {review_text}",
                intent_level="hot",
                lead_score=10,
            )
            results["flagged"] += 1

        response_text = generate_review_response(review_text, stars, reviewer)
        reply_result = reply_to_review(review_name, response_text)

        if reply_result.get("status") == "replied":
            results["responded"] += 1

    print(f"[GBP] Review cycle: checked={results['checked']}, responded={results['responded']}, flagged={results['flagged']}", flush=True)
    return results


# ─────────────────────────────────────────────────────────────────────
# Q&A MANAGEMENT
# ─────────────────────────────────────────────────────────────────────

CFW_QA_PAIRS = [
    {
        "question": "How much does a cargo van wrap cost?",
        "answer": "Cargo van wraps at Chicago Fleet Wraps start around $3,750 for a full wrap using premium 3M or Avery film. Get an exact quote in 60 seconds at chicagofleetwraps.com/calculator — no phone call required. We respond within 2 hours with detailed pricing.",
    },
    {
        "question": "Do you wrap Rivian vehicles?",
        "answer": "Yes — we've wrapped over 600 Rivians and have a second location in Bloomington, IL near the Rivian plant. We're one of the most experienced Rivian wrap shops in the Midwest. Call (312) 597-1286 or visit chicagofleetwraps.com.",
    },
    {
        "question": "How long does a vehicle wrap take?",
        "answer": "Most jobs take 3-5 business days at Chicago Fleet Wraps. Fleet jobs with multiple vehicles are scheduled accordingly. We'll give you an exact timeline with your quote.",
    },
    {
        "question": "Do you offer fleet discounts?",
        "answer": "Yes — we offer up to 15% off for fleet orders (3 or more vehicles). Fleet wraps are also typically deductible under Section 179 as a business expense. Call us at (312) 597-1286 to discuss fleet pricing.",
    },
    {
        "question": "What vinyl brands do you use?",
        "answer": "We use 3M 2080 series, Avery Dennison Supreme Wrapping Film (SW900), and XPEL for paint protection film (PPF). We don't use gray-market or budget films — it shows in the longevity.",
    },
    {
        "question": "How long does a wrap last?",
        "answer": "Quality wraps using 3M or Avery film last 5-7 years with proper care (hand wash only, no automatic car washes). We've seen our installs hold up through Chicago winters for 7+ years when properly maintained.",
    },
    {
        "question": "Do you do paint protection film (PPF)?",
        "answer": "Yes — we install XPEL PPF for paint protection. PPF protects against rock chips, road debris, and UV damage. It can be applied clear (invisible) or in satin/matte finishes. Great for EVs, Rivians, and high-end vehicles.",
    },
]


def seed_gbp_qa() -> dict:
    """Post pre-written Q&A pairs to the GBP Questions section."""
    if not GBP_ACCESS_TOKEN or not GBP_LOCATION_ID:
        return {"status": "no_credentials", "qa_count": len(CFW_QA_PAIRS)}

    results = {"seeded": 0, "errors": 0}
    url = f"https://mybusiness.googleapis.com/v4/accounts/{GBP_ACCOUNT_ID}/locations/{GBP_LOCATION_ID}/questions"
    headers = {"Authorization": f"Bearer {GBP_ACCESS_TOKEN}", "Content-Type": "application/json"}

    for qa in CFW_QA_PAIRS:
        try:
            # First post the question, then answer it
            q_response = requests.post(url, headers=headers, json={"text": qa["question"]}, timeout=20)
            if q_response.status_code == 200:
                question_name = q_response.json().get("name", "")
                if question_name:
                    answer_url = f"https://mybusiness.googleapis.com/v4/{question_name}/answers"
                    requests.post(answer_url, headers=headers, json={"text": qa["answer"]}, timeout=20)
                    results["seeded"] += 1
        except Exception:
            results["errors"] += 1

    return results


# ─────────────────────────────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────────────────────────────

def _log_gbp_action(action: str, data: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    log = []
    if os.path.exists(GBP_LOG):
        try:
            with open(GBP_LOG) as f:
                log = json.load(f)
        except Exception:
            pass
    log.append({"timestamp": str(datetime.now()), "action": action, **data})
    log = log[-500:]
    with open(GBP_LOG, "w") as f:
        json.dump(log, f, indent=2)
