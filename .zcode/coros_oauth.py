"""COROS MCP OAuth authorization-code flow with PKCE.

Runs a one-shot local listener on :8400, waits for the COROS redirect,
exchanges the code for tokens and saves them next to this script.
"""
import base64
import hashlib
import json
import secrets
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

ISSUER = "https://mcpeu.coros.com"
CLIENT_ID = "936675bf-861d-4dbb-bd83-52f16805ca27"
REDIRECT_URI = "http://localhost:8400/callback"
SCOPE = "openid mcp.tools offline_access"
RESOURCE = "https://mcpeu.coros.com/mcp"
AUTH_FILE = r"E:\git\ask_question\здоровье\.zcode\coros-auth.json"

verifier = secrets.token_urlsafe(64)
challenge = base64.urlsafe_b64encode(
    hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()

params = urllib.parse.urlencode({
    "client_id": CLIENT_ID,
    "response_type": "code",
    "redirect_uri": REDIRECT_URI,
    "scope": SCOPE,
    "resource": RESOURCE,
    "code_challenge": challenge,
    "code_challenge_method": "S256",
})
auth_url = f"{ISSUER}/oauth2/authorize?{params}"
print("AUTH_URL:", auth_url, flush=True)

result = {}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        if parsed.path == "/callback" and "code" in qs:
            result["code"] = qs["code"][0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(
                "<h2>COROS подключён — это окно можно закрыть</h2>".encode())
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(f"no code: {qs}".encode())

    def log_message(self, *args):
        pass


server = HTTPServer(("127.0.0.1", 8400), Handler)
server.handle_request()

code = result["code"]
data = urllib.parse.urlencode({
    "grant_type": "authorization_code",
    "code": code,
    "redirect_uri": REDIRECT_URI,
    "client_id": CLIENT_ID,
    "code_verifier": verifier,
    "resource": RESOURCE,
}).encode()

import urllib.request
req = urllib.request.Request(
    f"{ISSUER}/oauth2/token", data=data,
    headers={"Content-Type": "application/x-www-form-urlencoded"})
with urllib.request.urlopen(req, timeout=30) as resp:
    tokens = json.loads(resp.read())

tokens["client_id"] = CLIENT_ID
tokens["resource"] = RESOURCE
tokens["redirect_uri"] = REDIRECT_URI
tokens["code_verifier_used"] = True
with open(AUTH_FILE, "w", encoding="utf-8") as f:
    json.dump(tokens, f, indent=2)

print("TOKENS_SAVED:", AUTH_FILE, flush=True)
print("SCOPE_GRANTED:", tokens.get("scope"), flush=True)
print("HAS_REFRESH:", bool(tokens.get("refresh_token")), flush=True)
