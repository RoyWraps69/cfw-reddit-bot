"""
Chicago Fleet Wraps — Hot Lead Alert System v1.0

When the bot detects a warm or hot lead anywhere (Reddit DM, comment reply,
calculator visitor, Instagram DM, Facebook comment), Roy gets a text message
within 60 seconds. No more lost leads.

Integration points:
- Reddit DM replies (from dm_monitor.py)
- Positive comment replies (from reply_engine.py)
- Calculator webhook (from calculator_webhook.py)
- Instagram/Facebook DMs (from instagram_bot.py, facebook_bot.py)

Uses Twilio for SMS. Falls back to email if Twilio not configured.
Also supports Slack webhook for team notifications.
"""

import os
import json
import time
from datetime import datetime, date

# Optional — graceful fallback
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

# Credentials from environment
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_NUMBER = os.environ.get("TWILIO_FROM_NUMBER", "")  # Your Twilio number
ROY_PHONE_NUMBER = os.environ.get("ROY_PHONE_NUMBER", "")       # +13125551234

SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")
ALERT_EMAIL = os.environ.get("ALERT_EMAIL", "")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
ALERT_LOG_FILE = os.path.join(DATA_DIR, "alert_log.json")

# ─────────────────────────────────────────────────────────────────────
# LEAD SCORING
# ─────────────────────────────────────────────────────────────────────

INTENT_SCORES = {
    "hot": 10,      # Explicitly asking for contact/price/appointment
    "warm": 6,      # Showing interest, asking follow-ups
    "calculator": 9, # Used the price calculator — highest commercial intent
    "dm_request": 8, # Asked to be DMed
    "cold": 2,
    "spam": 0,
}

HOT_KEYWORDS = [
    "how do i", "how can i", "can i call", "what's the number",
    "how much would", "get a quote", "book an appointment", "schedule",
    "interested", "want to wrap", "need a wrap", "ready to", "let's do it",
    "how do i contact", "do you have availability", "when can you",
    "price for my", "quote for my", "estimate for",
]

WARM_KEYWORDS = [
    "tell me more", "what do you think", "sounds good", "that makes sense",
    "good point", "didn't know that", "interesting", "considering",
    "been thinking about", "looking into", "checking out", "researching",
]


def score_lead(text: str, source: str = "reddit") -> dict:
    """Score a lead based on text content and source."""
    text_lower = text.lower()
    score = 0
    signals = []

    # Source bonus
    if source == "calculator":
        score += INTENT_SCORES["calculator"]
        signals.append("Used price calculator")
        return {"score": score, "level": "hot", "signals": signals}

    if source == "dm":
        score += 3
        signals.append("Direct message")

    # Keyword detection
    for kw in HOT_KEYWORDS:
        if kw in text_lower:
            score += 4
            signals.append(f"Hot keyword: '{kw}'")
            break

    for kw in WARM_KEYWORDS:
        if kw in text_lower:
            score += 2
            signals.append(f"Warm keyword: '{kw}'")
            break

    # Question marks = engagement
    if text.count("?") > 0:
        score += 1
        signals.append("Contains questions")

    # Determine level
    if score >= 8:
        level = "hot"
    elif score >= 4:
        level = "warm"
    elif score >= 2:
        level = "cold"
    else:
        level = "ignore"

    return {"score": score, "level": level, "signals": signals}


# ─────────────────────────────────────────────────────────────────────
# ALERT FUNCTIONS
# ─────────────────────────────────────────────────────────────────────

def send_hot_lead_alert(
    platform: str,
    username: str,
    message_text: str,
    thread_title: str = "",
    thread_url: str = "",
    vehicle_type: str = "",
    price_estimate: str = "",
    intent_level: str = "warm",
    lead_score: int = 0,
) -> dict:
    """
    Send an alert to Roy when a hot/warm lead is detected.
    Tries SMS first, then Slack, then logs for email.
    """
    results = {}

    # Format the alert message
    sms_message = _format_sms(
        platform=platform,
        username=username,
        message=message_text,
        thread=thread_title,
        vehicle=vehicle_type,
        price=price_estimate,
        level=intent_level,
        score=lead_score,
    )

    slack_message = _format_slack(
        platform=platform,
        username=username,
        message=message_text,
        thread_title=thread_title,
        thread_url=thread_url,
        vehicle=vehicle_type,
        price=price_estimate,
        level=intent_level,
        score=lead_score,
    )

    # 1. SMS via Twilio
    if TWILIO_AVAILABLE and TWILIO_ACCOUNT_SID and ROY_PHONE_NUMBER:
        results["sms"] = _send_sms(sms_message)
    else:
        results["sms"] = {"status": "skipped", "reason": "Twilio not configured"}

    # 2. Slack webhook
    if SLACK_WEBHOOK_URL and REQUESTS_AVAILABLE:
        results["slack"] = _send_slack(slack_message)
    else:
        results["slack"] = {"status": "skipped", "reason": "Slack webhook not configured"}

    # 3. Always log
    _log_alert({
        "timestamp": str(datetime.now()),
        "platform": platform,
        "username": username,
        "message_preview": message_text[:200],
        "thread_title": thread_title,
        "vehicle_type": vehicle_type,
        "price_estimate": price_estimate,
        "intent_level": intent_level,
        "lead_score": lead_score,
        "alert_sent": results,
    })

    print(f"[LEAD ALERT] {intent_level.upper()} lead from {platform} — u/{username} — score {lead_score}", flush=True)
    print(f"[LEAD ALERT] SMS: {results['sms'].get('status')} | Slack: {results['slack'].get('status')}", flush=True)

    return results


def send_calculator_lead_alert(
    vehicle_type: str,
    estimated_price: str,
    email: str = "",
    phone: str = "",
    name: str = "",
    notes: str = "",
    ip_city: str = "",
) -> dict:
    """Special alert for calculator form submissions — highest priority."""

    contact_info = []
    if name:
        contact_info.append(f"Name: {name}")
    if phone:
        contact_info.append(f"Phone: {phone}")
    if email:
        contact_info.append(f"Email: {email}")
    if ip_city:
        contact_info.append(f"Location: {ip_city}")

    sms = f"""🔥 HOT LEAD — Price Calculator
Vehicle: {vehicle_type}
Est. Price: {estimated_price}
{chr(10).join(contact_info)}
{f'Notes: {notes[:100]}' if notes else ''}
Call NOW: this lead is hot."""

    results = {}
    if TWILIO_AVAILABLE and TWILIO_ACCOUNT_SID and ROY_PHONE_NUMBER:
        results["sms"] = _send_sms(sms)

    if SLACK_WEBHOOK_URL and REQUESTS_AVAILABLE:
        slack_payload = {
            "text": "🔥 *HOT LEAD — Price Calculator Used*",
            "attachments": [{
                "color": "#FF0000",
                "fields": [
                    {"title": "Vehicle", "value": vehicle_type, "short": True},
                    {"title": "Estimate", "value": estimated_price, "short": True},
                    {"title": "Contact", "value": "\n".join(contact_info) or "Not provided", "short": False},
                    {"title": "Notes", "value": notes or "None", "short": False},
                ],
                "footer": "CFW Lead Alert",
                "ts": int(time.time()),
            }],
        }
        results["slack"] = _send_slack(slack_payload)

    _log_alert({
        "timestamp": str(datetime.now()),
        "platform": "calculator",
        "vehicle_type": vehicle_type,
        "price_estimate": estimated_price,
        "contact": {"name": name, "phone": phone, "email": email},
        "intent_level": "hot",
        "lead_score": 10,
    })

    return results


# ─────────────────────────────────────────────────────────────────────
# DAILY LEAD SUMMARY (morning briefing)
# ─────────────────────────────────────────────────────────────────────

def send_morning_brief() -> dict:
    """Send Roy a morning summary of yesterday's leads and activity."""
    alerts = _load_alerts()
    today = str(date.today())

    # Yesterday's alerts
    yesterday_alerts = [a for a in alerts if a.get("timestamp", "").startswith(today)]

    hot_leads = [a for a in yesterday_alerts if a.get("intent_level") == "hot"]
    warm_leads = [a for a in yesterday_alerts if a.get("intent_level") == "warm"]

    # Load daily activity summary
    daily_log = os.path.join(os.path.dirname(DATA_DIR), "logs", "daily_activity.json")
    activity = {}
    if os.path.exists(daily_log):
        try:
            with open(daily_log) as f:
                activity = json.load(f)
        except Exception:
            pass

    brief = f"""☀️ CFW Morning Brief — {today}

LEADS:
  🔥 Hot leads: {len(hot_leads)}
  🟡 Warm leads: {len(warm_leads)}

REDDIT:
  Comments posted: {activity.get('total_comments', 0)}
  DMs sent: {activity.get('total_dms', 0)}
  Threads created: {activity.get('threads_created', 0)}

HOT LEADS TO FOLLOW UP:
"""
    for lead in hot_leads[:5]:
        brief += f"  • {lead.get('platform')} — {lead.get('username', 'unknown')} — {lead.get('vehicle_type', 'unknown vehicle')}\n"

    if not hot_leads:
        brief += "  None yesterday — keep the content engine running.\n"

    brief += f"\nGood luck today. chicagofleetwraps.com/calculator"

    results = {}
    if TWILIO_AVAILABLE and TWILIO_ACCOUNT_SID and ROY_PHONE_NUMBER:
        results["sms"] = _send_sms(brief[:1600])  # SMS limit

    return results


# ─────────────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────────────────────────────

def _format_sms(platform, username, message, thread, vehicle, price, level, score) -> str:
    emoji = "🔥" if level == "hot" else "🟡"
    lines = [
        f"{emoji} {level.upper()} LEAD — {platform}",
        f"From: {username}",
    ]
    if vehicle:
        lines.append(f"Vehicle: {vehicle}")
    if price:
        lines.append(f"Est: {price}")
    if thread:
        lines.append(f"Thread: {thread[:50]}")
    lines.append(f'"{message[:120]}"')
    lines.append(f"Score: {score}/10")
    return "\n".join(lines)


def _format_slack(platform, username, message, thread_title, thread_url,
                  vehicle, price, level, score) -> dict:
    color = "#FF4500" if level == "hot" else "#FFA500"
    fields = [
        {"title": "Platform", "value": platform, "short": True},
        {"title": "Username", "value": username, "short": True},
        {"title": "Intent", "value": level.upper(), "short": True},
        {"title": "Score", "value": f"{score}/10", "short": True},
    ]
    if vehicle:
        fields.append({"title": "Vehicle", "value": vehicle, "short": True})
    if price:
        fields.append({"title": "Est. Price", "value": price, "short": True})
    if thread_title:
        fields.append({"title": "Thread", "value": f"<{thread_url}|{thread_title[:60]}>" if thread_url else thread_title[:60], "short": False})
    fields.append({"title": "Message", "value": message[:300], "short": False})

    return {
        "text": f"{'🔥' if level == 'hot' else '🟡'} *New {level.upper()} Lead — {platform}*",
        "attachments": [{"color": color, "fields": fields, "ts": int(time.time())}],
    }


def _send_sms(message: str) -> dict:
    try:
        twilio_client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        msg = twilio_client.messages.create(
            body=message[:1600],
            from_=TWILIO_FROM_NUMBER,
            to=ROY_PHONE_NUMBER,
        )
        return {"status": "sent", "sid": msg.sid}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _send_slack(payload: dict) -> dict:
    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
        return {"status": "sent" if response.status_code == 200 else "error",
                "code": response.status_code}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _log_alert(data: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    alerts = _load_alerts()
    alerts.append(data)
    alerts = alerts[-500:]
    with open(ALERT_LOG_FILE, "w") as f:
        json.dump(alerts, f, indent=2)


def _load_alerts() -> list:
    if os.path.exists(ALERT_LOG_FILE):
        try:
            with open(ALERT_LOG_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return []
