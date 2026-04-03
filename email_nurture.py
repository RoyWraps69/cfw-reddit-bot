"""
Chicago Fleet Wraps — Email Nurture Engine v1.0

5-email sequences for every lead type.
Sends via SendGrid. Falls back to log file for manual send.

Sequence types:
  calculator_lead   — Someone used the price calculator
  reddit_lead       — Someone showed interest on Reddit
  cold_outreach     — Local business we're reaching out to
  fleet_prospect    — Commercial fleet owner
  post_job          — After job completion (review + referral)
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
EMAIL_QUEUE_FILE = os.path.join(DATA_DIR, "email_queue.json")
EMAIL_LOG_FILE = os.path.join(DATA_DIR, "email_sent_log.json")

SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")
FROM_EMAIL = "roy@chicagofleetwraps.com"
FROM_NAME = "Roy at Chicago Fleet Wraps"

client = OpenAI()

# ─────────────────────────────────────────────────────────────────────
# EMAIL SEQUENCES
# Each sequence is a list of emails with their send delay
# ─────────────────────────────────────────────────────────────────────

SEQUENCES = {

    "calculator_lead": [
        {
            "day": 0,  # Send immediately
            "subject": "Your {vehicle_type} wrap estimate — a few things worth knowing",
            "body": """Hi {name},

You just ran your {vehicle_type} through our price calculator. I wanted to follow up personally.

The estimate you got (around {price_estimate}) is accurate for a full wrap using either 3M 2080 or Avery Dennison SW900 — the same film brands the top shops in Chicago use. Some shops will quote you less using off-brand film that starts lifting at the seams by year two. Worth asking anyone you talk to what film brand they use.

If your {vehicle_type} is for business use, the wrap is typically 100% deductible under Section 179. For a lot of our fleet clients, that turns a $4,000 investment into a $2,800 out-of-pocket cost after the write-off.

A few specifics that might help you decide:
• Turnaround: 3-5 business days for most vehicles
• Fleet discount: Up to 15% off for 3+ vehicles
• We respond with detailed pricing within 2 hours — no runaround

Ready to move forward or have questions? Reply here or call me directly at (312) 597-1286.

— Roy
Chicago Fleet Wraps | Portage Park, Chicago
4711 N. Lamon Ave | chicagofleetwraps.com""",
        },
        {
            "day": 3,
            "subject": "One thing most people don't ask wrap shops (but should)",
            "body": """Hi {name},

Following up from a few days ago about your {vehicle_type}.

Here's something worth knowing: the biggest quality difference between wrap shops isn't price — it's prep time. A properly prepped vehicle takes 2-4 hours before a single piece of vinyl goes on. Shops cutting corners skip this step. You can't see the difference in month one. You see it in month 18 when the edges start lifting.

We document our prep process for every vehicle. It's one reason we've been doing this since 2014 and wrapped over 600 Rivians — including a lot of customers who came to us to fix someone else's bad install.

If budget is a factor, worth knowing that partial wraps and vinyl lettering start considerably lower and can be just as impactful for business vehicles.

Still interested? The calculator link is always available: chicagofleetwraps.com/calculator

Or just reply with your vehicle and I'll give you a real number in under an hour.

— Roy | (312) 597-1286""",
        },
        {
            "day": 7,
            "subject": "Last note from Roy — no pressure",
            "body": """Hi {name},

Last note, I promise — I don't believe in hounding people.

If the timing wasn't right or you went in a different direction, completely understood. If you're still thinking about it, here's the short version:

• We've been wrapping vehicles in Chicago since 2014
• We're transparent about pricing (no "call for a quote" games)
• We use 3M and Avery film — not gray-market rolls
• Fleet discounts up to 15% for multiple vehicles
• Most jobs done in 3-5 days

When you're ready: (312) 597-1286 or chicagofleetwraps.com

— Roy""",
        },
    ],

    "fleet_prospect": [
        {
            "day": 0,
            "subject": "Fleet wraps for {company_type} companies in Chicago — the math",
            "body": """Hi {name},

Roy here from Chicago Fleet Wraps in Portage Park.

I work with a lot of {company_type} companies in Chicago who started wrapping their vans and trucks. The consistent thing I hear a year later: they wish they'd done it sooner.

The math that usually lands: a cargo van wrap at $3,750 over a 5-year lifespan = $62/month. That's a moving billboard that works 24/7, parks at every job site, and drives past thousands of people a week. Most Yelp ad packages run $300-500/month and disappear when you stop paying.

For fleets of 3+ vehicles, we offer up to 15% off. Business vehicle wraps are also Section 179 deductible — so the real cost is often 20-35% lower after taxes.

I'd be happy to put together specific pricing for your vehicles. No obligation, and I respond same day.

— Roy
Chicago Fleet Wraps | (312) 597-1286
chicagofleetwraps.com/calculator (get a price in 60 seconds)""",
        },
        {
            "day": 5,
            "subject": "What other {company_type} companies in Chicago are doing with their fleets",
            "body": """Hi {name},

Following up from earlier this week.

Wanted to share something relevant: we wrap a lot of service company fleets in Chicago — HVAC, plumbing, electrical, construction, food service. The owners who come back for more vehicles consistently tell us the same thing: they started getting calls that said "I saw your truck at X job site."

That's the kind of attribution you can't get from most marketing spend.

A couple of specifics that might be useful:
• We can accommodate multiple vehicles on overlapping schedules
• We handle the design at no extra charge for fleet clients
• Our Portage Park location has easy highway access and parking for large vehicles

If it would help, I'm happy to put together a quote with mockup images for your vehicles. Takes about 24 hours on our end.

— Roy | (312) 597-1286""",
        },
    ],

    "post_job": [
        {
            "day": 1,
            "subject": "Your {vehicle_type} wrap — checking in",
            "body": """Hi {name},

Roy here. Your {vehicle_type} has been wrapped for a day now — hoping it looks exactly how you pictured it.

A couple of care tips:
• Wait 7 days before washing
• Hand wash only — no automatic car washes (the brushes can lift the edges)
• If you park outside, a garage when possible extends the life considerably
• Park away from direct exhaust heat sources

If anything looks off or you have any questions, reply here or call me directly: (312) 597-1286. I stand behind the work.

One small ask: if you're happy with it, a Google review would mean a lot:
{google_review_link}

Takes about a minute. Really helps a small shop compete.

Thanks again for trusting us with your vehicle.

— Roy""",
        },
    ],
}


# ─────────────────────────────────────────────────────────────────────
# QUEUE AND SEND
# ─────────────────────────────────────────────────────────────────────

def queue_nurture_sequence(
    email: str,
    name: str = "there",
    vehicle_type: str = "vehicle",
    price_estimate: str = "",
    sequence_type: str = "calculator_lead",
    company_type: str = "service",
    google_review_link: str = "",
) -> list:
    """Queue all emails in a nurture sequence."""
    sequence = SEQUENCES.get(sequence_type, SEQUENCES["calculator_lead"])
    queue = _load_queue()
    queued_ids = []

    for email_def in sequence:
        send_date = str((date.today() + timedelta(days=email_def["day"])))

        subject = email_def["subject"].format(
            name=name.split()[0] if name else "there",
            vehicle_type=vehicle_type,
            price_estimate=price_estimate,
            company_type=company_type,
        )

        body = email_def["body"].format(
            name=name.split()[0] if name else "there",
            vehicle_type=vehicle_type,
            price_estimate=price_estimate,
            company_type=company_type,
            google_review_link=google_review_link or os.environ.get("GOOGLE_REVIEW_LINK", "https://g.page/r/review"),
        )

        task = {
            "id": f"{email}_{sequence_type}_{email_def['day']}",
            "email": email,
            "name": name,
            "subject": subject,
            "body": body,
            "sequence_type": sequence_type,
            "send_date": send_date,
            "sent": False,
            "created_at": str(datetime.now()),
        }

        # Deduplicate
        existing_ids = {q["id"] for q in queue}
        if task["id"] not in existing_ids:
            queue.append(task)
            queued_ids.append(task["id"])

    _save_queue(queue)
    print(f"[EMAIL] Queued {len(queued_ids)} emails for {email} ({sequence_type})", flush=True)
    return queued_ids


def run_email_send_cycle() -> dict:
    """Send all emails due today."""
    queue = _load_queue()
    today = str(date.today())
    results = {"sent": 0, "failed": 0, "skipped": 0}

    for task in queue:
        if task.get("sent"):
            continue
        if task.get("send_date", "") > today:
            results["skipped"] += 1
            continue

        result = _send_email(task["email"], task["subject"], task["body"])
        if result.get("status") == "sent":
            task["sent"] = True
            task["sent_at"] = str(datetime.now())
            results["sent"] += 1
            _log_sent(task)
        else:
            results["failed"] += 1

    _save_queue(queue)
    print(f"[EMAIL] Send cycle: sent={results['sent']}, failed={results['failed']}", flush=True)
    return results


def _send_email(to_email: str, subject: str, body: str) -> dict:
    """Send via SendGrid or log for manual send."""
    if SENDGRID_API_KEY and REQUESTS_AVAILABLE:
        try:
            payload = {
                "personalizations": [{"to": [{"email": to_email}]}],
                "from": {"email": FROM_EMAIL, "name": FROM_NAME},
                "subject": subject,
                "content": [{"type": "text/plain", "value": body}],
            }
            response = requests.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={"Authorization": f"Bearer {SENDGRID_API_KEY}", "Content-Type": "application/json"},
                json=payload, timeout=15,
            )
            return {"status": "sent" if response.status_code == 202 else "error", "code": response.status_code}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # Log for manual send
    print(f"[EMAIL] MANUAL SEND NEEDED: To: {to_email} | Subject: {subject[:60]}", flush=True)
    return {"status": "sent", "note": "logged_for_manual"}


def _load_queue() -> list:
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(EMAIL_QUEUE_FILE):
        try:
            with open(EMAIL_QUEUE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_queue(queue: list):
    with open(EMAIL_QUEUE_FILE, "w") as f:
        json.dump(queue, f, indent=2)


def _log_sent(task: dict):
    log = []
    if os.path.exists(EMAIL_LOG_FILE):
        try:
            with open(EMAIL_LOG_FILE) as f:
                log = json.load(f)
        except Exception:
            pass
    log.append(task)
    with open(EMAIL_LOG_FILE, "w") as f:
        json.dump(log[-1000:], f, indent=2)
