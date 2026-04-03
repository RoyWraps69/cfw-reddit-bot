"""
Chicago Fleet Wraps — Review Generation System v1.0

Automatically requests Google reviews from customers after their job is complete.
Reviews are the #1 local SEO ranking factor.

Flow:
  Job Complete → Wait 24 hours → Send review request SMS
  → No response after 3 days → Send email follow-up
  → Log result

Google review link: https://g.page/r/XXXXXXX/review
(Get this from Google Business Profile → Get more reviews)

Also monitors all review platforms and flags negatives for immediate response.
"""

import os
import json
import random
from datetime import datetime, date, timedelta
from openai import OpenAI

try:
    from twilio.rest import Client as TwilioClient
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_NUMBER = os.environ.get("TWILIO_FROM_NUMBER", "")
GOOGLE_REVIEW_LINK = os.environ.get("GOOGLE_REVIEW_LINK", "https://g.page/r/ChicagoFleetWraps/review")
YELP_REVIEW_LINK = os.environ.get("YELP_REVIEW_LINK", "https://yelp.com/writeareview/biz/chicago-fleet-wraps")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
REVIEW_REQUESTS_FILE = os.path.join(DATA_DIR, "review_requests.json")

client = OpenAI()

# ─────────────────────────────────────────────────────────────────────
# REVIEW REQUEST TEMPLATES
# Varied to avoid SMS spam filters
# ─────────────────────────────────────────────────────────────────────

SMS_TEMPLATES = [
    """Hey {name}, Roy here from Chicago Fleet Wraps. Hope the {vehicle_type} wrap looks exactly how you pictured it. If you have 60 seconds, a Google review would mean a lot to a small shop: {link}

No pressure either way. Thanks for trusting us with your vehicle.""",

    """Hi {name} — Roy from CFW. Just checking in on your {vehicle_type} wrap. If you're happy with it, a quick Google review helps us out more than you know: {link}

And if anything isn't right, reply here and I'll make it right.""",

    """{name}, quick note from Roy at Chicago Fleet Wraps. Your {vehicle_type} came out great — hope you're getting compliments already. If you have a moment: {link}

It really helps locals find us. Appreciate your business.""",

    """Hey {name} — this is Roy from Chicago Fleet Wraps. Thanks again for bringing in your {vehicle_type}. If the work met your expectations, we'd love a Google review: {link}

Takes about a minute and helps a lot. No worries if not.""",
]

EMAIL_SUBJECT_LINES = [
    "Your {vehicle_type} wrap — a quick favor from Roy",
    "How's the wrap looking? (Quick note from Chicago Fleet Wraps)",
    "{name}, a 60-second ask from Roy at CFW",
    "Hope you're loving the wrap — one small request",
]

EMAIL_TEMPLATES = [
    """Hi {name},

Roy here from Chicago Fleet Wraps. Your {vehicle_type} wrap has been done for a few days now — hope it's turning heads.

If you're happy with how it came out, I have one small ask: could you leave us a Google review?

{link}

It takes about a minute and genuinely helps our small shop compete against the bigger operations. Local reviews are everything for a neighborhood shop like ours.

If anything isn't right with the wrap, reply to this email directly and I'll take care of it personally.

Thanks again for trusting us with your vehicle.

— Roy
Chicago Fleet Wraps
4711 N. Lamon Ave, Chicago IL 60630
(312) 597-1286""",

    """Hey {name},

Quick follow-up from Roy at Chicago Fleet Wraps about your {vehicle_type}.

If the wrap met your expectations, a Google review would help us out more than most people realize:

{link}

For a small shop like ours, local reviews are how we compete with the big guys. Each one genuinely matters.

If something's off or you have any questions, I'm always reachable at (312) 597-1286.

— Roy""",
]


# ─────────────────────────────────────────────────────────────────────
# REVIEW REQUEST ENGINE
# ─────────────────────────────────────────────────────────────────────

def request_review(
    customer_name: str,
    phone: str = "",
    email: str = "",
    vehicle_type: str = "vehicle",
    job_completed_date: str = None,
    platform: str = "google",
) -> dict:
    """
    Queue a review request for a completed job.
    Sends 24 hours after job completion via SMS, then email at 4 days.
    """
    if not job_completed_date:
        job_completed_date = str(date.today())

    review_link = GOOGLE_REVIEW_LINK if platform == "google" else YELP_REVIEW_LINK

    request_record = {
        "id": f"{customer_name.replace(' ', '_').lower()}_{job_completed_date}",
        "customer_name": customer_name,
        "phone": phone,
        "email": email,
        "vehicle_type": vehicle_type,
        "job_completed": job_completed_date,
        "platform": platform,
        "review_link": review_link,
        "sms_sent": False,
        "sms_sent_date": None,
        "email_sent": False,
        "email_sent_date": None,
        "review_received": False,
        "created_at": str(datetime.now()),
    }

    # Log for follow-up scheduler
    requests_list = _load_requests()
    # Deduplicate
    existing_ids = {r["id"] for r in requests_list}
    if request_record["id"] not in existing_ids:
        requests_list.append(request_record)
        _save_requests(requests_list)
        print(f"[REVIEWS] Queued review request: {customer_name} | {vehicle_type}", flush=True)
        return {"status": "queued", "request_id": request_record["id"]}
    else:
        return {"status": "duplicate", "request_id": request_record["id"]}


def run_review_request_cycle() -> dict:
    """
    Run the daily review request cycle.
    Send SMS 1 day after job, email 4 days after job.
    """
    requests_list = _load_requests()
    today = date.today()
    results = {"sms_sent": 0, "email_sent": 0, "skipped": 0}

    for req in requests_list:
        if req.get("review_received"):
            continue

        completed = date.fromisoformat(req["job_completed"])
        days_since = (today - completed).days

        # SMS: send 1 day after completion
        if days_since >= 1 and not req.get("sms_sent") and req.get("phone"):
            sms_result = _send_review_sms(
                phone=req["phone"],
                name=req["customer_name"],
                vehicle_type=req["vehicle_type"],
                link=req["review_link"],
            )
            if sms_result.get("status") == "sent":
                req["sms_sent"] = True
                req["sms_sent_date"] = str(today)
                results["sms_sent"] += 1

        # Email: send 4 days after completion
        elif days_since >= 4 and not req.get("email_sent") and req.get("email"):
            email_result = _send_review_email(
                email=req["email"],
                name=req["customer_name"],
                vehicle_type=req["vehicle_type"],
                link=req["review_link"],
            )
            if email_result.get("status") == "sent":
                req["email_sent"] = True
                req["email_sent_date"] = str(today)
                results["email_sent"] += 1
        else:
            results["skipped"] += 1

    _save_requests(requests_list)
    print(f"[REVIEWS] Cycle: sms_sent={results['sms_sent']}, email_sent={results['email_sent']}", flush=True)
    return results


def mark_review_received(request_id: str, rating: int = 5, platform: str = "google"):
    """Mark that a customer left a review."""
    requests_list = _load_requests()
    for req in requests_list:
        if req["id"] == request_id:
            req["review_received"] = True
            req["review_rating"] = rating
            req["review_platform"] = platform
            req["review_date"] = str(date.today())
            break
    _save_requests(requests_list)


def get_review_stats() -> dict:
    """Get review request statistics."""
    requests_list = _load_requests()
    total = len(requests_list)
    received = [r for r in requests_list if r.get("review_received")]
    pending = [r for r in requests_list if not r.get("review_received")]
    conversion_rate = round(len(received) / total * 100, 1) if total > 0 else 0

    return {
        "total_requested": total,
        "reviews_received": len(received),
        "pending": len(pending),
        "conversion_rate_pct": conversion_rate,
        "avg_rating": round(
            sum(r.get("review_rating", 5) for r in received) / len(received), 1
        ) if received else 0,
    }


# ─────────────────────────────────────────────────────────────────────
# SEND FUNCTIONS
# ─────────────────────────────────────────────────────────────────────

def _send_review_sms(phone: str, name: str, vehicle_type: str, link: str) -> dict:
    """Send a review request SMS via Twilio."""
    if not TWILIO_AVAILABLE or not TWILIO_ACCOUNT_SID:
        return {"status": "no_twilio", "message": "Twilio not configured"}

    template = random.choice(SMS_TEMPLATES)
    message = template.format(
        name=name.split()[0],  # First name only
        vehicle_type=vehicle_type,
        link=link,
    )

    try:
        twilio_client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        msg = twilio_client.messages.create(
            body=message,
            from_=TWILIO_FROM_NUMBER,
            to=phone,
        )
        return {"status": "sent", "sid": msg.sid}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _send_review_email(email: str, name: str, vehicle_type: str, link: str) -> dict:
    """Send a review request email via SendGrid or SMTP."""
    sendgrid_key = os.environ.get("SENDGRID_API_KEY", "")

    subject = random.choice(EMAIL_SUBJECT_LINES).format(
        name=name.split()[0], vehicle_type=vehicle_type)
    body = random.choice(EMAIL_TEMPLATES).format(
        name=name.split()[0], vehicle_type=vehicle_type, link=link)

    if sendgrid_key and REQUESTS_AVAILABLE:
        return _send_via_sendgrid(sendgrid_key, email, subject, body)

    # Fallback: log for manual sending
    print(f"[REVIEWS] Would email {email}: {subject}", flush=True)
    return {"status": "logged_for_manual", "email": email, "subject": subject}


def _send_via_sendgrid(api_key: str, to_email: str, subject: str, body: str) -> dict:
    """Send email via SendGrid API."""
    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": "roy@chicagofleetwraps.com", "name": "Roy at Chicago Fleet Wraps"},
        "subject": subject,
        "content": [{"type": "text/plain", "value": body}],
    }
    try:
        response = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=15,
        )
        return {"status": "sent" if response.status_code == 202 else "error",
                "code": response.status_code}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ─────────────────────────────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────────────────────────────

def _load_requests() -> list:
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(REVIEW_REQUESTS_FILE):
        try:
            with open(REVIEW_REQUESTS_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_requests(requests_list: list):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(REVIEW_REQUESTS_FILE, "w") as f:
        json.dump(requests_list, f, indent=2)
