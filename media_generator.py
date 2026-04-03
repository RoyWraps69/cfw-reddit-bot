"""
Chicago Fleet Wraps — Media Generator v3.0
AI IMAGE & VIDEO GENERATION FOR SOCIAL MEDIA

v3.0 RULES:
- EVERY image must be an AI-generated photo of a wrapped vehicle
- NO Pillow templates, NO gradient backgrounds, NO text-on-color
- If DALL-E fails, retry with a simpler prompt
- If all retries fail, use a curated stock photo URL as last resort
- Video: ffmpeg slideshow with Ken Burns effect for TikTok
- Caption adaptation per platform
- Content uniqueness tracking

RULE: Each post is UNIQUE content, but the SAME content gets published
across all platforms (Facebook, Instagram, TikTok) simultaneously,
with platform-specific caption adaptations.
"""
import os
import json
import time
import hashlib
import random
import requests
from datetime import datetime
from openai import OpenAI
from config import DATA_DIR, OPENAI_MODEL, BUSINESS_CONTEXT

base_url = os.environ.get("OPENAI_BASE_URL", None)
client = OpenAI(base_url=base_url) if base_url else OpenAI()

MEDIA_DIR = os.path.join(DATA_DIR, "generated_media")
MEDIA_LOG = os.path.join(DATA_DIR, "media_generation_log.json")
PUBLISHED_HASHES = os.path.join(DATA_DIR, "published_content_hashes.json")


def _ensure_dirs():
    os.makedirs(MEDIA_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)


# ─────────────────────────────────────────────
# CONTENT UNIQUENESS
# ─────────────────────────────────────────────

def _load_published_hashes() -> set:
    if os.path.exists(PUBLISHED_HASHES):
        try:
            with open(PUBLISHED_HASHES, "r") as f:
                return set(json.load(f))
        except Exception:
            pass
    return set()


def _save_published_hash(content_hash: str):
    hashes = _load_published_hashes()
    hashes.add(content_hash)
    hashes_list = list(hashes)[-2000:]
    with open(PUBLISHED_HASHES, "w") as f:
        json.dump(hashes_list, f)


def _content_hash(topic: str, image_prompt: str) -> str:
    raw = f"{topic.lower().strip()}|{image_prompt.lower().strip()}"
    return hashlib.md5(raw.encode()).hexdigest()


def is_content_unique(topic: str, image_prompt: str) -> bool:
    h = _content_hash(topic, image_prompt)
    return h not in _load_published_hashes()


def mark_content_published(topic: str, image_prompt: str):
    h = _content_hash(topic, image_prompt)
    _save_published_hash(h)


# ─────────────────────────────────────────────
# WRAPPED VEHICLE PROMPT BUILDER
# ─────────────────────────────────────────────

# Variety pools for generating diverse wrapped vehicle images
VEHICLE_TYPES = [
    "Ford F-150 pickup truck", "Ram 1500 pickup truck", "Chevy Silverado pickup truck",
    "Mercedes Sprinter van", "Ford Transit cargo van", "Ram ProMaster van",
    "Tesla Model 3 sedan", "Tesla Model Y SUV", "Rivian R1T pickup truck",
    "Rivian R1S SUV", "BMW M4 coupe", "Porsche 911", "Dodge Charger",
    "Ford Mustang", "Chevy Corvette C8", "Lamborghini Huracan",
    "box truck", "food truck", "Jeep Wrangler", "Toyota Supra",
    "Audi RS5", "McLaren 720S", "Cadillac Escalade", "GMC Sierra",
]

WRAP_STYLES = [
    "matte black vinyl wrap", "satin midnight blue wrap", "gloss racing red wrap",
    "matte military green wrap", "satin pearl white wrap", "chrome delete black wrap",
    "carbon fiber accent wrap", "matte charcoal gray wrap", "satin bronze wrap",
    "gloss electric blue wrap", "matte forest green wrap", "satin lavender purple wrap",
    "color shift chameleon wrap", "matte khaki tan wrap", "gloss sunset orange wrap",
    "satin nardo gray wrap", "full commercial fleet graphics wrap",
    "branded delivery van wrap with company logo graphics",
    "matte army olive drab wrap", "gloss candy apple red wrap",
]

SETTINGS = [
    "parked on a Chicago city street with skyline in background",
    "in a professional wrap shop with bright lighting",
    "driving through downtown Chicago at golden hour",
    "parked in front of a modern commercial building",
    "on display at a car show under professional lighting",
    "parked on Michigan Avenue in Chicago",
    "in a clean garage with LED strip lighting",
    "on a rooftop parking deck with city skyline behind",
    "driving on Lake Shore Drive with Lake Michigan visible",
    "parked outside a trendy restaurant at night with neon reflections",
]


def _build_vehicle_image_prompt(decision: dict) -> str:
    """Build a detailed DALL-E prompt that always produces a wrapped vehicle photo.

    Uses the decision context to make it relevant, but guarantees the output
    is a photograph of a wrapped vehicle — never text, never a template.
    """
    topic = decision.get("topic", "")
    image_prompt = decision.get("image_prompt", "")
    audience = decision.get("audience", "")

    # Pick vehicle, wrap style, and setting — use decision hints if available
    vehicle = random.choice(VEHICLE_TYPES)
    wrap = random.choice(WRAP_STYLES)
    setting = random.choice(SETTINGS)

    # Try to extract vehicle/wrap hints from the decision
    topic_lower = (topic + " " + image_prompt).lower()
    for v in VEHICLE_TYPES:
        if any(word in topic_lower for word in v.lower().split()[:2]):
            vehicle = v
            break
    for w in WRAP_STYLES:
        if any(word in topic_lower for word in w.lower().split()[:2]):
            wrap = w
            break

    # If the topic mentions fleet/commercial, bias toward commercial vehicles
    if any(kw in topic_lower for kw in ["fleet", "commercial", "business", "delivery", "van", "truck wrap", "box truck"]):
        vehicle = random.choice([
            "Mercedes Sprinter van", "Ford Transit cargo van", "Ram ProMaster van",
            "box truck", "food truck", "Ford F-150 pickup truck",
        ])
        wrap = random.choice([
            "full commercial fleet graphics wrap",
            "branded delivery van wrap with company logo graphics",
            "matte black vinyl wrap", "gloss white wrap with vinyl lettering",
        ])

    prompt = (
        f"Professional automotive photograph of a {vehicle} with a {wrap}, "
        f"{setting}. The wrap is freshly installed, flawless, with no bubbles "
        f"or imperfections. Shot with a Canon EOS R5, 85mm lens, shallow depth "
        f"of field, natural lighting, photorealistic, ultra high resolution, 8K quality. "
        f"The vehicle is the hero of the image — no people, no text, no logos, "
        f"no watermarks, no words anywhere in the image."
    )

    return prompt


def _build_simple_fallback_prompt() -> str:
    """Build a simpler prompt for retry attempts."""
    vehicle = random.choice(VEHICLE_TYPES[:10])  # stick to common vehicles
    wrap = random.choice(WRAP_STYLES[:10])
    return (
        f"Professional photo of a {vehicle} with a {wrap} parked in Chicago. "
        f"Photorealistic, high quality, no text, no logos, no watermarks, no words."
    )


# ─────────────────────────────────────────────
# AI IMAGE GENERATION (DALL-E with retries)
# ─────────────────────────────────────────────

def generate_ai_image(image_prompt: str, retries: int = 3) -> str:
    """Generate an AI image via DALL-E. Retries with simpler prompts on failure.

    Returns local filepath or empty string.
    """
    _ensure_dirs()

    for attempt in range(retries):
        prompt = image_prompt if attempt == 0 else _build_simple_fallback_prompt()
        print(f"  [MEDIA] AI image attempt {attempt + 1}/{retries}: {prompt[:100]}...", flush=True)

        try:
            response = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )

            image_url = response.data[0].url
            if not image_url:
                print(f"  [MEDIA] Attempt {attempt + 1}: no URL returned", flush=True)
                continue

            timestamp = int(time.time())
            filepath = os.path.join(MEDIA_DIR, f"cfw_ai_{timestamp}_{attempt}.png")

            img_response = requests.get(image_url, timeout=60)
            if img_response.status_code == 200:
                with open(filepath, "wb") as f:
                    f.write(img_response.content)
                print(f"  [MEDIA] AI image saved: {filepath}", flush=True)
                _log_generation("ai_image", prompt[:300], filepath)
                return filepath
            else:
                print(f"  [MEDIA] Attempt {attempt + 1}: download failed ({img_response.status_code})", flush=True)

        except Exception as e:
            print(f"  [MEDIA] Attempt {attempt + 1} failed: {e}", flush=True)
            time.sleep(2)

    print("  [MEDIA] All AI image attempts failed", flush=True)
    return ""


# ─────────────────────────────────────────────
# STOCK PHOTO FALLBACK (last resort)
# ─────────────────────────────────────────────

def _download_stock_fallback() -> str:
    """Download a free stock photo of a wrapped/modified vehicle as absolute last resort.

    Uses Unsplash/Pexels free API for a car photo. This is better than
    posting nothing or posting a text-on-gradient template.
    """
    _ensure_dirs()
    print("  [MEDIA] Trying stock photo fallback...", flush=True)

    # Try Pexels free API (no key needed for basic search)
    search_terms = [
        "wrapped car", "vinyl wrap vehicle", "custom car wrap",
        "matte black car", "vehicle graphics", "fleet vehicle wrap",
        "car color change", "modified sports car",
    ]
    query = random.choice(search_terms)

    try:
        # Pexels API (free tier)
        pexels_key = os.environ.get("PEXELS_API_KEY", "")
        if pexels_key:
            r = requests.get(
                "https://api.pexels.com/v1/search",
                headers={"Authorization": pexels_key},
                params={"query": query, "per_page": 10, "orientation": "square"},
                timeout=15,
            )
            if r.status_code == 200:
                photos = r.json().get("photos", [])
                if photos:
                    photo = random.choice(photos)
                    img_url = photo.get("src", {}).get("large2x", photo.get("src", {}).get("large", ""))
                    if img_url:
                        img_r = requests.get(img_url, timeout=30)
                        if img_r.status_code == 200:
                            filepath = os.path.join(MEDIA_DIR, f"cfw_stock_{int(time.time())}.jpg")
                            with open(filepath, "wb") as f:
                                f.write(img_r.content)
                            print(f"  [MEDIA] Stock photo saved: {filepath}", flush=True)
                            _log_generation("stock_photo", query, filepath)
                            return filepath
    except Exception as e:
        print(f"  [MEDIA] Stock photo fallback failed: {e}", flush=True)

    return ""


# ─────────────────────────────────────────────
# MAIN IMAGE GENERATION (with fallback chain)
# ─────────────────────────────────────────────

def generate_image(image_prompt: str = "", style: str = "photorealistic",
                   decision: dict = None) -> str:
    """Generate an image of a wrapped vehicle.

    Fallback chain:
    1. DALL-E with full detailed prompt (3 retries)
    2. Stock photo of a wrapped/modified car
    3. Empty string (post will be skipped — never post without an image)

    NEVER returns a Pillow template or text-on-gradient image.
    """
    _ensure_dirs()

    if decision is None:
        decision = {}

    # Build a proper wrapped-vehicle prompt
    if not image_prompt:
        image_prompt = _build_vehicle_image_prompt(decision)
    else:
        # Enhance whatever prompt was provided to ensure it's a vehicle photo
        if "vehicle" not in image_prompt.lower() and "car" not in image_prompt.lower() and "truck" not in image_prompt.lower() and "van" not in image_prompt.lower():
            image_prompt = (
                f"Professional automotive photograph: {image_prompt}. "
                f"Must show a real wrapped vehicle. Photorealistic, no text, no logos, no watermarks."
            )

    # Attempt 1: DALL-E AI generation (with retries)
    ai_image = generate_ai_image(image_prompt, retries=3)
    if ai_image:
        return ai_image

    # Attempt 2: Stock photo fallback
    stock = _download_stock_fallback()
    if stock:
        return stock

    # No image available — return empty (caller must NOT post without an image)
    print("  [MEDIA] CRITICAL: No image could be generated. Post will be skipped.", flush=True)
    return ""


def generate_branded_image(headline: str, subtext: str = "",
                           topic: str = "", style_idx: int = None) -> str:
    """Generate an AI image of a wrapped vehicle based on headline/topic.

    This replaces the old Pillow template function. Now it always generates
    a real AI photo of a wrapped vehicle — never a text-on-gradient template.
    """
    decision = {
        "topic": topic or headline,
        "image_prompt": f"{headline}. {subtext}".strip(),
        "headline": headline,
        "subtext": subtext,
    }
    return generate_image(decision=decision)


# ─────────────────────────────────────────────
# VIDEO GENERATION (from image)
# ─────────────────────────────────────────────

def create_slideshow_video(image_path: str, caption: str, duration: int = 10) -> str:
    """Create a simple slideshow video from an image for TikTok."""
    _ensure_dirs()

    if not image_path or not os.path.exists(image_path):
        print("  [MEDIA] No image for video creation", flush=True)
        return ""

    timestamp = int(time.time())
    video_path = os.path.join(MEDIA_DIR, f"cfw_video_{timestamp}.mp4")

    try:
        import subprocess

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", image_path,
            "-vf", f"zoompan=z='min(zoom+0.001,1.3)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={duration*25}:s=1080x1080:fps=25",
            "-c:v", "libx264",
            "-t", str(duration),
            "-pix_fmt", "yuv420p",
            "-preset", "fast",
            video_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if result.returncode == 0 and os.path.exists(video_path):
            print(f"  [MEDIA] Video created: {video_path}", flush=True)
            _log_generation("video", f"slideshow from {image_path}", video_path)
            return video_path
        else:
            print(f"  [MEDIA] ffmpeg error: {result.stderr[:200]}", flush=True)
            return ""

    except Exception as e:
        print(f"  [MEDIA] Video creation error: {e}", flush=True)
        return ""


# ─────────────────────────────────────────────
# PLATFORM CAPTION ADAPTATION
# ─────────────────────────────────────────────

def adapt_captions(decision: dict) -> dict:
    """Adapt caption for each platform. Same content, different voice."""
    base_caption = decision.get("caption", "")
    base_hashtags = decision.get("hashtags", [])
    topic = decision.get("topic", "")

    try:
        prompt = f"""You have ONE piece of content about: {topic}

Original caption: {base_caption}
Original hashtags: {', '.join(base_hashtags)}

Adapt this caption for THREE platforms. Same content, different voice.
Return ONLY valid JSON:

{{
    "facebook": {{
        "caption": "Facebook version — conversational, longer, ask a question to spark discussion",
        "hashtags": ["3-5 relevant hashtags"]
    }},
    "instagram": {{
        "caption": "Instagram version — visual-first, engaging, polished but real",
        "hashtags": ["15-25 relevant hashtags for reach"]
    }},
    "tiktok": {{
        "caption": "TikTok version — hook in first 3 words, short, trendy, casual",
        "hashtags": ["5-8 trending relevant hashtags"]
    }}
}}

RULES:
- Each platform caption should feel NATIVE to that platform
- Sound like a real business owner (Roy), not a marketing agency
- No emojis"""

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=600,
        )

        result = response.choices[0].message.content.strip()
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]

        return json.loads(result.strip())

    except Exception as e:
        print(f"  [MEDIA] Caption adaptation error: {e}", flush=True)
        return {
            "facebook": {"caption": base_caption, "hashtags": base_hashtags[:5]},
            "instagram": {"caption": base_caption, "hashtags": base_hashtags},
            "tiktok": {"caption": base_caption[:150], "hashtags": base_hashtags[:8]},
        }


# ─────────────────────────────────────────────
# FULL CONTENT PACKAGE
# ─────────────────────────────────────────────

def create_content_package(decision: dict) -> dict:
    """Create a complete content package from a brain decision.

    Generates one unique piece of content and packages it for all platforms.
    ALWAYS produces an AI image of a wrapped vehicle — never a template.
    If no image can be generated, returns {"unique": False} to skip this post.
    """
    _ensure_dirs()

    topic = decision.get("topic", "vehicle wrap")
    image_prompt = decision.get("image_prompt", "")

    # Check uniqueness
    if not is_content_unique(topic, image_prompt):
        print(f"  [MEDIA] Content already published, requesting new decision", flush=True)
        return {"unique": False}

    content_id = f"content_{int(time.time())}"

    # Step 1: Generate the AI image (MUST be a wrapped vehicle photo)
    image_path = generate_image(image_prompt, decision=decision)

    if not image_path or not os.path.exists(image_path):
        print(f"  [MEDIA] SKIPPING: Could not generate image for '{topic}'", flush=True)
        return {"unique": False}

    # Step 2: Create video version for TikTok
    video_path = ""
    if image_path:
        video_path = create_slideshow_video(image_path, decision.get("caption", ""))

    # Step 3: Adapt captions for each platform
    platform_content = adapt_captions(decision)

    # Step 4: Mark as published
    mark_content_published(topic, image_prompt)

    package = {
        "image_path": image_path,
        "video_path": video_path,
        "platforms": platform_content,
        "topic": topic,
        "content_id": content_id,
        "unique": True,
        "decision": decision,
        "generated_at": datetime.now().isoformat(),
    }

    _log_generation("package", json.dumps(decision)[:300], content_id)

    print(f"  [MEDIA] Content package ready: {content_id}", flush=True)
    print(f"  [MEDIA]   Image: {image_path}", flush=True)
    print(f"  [MEDIA]   Video: {'YES' if video_path else 'NO'}", flush=True)

    return package


# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────

def _log_generation(media_type: str, prompt: str, output: str):
    _ensure_dirs()
    log = []
    if os.path.exists(MEDIA_LOG):
        try:
            with open(MEDIA_LOG, "r") as f:
                log = json.load(f)
        except Exception:
            log = []

    log.append({
        "date": datetime.now().isoformat(),
        "type": media_type,
        "prompt": prompt[:300],
        "output": output,
    })
    log = log[-500:]
    with open(MEDIA_LOG, "w") as f:
        json.dump(log, f, indent=2)


if __name__ == "__main__":
    # Test AI image generation
    test_decision = {
        "topic": "matte black Ford F-150 fleet wrap",
        "image_prompt": "Ford F-150 with matte black vinyl wrap in Chicago",
        "caption": "Transform your fleet with premium matte black wraps",
    }
    result = generate_image(decision=test_decision)
    print(f"Test result: {result}")
