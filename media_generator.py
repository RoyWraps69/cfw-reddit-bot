"""
Chicago Fleet Wraps — Media Generator v4.0
PRE-GENERATED CDN IMAGE LIBRARY + AI CAPTIONS

v4.0 ARCHITECTURE:
- Images are PRE-GENERATED externally (via Manus/NanoBanana) and uploaded to CDN
- This module picks the best image from data/image_library.json based on topic
- NO runtime DALL-E calls — zero OpenAI image API dependency
- NO Pillow templates, NO gradient backgrounds, NO text-on-color
- Every image shows an installer wrapping a vehicle inside a shop
- Caption adaptation per platform via GPT
- Content uniqueness tracking
- Least-recently-used rotation so images don't repeat

RULE: Each post is UNIQUE content, but the SAME content gets published
across all platforms (Facebook, Instagram, TikTok) simultaneously,
with platform-specific caption adaptations.
"""
import os
import json
import time
import hashlib
import random
import logging
from datetime import datetime
from openai import OpenAI
from config import DATA_DIR, OPENAI_MODEL, BUSINESS_CONTEXT

log = logging.getLogger("media_generator")

# Chat completions client — uses proxy if configured
_chat_base_url = os.environ.get("OPENAI_BASE_URL", None)
client = OpenAI(base_url=_chat_base_url) if _chat_base_url else OpenAI()

MEDIA_DIR = os.path.join(DATA_DIR, "generated_media")
MEDIA_LOG = os.path.join(DATA_DIR, "media_generation_log.json")
PUBLISHED_HASHES = os.path.join(DATA_DIR, "published_content_hashes.json")
IMAGE_LIBRARY = os.path.join(DATA_DIR, "image_library.json")


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


def _content_hash(topic: str, image_id: str) -> str:
    raw = f"{topic.lower().strip()}|{image_id.lower().strip()}"
    return hashlib.md5(raw.encode()).hexdigest()


def is_content_unique(topic: str, image_id: str) -> bool:
    h = _content_hash(topic, image_id)
    return h not in _load_published_hashes()


def mark_content_published(topic: str, image_id: str):
    h = _content_hash(topic, image_id)
    _save_published_hash(h)


# ─────────────────────────────────────────────
# PRE-GENERATED IMAGE LIBRARY
# ─────────────────────────────────────────────

def _load_image_library() -> list:
    """Load the pre-generated image library from JSON."""
    if os.path.exists(IMAGE_LIBRARY):
        try:
            with open(IMAGE_LIBRARY, "r") as f:
                data = json.load(f)
                return data.get("images", [])
        except Exception as e:
            log.warning(f"Failed to load image library: {e}")
    return []


def _save_image_library(images: list):
    """Save updated image library (with usage counts)."""
    data = {
        "version": "1.0",
        "updated_at": datetime.now().isoformat(),
        "description": "Pre-generated AI images of wrapped vehicles for social media posting.",
        "images": images,
    }
    with open(IMAGE_LIBRARY, "w") as f:
        json.dump(data, f, indent=2)


def _score_image_for_topic(image: dict, topic: str, image_prompt: str = "") -> float:
    """Score how well an image matches a topic. Higher = better match."""
    score = 0.0
    topic_lower = (topic + " " + image_prompt).lower()
    tags = image.get("tags", [])
    vehicle = image.get("vehicle", "").lower()
    wrap_style = image.get("wrap_style", "").lower()

    # Tag matches
    for tag in tags:
        if tag.lower() in topic_lower:
            score += 2.0

    # Vehicle match
    for word in vehicle.split():
        if word in topic_lower:
            score += 3.0

    # Wrap style match
    for word in wrap_style.split():
        if word in topic_lower:
            score += 2.5

    # Fleet/commercial topic → prefer van/truck images
    if any(kw in topic_lower for kw in ["fleet", "commercial", "business", "delivery"]):
        if any(t in tags for t in ["van", "fleet", "commercial", "truck"]):
            score += 5.0

    # Sports car topic → prefer sports car images
    if any(kw in topic_lower for kw in ["sports", "exotic", "luxury", "color change", "chameleon"]):
        if any(t in tags for t in ["sports car", "exotic", "chameleon"]):
            score += 5.0

    # Penalize heavily-used images (least-recently-used rotation)
    used_count = image.get("used_count", 0)
    score -= used_count * 3.0

    return score


def pick_image(decision: dict) -> dict:
    """Pick the best image from the library for a given content decision.

    Uses topic matching + least-recently-used rotation to ensure variety.
    Returns the image dict with 'url' field, or {} if library is empty.
    """
    images = _load_image_library()
    if not images:
        log.warning("Image library is empty! No pre-generated images available.")
        return {}

    topic = decision.get("topic", "")
    image_prompt = decision.get("image_prompt", "")

    # Score all images
    scored = []
    for img in images:
        s = _score_image_for_topic(img, topic, image_prompt)
        scored.append((s, img))

    # Sort by score (highest first), with random tiebreaker
    scored.sort(key=lambda x: (x[0], random.random()), reverse=True)

    # Pick the best match
    best = scored[0][1]

    # Update usage count
    best["used_count"] = best.get("used_count", 0) + 1
    best["last_used"] = datetime.now().isoformat()
    _save_image_library(images)

    log.info(f"  [MEDIA] Selected image: {best.get('id')} (vehicle={best.get('vehicle')}, wrap={best.get('wrap_style')})")
    print(f"  [MEDIA] Selected image: {best.get('id')} — {best.get('vehicle')} {best.get('wrap_style')}", flush=True)

    return best


def generate_image(image_prompt: str = "", style: str = "photorealistic",
                   decision: dict = None) -> str:
    """Get an image URL from the pre-generated library.

    This replaces the old DALL-E runtime generation. Now it simply picks
    the best matching pre-generated image from the CDN library.

    Returns the CDN URL string, or empty string if library is empty.
    """
    if decision is None:
        decision = {}

    if not decision.get("topic") and image_prompt:
        decision["topic"] = image_prompt
        decision["image_prompt"] = image_prompt

    img = pick_image(decision)
    if img and img.get("url"):
        return img["url"]

    log.error("  [MEDIA] CRITICAL: No images in library. Cannot generate content.")
    print("  [MEDIA] CRITICAL: Image library is empty. Run content pre-generation first.", flush=True)
    return ""


def generate_branded_image(headline: str, subtext: str = "",
                           topic: str = "", style_idx: int = None) -> str:
    """Get a pre-generated image URL based on headline/topic.

    This replaces the old Pillow template function. Now it picks from
    the pre-generated CDN library — never generates at runtime.
    """
    decision = {
        "topic": topic or headline,
        "image_prompt": f"{headline}. {subtext}".strip(),
    }
    return generate_image(decision=decision)


# ─────────────────────────────────────────────
# VIDEO GENERATION (from image URL)
# ─────────────────────────────────────────────

def create_slideshow_video(image_source: str, caption: str, duration: int = 10) -> str:
    """Create a simple slideshow video from an image for TikTok.

    image_source can be a local path or a CDN URL.
    """
    _ensure_dirs()

    if not image_source:
        print("  [MEDIA] No image for video creation", flush=True)
        return ""

    # If it's a URL, download it first
    local_path = image_source
    if image_source.startswith("http"):
        try:
            import requests
            r = requests.get(image_source, timeout=30)
            if r.status_code == 200:
                local_path = os.path.join(MEDIA_DIR, f"video_src_{int(time.time())}.png")
                with open(local_path, "wb") as f:
                    f.write(r.content)
            else:
                print(f"  [MEDIA] Failed to download image for video: {r.status_code}", flush=True)
                return ""
        except Exception as e:
            print(f"  [MEDIA] Image download error: {e}", flush=True)
            return ""

    if not os.path.exists(local_path):
        print("  [MEDIA] No local image for video creation", flush=True)
        return ""

    timestamp = int(time.time())
    video_path = os.path.join(MEDIA_DIR, f"cfw_video_{timestamp}.mp4")

    try:
        import subprocess

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", local_path,
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
            _log_generation("video", f"slideshow from {image_source}", video_path)
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
Original hashtags: {', '.join(base_hashtags) if isinstance(base_hashtags, list) else base_hashtags}

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
- Every caption must end with an engagement question for business owners
- Geo-target Chicago, IL area
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
            "facebook": {"caption": base_caption, "hashtags": base_hashtags[:5] if isinstance(base_hashtags, list) else []},
            "instagram": {"caption": base_caption, "hashtags": base_hashtags if isinstance(base_hashtags, list) else []},
            "tiktok": {"caption": base_caption[:150], "hashtags": base_hashtags[:8] if isinstance(base_hashtags, list) else []},
        }


# ─────────────────────────────────────────────
# FULL CONTENT PACKAGE
# ─────────────────────────────────────────────

def create_content_package(decision: dict) -> dict:
    """Create a complete content package from a brain decision.

    Picks a pre-generated image from the CDN library and generates
    platform-adapted captions. No runtime image generation needed.
    If no image is available, returns {"unique": False} to skip.
    """
    _ensure_dirs()

    topic = decision.get("topic", "vehicle wrap")
    image_prompt = decision.get("image_prompt", "")

    # Pick an image from the pre-generated library
    image = pick_image(decision)
    if not image or not image.get("url"):
        print(f"  [MEDIA] SKIPPING: No images available in library for '{topic}'", flush=True)
        return {"unique": False}

    image_url = image["url"]
    image_id = image.get("id", image_url)

    # Check uniqueness (topic + image combination)
    if not is_content_unique(topic, image_id):
        print(f"  [MEDIA] Content already published (topic+image combo), requesting new decision", flush=True)
        return {"unique": False}

    content_id = f"content_{int(time.time())}"

    # Adapt captions for each platform
    platform_content = adapt_captions(decision)

    # Mark as published
    mark_content_published(topic, image_id)

    package = {
        "image_url": image_url,
        "image_id": image_id,
        "image_vehicle": image.get("vehicle", ""),
        "image_wrap_style": image.get("wrap_style", ""),
        "platforms": platform_content,
        "topic": topic,
        "content_id": content_id,
        "unique": True,
        "decision": decision,
        "generated_at": datetime.now().isoformat(),
    }

    _log_generation("package", json.dumps({"topic": topic, "image": image_id})[:300], content_id)

    print(f"  [MEDIA] Content package ready: {content_id}", flush=True)
    print(f"  [MEDIA]   Image: {image_url[:80]}...", flush=True)
    print(f"  [MEDIA]   Vehicle: {image.get('vehicle')} — {image.get('wrap_style')}", flush=True)

    return package


# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────

def _log_generation(media_type: str, prompt: str, output: str):
    _ensure_dirs()
    log_data = []
    if os.path.exists(MEDIA_LOG):
        try:
            with open(MEDIA_LOG, "r") as f:
                log_data = json.load(f)
        except Exception:
            log_data = []

    log_data.append({
        "date": datetime.now().isoformat(),
        "type": media_type,
        "prompt": prompt[:300],
        "output": output,
    })
    log_data = log_data[-500:]
    with open(MEDIA_LOG, "w") as f:
        json.dump(log_data, f, indent=2)


# ─────────────────────────────────────────────
# LIBRARY STATUS
# ─────────────────────────────────────────────

def library_status() -> dict:
    """Get status of the pre-generated image library."""
    images = _load_image_library()
    if not images:
        return {"total": 0, "status": "EMPTY — needs pre-generation"}

    total = len(images)
    used = sum(1 for img in images if img.get("used_count", 0) > 0)
    avg_usage = sum(img.get("used_count", 0) for img in images) / total if total else 0

    vehicles = list(set(img.get("vehicle", "") for img in images))
    styles = list(set(img.get("wrap_style", "") for img in images))

    return {
        "total": total,
        "used": used,
        "unused": total - used,
        "avg_usage": round(avg_usage, 1),
        "vehicles": vehicles,
        "wrap_styles": styles,
        "status": "OK" if total >= 5 else "LOW — needs more images",
    }


if __name__ == "__main__":
    # Show library status
    status = library_status()
    print(f"Image Library Status:")
    for k, v in status.items():
        print(f"  {k}: {v}")

    # Test image selection
    test_decision = {
        "topic": "matte black Ford F-150 fleet wrap",
        "image_prompt": "Ford F-150 with matte black vinyl wrap",
    }
    img = pick_image(test_decision)
    if img:
        print(f"\nSelected for test: {img.get('id')} — {img.get('url', '')[:60]}...")
    else:
        print("\nNo images available!")
