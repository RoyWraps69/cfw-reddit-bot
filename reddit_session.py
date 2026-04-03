"""
Chicago Fleet Wraps Reddit Bot — Reddit Session Manager
Handles authentication via browser cookies (no API app registration needed).
Supports both cookie-file auth and environment-variable auth for deployment.
"""
import json
import os
import re
import time
import requests
from config import DATA_DIR


class RedditSession:
    """Manages an authenticated Reddit session using exported browser cookies."""

    OLD_URL = "https://old.reddit.com"
    BASE_URL = "https://www.reddit.com"
    OAUTH_URL = "https://oauth.reddit.com"

    def __init__(self, username: str):
        self.username = username
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })
        self._modhash = None
        self._logged_in = False
        self._token_v2 = None

    def login(self) -> bool:
        """Authenticate using cookies from file or environment variable."""
        print(f"  [AUTH] Authenticating as u/{self.username}...")

        # Method 1: Load cookies from JSON file
        cookie_file = os.path.join(DATA_DIR, "reddit_cookies.json")
        if os.path.exists(cookie_file):
            print(f"  [AUTH] Loading cookies from {cookie_file}...", flush=True)
            return self._login_from_cookie_file(cookie_file)

        # Method 2: Load cookies from environment variable (for Railway)
        cookies_env = os.environ.get("REDDIT_COOKIES_JSON", "")
        if cookies_env:
            print(f"  [AUTH] Loading cookies from REDDIT_COOKIES_JSON env var...", flush=True)
            return self._login_from_cookie_string(cookies_env)

        # Method 3: Use token_v2 directly from env var
        token = os.environ.get("REDDIT_TOKEN_V2", "")
        if token:
            print(f"  [AUTH] Using REDDIT_TOKEN_V2 env var...", flush=True)
            return self._login_with_token(token)

        print("  [AUTH] No cookie file, REDDIT_COOKIES_JSON, or REDDIT_TOKEN_V2 found!", flush=True)
        return False

    def _login_from_cookie_file(self, filepath: str) -> bool:
        """Load cookies from a JSON file."""
        try:
            with open(filepath, "r") as f:
                cookies_list = json.load(f)
            return self._apply_cookies(cookies_list)
        except Exception as e:
            print(f"  [AUTH] Error loading cookie file: {e}", flush=True)
            return False

    def _login_from_cookie_string(self, cookies_json: str) -> bool:
        """Load cookies from a JSON string (env var)."""
        try:
            cookies_list = json.loads(cookies_json)
            return self._apply_cookies(cookies_list)
        except Exception as e:
            print(f"  [AUTH] Error parsing cookie JSON: {e}", flush=True)
            return False

    def _login_with_token(self, token: str) -> bool:
        """Use a bearer token directly."""
        self._token_v2 = token
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
        })
        return self._verify_login()

    def _apply_cookies(self, cookies_list: list) -> bool:
        """Apply a list of cookie dicts to the session and verify."""
        for c in cookies_list:
            self.session.cookies.set(
                c["name"],
                c["value"],
                domain=c.get("domain", ".reddit.com"),
                path=c.get("path", "/"),
            )
            # Capture token_v2 for OAuth API calls
            if c["name"] == "token_v2":
                self._token_v2 = c["value"]

        return self._verify_login()

    def _verify_login(self) -> bool:
        """Verify we're logged in by checking /api/me.json."""
        try:
            resp = self.session.get(
                f"{self.OLD_URL}/api/me.json",
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                name = data.get("data", {}).get("name", "")
                if name:
                    self._modhash = data.get("data", {}).get("modhash", "")
                    self._logged_in = True
                    karma = data.get("data", {}).get("comment_karma", 0) + \
                            data.get("data", {}).get("link_karma", 0)
                    print(f"  [AUTH] Verified! Logged in as u/{name} (karma: {karma})", flush=True)
                    return True

            # Try with bearer token if available
            if self._token_v2:
                resp = self.session.get(
                    f"{self.OAUTH_URL}/api/v1/me",
                    headers={
                        "Authorization": f"Bearer {self._token_v2}",
                        "User-Agent": f"CFWBot/1.0 (by u/{self.username})",
                    },
                    timeout=10,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("name"):
                        self._logged_in = True
                        print(f"  [AUTH] Verified via OAuth! Logged in as u/{data['name']}", flush=True)
                        return True

            print("  [AUTH] Could not verify login.", flush=True)
            return False

        except Exception as e:
            print(f"  [AUTH] Verification error: {e}", flush=True)
            return False

    def _ensure_auth(self) -> bool:
        """Ensure we have a valid auth session."""
        if self._logged_in:
            return True
        return self.login()

    def _get_api_headers(self) -> dict:
        """Get headers for Reddit API calls (used by damage_control.py)."""
        headers = {
            "User-Agent": self.session.headers.get("User-Agent", "CFWBot/1.0"),
            "Referer": f"{self.OLD_URL}/",
        }
        modhash = self._get_modhash()
        if modhash:
            headers["X-Modhash"] = modhash
        if self._token_v2:
            headers["Authorization"] = f"Bearer {self._token_v2}"
        return headers

    def _get_modhash(self) -> str:
        """Get a fresh modhash if needed."""
        if self._modhash:
            return self._modhash
        try:
            resp = self.session.get(f"{self.OLD_URL}", timeout=10)
            match = re.search(r'modhash["\s:]+([a-z0-9]{20,})', resp.text)
            if match:
                self._modhash = match.group(1)
        except Exception:
            pass
        return self._modhash or ""

    def post_comment(self, thread_fullname: str, comment_text: str) -> bool:
        """Post a comment to a Reddit thread.
        thread_fullname: e.g., 't3_abc123'
        """
        if not self._ensure_auth():
            print("  [ERROR] Not authenticated, cannot post comment", flush=True)
            return False

        try:
            modhash = self._get_modhash()
            resp = self.session.post(
                f"{self.OLD_URL}/api/comment",
                data={
                    "thing_id": thread_fullname,
                    "text": comment_text,
                    "uh": modhash,
                    "api_type": "json",
                },
                headers={"Referer": f"{self.OLD_URL}/"},
                timeout=15,
            )

            if resp.status_code == 200:
                data = resp.json()
                errors = data.get("json", {}).get("errors", [])
                if not errors:
                    print(f"  [SUCCESS] Comment posted to {thread_fullname}", flush=True)
                    return True
                else:
                    print(f"  [FAILED] Comment errors: {errors}", flush=True)
                    for err in errors:
                        if "RATELIMIT" in str(err):
                            nums = re.findall(r'(\d+)\s*minute', str(err))
                            wait_time = int(nums[0]) * 60 + 30 if nums else 600
                            print(f"  [RATELIMIT] Waiting {wait_time} seconds...", flush=True)
                            time.sleep(wait_time)
                    return False
            else:
                print(f"  [FAILED] Comment post status: {resp.status_code}", flush=True)
                return False

        except Exception as e:
            print(f"  [ERROR] Comment posting error: {e}", flush=True)
            return False

    def send_dm(self, to_user: str, subject: str, message: str) -> bool:
        """Send a private message to a Reddit user."""
        if not self._ensure_auth():
            return False

        try:
            resp = self.session.post(
                f"{self.OLD_URL}/api/compose",
                data={
                    "to": to_user,
                    "subject": subject,
                    "text": message,
                    "uh": self._get_modhash(),
                    "api_type": "json",
                },
                headers={"Referer": f"{self.OLD_URL}/"},
                timeout=15,
            )

            if resp.status_code == 200:
                data = resp.json()
                errors = data.get("json", {}).get("errors", [])
                if not errors:
                    print(f"  [SUCCESS] DM sent to u/{to_user}", flush=True)
                    return True
                else:
                    print(f"  [FAILED] DM errors: {errors}", flush=True)
                    return False
            return False

        except Exception as e:
            print(f"  [ERROR] DM error: {e}", flush=True)
            return False

    def create_thread(self, subreddit: str, title: str, body: str) -> bool:
        """Create a new self-post thread in a subreddit."""
        if not self._ensure_auth():
            return False

        try:
            resp = self.session.post(
                f"{self.OLD_URL}/api/submit",
                data={
                    "sr": subreddit,
                    "kind": "self",
                    "title": title,
                    "text": body,
                    "uh": self._get_modhash(),
                    "api_type": "json",
                    "resubmit": "true",
                },
                headers={"Referer": f"{self.OLD_URL}/r/{subreddit}/submit"},
                timeout=15,
            )

            if resp.status_code == 200:
                data = resp.json()
                errors = data.get("json", {}).get("errors", [])
                if not errors:
                    url = data.get("json", {}).get("data", {}).get("url", "")
                    print(f"  [SUCCESS] Thread created: {url}", flush=True)
                    return True
                else:
                    print(f"  [FAILED] Thread errors: {errors}", flush=True)
                    return False
            return False

        except Exception as e:
            print(f"  [ERROR] Thread creation error: {e}", flush=True)
            return False

    def get_my_comments(self, limit: int = 25) -> list:
        """Fetch the authenticated user's recent comments."""
        try:
            resp = self.session.get(
                f"{self.OLD_URL}/user/{self.username}/comments.json",
                params={"limit": limit, "sort": "new"},
                timeout=10,
            )

            if resp.status_code == 200:
                data = resp.json()
                comments = []
                for child in data.get("data", {}).get("children", []):
                    c = child.get("data", {})
                    comments.append({
                        "id": c.get("id"),
                        "body": c.get("body", ""),
                        "link_id": c.get("link_id", ""),
                        "permalink": c.get("permalink", ""),
                        "created_utc": c.get("created_utc", 0),
                        "subreddit": c.get("subreddit", ""),
                    })
                return comments
            return []

        except Exception as e:
            print(f"  [ERROR] Failed to fetch comments: {e}", flush=True)
            return []

    def get_comment_replies(self, comment_permalink: str) -> list:
        """Fetch replies to a specific comment."""
        try:
            url = f"{self.BASE_URL}{comment_permalink}.json"
            resp = self.session.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                replies = []
                if len(data) > 1:
                    for child in data[1].get("data", {}).get("children", []):
                        c = child.get("data", {})
                        if c.get("body") and c.get("author") != self.username:
                            replies.append({
                                "author": c.get("author", ""),
                                "body": c.get("body", ""),
                                "created_utc": c.get("created_utc", 0),
                            })
                return replies
            return []

        except Exception as e:
            print(f"  [ERROR] Failed to fetch replies: {e}", flush=True)
            return []

    def get_karma(self) -> int:
        """Get the current user's karma."""
        try:
            resp = self.session.get(
                f"{self.OLD_URL}/user/{self.username}/about.json",
                timeout=10,
            )

            if resp.status_code == 200:
                data = resp.json()
                d = data.get("data", {})
                return d.get("comment_karma", 0) + d.get("link_karma", 0)
            return 0

        except Exception as e:
            print(f"  [ERROR] Failed to get karma: {e}", flush=True)
            return 0
