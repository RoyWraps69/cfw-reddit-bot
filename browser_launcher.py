#!/usr/bin/env python3
"""
Chicago Fleet Wraps — Browser Launcher v1.0
Shared module for launching Playwright browsers with restored session cookies.

In GitHub Actions: launches a fresh headless browser and loads saved cookies.
Locally: tries CDP connect first, falls back to fresh launch.
"""
import os
import json
import asyncio
from config import DATA_DIR

FB_COOKIES_FILE = os.path.join(DATA_DIR, "fb_cookies.json")
IG_COOKIES_FILE = os.path.join(DATA_DIR, "ig_cookies.json")
TT_COOKIES_FILE = os.path.join(DATA_DIR, "tt_cookies.json")
STORAGE_STATE_FILE = os.path.join(DATA_DIR, "full_storage_state.json")


def _load_cookies(cookie_file: str) -> list:
    """Load cookies from a JSON file."""
    if not os.path.exists(cookie_file):
        print(f"  [BROWSER] Cookie file not found: {cookie_file}")
        return []
    try:
        with open(cookie_file, "r") as f:
            cookies = json.load(f)
        print(f"  [BROWSER] Loaded {len(cookies)} cookies from {os.path.basename(cookie_file)}")
        return cookies
    except Exception as e:
        print(f"  [BROWSER] Error loading cookies: {e}")
        return []


async def launch_browser(platform: str):
    """
    Launch a Playwright browser for the given platform.
    
    Returns (playwright_instance, browser, context, page)
    
    Platform should be: 'facebook', 'instagram', or 'tiktok'
    """
    from playwright.async_api import async_playwright
    
    pw = await async_playwright().start()
    
    # First try CDP connect (works when running locally with browser open)
    try:
        browser = await pw.chromium.connect_over_cdp("http://localhost:9222")
        contexts = browser.contexts
        if contexts:
            context = contexts[0]
            page = await context.new_page()
            print(f"  [{platform.upper()}] Connected via CDP (local mode)")
            return pw, browser, context, page
    except Exception:
        pass  # CDP not available, launch fresh browser
    
    # Launch a fresh headless browser with cookies
    print(f"  [{platform.upper()}] Launching fresh headless browser...")
    
    browser = await pw.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled",
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]
    )
    
    # Try loading full storage state first
    if os.path.exists(STORAGE_STATE_FILE):
        try:
            context = await browser.new_context(
                storage_state=STORAGE_STATE_FILE,
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )
            print(f"  [{platform.upper()}] Loaded full storage state")
        except Exception as e:
            print(f"  [{platform.upper()}] Storage state failed: {e}, using cookies instead")
            context = await browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )
    else:
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
    
    # Load platform-specific cookies
    cookie_map = {
        "facebook": FB_COOKIES_FILE,
        "instagram": IG_COOKIES_FILE,
        "tiktok": TT_COOKIES_FILE,
    }
    
    cookie_file = cookie_map.get(platform, "")
    if cookie_file:
        cookies = _load_cookies(cookie_file)
        if cookies:
            # Playwright expects cookies in a specific format
            valid_cookies = []
            for c in cookies:
                cookie = {
                    "name": c["name"],
                    "value": c["value"],
                    "domain": c.get("domain", ""),
                    "path": c.get("path", "/"),
                }
                # Only add optional fields if present
                if c.get("expires", -1) > 0:
                    cookie["expires"] = c["expires"]
                if c.get("httpOnly"):
                    cookie["httpOnly"] = True
                if c.get("secure"):
                    cookie["secure"] = True
                if c.get("sameSite"):
                    ss = c["sameSite"]
                    if ss in ["Strict", "Lax", "None"]:
                        cookie["sameSite"] = ss
                
                valid_cookies.append(cookie)
            
            try:
                await context.add_cookies(valid_cookies)
                print(f"  [{platform.upper()}] Added {len(valid_cookies)} cookies")
            except Exception as e:
                print(f"  [{platform.upper()}] Error adding cookies: {e}")
    
    page = await context.new_page()
    print(f"  [{platform.upper()}] Browser ready")
    
    return pw, browser, context, page


async def close_browser(pw, browser):
    """Clean up browser resources."""
    try:
        await browser.close()
    except Exception:
        pass
    try:
        await pw.stop()
    except Exception:
        pass
