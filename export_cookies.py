#!/usr/bin/env python3
"""
Export Reddit cookies from the local browser for Railway deployment.
Outputs a single-line JSON string you can paste into Railway's REDDIT_COOKIES_JSON env var.

Usage:
  python3 export_cookies.py
"""
import sqlite3
import shutil
import json
import os
import sys
from pathlib import Path


def find_cookie_db():
    """Find the Chromium cookie database."""
    possible_paths = [
        Path.home() / ".browser_data_dir" / "Default" / "Cookies",
        Path.home() / ".config" / "chromium" / "Default" / "Cookies",
        Path.home() / ".config" / "google-chrome" / "Default" / "Cookies",
    ]
    for p in possible_paths:
        if p.exists():
            return str(p)
    return None


def decrypt_cookie_linux(encrypted_value):
    """Decrypt Chromium cookies on Linux."""
    if not encrypted_value:
        return ""
    try:
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA1(),
            length=16,
            salt=b"saltysalt",
            iterations=1,
        )
        key = kdf.derive(b"peanuts")

        if encrypted_value[:3] in (b"v10", b"v11"):
            encrypted_value = encrypted_value[3:]
            iv = b" " * 16
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
            decryptor = cipher.decryptor()
            decrypted = decryptor.update(encrypted_value) + decryptor.finalize()
            pad_len = decrypted[-1]
            if isinstance(pad_len, int) and pad_len <= 16:
                decrypted = decrypted[:-pad_len]
            return decrypted.decode("utf-8", errors="replace")
    except ImportError:
        print("ERROR: Install cryptography package: pip install cryptography")
        sys.exit(1)
    return ""


def export_cookies():
    """Export Reddit cookies as JSON."""
    db_path = find_cookie_db()
    if not db_path:
        print("ERROR: Could not find Chromium cookie database.")
        print("Make sure you're logged into Reddit in the browser first.")
        sys.exit(1)

    # Copy to avoid locking
    tmp_path = "/tmp/cookies_export.db"
    shutil.copy2(db_path, tmp_path)

    conn = sqlite3.connect(tmp_path)
    cursor = conn.cursor()

    # Get essential Reddit cookies
    essential_names = [
        "reddit_session", "token_v2", "csrf_token", "edgebucket",
        "loid", "session_tracker", "csv", "pc",
    ]

    cursor.execute("""
        SELECT name, encrypted_value, host_key, path, is_httponly, is_secure
        FROM cookies
        WHERE host_key LIKE '%reddit.com%'
        AND host_key NOT LIKE '%reddithelp%'
    """)

    cookies = []
    for row in cursor.fetchall():
        name = row[0]
        decrypted = decrypt_cookie_linux(row[1])
        if not decrypted:
            continue
        cookies.append({
            "name": name,
            "value": decrypted,
            "domain": row[2],
            "path": row[3],
            "httponly": bool(row[4]),
            "secure": bool(row[5]),
        })

    conn.close()
    os.remove(tmp_path)

    if not cookies:
        print("ERROR: No Reddit cookies found. Are you logged in?")
        sys.exit(1)

    # Output
    cookie_json = json.dumps(cookies, separators=(",", ":"))

    print("\n" + "=" * 60)
    print("  REDDIT COOKIES EXPORTED SUCCESSFULLY")
    print("=" * 60)
    print(f"\n  Found {len(cookies)} cookies\n")

    # Save to file
    output_file = os.path.join(os.path.dirname(__file__), "data", "reddit_cookies.json")
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(cookies, f, indent=2)
    print(f"  Saved to: {output_file}")

    # Print for Railway
    print(f"\n  For Railway, set this environment variable:")
    print(f"\n  REDDIT_COOKIES_JSON={cookie_json}\n")

    return cookies


if __name__ == "__main__":
    export_cookies()
