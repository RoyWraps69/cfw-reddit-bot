"""
Chicago Fleet Wraps — AI Content Creator v1.0

Generates platform-optimized content for:
- TikTok (15s, 30s, 60s)
- Instagram Reels (15s, 30s, 60s, 90s)
- YouTube Shorts (60s)
- Facebook (video + carousel + text post)

5 content archetypes, each with platform variants:
1. Before/After Story
2. Day-in-the-Shop
3. Education Wrap ("things most wrap shops won't tell you")
4. Client Transformation Drama
5. Competitor Comparison ("what $3,000 gets you at different shops")

Connects to:
- RunwayML Gen-3 (text-to-video)
- HeyGen (AI avatar spokesperson)
- ElevenLabs (Roy voice synthesis)
- Pika Labs (image + prompt → video)
- OpenAI DALL-E 3 (thumbnail/still images)

Content is scheduled, tracked, and feeds back into the self-optimizer.
"""

import os
import json
import random
import time
from datetime import datetime, date
from openai import OpenAI

# Optional imports — graceful fallback if API keys not set
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CONTENT_QUEUE_DIR = os.path.join(DATA_DIR, "content_queue")
CONTENT_LOG_FILE = os.path.join(DATA_DIR, "content_log.json")

# API Keys (all from environment variables)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
RUNWAY_API_KEY = os.environ.get("RUNWAY_API_KEY", "")
HEYGEN_API_KEY = os.environ.get("HEYGEN_API_KEY", "")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
PIKA_API_KEY = os.environ.get("PIKA_API_KEY", "")

client = OpenAI()

# ─────────────────────────────────────────────────────────────────────
# BUSINESS CONTEXT (keep in sync with config.py)
# ─────────────────────────────────────────────────────────────────────

CFW_FACTS = """
Chicago Fleet Wraps (CFW) — 4711 N. Lamon Ave, Chicago IL 60630 (Portage Park)
Owner: Roy ("Roy Wraps") | Since 2014 | 10+ years | 600+ Rivians wrapped
Also: Bloomington, IL location near the Rivian manufacturing plant
Services: fleet wraps, color change, vinyl lettering, decals, EV wraps, PPF
Materials: 3M 2080, Avery Dennison SW900, XPEL PPF
Turnaround: 3-5 days most jobs
Fleet discount: up to 15%
Price ranges: Cargo van $3,750+ | Full color change $3,500-4,500+
Phone: (312) 597-1286
Website: chicagofleetwraps.com (has online price calculator — no call required)
Key differentiators: transparent pricing, 2-hour response time, no upselling
"""

# ─────────────────────────────────────────────────────────────────────
# PLATFORM SPECIFICATIONS
# ─────────────────────────────────────────────────────────────────────

PLATFORM_SPECS = {
    "tiktok": {
        "max_duration_s": 60,
        "sweet_spot_s": 15,  # 15s gets highest completion rate
        "aspect_ratio": "9:16",
        "hook_window_s": 3,  # First 3 seconds determine swipe-off rate
        "caption_max_chars": 2200,
        "hashtag_count": 5,
        "best_times": ["7AM", "12PM", "7PM", "9PM"],
        "voice": "fast, punchy, direct, trending audio",
        "trending_formats": ["POV:", "Tell me why", "Things I wish I knew", "The secret nobody talks about"],
    },
    "instagram_reels": {
        "max_duration_s": 90,
        "sweet_spot_s": 30,
        "aspect_ratio": "9:16",
        "hook_window_s": 3,
        "caption_max_chars": 2200,
        "hashtag_count": 10,
        "best_times": ["6AM", "12PM", "7PM"],
        "voice": "aspirational, visual-first, community-driven",
        "trending_formats": ["Before vs After", "Watch this transformation", "Day in my life"],
    },
    "youtube_shorts": {
        "max_duration_s": 60,
        "sweet_spot_s": 50,
        "aspect_ratio": "9:16",
        "hook_window_s": 5,
        "caption_max_chars": 500,
        "hashtag_count": 3,
        "best_times": ["3PM", "8PM"],
        "voice": "educational, authoritative, searchable",
        "trending_formats": ["How to", "Why you should", "X things about", "The truth about"],
    },
    "facebook": {
        "max_duration_s": 240,
        "sweet_spot_s": 60,
        "aspect_ratio": "16:9",  # Facebook prefers landscape for video
        "hook_window_s": 5,
        "caption_max_chars": 63206,
        "hashtag_count": 3,
        "best_times": ["1PM", "3PM", "8PM"],
        "voice": "community, local, trust-building, longer form okay",
        "trending_formats": ["Story post", "Before/after gallery", "Local business spotlight"],
    },
}

# ─────────────────────────────────────────────────────────────────────
# CONTENT ARCHETYPES
# ─────────────────────────────────────────────────────────────────────

CONTENT_ARCHETYPES = {

    "before_after": {
        "name": "Before/After Transformation",
        "description": "The most powerful format in the wrap industry. Show the vehicle before and after.",
        "psychology": "Visual proof. Social proof. Desire creation.",
        "platform_priority": ["instagram_reels", "tiktok", "facebook"],
        "frequency": "2x per week",
    },

    "day_in_shop": {
        "name": "Day in the Shop",
        "description": "Behind the scenes: wrapping process, team, tools, challenges.",
        "psychology": "Authority. Transparency. Humanization. Liking.",
        "platform_priority": ["tiktok", "instagram_reels", "youtube_shorts"],
        "frequency": "1x per week",
    },

    "education": {
        "name": "Education Wrap",
        "description": "Things most wrap shops won't tell you. How to spot a bad install. Film guide.",
        "psychology": "Reciprocity. Authority. Trust-building.",
        "platform_priority": ["youtube_shorts", "tiktok", "facebook"],
        "frequency": "2x per week",
    },

    "client_story": {
        "name": "Client Transformation Drama",
        "description": "A client's story: their problem, their skepticism, the result, their reaction.",
        "psychology": "Social proof. Story. Emotional connection. Commitment/consistency.",
        "platform_priority": ["facebook", "instagram_reels", "youtube_shorts"],
        "frequency": "1x per week",
    },

    "competitor_comparison": {
        "name": "What $3,000 Gets You",
        "description": "Side-by-side: what you get at a cheap shop vs a quality shop. Educational not aggressive.",
        "psychology": "Contrast principle. Authority. Fear of bad outcome.",
        "platform_priority": ["tiktok", "youtube_shorts", "facebook"],
        "frequency": "1x per 2 weeks",
    },

    "rivian_special": {
        "name": "Rivian/EV Specialist Content",
        "description": "Deep-dive on Rivian wraps — the challenges, the solutions, the results.",
        "psychology": "Hyper-niche authority. Community belonging. Scarcity (few shops can do this).",
        "platform_priority": ["youtube_shorts", "instagram_reels", "reddit"],
        "frequency": "1x per week",
    },

    "price_transparency": {
        "name": "What Does a Wrap Actually Cost?",
        "description": "Break down the real pricing. Kill the mystery. Drive calculator traffic.",
        "psychology": "Reciprocity. Transparency. Loss aversion ('you might be overpaying').",
        "platform_priority": ["tiktok", "facebook", "youtube_shorts"],
        "frequency": "1x per 2 weeks",
    },
}

# ─────────────────────────────────────────────────────────────────────
# SCRIPT GENERATOR
# ─────────────────────────────────────────────────────────────────────

def generate_video_script(
    archetype: str,
    platform: str,
    duration_s: int = None,
    vehicle_focus: str = None,
    seasonal_angle: str = None,
) -> dict:
    """Generate a complete video script with hook, body, CTA, and caption.

    Returns:
        {
            "hook": str,          # First 3-5 seconds — must stop the scroll
            "script": str,        # Full spoken script with timestamps
            "b_roll_notes": str,  # Visual direction for each section
            "caption": str,       # Platform-optimized caption
            "hashtags": list,     # Relevant hashtags
            "thumbnail_prompt": str,  # DALL-E prompt for thumbnail
            "runway_prompt": str, # RunwayML prompt if AI video needed
            "duration_s": int,
            "platform": str,
            "archetype": str,
        }
    """
    spec = PLATFORM_SPECS.get(platform, PLATFORM_SPECS["tiktok"])
    archetype_data = CONTENT_ARCHETYPES.get(archetype, CONTENT_ARCHETYPES["before_after"])
    duration_s = duration_s or spec["sweet_spot_s"]

    vehicle_context = f"Vehicle focus: {vehicle_focus}" if vehicle_focus else "General vehicle content (van, truck, or fleet)"
    seasonal_context = f"Seasonal angle: {seasonal_angle}" if seasonal_angle else ""

    prompt = f"""You are a social media content director for Chicago Fleet Wraps, a vehicle wrap shop in Chicago.
Your job is to write a video script that will perform on {platform}.

PLATFORM CONTEXT:
- Duration: {duration_s} seconds
- Hook window: First {spec['hook_window_s']} seconds are everything
- Voice/style: {spec['voice']}
- Best performing formats: {', '.join(spec['trending_formats'])}

CONTENT ARCHETYPE: {archetype_data['name']}
{archetype_data['description']}
Psychology: {archetype_data['psychology']}

BUSINESS FACTS (use selectively — don't cram them all in):
{CFW_FACTS}

{vehicle_context}
{seasonal_context}

RULES:
- The hook MUST create a pattern interrupt in {spec['hook_window_s']} seconds or less
- Script should sound like a real person talking, not an ad
- Include specific facts and numbers (not vague claims)
- End with ONE clear action: calculator link, phone number, or "comment your vehicle"
- Do NOT use: "amazing", "incredible", "best in Chicago", "world-class"
- Do NOT make up specific client testimonials or statistics you don't have
- The CTA should feel natural, not bolted on

WHAT TO RETURN — valid JSON only:
{{
    "hook": "The exact opening line(s) — {spec['hook_window_s']} seconds max",
    "script": "Full word-for-word script with [TIMESTAMP] markers every 10 seconds",
    "b_roll_notes": "Shot-by-shot visual direction (what the camera shows while audio plays)",
    "caption": "Platform caption ({spec['caption_max_chars'][:4]} char limit, includes emojis if appropriate for {platform})",
    "hashtags": ["list", "of", "{spec['hashtag_count']}", "hashtags"],
    "thumbnail_prompt": "DALL-E 3 prompt for a thumbnail image",
    "runway_prompt": "RunwayML Gen-3 text prompt for AI video generation if no real footage available",
    "hook_type": "which trending format this uses: {' or '.join(spec['trending_formats'])}",
    "duration_s": {duration_s}
}}"""

    response = client.chat.completions.create(
        model="gpt-4o",  # Use 4o for content creation — better creativity
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
        max_tokens=1500,
        response_format={"type": "json_object"},
    )

    try:
        result = json.loads(response.choices[0].message.content)
        result["platform"] = platform
        result["archetype"] = archetype
        result["generated_at"] = str(datetime.now())
        return result
    except (json.JSONDecodeError, KeyError):
        return {
            "hook": "Your vehicle is driving past thousands of people every day. Are they remembering you?",
            "script": "[0:00] Your vehicle is a moving billboard. [0:05] Most business owners don't think about it that way. [0:10] Chicago Fleet Wraps. Since 2014. chicagofleetwraps.com",
            "caption": "Your van is a billboard. Make it work. chicagofleetwraps.com #ChicagoFleetWraps #VehicleWrap #Chicago",
            "hashtags": ["#ChicagoFleetWraps", "#VehicleWrap", "#Chicago", "#FleetWraps", "#CarWrap"],
            "thumbnail_prompt": "A dramatically wrapped cargo van on a Chicago street, professional photography, before/after split",
            "runway_prompt": "Time-lapse of a white cargo van being professionally wrapped in a Chicago shop, dramatic lighting",
            "platform": platform,
            "archetype": archetype,
            "generated_at": str(datetime.now()),
        }


def generate_weekly_content_calendar(week_offset: int = 0) -> dict:
    """Generate a full week of content across all platforms.

    Returns a calendar dict with content for each day and platform.
    """
    calendar = {}

    # Weekly schedule — varies archetypes to avoid repetition
    weekly_plan = [
        {"day": "Monday", "archetype": "before_after", "platform": "instagram_reels"},
        {"day": "Monday", "archetype": "education", "platform": "tiktok"},
        {"day": "Tuesday", "archetype": "day_in_shop", "platform": "tiktok"},
        {"day": "Tuesday", "archetype": "price_transparency", "platform": "facebook"},
        {"day": "Wednesday", "archetype": "before_after", "platform": "tiktok"},
        {"day": "Wednesday", "archetype": "rivian_special", "platform": "instagram_reels"},
        {"day": "Thursday", "archetype": "client_story", "platform": "facebook"},
        {"day": "Thursday", "archetype": "education", "platform": "youtube_shorts"},
        {"day": "Friday", "archetype": "before_after", "platform": "instagram_reels"},
        {"day": "Friday", "archetype": "day_in_shop", "platform": "tiktok"},
        {"day": "Saturday", "archetype": "competitor_comparison", "platform": "youtube_shorts"},
        {"day": "Saturday", "archetype": "before_after", "platform": "facebook"},
    ]

    for item in weekly_plan:
        day = item["day"]
        if day not in calendar:
            calendar[day] = []

        script = generate_video_script(
            archetype=item["archetype"],
            platform=item["platform"],
        )
        calendar[day].append({
            "platform": item["platform"],
            "archetype": item["archetype"],
            "content": script,
        })
        time.sleep(1)  # Rate limit OpenAI calls

    return calendar


def save_content_to_queue(content: dict, platform: str, archetype: str):
    """Save generated content to the queue for review and scheduling."""
    os.makedirs(CONTENT_QUEUE_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{platform}_{archetype}.json"
    filepath = os.path.join(CONTENT_QUEUE_DIR, filename)

    with open(filepath, "w") as f:
        json.dump(content, f, indent=2)

    return filepath


def get_content_queue() -> list:
    """Get all pending content from the queue."""
    os.makedirs(CONTENT_QUEUE_DIR, exist_ok=True)
    files = sorted([f for f in os.listdir(CONTENT_QUEUE_DIR) if f.endswith(".json")])
    queue = []
    for f in files:
        try:
            with open(os.path.join(CONTENT_QUEUE_DIR, f)) as fh:
                queue.append({"file": f, "content": json.load(fh)})
        except Exception:
            pass
    return queue


# ─────────────────────────────────────────────────────────────────────
# AI VIDEO GENERATION — API CONNECTORS
# ─────────────────────────────────────────────────────────────────────

def generate_runway_video(prompt: str, duration_s: int = 4) -> dict:
    """Generate a video clip using RunwayML Gen-3 Alpha.

    Requires RUNWAY_API_KEY environment variable.
    Returns: {"task_id": str, "status": str, "video_url": str or None}
    """
    if not RUNWAY_API_KEY:
        return {"status": "no_api_key", "video_url": None,
                "note": "Set RUNWAY_API_KEY env var to enable RunwayML generation"}

    headers = {
        "Authorization": f"Bearer {RUNWAY_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "gen3a_turbo",
        "textPrompt": prompt,
        "seconds": min(duration_s, 10),  # Gen-3 max 10 seconds
        "ratio": "768:1280",  # 9:16 vertical
        "motion": "dynamic",
    }

    try:
        response = requests.post(
            "https://api.runwayml.com/v1/image_to_video",
            headers=headers,
            json=payload,
            timeout=30,
        )
        if response.status_code == 200:
            data = response.json()
            return {"task_id": data.get("id"), "status": "submitted", "video_url": None}
        else:
            return {"status": "error", "code": response.status_code, "video_url": None}
    except Exception as e:
        return {"status": "error", "error": str(e), "video_url": None}


def generate_heygen_avatar_video(script: str, avatar_id: str = None) -> dict:
    """Generate an AI avatar spokesperson video using HeyGen.

    Best for: client testimonials, educational explainers, spokesperson ads.
    Requires HEYGEN_API_KEY environment variable.
    """
    if not HEYGEN_API_KEY:
        return {"status": "no_api_key", "video_url": None,
                "note": "Set HEYGEN_API_KEY env var to enable HeyGen avatar videos"}

    headers = {
        "X-Api-Key": HEYGEN_API_KEY,
        "Content-Type": "application/json",
    }

    # Default to a professional avatar if none specified
    avatar_id = avatar_id or "avatar_realistic_male_chicago"

    payload = {
        "video_inputs": [{
            "character": {
                "type": "avatar",
                "avatar_id": avatar_id,
            },
            "voice": {
                "type": "text",
                "input_text": script,
                "voice_id": "en-US-ChristopherNeural",  # Chicago-appropriate voice
            },
        }],
        "dimension": {"width": 1080, "height": 1920},  # 9:16
    }

    try:
        response = requests.post(
            "https://api.heygen.com/v2/video/generate",
            headers=headers,
            json=payload,
            timeout=30,
        )
        if response.status_code == 200:
            data = response.json()
            return {"video_id": data.get("data", {}).get("video_id"), "status": "submitted", "video_url": None}
        else:
            return {"status": "error", "code": response.status_code, "video_url": None}
    except Exception as e:
        return {"status": "error", "error": str(e), "video_url": None}


def generate_elevenlabs_voiceover(text: str, voice_id: str = None) -> dict:
    """Generate a voiceover using ElevenLabs.

    Ideal for: TikTok voiceovers, ad narration, video script audio.
    Requires ELEVENLABS_API_KEY.
    """
    if not ELEVENLABS_API_KEY:
        return {"status": "no_api_key", "audio_url": None,
                "note": "Set ELEVENLABS_API_KEY env var. Clone Roy's voice for authentic brand audio."}

    # For CFW, recommend cloning Roy's actual voice
    voice_id = voice_id or os.environ.get("ELEVENLABS_ROY_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Default: ElevenLabs Josh

    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }

    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.6,      # Slight variation for natural feel
            "similarity_boost": 0.85,
            "style": 0.3,          # Low style for professional tone
        },
    }

    try:
        response = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers=headers,
            json=payload,
            timeout=30,
        )
        if response.status_code == 200:
            # Save audio file locally
            audio_dir = os.path.join(DATA_DIR, "audio")
            os.makedirs(audio_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            audio_path = os.path.join(audio_dir, f"voiceover_{timestamp}.mp3")
            with open(audio_path, "wb") as f:
                f.write(response.content)
            return {"status": "success", "audio_path": audio_path, "text": text}
        else:
            return {"status": "error", "code": response.status_code}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def generate_thumbnail(prompt: str) -> dict:
    """Generate a thumbnail image using DALL-E 3."""
    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=f"Professional vehicle wrap photography. {prompt}. Chicago setting. High contrast. Bold colors. No text overlay.",
            size="1024x1792",  # 9:16 for vertical
            quality="hd",
            n=1,
        )
        return {
            "status": "success",
            "url": response.data[0].url,
            "revised_prompt": response.data[0].revised_prompt,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ─────────────────────────────────────────────────────────────────────
# CONTENT PERFORMANCE TRACKING
# ─────────────────────────────────────────────────────────────────────

def log_content_performance(
    platform: str,
    archetype: str,
    hook: str,
    views: int = 0,
    likes: int = 0,
    comments: int = 0,
    shares: int = 0,
    saves: int = 0,
    link_clicks: int = 0,
):
    """Log content performance for the self-optimizer to learn from."""
    os.makedirs(DATA_DIR, exist_ok=True)

    log = []
    if os.path.exists(CONTENT_LOG_FILE):
        try:
            with open(CONTENT_LOG_FILE) as f:
                log = json.load(f)
        except Exception:
            pass

    engagement_rate = 0
    if views > 0:
        engagement_rate = round((likes + comments + shares + saves) / views * 100, 2)

    log.append({
        "date": str(date.today()),
        "platform": platform,
        "archetype": archetype,
        "hook": hook[:100],
        "views": views,
        "likes": likes,
        "comments": comments,
        "shares": shares,
        "saves": saves,
        "link_clicks": link_clicks,
        "engagement_rate": engagement_rate,
    })

    with open(CONTENT_LOG_FILE, "w") as f:
        json.dump(log[-500:], f, indent=2)  # Keep last 500 entries


def get_top_performing_content(platform: str = None, limit: int = 5) -> list:
    """Get the top performing content entries for a given platform."""
    if not os.path.exists(CONTENT_LOG_FILE):
        return []

    try:
        with open(CONTENT_LOG_FILE) as f:
            log = json.load(f)
    except Exception:
        return []

    if platform:
        log = [e for e in log if e["platform"] == platform]

    return sorted(log, key=lambda x: x.get("engagement_rate", 0), reverse=True)[:limit]
