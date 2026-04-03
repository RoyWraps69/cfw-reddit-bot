"""
Instagram Bot v4.0 — Graph API Edition
Posts to @chicago_fleet_wraps via Meta Graph API.
No browser automation — rock solid API calls only.
"""

import os, json, time, logging, requests, subprocess

log = logging.getLogger("instagram_bot")

IG_ACCOUNT_ID = "17841470140774907"
GRAPH_URL = "https://graph.facebook.com/v25.0"
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
TOKEN_FILE = os.path.join(DATA_DIR, "fb_page_token.txt")  # Same token works for IG
HISTORY_FILE = os.path.join(DATA_DIR, "ig_post_history.json")


def _get_token() -> str:
    if os.path.exists(TOKEN_FILE):
        return open(TOKEN_FILE).read().strip()
    return os.environ.get("FB_PAGE_TOKEN", "")


def _load_history() -> list:
    if os.path.exists(HISTORY_FILE):
        try:
            return json.load(open(HISTORY_FILE))
        except Exception:
            return []
    return []


def _save_history(history: list):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(HISTORY_FILE, "w") as f:
        json.dump(history[-200:], f, indent=2)


def _upload_image_public(image_path: str) -> str:
    """Upload image to get a public URL (required by Instagram API)."""
    try:
        result = subprocess.run(
            ["manus-upload-file", image_path],
            capture_output=True, text=True, timeout=120
        )
        for line in result.stdout.strip().split("\n"):
            if "CDN URL:" in line:
                return line.split("CDN URL:")[-1].strip()
            if line.strip().startswith("http"):
                return line.strip()
    except Exception as e:
        log.error(f"Upload failed: {e}")
    return ""


def post_with_image(caption: str, image_path: str) -> dict:
    """Post a photo with caption to Instagram."""
    token = _get_token()
    if not token:
        return {"success": False, "error": "No token"}

    public_url = _upload_image_public(image_path)
    if not public_url:
        print(f"  [INSTAGRAM] Failed to upload image to public URL", flush=True)
        return {"success": False, "error": "Image upload failed"}

    # Step 1: Create media container
    r = requests.post(f"{GRAPH_URL}/{IG_ACCOUNT_ID}/media", data={
        "image_url": public_url,
        "caption": caption,
        "access_token": token
    })
    data = r.json()
    print(f"  [INSTAGRAM] Container: {r.status_code}", flush=True)

    if r.status_code != 200 or "id" not in data:
        print(f"  [INSTAGRAM] Container failed: {data}", flush=True)
        return {"success": False, "error": str(data)}

    container_id = data["id"]

    # Step 2: Wait for processing
    print(f"  [INSTAGRAM] Waiting for media processing...", flush=True)
    for attempt in range(12):
        time.sleep(5)
        status_r = requests.get(f"{GRAPH_URL}/{container_id}",
            params={"fields": "status_code", "access_token": token})
        if status_r.status_code == 200:
            status = status_r.json().get("status_code", "")
            if status == "FINISHED":
                break
            elif status == "ERROR":
                print(f"  [INSTAGRAM] Media processing error", flush=True)
                return {"success": False, "error": "Media processing failed"}

    # Step 3: Publish
    r2 = requests.post(f"{GRAPH_URL}/{IG_ACCOUNT_ID}/media_publish", data={
        "creation_id": container_id,
        "access_token": token
    })
    data2 = r2.json()
    print(f"  [INSTAGRAM] Publish: {r2.status_code}", flush=True)

    if r2.status_code == 200 and "id" in data2:
        media_id = data2["id"]
        permalink = ""
        try:
            pr = requests.get(f"{GRAPH_URL}/{media_id}",
                params={"fields": "permalink", "access_token": token})
            if pr.status_code == 200:
                permalink = pr.json().get("permalink", "")
        except Exception:
            pass

        record = {
            "media_id": media_id,
            "caption": caption[:200],
            "type": "photo",
            "timestamp": time.time(),
            "url": permalink or "https://instagram.com/chicago_fleet_wraps"
        }
        history = _load_history()
        history.append(record)
        _save_history(history)
        print(f"  [INSTAGRAM] Posted: {record['url']}", flush=True)
        return {"success": True, "media_id": media_id, "url": record["url"]}

    print(f"  [INSTAGRAM] Publish failed: {data2}", flush=True)
    return {"success": False, "error": str(data2)}


def get_engagement(media_id: str) -> dict:
    """Get engagement stats for a post."""
    token = _get_token()
    if not token:
        return {}
    r = requests.get(f"{GRAPH_URL}/{media_id}",
        params={"fields": "like_count,comments_count", "access_token": token})
    if r.status_code == 200:
        d = r.json()
        return {
            "likes": d.get("like_count", 0),
            "comments": d.get("comments_count", 0)
        }
    return {}


# ─── Public interface for master.py ──────────────────────────────

def create_post(caption: str = "", image_path: str = "", **kwargs) -> dict:
    """Main entry: create an Instagram post (always requires an image)."""
    from media_generator import generate_branded_image

    if not caption:
        caption = kwargs.get("text", "Chicago Fleet Wraps — premium vehicle wraps. #VehicleWraps #ChicagoFleetWraps")

    if not image_path or not os.path.exists(image_path):
        try:
            headline = caption[:60]
            subtext = caption[60:160] if len(caption) > 60 else ""
            image_path = generate_branded_image(headline, subtext)
        except Exception as e:
            log.warning(f"Image gen failed: {e}")
            return {"success": False, "error": "Instagram requires an image"}

    return post_with_image(caption, image_path)


def engage_with_posts(**kwargs) -> dict:
    """Check engagement on recent posts."""
    stats = {"checked": 0, "total_likes": 0, "total_comments": 0}
    for post in _load_history()[-10:]:
        eng = get_engagement(post.get("media_id", ""))
        if eng:
            stats["checked"] += 1
            stats["total_likes"] += eng.get("likes", 0)
            stats["total_comments"] += eng.get("comments", 0)
    return stats


def start(**kwargs):
    print("  [INSTAGRAM] Graph API bot ready", flush=True)


def stop(**kwargs):
    pass
