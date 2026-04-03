"""
Chicago Fleet Wraps — Price Calculator Webhook v1.0

A lightweight Flask server that receives form submissions from the
chicagofleetwraps.com price calculator and:
1. Fires an immediate SMS/Slack alert to Roy
2. Logs the lead to the CRM pipeline
3. Triggers a DM follow-up sequence if email provided
4. Feeds vehicle type data back to the content strategy engine

Deploy this as a separate Railway service or on the same instance.
Add the webhook URL to your website's calculator form action.

The calculator form should POST to: https://your-server.railway.app/webhook/calculator

Expected form fields:
  vehicle_type   — "cargo_van", "box_truck", "car", "pickup_truck", etc.
  vehicle_year   — year string
  vehicle_make   — brand
  vehicle_model  — model
  wrap_type      — "full_wrap", "partial_wrap", "lettering", "color_change"
  estimated_price — pre-calculated estimate from JS
  name           — optional
  email          — optional
  phone          — optional
  notes          — optional
  referral       — where they heard about CFW (utm_source)
"""

import os
import json
from datetime import datetime
from flask import Flask, request, jsonify, abort

# Internal modules
from lead_alert import send_calculator_lead_alert, score_lead
from lead_crm import add_lead, LeadSource, LeadStatus

app = Flask(__name__)
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "cfw-secret-2024")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CALC_LOG = os.path.join(DATA_DIR, "calculator_submissions.json")

# ─────────────────────────────────────────────────────────────────────
# VEHICLE TYPE → PRICE ESTIMATION
# Mirrors the logic in the website's price calculator
# ─────────────────────────────────────────────────────────────────────

PRICE_RANGES = {
    "cargo_van": {"full": "$3,750 - $4,500", "partial": "$1,800 - $2,400", "lettering": "$450 - $900"},
    "box_truck": {"full": "$4,500 - $6,500", "partial": "$2,200 - $3,000", "lettering": "$600 - $1,200"},
    "pickup_truck": {"full": "$3,200 - $4,200", "partial": "$1,500 - $2,200", "lettering": "$400 - $800"},
    "car": {"full": "$3,200 - $4,800", "partial": "$1,400 - $2,000", "color_change": "$3,500 - $4,500"},
    "suv": {"full": "$3,500 - $5,000", "partial": "$1,600 - $2,200", "color_change": "$3,700 - $4,800"},
    "sprinter_van": {"full": "$4,200 - $5,500", "partial": "$2,000 - $2,800", "lettering": "$500 - $1,000"},
    "trailer": {"full": "$2,500 - $4,500", "partial": "$1,200 - $2,000", "lettering": "$400 - $900"},
    "rivian": {"full": "$4,200 - $5,500", "color_change": "$4,000 - $5,200", "ppf": "$3,000 - $6,000"},
    "tesla": {"full": "$3,800 - $5,000", "color_change": "$3,800 - $4,800", "ppf": "$2,800 - $5,500"},
}


def get_price_estimate(vehicle_type: str, wrap_type: str) -> str:
    vtype = vehicle_type.lower().replace(" ", "_")
    for key in PRICE_RANGES:
        if key in vtype or vtype in key:
            wrap_prices = PRICE_RANGES[key]
            return wrap_prices.get(wrap_type, wrap_prices.get("full", "Contact for quote"))
    return "Contact for custom quote"


# ─────────────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "CFW Calculator Webhook"})


@app.route("/webhook/calculator", methods=["POST"])
def calculator_webhook():
    """Receive calculator form submissions."""

    # Optional secret validation
    secret = request.headers.get("X-Webhook-Secret", "")
    if WEBHOOK_SECRET and secret != WEBHOOK_SECRET:
        # Don't hard fail — some form builders can't set headers
        pass

    data = {}
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()

    if not data:
        return jsonify({"error": "No data received"}), 400

    # Extract fields
    vehicle_type = data.get("vehicle_type", data.get("vehicle", "Unknown Vehicle"))
    wrap_type = data.get("wrap_type", "full_wrap")
    name = data.get("name", "")
    email = data.get("email", "")
    phone = data.get("phone", "")
    notes = data.get("notes", data.get("message", ""))
    referral = data.get("referral", data.get("utm_source", "calculator"))
    estimated_price = data.get("estimated_price", get_price_estimate(vehicle_type, wrap_type))
    ip_city = _get_city_from_ip(request.remote_addr)

    # Log submission
    submission = {
        "timestamp": str(datetime.now()),
        "vehicle_type": vehicle_type,
        "wrap_type": wrap_type,
        "estimated_price": estimated_price,
        "name": name,
        "email": email,
        "phone": phone,
        "notes": notes,
        "referral": referral,
        "ip": request.remote_addr,
        "city": ip_city,
    }
    _log_submission(submission)

    # 1. Fire immediate alert to Roy
    alert_result = send_calculator_lead_alert(
        vehicle_type=f"{vehicle_type} ({wrap_type})",
        estimated_price=estimated_price,
        email=email,
        phone=phone,
        name=name,
        notes=notes,
        ip_city=ip_city,
    )

    # 2. Add to CRM
    crm_lead = add_lead(
        source=LeadSource.CALCULATOR,
        platform="website",
        username=name or "calculator_visitor",
        vehicle_type=vehicle_type,
        price_estimate=estimated_price,
        contact_email=email,
        contact_phone=phone,
        notes=f"Wrap type: {wrap_type}. {notes}".strip(),
        referral=referral,
        intent_level="hot",
        lead_score=9,
    )

    # 3. Queue email nurture if email provided
    if email:
        try:
            from email_nurture import queue_nurture_sequence
            queue_nurture_sequence(
                email=email,
                name=name,
                vehicle_type=vehicle_type,
                price_estimate=estimated_price,
                sequence_type="calculator_lead",
            )
        except Exception as e:
            print(f"[WEBHOOK] Email nurture error: {e}", flush=True)

    print(f"[WEBHOOK] Calculator submission: {vehicle_type} ({wrap_type}) — {estimated_price}", flush=True)

    return jsonify({
        "status": "received",
        "lead_id": crm_lead.get("lead_id"),
        "message": "Thank you! Roy will be in touch within 2 hours.",
    })


@app.route("/webhook/reddit-lead", methods=["POST"])
def reddit_lead_webhook():
    """Internal webhook — called by the Reddit bot when a hot lead is detected."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data"}), 400

    from lead_alert import send_hot_lead_alert
    from lead_crm import add_lead

    result = send_hot_lead_alert(
        platform="reddit",
        username=data.get("username", "unknown"),
        message_text=data.get("message", ""),
        thread_title=data.get("thread_title", ""),
        thread_url=data.get("thread_url", ""),
        vehicle_type=data.get("vehicle_type", ""),
        intent_level=data.get("intent_level", "warm"),
        lead_score=data.get("lead_score", 5),
    )

    add_lead(
        source=LeadSource.REDDIT,
        platform="reddit",
        username=data.get("username"),
        vehicle_type=data.get("vehicle_type", ""),
        intent_level=data.get("intent_level", "warm"),
        lead_score=data.get("lead_score", 5),
        notes=data.get("message", "")[:500],
        thread_url=data.get("thread_url", ""),
    )

    return jsonify({"status": "ok", "alert": result})


@app.route("/webhook/review-submitted", methods=["POST"])
def review_submitted():
    """Called when a customer submits a review (from review request link)."""
    data = request.get_json() or request.form.to_dict()
    platform = data.get("platform", "google")
    customer_name = data.get("name", "Customer")
    rating = data.get("rating", 5)
    review_text = data.get("text", "")

    print(f"[WEBHOOK] Review submitted: {platform} | {customer_name} | {rating}★", flush=True)

    # Log and alert for low ratings
    if int(rating) <= 3:
        from lead_alert import send_hot_lead_alert
        send_hot_lead_alert(
            platform=f"{platform}_review",
            username=customer_name,
            message_text=f"{rating}★ Review: {review_text}",
            intent_level="hot",
            lead_score=10,
        )

    return jsonify({"status": "received", "message": "Thank you for your review!"})


@app.route("/submissions", methods=["GET"])
def view_submissions():
    """Simple endpoint to view recent calculator submissions."""
    submissions = _load_submissions()
    recent = list(reversed(submissions[-20:]))
    return jsonify({"count": len(submissions), "recent": recent})


# ─────────────────────────────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────────────────────────────

def _log_submission(data: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    submissions = _load_submissions()
    submissions.append(data)
    submissions = submissions[-1000:]
    with open(CALC_LOG, "w") as f:
        json.dump(submissions, f, indent=2)


def _load_submissions() -> list:
    if os.path.exists(CALC_LOG):
        try:
            with open(CALC_LOG) as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _get_city_from_ip(ip: str) -> str:
    """Try to get city from IP for context."""
    if not ip or ip in ("127.0.0.1", "::1"):
        return "Local"
    try:
        import requests
        r = requests.get(f"http://ip-api.com/json/{ip}?fields=city,regionName", timeout=3)
        if r.status_code == 200:
            d = r.json()
            return f"{d.get('city', '')}, {d.get('regionName', '')}".strip(", ")
    except Exception:
        pass
    return ""


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    print(f"[WEBHOOK] Calculator webhook server starting on port {port}", flush=True)
    app.run(host="0.0.0.0", port=port, debug=False)
