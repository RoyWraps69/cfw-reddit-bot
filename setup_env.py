#!/usr/bin/env python3
"""
Chicago Fleet Wraps — Environment Setup Script

This script:
1. Reads your existing .env file (preserves all your current secret keys)
2. Adds any new keys needed by the v6.0 upgrade (with blank values)
3. Shows you exactly what's missing and what to fill in
4. Never overwrites a key that already has a value

Run: python setup_env.py
"""

import os
import sys

ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
EXAMPLE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env.example")

# All keys in the complete system, with descriptions and priority
ALL_KEYS = {
    # ── REQUIRED ──────────────────────────────────────────────
    "REDDIT_USERNAME": {
        "required": True, "priority": 1,
        "description": "Your Reddit username",
        "example": "AddressRadiant8768",
        "category": "Reddit",
    },
    "OPENAI_API_KEY": {
        "required": True, "priority": 1,
        "description": "OpenAI API key — get from platform.openai.com",
        "example": "sk-...",
        "category": "AI",
    },

    # ── TIER 1: REVENUE ───────────────────────────────────────
    "TWILIO_ACCOUNT_SID": {
        "required": False, "priority": 2,
        "description": "Twilio Account SID — for SMS lead alerts to Roy",
        "example": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "category": "SMS",
        "signup": "https://twilio.com",
    },
    "TWILIO_AUTH_TOKEN": {
        "required": False, "priority": 2,
        "description": "Twilio Auth Token",
        "example": "your_auth_token",
        "category": "SMS",
    },
    "TWILIO_FROM_NUMBER": {
        "required": False, "priority": 2,
        "description": "Your Twilio phone number (buy a 312 number)",
        "example": "+13125550000",
        "category": "SMS",
    },
    "ROY_PHONE_NUMBER": {
        "required": False, "priority": 2,
        "description": "Roy's actual cell phone — where lead alerts go",
        "example": "+13125550001",
        "category": "SMS",
    },
    "SLACK_WEBHOOK_URL": {
        "required": False, "priority": 3,
        "description": "Slack webhook for lead alerts (optional team channel)",
        "example": "https://hooks.slack.com/services/...",
        "category": "Notifications",
    },
    "GBP_ACCESS_TOKEN": {
        "required": False, "priority": 2,
        "description": "Google Business Profile OAuth token",
        "example": "ya29.xxx",
        "category": "Google",
        "signup": "https://developers.google.com/my-business",
    },
    "GBP_ACCOUNT_ID": {
        "required": False, "priority": 2,
        "description": "GBP Account ID (from Google My Business API)",
        "example": "accounts/123456789",
        "category": "Google",
    },
    "GBP_LOCATION_ID": {
        "required": False, "priority": 2,
        "description": "GBP Location ID for 4711 N. Lamon Ave",
        "example": "locations/987654321",
        "category": "Google",
    },
    "GOOGLE_REVIEW_LINK": {
        "required": False, "priority": 2,
        "description": "Your Google review direct link",
        "example": "https://g.page/r/ChicagoFleetWraps/review",
        "category": "Google",
    },
    "SENDGRID_API_KEY": {
        "required": False, "priority": 2,
        "description": "SendGrid API key for email nurture sequences (100/day free)",
        "example": "SG.xxx",
        "category": "Email",
        "signup": "https://sendgrid.com",
    },
    "WEBHOOK_SECRET": {
        "required": False, "priority": 2,
        "description": "Secret for calculator webhook (add to your website form)",
        "example": "cfw-secret-change-this-to-something-random",
        "category": "Webhook",
    },

    # ── TIER 2: CONTENT CREATION ──────────────────────────────
    "RUNWAY_API_KEY": {
        "required": False, "priority": 3,
        "description": "RunwayML Gen-3 API key for AI video generation",
        "example": "rw-xxx",
        "category": "Video AI",
        "signup": "https://runwayml.com",
    },
    "HEYGEN_API_KEY": {
        "required": False, "priority": 3,
        "description": "HeyGen API key for AI avatar videos",
        "example": "xxx",
        "category": "Video AI",
        "signup": "https://heygen.com",
    },
    "ELEVENLABS_API_KEY": {
        "required": False, "priority": 3,
        "description": "ElevenLabs API key for Roy's voice synthesis",
        "example": "xxx",
        "category": "Voice AI",
        "signup": "https://elevenlabs.io",
    },
    "ELEVENLABS_ROY_VOICE_ID": {
        "required": False, "priority": 3,
        "description": "ElevenLabs Voice ID after cloning Roy's voice",
        "example": "21m00Tcm4TlvDq8ikWAM",
        "category": "Voice AI",
    },
    "PIKA_API_KEY": {
        "required": False, "priority": 4,
        "description": "Pika Labs API key for image-to-video",
        "example": "xxx",
        "category": "Video AI",
        "signup": "https://pika.art",
    },

    # ── TIER 3: SOCIAL MEDIA ──────────────────────────────────
    "FACEBOOK_PAGE_TOKEN": {
        "required": False, "priority": 3,
        "description": "Facebook Page Access Token for posting",
        "example": "EAAG...",
        "category": "Social",
    },
    "FACEBOOK_PAGE_ID": {
        "required": False, "priority": 3,
        "description": "Facebook Page ID",
        "example": "123456789",
        "category": "Social",
    },
    "INSTAGRAM_USERNAME": {
        "required": False, "priority": 4,
        "description": "Instagram username",
        "example": "chicagofleetwraps",
        "category": "Social",
    },
    "INSTAGRAM_PASSWORD": {
        "required": False, "priority": 4,
        "description": "Instagram password",
        "example": "your_password",
        "category": "Social",
    },
    "TIKTOK_SESSION_ID": {
        "required": False, "priority": 4,
        "description": "TikTok session ID (from browser cookies)",
        "example": "xxx",
        "category": "Social",
    },
    "YOUTUBE_API_KEY": {
        "required": False, "priority": 4,
        "description": "YouTube Data API v3 key",
        "example": "AIza...",
        "category": "Social",
    },
    "YOUTUBE_CHANNEL_ID": {
        "required": False, "priority": 4,
        "description": "YouTube Channel ID",
        "example": "UCxxx",
        "category": "Social",
    },

    # ── TIER 4: WEBSITE / SEO ─────────────────────────────────
    "WORDPRESS_URL": {
        "required": False, "priority": 3,
        "description": "WordPress site URL",
        "example": "https://chicagofleetwraps.com",
        "category": "SEO",
    },
    "WORDPRESS_USERNAME": {
        "required": False, "priority": 3,
        "description": "WordPress admin username",
        "example": "admin",
        "category": "SEO",
    },
    "WORDPRESS_APP_PASSWORD": {
        "required": False, "priority": 3,
        "description": "WordPress Application Password (Users → Profile → App Passwords)",
        "example": "xxxx xxxx xxxx xxxx xxxx xxxx",
        "category": "SEO",
    },
    "YELP_REVIEW_LINK": {
        "required": False, "priority": 3,
        "description": "Yelp review direct link",
        "example": "https://yelp.com/writeareview/biz/chicago-fleet-wraps",
        "category": "Reviews",
    },
}


def load_env(filepath: str) -> dict:
    """Load key=value pairs from a .env file."""
    env = {}
    if not os.path.exists(filepath):
        return env
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, val = line.partition("=")
                env[key.strip()] = val.strip()
    return env


def run_setup():
    print("\n" + "=" * 65)
    print("  CHICAGO FLEET WRAPS — ENVIRONMENT SETUP")
    print("=" * 65 + "\n")

    # Load existing .env
    existing_env = load_env(ENV_FILE)
    existing_count = len([v for v in existing_env.values() if v])

    if existing_env:
        print(f"✅ Found existing .env with {existing_count} configured keys")
        print(f"   Preserving all existing values.\n")
    else:
        print("📄 No existing .env found — creating fresh one.\n")

    # Figure out what's missing
    missing_required = []
    missing_optional = []

    for key, info in ALL_KEYS.items():
        current_val = existing_env.get(key, "")
        if not current_val:
            if info["required"]:
                missing_required.append((key, info))
            else:
                missing_optional.append((key, info))

    # Build the new .env content
    lines = [
        "# Chicago Fleet Wraps Bot — Environment Variables",
        "# Generated by setup_env.py — DO NOT COMMIT THIS FILE",
        "# Last updated: " + __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "",
    ]

    current_category = None
    for key, info in ALL_KEYS.items():
        cat = info["category"]
        if cat != current_category:
            lines.append(f"# ── {cat} {'─' * (50 - len(cat))}")
            current_category = cat

        current_val = existing_env.get(key, "")
        comment = f"  # {info['description']}"
        if info.get("signup"):
            comment += f" | {info['signup']}"

        lines.append(f"{key}={current_val}{comment}")

    # Write the merged .env
    with open(ENV_FILE, "w") as f:
        f.write("\n".join(lines) + "\n")

    print(f"✅ .env written with {len(ALL_KEYS)} keys\n")

    # Print status report
    print("=" * 65)
    print("  SETUP STATUS REPORT")
    print("=" * 65)

    if missing_required:
        print(f"\n🔴 REQUIRED (bot won't start without these):")
        for key, info in missing_required:
            print(f"   {key}")
            print(f"   → {info['description']}")
            if info.get("signup"):
                print(f"   → Sign up: {info['signup']}")
            print()

    # Group optional by priority
    p2 = [(k, v) for k, v in missing_optional if v["priority"] == 2]
    p3 = [(k, v) for k, v in missing_optional if v["priority"] == 3]
    p4 = [(k, v) for k, v in missing_optional if v["priority"] >= 4]

    if p2:
        print(f"\n🟡 WEEK 1 — SET THESE FIRST (direct revenue impact):")
        for key, info in p2:
            line = f"   {key} — {info['description']}"
            if info.get("signup"):
                line += f" ({info['signup']})"
            print(line)

    if p3:
        print(f"\n🔵 WEEK 2 — CONTENT + SEO:")
        for key, info in p3:
            print(f"   {key} — {info['description']}")

    if p4:
        print(f"\n⚪ WEEK 3 — NICE TO HAVE:")
        for key, info in p4:
            print(f"   {key} — {info['description']}")

    # Count what's ready
    configured = {k: v for k, v in existing_env.items() if v and k in ALL_KEYS}
    print(f"\n{'=' * 65}")
    print(f"  CONFIGURED: {len(configured)}/{len(ALL_KEYS)} keys")
    print(f"  MISSING REQUIRED: {len(missing_required)}")
    print(f"  MISSING WEEK 1: {len(p2)}")
    print(f"{'=' * 65}")

    if not missing_required:
        print(f"\n✅ Required keys are set. Ready to run:\n")
        print(f"   python master_runner.py once   # test one cycle")
        print(f"   python master_runner.py run    # start continuous operation")
        print(f"   python master_runner.py status # check system status")
    else:
        print(f"\n⚠️  Fill in missing required keys in .env first, then run:")
        print(f"   python master_runner.py once")

    print(f"\nOpen .env and fill in the missing values.\n")


if __name__ == "__main__":
    run_setup()
