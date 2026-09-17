"""Refresh the COROS MCP access token and update .zcode/config.json.

Run when the token (~30 days) is close to expiry or after a 401:
    python coros_refresh.py
Falls back to full re-authorization if the refresh token is rejected.
"""
import base64
import json
import os
import secrets
import subprocess
import sys
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
AUTH_FILE = os.path.join(HERE, "coros-auth.json")
CONFIG_FILE = os.path.join(HERE, "config.json")
ISSUER = "https://mcpeu.coros.com"


def post_form(url, data):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode(),
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read()), None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}: {e.read().decode(errors='replace')[:200]}"


def apply_token(tokens):
    tokens.setdefault  # no-op to keep structure obvious
    with open(AUTH_FILE, "w", encoding="utf-8") as f:
        json.dump(tokens, f, indent=2)
    with open(CONFIG_FILE, encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["mcp"]["servers"]["coros"]["headers"]["Authorization"] = \
        f"Bearer {tokens['access_token']}"
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def refresh():
    with open(AUTH_FILE, encoding="utf-8") as f:
        auth = json.load(f)
    tokens, err = post_form(f"{ISSUER}/oauth2/token", {
        "grant_type": "refresh_token",
        "refresh_token": auth["refresh_token"],
        "client_id": auth["client_id"],
        "resource": auth["resource"],
    })
    if err:
        print("Refresh failed:", err)
        return False
    merged = {**auth, **tokens, "client_id": auth["client_id"],
              "resource": auth["resource"], "redirect_uri": auth["redirect_uri"]}
    apply_token(merged)
    print(f"OK: new token, expires_in={tokens.get('expires_in')}s; "
          f"config.json updated")
    return True


def reauthorize():
    print("Starting full re-authorization (browser)...")
    subprocess.run([sys.executable, os.path.join(HERE, "coros_oauth.py")],
                   check=True)
    with open(AUTH_FILE, encoding="utf-8") as f:
        auth = json.load(f)
    apply_token(auth)
    print("OK: config.json updated with the new token")


if __name__ == "__main__":
    if not refresh():
        reauthorize()
