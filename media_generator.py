"""
Chicago Fleet Wraps — Media Generator v1.0
AI IMAGE & VIDEO GENERATION FOR SOCIAL MEDIA

This module:
1. Takes a content decision from the brain
2. Generates a unique AI image (via OpenAI DALL-E or compatible API)
3. Optionally creates a slideshow video from the image for TikTok
4. Adapts the caption for each platform's native voice
5. Returns platform-ready content packages

RULE: Each post is UNIQUE content, but the SAME content gets published
across all platforms (Facebook, Instagram, TikTok) simultaneously,
with platform-specific caption adaptations.
"""
import os
import json
import time
import hashlib
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


def _load_published_hashes() -> set:
    """Load hashes of previously published content to ensure uniqueness."""
    if os.path.exists(PUBLISHED_HASHES):
        try:
            with open(PUBLISHED_HASHES, "r") as f:
                return set(json.load(f))
        except Exception:
            pass
    return set()


def _save_published_hash(content_hash: str):
    """Save a content hash to prevent duplicate posts."""
    hashes = _load_published_hashes()
    hashes.add(content_hash)
    # Keep last 2000 hashes
    hashes_list = list(hashes)[-2000:]
    with open(PUBLISHED_HASHES, "w") as f:
        json.dump(hashes_list, f)


def _content_hash(topic: str, image_prompt: str) -> str:
    """Generate a hash for content uniqueness check."""
    raw = f"{topic.lower().strip()}|{image_prompt.lower().strip()}"
    return hashlib.md5(raw.encode()).hexdigest()


def is_content_unique(topic: str, image_prompt: str) -> bool:
    """Check if this content has been published before."""
    h = _content_hash(topic, image_prompt)
    return h not in _load_published_hashes()


def mark_content_published(topic: str, image_prompt: str):
    """Mark content as published to prevent future duplicates."""
    h = _content_hash(topic, image_prompt)
    _save_published_hash(h)


# ─────────────────────────────────────────────
# AI IMAGE GENERATION
# ─────────────────────────────────────────────

def generate_image(image_prompt: str, style: str = "photorealistic") -> str:
    """Generate an AI image using OpenAI DALL-E API.
    
    Returns the local file path of the saved image, or empty string on failure.
    """
    _ensure_dirs()

    # Enhance the prompt for better results
    enhanced_prompt = _enhance_image_prompt(image_prompt, style)

    print(f"  [MEDIA] Generating image: {enhanced_prompt[:80]}...", flush=True)

    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=enhanced_prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )

        image_url = response.data[0].url
        if not image_url:
            print("  [MEDIA] No image URL returned", flush=True)
            return ""

        # Download the image
        timestamp = int(time.time())
        filename = f"cfw_post_{timestamp}.png"
        filepath = os.path.join(MEDIA_DIR, filename)

        img_response = requests.get(image_url, timeout=60)
        if img_response.status_code == 200:
            with open(filepath, "wb") as f:
                f.write(img_response.content)
            print(f"  [MEDIA] Image saved: {filepath}", flush=True)
            _log_generation("image", enhanced_prompt, filepath)
            return filepath
        else:
            print(f"  [MEDIA] Download failed: {img_response.status_code}", flush=True)
            return ""

    except Exception as e:
        print(f"  [MEDIA] Image generation error: {e}", flush=True)
        # Fallback: try with a simpler prompt
        return _fallback_image_generation(image_prompt)


def _enhance_image_prompt(prompt: str, style: str) -> str:
    """Enhance the image prompt for better AI generation results."""
    style_additions = {
        "photorealistic": "Photorealistic, professional automotive photography, high resolution, 4K quality, natural lighting",
        "dramatic": "Dramatic cinematic lighting, moody atmosphere, professional automotive photography, 4K",
        "clean": "Clean studio lighting, white background, professional product photography, sharp focus",
        "urban": "Urban street photography, city backdrop, natural lighting, candid feel, high quality",
        "action": "Dynamic angle, motion blur background, sharp subject, professional sports photography",
    }

    addition = style_additions.get(style, style_additions["photorealistic"])

    # Add Chicago context if not already present
    chicago_context = ""
    if "chicago" not in prompt.lower():
        chicago_context = ", Chicago cityscape in background"

    # Ensure no text/logos in the image (AI struggles with text)
    no_text = ". Do NOT include any text, logos, watermarks, or words in the image."

    return f"{prompt}{chicago_context}. {addition}{no_text}"


def _fallback_image_generation(original_prompt: str) -> str:
    """Fallback image generation with a simplified prompt."""
    _ensure_dirs()
    simple_prompt = f"Professional photo of a wrapped vehicle, vinyl car wrap, automotive photography, high quality, no text or logos"

    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=simple_prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )

        image_url = response.data[0].url
        if not image_url:
            return ""

        timestamp = int(time.time())
        filepath = os.path.join(MEDIA_DIR, f"cfw_fallback_{timestamp}.png")

        img_response = requests.get(image_url, timeout=60)
        if img_response.status_code == 200:
            with open(filepath, "wb") as f:
                f.write(img_response.content)
            print(f"  [MEDIA] Fallback image saved: {filepath}", flush=True)
            return filepath

    except Exception as e:
        print(f"  [MEDIA] Fallback generation also failed: {e}", flush=True)

    return ""


# ─────────────────────────────────────────────
# VIDEO GENERATION (from image)
# ─────────────────────────────────────────────

def create_slideshow_video(image_path: str, caption: str, duration: int = 10) -> str:
    """Create a simple slideshow video from an image for TikTok.
    
    Uses ffmpeg to create a video with zoom/pan effect.
    Returns the video file path, or empty string on failure.
    """
    _ensure_dirs()

    if not image_path or not os.path.exists(image_path):
        print("  [MEDIA] No image for video creation", flush=True)
        return ""

    timestamp = int(time.time())
    video_path = os.path.join(MEDIA_DIR, f"cfw_video_{timestamp}.mp4")

    try:
        import subprocess

        # Ken Burns effect: slow zoom in over duration
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
    """Take a single content decision and adapt the caption for each platform.
    
    Same content, different voice per platform.
    Returns dict with platform-specific captions and hashtags.
    """
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
        "caption": "Facebook version — conversational, can be longer, ask a question to spark discussion, informative",
        "hashtags": ["3-5 relevant hashtags"]
    }},
    "instagram": {{
        "caption": "Instagram version — visual-first, engaging, slightly polished but still real",
        "hashtags": ["15-25 relevant hashtags for reach"]
    }},
    "tiktok": {{
        "caption": "TikTok version — hook in first 3 words, short, trendy, casual",
        "hashtags": ["5-8 trending relevant hashtags"]
    }}
}}

RULES:
- Each platform caption should feel NATIVE to that platform
- Facebook: longer, discussion-oriented, ask a question
- Instagram: medium length, visual description, heavy hashtags
- TikTok: SHORT, punchy, hook-first, trending hashtags
- All must be about the same topic/content
- Sound like a real business, not a marketing agency
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

        adapted = json.loads(result.strip())
        return adapted

    except Exception as e:
        print(f"  [MEDIA] Caption adaptation error: {e}", flush=True)
        # Fallback: use the same caption everywhere
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
    
    This is the main function called by the master orchestrator.
    It generates one unique piece of content and packages it for all platforms.
    
    Returns:
    {
        "image_path": "/path/to/image.png",
        "video_path": "/path/to/video.mp4" or "",
        "platforms": {
            "facebook": {"caption": "...", "hashtags": [...]},
            "instagram": {"caption": "...", "hashtags": [...]},
            "tiktok": {"caption": "...", "hashtags": [...]},
        },
        "topic": "...",
        "content_id": "unique_id",
        "unique": True/False,
    }
    """
    _ensure_dirs()

    topic = decision.get("topic", "vehicle wrap")
    image_prompt = decision.get("image_prompt", "")

    # Check uniqueness
    if not is_content_unique(topic, image_prompt):
        print(f"  [MEDIA] Content already published, requesting new decision", flush=True)
        return {"unique": False}

    content_id = f"content_{int(time.time())}"

    # Step 1: Generate the image
    image_path = ""
    if image_prompt:
        image_path = generate_image(image_prompt)

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

    # Log the package
    _log_generation("package", json.dumps(decision)[:300], content_id)

    print(f"  [MEDIA] Content package ready: {content_id}", flush=True)
    print(f"  [MEDIA]   Image: {'YES' if image_path else 'NO'}", flush=True)
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
    # Test image generation
    test_prompt = "A matte black Tesla Model Y with a vinyl wrap, parked in front of the Chicago Bean sculpture at Millennium Park, golden hour lighting, professional automotive photography"
    result = generate_image(test_prompt)
    print(f"Test result: {result}")
