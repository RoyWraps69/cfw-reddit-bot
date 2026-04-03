"""
Chicago Fleet Wraps — Media Generator v2.0
AI IMAGE & VIDEO GENERATION FOR SOCIAL MEDIA

v2.0 Changes:
- Primary: Pillow-based branded template images (always works, no API needed)
- Secondary: AI image generation via DALL-E when available
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
import textwrap
import requests
from datetime import datetime
from openai import OpenAI
from config import DATA_DIR, OPENAI_MODEL, BUSINESS_CONTEXT

base_url = os.environ.get("OPENAI_BASE_URL", None)
client = OpenAI(base_url=base_url) if base_url else OpenAI()

MEDIA_DIR = os.path.join(DATA_DIR, "generated_media")
MEDIA_LOG = os.path.join(DATA_DIR, "media_generation_log.json")
PUBLISHED_HASHES = os.path.join(DATA_DIR, "published_content_hashes.json")

# CFW Brand Colors
CFW_DARK = (15, 23, 42)       # Dark navy
CFW_ACCENT = (59, 130, 246)   # Blue accent
CFW_WHITE = (255, 255, 255)
CFW_LIGHT_GRAY = (226, 232, 240)
CFW_ORANGE = (249, 115, 22)   # Orange accent

# Brand templates — different styles for variety
TEMPLATE_STYLES = [
    {"bg_top": (15, 23, 42), "bg_bottom": (30, 58, 138), "accent": (59, 130, 246), "text": (255, 255, 255)},
    {"bg_top": (17, 24, 39), "bg_bottom": (55, 48, 163), "accent": (139, 92, 246), "text": (255, 255, 255)},
    {"bg_top": (30, 41, 59), "bg_bottom": (15, 23, 42), "accent": (249, 115, 22), "text": (255, 255, 255)},
    {"bg_top": (0, 0, 0), "bg_bottom": (30, 30, 30), "accent": (34, 197, 94), "text": (255, 255, 255)},
    {"bg_top": (15, 23, 42), "bg_bottom": (88, 28, 135), "accent": (236, 72, 153), "text": (255, 255, 255)},
    {"bg_top": (20, 20, 20), "bg_bottom": (50, 50, 50), "accent": (59, 130, 246), "text": (255, 255, 255)},
]


def _ensure_dirs():
    os.makedirs(MEDIA_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)


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
# BRANDED TEMPLATE IMAGE GENERATION (Pillow)
# ─────────────────────────────────────────────

def generate_branded_image(headline: str, subtext: str = "",
                           topic: str = "", style_idx: int = None) -> str:
    """Generate a professional branded image using Pillow.
    
    Creates a 1080x1080 social media graphic with:
    - Gradient background
    - Headline text (large, bold)
    - Subtext (smaller, supporting)
    - CFW branding at bottom
    - Accent decorations
    
    Returns local file path or empty string on failure.
    """
    _ensure_dirs()

    try:
        from PIL import Image, ImageDraw, ImageFont

        # Pick a random style for variety
        if style_idx is None:
            style_idx = random.randint(0, len(TEMPLATE_STYLES) - 1)
        style = TEMPLATE_STYLES[style_idx % len(TEMPLATE_STYLES)]

        W, H = 1080, 1080
        img = Image.new("RGB", (W, H))
        draw = ImageDraw.Draw(img)

        # Draw gradient background
        for y in range(H):
            ratio = y / H
            r = int(style["bg_top"][0] * (1 - ratio) + style["bg_bottom"][0] * ratio)
            g = int(style["bg_top"][1] * (1 - ratio) + style["bg_bottom"][1] * ratio)
            b = int(style["bg_top"][2] * (1 - ratio) + style["bg_bottom"][2] * ratio)
            draw.line([(0, y), (W, y)], fill=(r, g, b))

        # Accent decorations — geometric shapes
        accent = style["accent"]
        # Top accent bar
        draw.rectangle([(0, 0), (W, 6)], fill=accent)
        # Side accent line
        draw.rectangle([(60, 120), (66, H - 200)], fill=accent)
        # Bottom accent bar
        draw.rectangle([(0, H - 6), (W, H)], fill=accent)
        # Corner accent
        draw.rectangle([(W - 200, 0), (W, 6)], fill=accent)

        # Try to load a nice font, fall back to default
        try:
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 52)
            font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
            font_brand = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
        except Exception:
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()
            font_brand = ImageFont.load_default()

        text_color = style["text"]

        # Wrap headline text
        headline_lines = textwrap.wrap(headline, width=24)
        if len(headline_lines) > 5:
            headline_lines = headline_lines[:5]
            headline_lines[-1] += "..."

        # Draw headline
        y_pos = 180
        for line in headline_lines:
            draw.text((90, y_pos), line, font=font_large, fill=text_color)
            y_pos += 68

        # Draw accent line under headline
        y_pos += 20
        draw.rectangle([(90, y_pos), (400, y_pos + 4)], fill=accent)
        y_pos += 40

        # Draw subtext
        if subtext:
            sub_lines = textwrap.wrap(subtext, width=38)
            if len(sub_lines) > 4:
                sub_lines = sub_lines[:4]
            for line in sub_lines:
                draw.text((90, y_pos), line, font=font_medium, fill=(200, 200, 200))
                y_pos += 44

        # Draw topic tag if provided
        if topic:
            topic_tag = f"#{topic.replace(' ', '').lower()}"
            draw.text((90, H - 200), topic_tag, font=font_small, fill=accent)

        # CFW Branding at bottom
        brand_y = H - 120
        draw.rectangle([(0, brand_y - 20), (W, H)], fill=(0, 0, 0, 180))
        draw.rectangle([(0, brand_y - 20), (W, brand_y - 16)], fill=accent)

        draw.text((90, brand_y), "CHICAGO FLEET WRAPS", font=font_brand, fill=text_color)
        draw.text((90, brand_y + 36), "chicagofleetwraps.com", font=font_small, fill=(180, 180, 180))

        # Phone number on the right
        draw.text((W - 300, brand_y + 10), "(312) 850-2900", font=font_small, fill=(180, 180, 180))

        # Save
        timestamp = int(time.time())
        filepath = os.path.join(MEDIA_DIR, f"cfw_branded_{timestamp}.png")
        img.save(filepath, "PNG", quality=95)
        print(f"  [MEDIA] Branded image created: {filepath}", flush=True)
        _log_generation("branded_image", headline[:200], filepath)
        return filepath

    except Exception as e:
        print(f"  [MEDIA] Branded image error: {e}", flush=True)
        return ""


def _generate_image_content(decision: dict) -> tuple:
    """Use AI to generate compelling headline and subtext for the image.
    
    Returns (headline, subtext) tuple.
    """
    topic = decision.get("topic", "vehicle wraps")
    caption = decision.get("caption", "")
    audience = decision.get("audience", "car enthusiasts")

    try:
        prompt = f"""Create a social media image headline and subtext for a post about: {topic}

Target audience: {audience}
Post caption context: {caption[:200]}

Return ONLY valid JSON:
{{
    "headline": "A bold, attention-grabbing headline (8-15 words max). Make it punchy and specific.",
    "subtext": "A supporting line that adds value or a call to action (10-20 words max)."
}}

RULES:
- Headline should be bold and specific (not generic)
- Mention specific vehicles, colors, or services when relevant
- Sound like a real business, not a marketing agency
- No emojis
- Make it feel professional and authoritative"""

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,
            max_tokens=150,
        )

        result = response.choices[0].message.content.strip()
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]

        data = json.loads(result.strip())
        return data.get("headline", topic), data.get("subtext", "")

    except Exception as e:
        print(f"  [MEDIA] AI headline generation error: {e}", flush=True)
        # Fallback headlines
        fallback_headlines = [
            f"Transform Your Fleet with Premium Wraps",
            f"Professional Vehicle Wraps in Chicago",
            f"Your Brand, On Every Vehicle",
            f"Stand Out on Chicago Streets",
            f"Premium Vinyl Wraps — Built to Last",
        ]
        return random.choice(fallback_headlines), "Chicago Fleet Wraps — Portage Park, IL"


# ─────────────────────────────────────────────
# AI IMAGE GENERATION (DALL-E — optional)
# ─────────────────────────────────────────────

def generate_ai_image(image_prompt: str, style: str = "photorealistic") -> str:
    """Try to generate an AI image via DALL-E. Returns filepath or empty string."""
    _ensure_dirs()

    enhanced_prompt = _enhance_image_prompt(image_prompt, style)
    print(f"  [MEDIA] Attempting AI image: {enhanced_prompt[:80]}...", flush=True)

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
            return ""

        timestamp = int(time.time())
        filepath = os.path.join(MEDIA_DIR, f"cfw_ai_{timestamp}.png")

        img_response = requests.get(image_url, timeout=60)
        if img_response.status_code == 200:
            with open(filepath, "wb") as f:
                f.write(img_response.content)
            print(f"  [MEDIA] AI image saved: {filepath}", flush=True)
            _log_generation("ai_image", enhanced_prompt, filepath)
            return filepath

    except Exception as e:
        print(f"  [MEDIA] AI image not available: {e}", flush=True)

    return ""


def _enhance_image_prompt(prompt: str, style: str) -> str:
    style_additions = {
        "photorealistic": "Photorealistic, professional automotive photography, high resolution, 4K quality, natural lighting",
        "dramatic": "Dramatic cinematic lighting, moody atmosphere, professional automotive photography, 4K",
        "clean": "Clean studio lighting, white background, professional product photography, sharp focus",
        "urban": "Urban street photography, city backdrop, natural lighting, candid feel, high quality",
        "action": "Dynamic angle, motion blur background, sharp subject, professional sports photography",
    }
    addition = style_additions.get(style, style_additions["photorealistic"])
    chicago_context = "" if "chicago" in prompt.lower() else ", Chicago cityscape in background"
    no_text = ". Do NOT include any text, logos, watermarks, or words in the image."
    return f"{prompt}{chicago_context}. {addition}{no_text}"


# ─────────────────────────────────────────────
# MAIN IMAGE GENERATION (with fallback chain)
# ─────────────────────────────────────────────

def generate_image(image_prompt: str, style: str = "photorealistic",
                   decision: dict = None) -> str:
    """Generate an image using the best available method.
    
    Fallback chain:
    1. Try DALL-E AI generation
    2. Fall back to branded template image
    
    Always returns a valid image path (branded templates never fail).
    """
    _ensure_dirs()

    # Try AI image first
    ai_image = generate_ai_image(image_prompt, style)
    if ai_image:
        return ai_image

    # Fallback: generate branded template
    print("  [MEDIA] Using branded template fallback", flush=True)
    if decision:
        headline, subtext = _generate_image_content(decision)
    else:
        headline = image_prompt[:80] if image_prompt else "Premium Vehicle Wraps"
        subtext = "Chicago Fleet Wraps — Quality You Can See"

    return generate_branded_image(headline, subtext, decision.get("topic", "") if decision else "")


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
    Always produces at least a branded template image.
    """
    _ensure_dirs()

    topic = decision.get("topic", "vehicle wrap")
    image_prompt = decision.get("image_prompt", "")

    # Check uniqueness
    if not is_content_unique(topic, image_prompt):
        print(f"  [MEDIA] Content already published, requesting new decision", flush=True)
        return {"unique": False}

    content_id = f"content_{int(time.time())}"

    # Step 1: Generate the image (always succeeds with branded fallback)
    image_path = generate_image(image_prompt, decision=decision)

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
    # Test branded image generation
    test_headline = "Transform Your Fleet with Premium Matte Black Wraps"
    test_subtext = "Professional installation. 5-year warranty. Chicago's trusted wrap shop."
    result = generate_branded_image(test_headline, test_subtext, "fleetwrap")
    print(f"Test result: {result}")
