"""
Chicago Fleet Wraps — Lead CRM v1.0

Tracks every lead from first contact through booked appointment.
Every single interested person gets logged, scored, and followed up.

Lead stages:
  NEW → CONTACTED → INTERESTED → QUOTED → BOOKED → COMPLETED → LOST

Sources:
  Reddit DM | Reddit Comment | Calculator | Instagram | Facebook | TikTok | Phone | Walk-in

The CRM answers:
  - How many leads came in this week?
  - What's the close rate by source?
  - Which vehicle types convert best?
  - What's the average time from first contact to booked job?
  - Which leads need follow-up today?
"""

import os
import json
import uuid
from datetime import datetime, date, timedelta
from enum import Enum

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CRM_FILE = os.path.join(DATA_DIR, "leads_crm.json")
FOLLOWUP_FILE = os.path.join(DATA_DIR, "followup_queue.json")


class LeadSource(str, Enum):
    REDDIT = "reddit"
    CALCULATOR = "calculator"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    TIKTOK = "tiktok"
    GOOGLE = "google"
    PHONE = "phone"
    WALK_IN = "walk_in"
    REFERRAL = "referral"
    EMAIL = "email"


class LeadStatus(str, Enum):
    NEW = "new"
    CONTACTED = "contacted"
    INTERESTED = "interested"
    QUOTED = "quoted"
    BOOKED = "booked"
    COMPLETED = "completed"
    LOST = "lost"
    SPAM = "spam"


# ─────────────────────────────────────────────────────────────────────
# CORE LEAD OPERATIONS
# ─────────────────────────────────────────────────────────────────────

def add_lead(
    source: LeadSource,
    platform: str,
    username: str = "",
    vehicle_type: str = "",
    price_estimate: str = "",
    contact_email: str = "",
    contact_phone: str = "",
    notes: str = "",
    referral: str = "",
    intent_level: str = "warm",
    lead_score: int = 5,
    thread_url: str = "",
) -> dict:
    """Add a new lead to the CRM. Returns the lead dict with assigned ID."""
    leads = _load_leads()

    # Deduplicate: check if this username already has a lead in the last 7 days
    if username:
        existing = _find_recent_lead(leads, username, platform, days=7)
        if existing:
            # Update existing lead instead of creating duplicate
            return update_lead(existing["lead_id"], notes=f"{existing.get('notes', '')} | {notes}".strip(" | "),
                               intent_level=max_intent(existing.get("intent_level"), intent_level))

    lead_id = str(uuid.uuid4())[:8].upper()
    lead = {
        "lead_id": lead_id,
        "created_at": str(datetime.now()),
        "updated_at": str(datetime.now()),
        "source": source.value if hasattr(source, 'value') else str(source),
        "platform": platform,
        "username": username,
        "vehicle_type": vehicle_type,
        "price_estimate": price_estimate,
        "contact_email": contact_email,
        "contact_phone": contact_phone,
        "notes": notes,
        "referral": referral,
        "intent_level": intent_level,
        "lead_score": lead_score,
        "status": LeadStatus.NEW.value,
        "thread_url": thread_url,
        "follow_up_count": 0,
        "next_follow_up": str((datetime.now() + timedelta(days=1)).date()),
        "history": [
            {"timestamp": str(datetime.now()), "action": "lead_created", "note": f"Source: {source}"}
        ],
    }

    leads.append(lead)
    _save_leads(leads)

    # Add to follow-up queue
    _queue_follow_up(lead_id, days=1, method="dm" if platform == "reddit" else "email")

    print(f"[CRM] New lead #{lead_id}: {username} | {vehicle_type} | {intent_level}", flush=True)
    return lead


def update_lead(
    lead_id: str,
    status: str = None,
    notes: str = None,
    price_estimate: str = None,
    contact_email: str = None,
    contact_phone: str = None,
    intent_level: str = None,
    action_note: str = None,
) -> dict:
    """Update a lead's status or information."""
    leads = _load_leads()

    for lead in leads:
        if lead["lead_id"] == lead_id:
            if status:
                lead["status"] = status
            if notes:
                lead["notes"] = notes
            if price_estimate:
                lead["price_estimate"] = price_estimate
            if contact_email:
                lead["contact_email"] = contact_email
            if contact_phone:
                lead["contact_phone"] = contact_phone
            if intent_level:
                lead["intent_level"] = intent_level
            lead["updated_at"] = str(datetime.now())

            if action_note:
                lead.setdefault("history", []).append({
                    "timestamp": str(datetime.now()),
                    "action": status or "updated",
                    "note": action_note,
                })

            _save_leads(leads)
            return lead

    return {"error": f"Lead {lead_id} not found"}


def get_leads_needing_followup() -> list:
    """Get all leads that need follow-up today."""
    leads = _load_leads()
    today = str(date.today())
    needs_followup = []

    for lead in leads:
        if lead.get("status") in (LeadStatus.NEW.value, LeadStatus.CONTACTED.value, LeadStatus.INTERESTED.value):
            next_fu = lead.get("next_follow_up", "")
            if next_fu <= today:
                needs_followup.append(lead)

    return sorted(needs_followup, key=lambda x: x.get("lead_score", 0), reverse=True)


def get_pipeline_summary() -> dict:
    """Get a complete pipeline overview."""
    leads = _load_leads()
    today = date.today()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    def is_recent(lead, since):
        try:
            created = datetime.strptime(lead["created_at"][:10], "%Y-%m-%d").date()
            return created >= since
        except Exception:
            return False

    total = len(leads)
    this_week = [l for l in leads if is_recent(l, week_ago)]
    this_month = [l for l in leads if is_recent(l, month_ago)]

    by_status = {}
    for lead in leads:
        s = lead.get("status", "unknown")
        by_status[s] = by_status.get(s, 0) + 1

    by_source = {}
    for lead in leads:
        s = lead.get("source", "unknown")
        by_source[s] = by_source.get(s, 0) + 1

    booked = [l for l in leads if l.get("status") == LeadStatus.BOOKED.value]
    close_rate = round(len(booked) / total * 100, 1) if total > 0 else 0

    hot_leads = [l for l in leads if l.get("intent_level") == "hot" and
                 l.get("status") in (LeadStatus.NEW.value, LeadStatus.CONTACTED.value)]

    return {
        "total_leads": total,
        "this_week": len(this_week),
        "this_month": len(this_month),
        "by_status": by_status,
        "by_source": by_source,
        "close_rate_pct": close_rate,
        "booked_total": len(booked),
        "hot_leads_needing_attention": len(hot_leads),
        "hot_leads": hot_leads[:5],
        "needs_followup_today": len(get_leads_needing_followup()),
        "generated_at": str(datetime.now()),
    }


def get_crm_report() -> str:
    """Generate a human-readable CRM report."""
    summary = get_pipeline_summary()
    lines = [
        "=" * 60,
        "CFW LEAD PIPELINE REPORT",
        f"Generated: {date.today()}",
        "=" * 60,
        "",
        f"TOTAL LEADS: {summary['total_leads']}",
        f"This week: {summary['this_week']} | This month: {summary['this_month']}",
        f"Close rate: {summary['close_rate_pct']}% | Booked: {summary['booked_total']}",
        "",
        "PIPELINE STATUS:",
    ]
    for status, count in summary["by_status"].items():
        lines.append(f"  {status.upper()}: {count}")

    lines.append("")
    lines.append("LEADS BY SOURCE:")
    for source, count in sorted(summary["by_source"].items(), key=lambda x: x[1], reverse=True):
        lines.append(f"  {source}: {count}")

    lines.append("")
    lines.append(f"⚠️  HOT LEADS NEEDING ATTENTION: {summary['hot_leads_needing_attention']}")
    for lead in summary["hot_leads"]:
        lines.append(f"  #{lead['lead_id']} — {lead['username']} — {lead['vehicle_type']} — {lead['platform']}")

    lines.append("")
    lines.append(f"📅 FOLLOW-UPS DUE TODAY: {summary['needs_followup_today']}")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────
# FOLLOW-UP QUEUE
# ─────────────────────────────────────────────────────────────────────

def _queue_follow_up(lead_id: str, days: int = 1, method: str = "email"):
    """Add a follow-up task to the queue."""
    os.makedirs(DATA_DIR, exist_ok=True)
    queue = _load_followup_queue()

    task = {
        "lead_id": lead_id,
        "due_date": str((date.today() + timedelta(days=days))),
        "method": method,
        "created_at": str(datetime.now()),
        "done": False,
    }
    queue.append(task)

    with open(FOLLOWUP_FILE, "w") as f:
        json.dump(queue, f, indent=2)


def complete_followup(lead_id: str):
    """Mark a follow-up as done and schedule the next one."""
    leads = _load_leads()
    queue = _load_followup_queue()

    # Mark done
    for task in queue:
        if task["lead_id"] == lead_id and not task["done"]:
            task["done"] = True
            break

    # Update lead and schedule next follow-up
    for lead in leads:
        if lead["lead_id"] == lead_id:
            follow_up_count = lead.get("follow_up_count", 0) + 1
            lead["follow_up_count"] = follow_up_count
            lead["updated_at"] = str(datetime.now())

            # Follow-up cadence: Day 1 → Day 3 → Day 7 → stop
            if follow_up_count == 1:
                next_days = 3
            elif follow_up_count == 2:
                next_days = 7
            else:
                next_days = None  # Stop following up

            if next_days:
                lead["next_follow_up"] = str((date.today() + timedelta(days=next_days)))
                _queue_follow_up(lead_id, days=next_days)

            lead.setdefault("history", []).append({
                "timestamp": str(datetime.now()),
                "action": "follow_up_completed",
                "note": f"Follow-up #{follow_up_count}",
            })
            break

    _save_leads(leads)
    with open(FOLLOWUP_FILE, "w") as f:
        json.dump(queue, f, indent=2)


# ─────────────────────────────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────────────────────────────

def max_intent(a: str, b: str) -> str:
    """Return the higher intent level."""
    order = {"hot": 3, "warm": 2, "cold": 1, "ignore": 0}
    return a if order.get(a, 0) >= order.get(b, 0) else b


def _find_recent_lead(leads: list, username: str, platform: str, days: int = 7):
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    for lead in reversed(leads):
        if (lead.get("username", "").lower() == username.lower() and
                lead.get("platform") == platform and
                lead.get("created_at", "") >= cutoff):
            return lead
    return None


def _load_leads() -> list:
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(CRM_FILE):
        try:
            with open(CRM_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_leads(leads: list):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CRM_FILE, "w") as f:
        json.dump(leads, f, indent=2)


def _load_followup_queue() -> list:
    if os.path.exists(FOLLOWUP_FILE):
        try:
            with open(FOLLOWUP_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return []
