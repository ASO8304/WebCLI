import os
import json
import asyncio
import time
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from roles.admin_handler import admin_handler
from roles.operator_handler import operator_handler
from roles.viewer_handler import viewer_handler

# Strong password hashing: Argon2id
from argon2 import PasswordHasher, exceptions as argon2_exceptions

# For pausing idle timeout while a long-running command is active
from core.process_manager import get_current_process


# -----------------------------
# Security: allowed browser origins
# Replace with your domain(s)
# -----------------------------
ALLOWED_ORIGINS = {
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://192.168.56.105:8080",
}


def origin_allowed(origin: str | None) -> bool:
    # Browsers sometimes send "null" for file:// pages (dev only). Here we only
    # allow origins in ALLOWED_ORIGINS. Tighten this list for production.
    return origin in ALLOWED_ORIGINS


app = FastAPI()
prefix = ">>>PROMPT:"

# CORS controls HTTP requests (not WS), but keep it locked down anyway.
CORS_ALLOW = [o for o in ALLOWED_ORIGINS if o != "null"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# ============================================================
# Session / idle-timeout configuration (INACTIVITY TIMEOUT)
# ============================================================
# These environment variables control when an authenticated WebSocket
# session is considered "idle" and should be terminated to force re-auth.
#
# How it works at a high level:
# - We wrap the FastAPI WebSocket in ActivityWebSocket which updates a
#   "last_client_activity" timestamp on every *receive* (i.e., user input).
# - A background _idle_watcher() task checks that timestamp every few seconds.
# - If no input arrives for IDLE_TIMEOUT_SECONDS, we notify and close the WS.
# - If a long-running command is active (e.g., tcpdump), the watcher *pauses*
#   the countdown by "touching" the last activity. This prevents mid-stream
#   disconnects while legitimate work is ongoing.
#
# Note: We use time.monotonic() for robust elapsed-time calculations that are
# not affected by system clock changes.
#
# Default idle timeout: 15 minutes (900 seconds). Override in the environment:
#   WEBCLI_IDLE_TIMEOUT=600  # 10 minutes, for example
IDLE_TIMEOUT_SECONDS = int(os.getenv("WEBCLI_IDLE_TIMEOUT", "900"))

# Optional pre-warning window before disconnect (in seconds). If > 0, the user
# gets a single warning message when remaining time <= IDLE_WARN_SECONDS.
# Set to 0 to disable warnings entirely.
IDLE_WARN_SECONDS = int(os.getenv("WEBCLI_IDLE_WARN", "60"))

# How often the watcher wakes up to check for inactivity (in seconds).
# Lower = more responsive but slightly more overhead.
IDLE_POLL_INTERVAL = float(os.getenv("WEBCLI_IDLE_POLL", "5"))

# -----------------------------
# Argon2id parameters (tune for your server)
# -----------------------------
PH = PasswordHasher(
    time_cost=3,         # Number of iterations (passes) over the memory.
                         # Tune so hashing takes ~0.5–1s on your server.

    memory_cost=128 * 1024, # Memory per hash in KiB (here 128 MiB).
                            # Increase to harden against GPU/ASIC attacks.

    parallelism=2,       # Threads (lanes). Usually <= CPU cores.

    hash_len=64,         # Bytes in the derived key (doesn't affect cracking cost).

    salt_len=32,         # Random salt length (>=16 recommended).
)

# Paths to user/credential stores. Adjust if you deploy elsewhere.
USERS_PATH = Path("/etc/webcli/users.json")
PASS_PATH = Path("/etc/webcli/pass.json")


def get_processor(role: str):
    # Map role → role handler (must be awaitable and follow your handler contract).
    return {
        "admin": admin_handler,
        "operator": operator_handler,
        "viewer": viewer_handler,
    }.get(role)


def verify_password(argon2_hash: str, password: str) -> bool:
    """
    Verify password against Argon2id hash.
    Only Argon2* hashes are accepted; malformed or unknown formats fail closed.
    """
    if not isinstance(argon2_hash, str) or not argon2_hash.startswith("$argon2"):
        return False
    try:
        PH.verify(argon2_hash, password)
        return True
    except argon2_exceptions.VerifyMismatchError:
        return False
    except Exception:
        # Any malformed hash or unexpected error -> fail closed.
        return False


# ============================================================
# ActivityWebSocket: tracks client activity for idle timeout
# ============================================================
class ActivityWebSocket:
    """
    Thin proxy around FastAPI's WebSocket that tracks *client* activity.

    Key idea:
    - We only refresh the idle timer on receive_* calls (i.e., when the *user*
      actually does something). Server-to-client sends do not count as activity.
    - The separate _idle_watcher() task reads last_client_activity to decide
      whether to warn or disconnect the session.
    - When a long-running command is detected, the watcher itself "touches"
      this timestamp so the session doesn't time out mid-command.
    """
    def __init__(self, ws: WebSocket):
        self._ws = ws
        # Start the clock now. This avoids immediate timeout if the user logs in
        # and pauses before sending the first command.
        self.last_client_activity = time.monotonic()

    # --- Delegate common receive methods and update activity timestamp ---

    async def receive_text(self) -> str:
        # Any inbound text from the client = real user activity.
        msg = await self._ws.receive_text()
        self.last_client_activity = time.monotonic()
        return msg

    async def receive_json(self) -> dict:
        obj = await self._ws.receive_json()
        self.last_client_activity = time.monotonic()
        return obj

    # --- Sends do not reset the timer (server output is not user activity) ---

    async def send_text(self, data: str):
        return await self._ws.send_text(data)

    async def send_json(self, data):
        return await self._ws.send_json(data)

    async def close(self, code: int = 1000, reason: str | None = None):
        return await self._ws.close(code=code, reason=reason)

    @property
    def headers(self):
        return self._ws.headers

    # Fallback to any other WebSocket attribute (e.g., .accept()).
    def __getattr__(self, name):
        return getattr(self._ws, name)


# ============================================================
# _idle_watcher: background task that enforces inactivity timeout
# ============================================================
async def _idle_watcher(aws: ActivityWebSocket):
    """
    Disconnects the session when there has been no *client* activity for
    IDLE_TIMEOUT_SECONDS. The countdown is paused while a long-running command
    is active (see core.process_manager.get_current_process).

    Lifecycle:
      - Runs as an asyncio Task started after successful login.
      - Checks every IDLE_POLL_INTERVAL seconds.
      - Optionally warns the user once (IDLE_WARN_SECONDS before timeout).
      - On timeout, sends a message and closes the WS with code 4000, forcing
        a fresh login on the next connection.

    Close codes used:
      - 4000: application-defined (allowed range 4000–4999).
      - 1008 (used elsewhere): policy violation (for origin block).
    """
    warned = False
    try:
        while True:
            await asyncio.sleep(IDLE_POLL_INTERVAL)

            # If a long-running process is active for this connection,
            # treat that as "activity": reset the timer to avoid mid-command drop.
            proc = get_current_process(aws)
            if proc and proc.returncode is None:
                aws.last_client_activity = time.monotonic()
                warned = False  # Cancel any previous warning once activity resumes
                continue

            elapsed = time.monotonic() - aws.last_client_activity
            remaining = IDLE_TIMEOUT_SECONDS - elapsed

            # One-time pre-warning (if enabled) when we're inside the warning window.
            if IDLE_WARN_SECONDS > 0 and not warned and remaining <= IDLE_WARN_SECONDS and remaining > 0:
                try:
                    mins = max(1, int(round(remaining / 60)))
                    await aws.send_text(
                        f"⚠️ Inactive for a while. You will be logged out in ~{mins} minute(s) unless you press a key."
                    )
                except Exception:
                    # Ignore send errors; the socket may already be closing.
                    pass
                warned = True

            # Hard disconnect at (or beyond) the timeout threshold.
            if elapsed >= IDLE_TIMEOUT_SECONDS:
                try:
                    await aws.send_text("⏳ Session timed out due to inactivity. Please sign in again.")
                except Exception:
                    pass
                try:
                    # 4000–4999 are app-specific close codes; using 4000 here.
                    await aws.close(code=4000, reason="Idle timeout")
                finally:
                    break
    except asyncio.CancelledError:
        # Normal cancellation (e.g., user logged out or connection closed)
        raise


# ============================================================
# WebSocket endpoint: login loop + session handoff + timeout wiring
# ============================================================
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Enforce Origin allowlist BEFORE accepting the handshake.
    # If not allowed, close with 1008 (policy violation).
    origin = websocket.headers.get("origin")
    if not origin_allowed(origin):
        await websocket.close(code=1008)
        return

    await websocket.accept()
    try:
        while True:
            # --- LOGIN PHASE ---
            await websocket.send_text(f"{prefix}Enter your username: ")
            username = await websocket.receive_text()

            await websocket.send_text(f"{prefix}[PASSWORD]Enter your password: ")
            password = await websocket.receive_text()

            # Load user store and password hashes from disk.
            with USERS_PATH.open("r", encoding="utf-8") as f:
                USERS = json.load(f)
            with PASS_PATH.open("r", encoding="utf-8") as f:
                PASS_HASHES = json.load(f)

            if username not in USERS:
                await websocket.send_text("❌ User not found.")
                continue

            user = USERS[username]
            userid = user["userid"]
            role = user["role"]
            stored_hash = PASS_HASHES.get(str(userid))

            if not stored_hash or not verify_password(stored_hash, password):
                await websocket.send_text("❌ Authentication failed.")
                continue

            # Opportunistic rehash: if Argon2 parameters were strengthened,
            # upgrade the stored hash after a successful login.
            try:
                if PH.check_needs_rehash(stored_hash):
                    new_hash = PH.hash(password)
                    PASS_HASHES[str(userid)] = new_hash
                    with PASS_PATH.open("w", encoding="utf-8") as f:
                        json.dump(PASS_HASHES, f, indent=2)
            except Exception:
                # Non-fatal: continue even if we fail to persist the upgrade.
                pass

            await websocket.send_text(f"✅ Welcome {username}! Your role is '{role}'.")

            processor = get_processor(role)
            if processor is None:
                await websocket.send_text("❌ Unknown role or invalid module.")
                continue

            # --- START OF AUTHENTICATED SESSION ---
            # Wrap the WebSocket so we can track client activity.
            aws = ActivityWebSocket(websocket)

            # Start the idle watcher in the background. It runs until:
            # - the session times out (and closes), or
            # - the handler returns and we cancel it in the finally-block.
            idle_task = asyncio.create_task(_idle_watcher(aws))

            try:
                # Hand over control to the role-specific handler.
                # Contract: handler returns True to "logout and return to login",
                # False (or None) to end the socket entirely.
                should_logout = await processor(aws, username)
            finally:
                # Whatever happens, make sure we stop the watcher cleanly.
                if not idle_task.done():
                    idle_task.cancel()
                    try:
                        await idle_task
                    except asyncio.CancelledError:
                        pass

            if not should_logout:
                # End of connection (socket will close after this message).
                await websocket.send_text("Session ended.")
                break
            else:
                # Loop again to the login prompt (fresh authentication).
                await websocket.send_text("🔄 Logged out. Returning to login.\n")

    except WebSocketDisconnect:
        # Normal path when the client disconnects.
        print(f"🔌 User '{username if 'username' in locals() else 'unknown'}' disconnected.")
