"""
Facebook Bot v4.0 — Graph API Edition
Posts to Chicago Fleet Wraps Facebook Page via Meta Graph API.
No browser automation — rock solid API calls only.
"""

import os, json, time, logging, requests, subprocess

log = logging.getLogger("facebook_bot")

PAGE_ID = "370000372871712"
GRAPH_URL = "https://graph.facebook.com/v25.0"
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
TOKEN_FILE = os.path.join(DATA_DIR, "fb_page_token.txt")
HISTORY_FILE = os.path.join(DATA_DIR, "fb_post_history.json")


def _get_token() -> str:
    for p in [TOKEN_FILE]:
        if os.path.exists(p):
            return open(p).read().strip()
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
    """Upload image to get a public URL."""
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


def post_text(caption: str) -> dict:
    """Post text-only to Facebook Page."""
    token = _get_token()
    if not token:
        return {"success": False, "error": "No token"}

    r = requests.post(f"{GRAPH_URL}/{PAGE_ID}/feed", data={
        "message": caption,
        "access_token": token
    })
    data = r.json()
    print(f"  [FACEBOOK] Text post: {r.status_code}", flush=True)

    if r.status_code == 200 and "id" in data:
        record = {
            "post_id": data["id"],
            "caption": caption[:200],
            "type": "text",
            "timestamp": time.time(),
            "url": f"https://facebook.com/{data['id'].replace('_', '/posts/')}"
        }
        history = _load_history()
        history.append(record)
        _save_history(history)
        print(f"  [FACEBOOK] Posted: {record['url']}", flush=True)
        return {"success": True, "post_id": data["id"], "url": record["url"]}

    print(f"  [FACEBOOK] Post failed: {data}", flush=True)
    return {"success": False, "error": str(data)}


def post_with_image(caption: str, image_path: str) -> dict:
    """Post photo with caption to Facebook Page."""
    token = _get_token()
    if not token:
        return {"success": False, "error": "No token"}

    public_url = _upload_image_public(image_path)

    if public_url:
        r = requests.post(f"{GRAPH_URL}/{PAGE_ID}/photos", data={
            "url": public_url,
            "message": caption,
            "access_token": token
        })
    else:
        # Direct upload fallback
        with open(image_path, "rb") as img:
            r = requests.post(f"{GRAPH_URL}/{PAGE_ID}/photos",
                data={"message": caption, "access_token": token},
                files={"source": img}
            )

    data = r.json()
    post_id = data.get("post_id", data.get("id", ""))
    print(f"  [FACEBOOK] Photo post: {r.status_code} id={post_id}", flush=True)

    if r.status_code == 200 and post_id:
        record = {
            "post_id": post_id,
            "caption": caption[:200],
            "type": "photo",
            "timestamp": time.time(),
            "url": f"https://facebook.com/{PAGE_ID}/posts/{post_id}"
        }
        history = _load_history()
        history.append(record)
        _save_history(history)
        print(f"  [FACEBOOK] Posted: {record['url']}", flush=True)
        return {"success": True, "post_id": post_id, "url": record["url"]}

    print(f"  [FACEBOOK] Photo post failed: {data}", flush=True)
    return {"success": False, "error": str(data)}


def get_engagement(post_id: str) -> dict:
    """Get engagement stats for a post."""
    token = _get_token()
    if not token:
        return {}
    r = requests.get(f"{GRAPH_URL}/{post_id}",
        params={"fields": "likes.summary(true),comments.summary(true),shares", "access_token": token})
    if r.status_code == 200:
        d = r.json()
        return {
            "likes": d.get("likes", {}).get("summary", {}).get("total_count", 0),
            "comments": d.get("comments", {}).get("summary", {}).get("total_count", 0),
            "shares": d.get("shares", {}).get("count", 0)
        }
    return {}


def delete_post(post_id: str) -> bool:
    """Delete a post (damage control)."""
    token = _get_token()
    if not token:
        return False
    r = requests.delete(f"{GRAPH_URL}/{post_id}?access_token={token}")
    return r.status_code == 200


def check_negative_reactions() -> list:
    """Find posts with 3+ negative reactions."""
    token = _get_token()
    if not token:
        return []
    negative = []
    for post in _load_history()[-20:]:
        pid = post.get("post_id", "")
        if not pid:
            continue
        r = requests.get(f"{GRAPH_URL}/{pid}", params={
            "fields": "reactions.type(ANGRY).summary(true).as(angry),reactions.type(SAD).summary(true).as(sad)",
            "access_token": token
        })
        if r.status_code == 200:
            d = r.json()
            angry = d.get("angry", {}).get("summary", {}).get("total_count", 0)
            sad = d.get("sad", {}).get("summary", {}).get("total_count", 0)
            if angry + sad >= 3:
                negative.append({"post_id": pid, "angry": angry, "sad": sad})
    return negative


# ─── Public interface for master.py ──────────────────────────────

def create_post(caption: str = "", image_path: str = "", **kwargs) -> dict:
    """Main entry: create a Facebook post with optional image."""
    from media_generator import generate_branded_image

    if not caption:
        caption = kwargs.get("text", "Chicago Fleet Wraps — premium vehicle wraps in Chicago.")

    if not image_path:
        try:
            headline = caption[:60]
            subtext = caption[60:160] if len(caption) > 60 else ""
            image_path = generate_branded_image(headline, subtext)
        except Exception as e:
            log.warning(f"Image gen failed: {e}")

    if image_path and os.path.exists(image_path):
        return post_with_image(caption, image_path)
    return post_text(caption)


def engage_with_posts(**kwargs) -> dict:
    """Check engagement on recent posts."""
    stats = {"checked": 0, "total_likes": 0, "total_comments": 0}
    for post in _load_history()[-10:]:
        eng = get_engagement(post.get("post_id", ""))
        if eng:
            stats["checked"] += 1
            stats["total_likes"] += eng.get("likes", 0)
            stats["total_comments"] += eng.get("comments", 0)
    return stats


def start(**kwargs):
    print("  [FACEBOOK] Graph API bot ready", flush=True)


def stop(**kwargs):
    pass
