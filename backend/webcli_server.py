import os
import json
import asyncio
import time
import random
import math
from collections import deque
from pathlib import Path
from typing import Optional, Deque, Dict, Tuple
from datetime import datetime, timedelta

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


def origin_allowed(origin: Optional[str]) -> bool:
    # Browsers often send "null" for file:// pages; we include it for dev only.
    return origin in ALLOWED_ORIGINS


app = FastAPI()
prefix = ">>>PROMPT:"

# CORS affects HTTP endpoints (not WS), but keep it tight anyway
CORS_ALLOW = [o for o in ALLOWED_ORIGINS if o != "null"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW,       # lock down in production
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# ============================================================
# Session / idle-timeout config
# ============================================================
# Default: 15 minutes. Change with env var WEBCLI_IDLE_TIMEOUT (seconds).
IDLE_TIMEOUT_SECONDS = int(os.getenv("WEBCLI_IDLE_TIMEOUT", "900"))
# Optional warning before disconnect (seconds). Set 0 to disable pre-warning.
IDLE_WARN_SECONDS = int(os.getenv("WEBCLI_IDLE_WARN", "60"))
# How often the watcher checks (seconds)
IDLE_POLL_INTERVAL = float(os.getenv("WEBCLI_IDLE_POLL", "5"))

# ============================================================
# Login throttling & lockout configuration
# ============================================================
# Sliding window size for counting failures (seconds)
AUTH_WINDOW = int(os.getenv("WEBCLI_AUTH_WINDOW", "300"))  # 5 minutes
# Thresholds before a temporary lockout triggers
AUTH_MAX_FAILS_PER_IP = int(os.getenv("WEBCLI_AUTH_MAX_FAILS_PER_IP", "20"))
AUTH_MAX_FAILS_PER_USER = int(os.getenv("WEBCLI_AUTH_MAX_FAILS_PER_USER", "10"))
# Lockout base duration and maximum cap (seconds); lockout escalates exponentially
AUTH_LOCKOUT_BASE = int(os.getenv("WEBCLI_AUTH_LOCKOUT_BASE", "30"))    # 30s
AUTH_LOCKOUT_MAX = int(os.getenv("WEBCLI_AUTH_LOCKOUT_MAX", "3600"))    # 1h
# Exponential backoff base per *failed attempt* (seconds) and max cap
AUTH_BACKOFF_BASE = float(os.getenv("WEBCLI_AUTH_BACKOFF_BASE", "1.0"))  # 1s
AUTH_BACKOFF_MAX = float(os.getenv("WEBCLI_AUTH_BACKOFF_MAX", "5.0"))    # 5s
# Add small random jitter to avoid lockstep guessing
AUTH_BACKOFF_JITTER = float(os.getenv("WEBCLI_AUTH_BACKOFF_JITTER", "0.25"))  # 25% jitter

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


USERS_PATH = Path("/etc/webcli/users.json")
PASS_PATH = Path("/etc/webcli/pass.json")


def get_processor(role: str):
    return {
        "admin": admin_handler,
        "operator": operator_handler,
        "viewer": viewer_handler,
    }.get(role)


def verify_password(argon2_hash: str, password: str) -> bool:
    """
    Verify password against Argon2id hash.
    Only Argon2id is supported; legacy formats are rejected.
    """
    if not isinstance(argon2_hash, str) or not argon2_hash.startswith("$argon2"):
        return False
    try:
        PH.verify(argon2_hash, password)
        return True
    except argon2_exceptions.VerifyMismatchError:
        return False
    except Exception:
        # Any malformed hash or unexpected error -> fail closed
        return False


# ============================================================
# Helper: track client activity for idle timeout
# ============================================================
class ActivityWebSocket:
    """
    Thin proxy around FastAPI's WebSocket that tracks *client* activity.
    We only refresh the timer on receive_* calls (i.e., when the user interacts).
    The idle watcher separately pauses timeout while a command is running.
    """
    def __init__(self, ws: WebSocket):
        self._ws = ws
        self.last_client_activity = time.monotonic()

    # ---- delegate commonly used methods, updating activity on receive ----
    async def receive_text(self) -> str:
        msg = await self._ws.receive_text()
        self.last_client_activity = time.monotonic()
        return msg

    async def receive_json(self) -> dict:
        obj = await self._ws.receive_json()
        self.last_client_activity = time.monotonic()
        return obj

    async def send_text(self, data: str):
        return await self._ws.send_text(data)

    async def send_json(self, data):
        return await self._ws.send_json(data)

    async def close(self, code: int = 1000, reason: Optional[str] = None):
        return await self._ws.close(code=code, reason=reason)

    # Expose headers, etc.
    @property
    def headers(self):
        return self._ws.headers

    # Fallback for anything else (e.g., .accept())
    def __getattr__(self, name):
        return getattr(self._ws, name)


# ============================================================
# NEW: login rate limiter with backoff/lockout
# ============================================================
class _KeyState:
    """Internal state for a single key (IP or username)."""
    __slots__ = ("fail_times", "lock_until", "lockouts")

    def __init__(self):
        self.fail_times: Deque[float] = deque()
        self.lock_until: float = 0.0
        self.lockouts: int = 0  # how many times this key has hit a lockout


class RateLimiter:
    """
    Sliding-window failure counter + exponential lockout scheduler
    used for both per-IP and per-username throttling.
    """

    def __init__(self, window_s: int, max_fails: int, lock_base_s: int, lock_max_s: int):
        self.window_s = window_s
        self.max_fails = max_fails
        self.lock_base_s = lock_base_s
        self.lock_max_s = lock_max_s
        self._states: Dict[str, _KeyState] = {}
        self._lock = asyncio.Lock()

    def _now(self) -> float:
        return time.monotonic()

    def _purge_old(self, st: _KeyState, now: float):
        cutoff = now - self.window_s
        while st.fail_times and st.fail_times[0] < cutoff:
            st.fail_times.popleft()

    async def check_blocked(self, key: str) -> float:
        """
        Returns seconds remaining if blocked, else 0.0
        """
        now = self._now()
        async with self._lock:
            st = self._states.get(key)
            if not st:
                return 0.0
            if st.lock_until > now:
                return st.lock_until - now
            return 0.0

    async def register_success(self, key: str):
        """Reset counters on successful auth."""
        async with self._lock:
            if key in self._states:
                self._states.pop(key, None)

    async def register_failure(self, key: str) -> Tuple[float, float]:
        """
        Register a failed attempt.
        Returns (backoff_delay_seconds, lock_remaining_seconds)
        lock_remaining_seconds is >0 only if a new (or existing) lockout applies.
        """
        now = self._now()
        async with self._lock:
            st = self._states.setdefault(key, _KeyState())

            # If currently locked, keep it
            if st.lock_until > now:
                return 0.0, st.lock_until - now

            # Add failure and purge outside window
            st.fail_times.append(now)
            self._purge_old(st, now)

            # Compute exponential backoff based on current failures in window
            n = len(st.fail_times)  # failures in the current window
            backoff = min(AUTH_BACKOFF_BASE * (2 ** max(0, n - 1)), AUTH_BACKOFF_MAX)
            # Add jitter: +/- AUTH_BACKOFF_JITTER * backoff
            jitter = (random.random() * 2 - 1) * AUTH_BACKOFF_JITTER * backoff
            backoff = max(0.0, backoff + jitter)

            # Trigger a lockout if threshold reached
            if n >= self.max_fails:
                # Escalate lockout duration exponentially per prior lockout count
                duration = min(self.lock_base_s * (2 ** st.lockouts), self.lock_max_s)
                st.lockouts += 1
                st.lock_until = now + duration
                st.fail_times.clear()  # reset the counter after a lock
                return backoff, duration

            return backoff, 0.0


# Instantiate two limiters: per-IP and per-username
_ip_limiter = RateLimiter(AUTH_WINDOW, AUTH_MAX_FAILS_PER_IP, AUTH_LOCKOUT_BASE, AUTH_LOCKOUT_MAX)
_user_limiter = RateLimiter(AUTH_WINDOW, AUTH_MAX_FAILS_PER_USER, AUTH_LOCKOUT_BASE, AUTH_LOCKOUT_MAX)


def _client_ip(ws: WebSocket) -> str:
    """
    Best-effort client IP extraction (supports reverse proxies).
    Note: behind multiple app workers you should back this with Redis.
    """
    # Prefer X-Forwarded-For if present
    h = ws.headers
    xff = (h.get("x-forwarded-for") or h.get("X-Forwarded-For") or "").strip()
    if xff:
        # If multiple, take the left-most (original client)
        return xff.split(",")[0].strip()
    # Fallback to the socket peer IP
    try:
        return ws.client.host if ws.client else "unknown"
    except Exception:
        return "unknown"


# ============================================================
# Wait-time formatter (NEW helper for user-friendly messages)
# ============================================================
def _format_wait(seconds: float) -> Tuple[str, str]:
    """
    Format a positive wait time into a human-readable duration and a local
    clock time string like '17:39:23' indicating when to try again.

    Returns:
        (duration_str, target_time_str)
        e.g., ("5 minutes", "17:39:23") or ("42 seconds", "12:01:07")
    """
    s = max(0, int(math.ceil(seconds)))
    now = datetime.now()
    target = now + timedelta(seconds=s)

    # Build a compact duration string
    hours, rem = divmod(s, 3600)
    minutes, secs = divmod(rem, 60)

    parts = []
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if secs and not hours and minutes < 5:
        # Include seconds for short waits; omit when we already show hours.
        parts.append(f"{secs} second{'s' if secs != 1 else ''}")

    if not parts:
        parts.append("0 seconds")

    duration_str = " ".join(parts)
    target_str = target.strftime("%H:%M:%S")
    return duration_str, target_str


# ============================================================
# Idle watcher (existing)
# ============================================================
async def _idle_watcher(aws: ActivityWebSocket):
    """
    Background task: disconnect if there's no client activity for IDLE_TIMEOUT_SECONDS.
    Pauses the countdown while a long-running command (tracked in core.process_manager)
    is active for this websocket.
    """
    warned = False
    try:
        while True:
            await asyncio.sleep(IDLE_POLL_INTERVAL)

            # If a long-running process is active, treat as activity (pause timer)
            proc = get_current_process(aws)
            if proc and proc.returncode is None:
                # "Touch" the last activity so the session doesn't time out mid-command
                aws.last_client_activity = time.monotonic()
                warned = False
                continue

            elapsed = time.monotonic() - aws.last_client_activity
            remaining = IDLE_TIMEOUT_SECONDS - elapsed

            # Send one-time warning if enabled
            if IDLE_WARN_SECONDS > 0 and not warned and remaining <= IDLE_WARN_SECONDS and remaining > 0:
                try:
                    mins = max(1, int(round(remaining / 60)))
                    await aws.send_text(
                        f"⚠️ Inactive for a while. You will be logged out in ~{mins} minute(s) unless you press a key."
                    )
                except Exception:
                    # Ignore send error; likely closing anyway
                    pass
                warned = True

            # Hard disconnect when timed out
            if elapsed >= IDLE_TIMEOUT_SECONDS:
                try:
                    await aws.send_text("⏳ Session timed out due to inactivity. Please sign in again.")
                except Exception:
                    pass
                try:
                    await aws.close(code=4000, reason="Idle timeout")
                finally:
                    break
    except asyncio.CancelledError:
        # Normal cancellation path when the session ends for other reasons
        raise


# ============================================================
# WebSocket endpoint with login throttling + idle timeout
# ============================================================
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Enforce Origin allowlist BEFORE accepting the handshake
    origin = websocket.headers.get("origin")
    if not origin_allowed(origin):
        # 1008 = Policy Violation
        await websocket.close(code=1008)
        return

    await websocket.accept()
    try:
        while True:
            # --- LOGIN ---
            await websocket.send_text(f"{prefix}Enter your username: ")
            username = await websocket.receive_text()

            # Check lockouts *before* asking for password (username known now).
            ip = _client_ip(websocket)

            ip_block = await _ip_limiter.check_blocked(ip)
            if ip_block > 0:
                dur, at = _format_wait(ip_block)
                await websocket.send_text(
                    f"⛔ Too many login attempts from your IP. Please wait {dur} and try again at {at}."
                )
                # Don't even ask for a password; loop back to login
                continue

            user_block = await _user_limiter.check_blocked(username)
            if user_block > 0:
                dur, at = _format_wait(user_block)
                await websocket.send_text(
                    f"⛔ Account temporarily locked due to failed attempts. Please wait {dur} and try again at {at}."
                )
                continue

            await websocket.send_text(f"{prefix}[PASSWORD]Enter your password: ")
            password = await websocket.receive_text()

            # Load user info
            with USERS_PATH.open("r", encoding="utf-8") as f:
                USERS = json.load(f)
            with PASS_PATH.open("r", encoding="utf-8") as f:
                PASS_HASHES = json.load(f)

            # Fast path: unknown user -> count against IP only (avoid user enumeration)
            user_exists = username in USERS
            if not user_exists:
                # Register IP failure, apply backoff/lock if needed
                backoff, lock_s = await _ip_limiter.register_failure(ip)
                if backoff > 0:
                    await asyncio.sleep(backoff)
                if lock_s > 0:
                    dur, at = _format_wait(lock_s)
                    await websocket.send_text(
                        f"❌ Too many failed attempts from your IP. Please wait {dur} and try again at {at}."
                    )
                else:
                    await websocket.send_text("❌ Authentication failed.")
                continue

            user = USERS[username]
            userid = user["userid"]
            role = user["role"]
            stored_hash = PASS_HASHES.get(str(userid))

            # Verify password; on failure count against both IP and username
            authed = bool(stored_hash) and verify_password(stored_hash, password)
            if not authed:
                # Register both failures
                backoff_ip, lock_ip = await _ip_limiter.register_failure(ip)
                backoff_user, lock_user = await _user_limiter.register_failure(username)

                # Apply the larger backoff to slow guesses
                delay = max(backoff_ip, backoff_user)
                if delay > 0:
                    await asyncio.sleep(delay)

                # Generic failure message + include wait time if a lock was triggered
                lock_wait = max(lock_ip, lock_user)
                if lock_wait > 0:
                    dur, at = _format_wait(lock_wait)
                    await websocket.send_text(
                        f"❌ Too many failed attempts. Please wait {dur} and try again at {at}."
                    )
                else:
                    await websocket.send_text("❌ Authentication failed.")
                continue

            # Optional: Upgrade hash if Argon2 parameters changed
            try:
                if PH.check_needs_rehash(stored_hash):
                    new_hash = PH.hash(password)
                    PASS_HASHES[str(userid)] = new_hash
                    with PASS_PATH.open("w", encoding="utf-8") as f:
                        json.dump(PASS_HASHES, f, indent=2)
            except Exception:
                # Non-fatal: login proceeds even if rehash persistence fails
                pass

            # Success: clear limiter state for this IP and user
            await _ip_limiter.register_success(ip)
            await _user_limiter.register_success(username)

            await websocket.send_text(f"✅ Welcome {username}! Your role is '{role}'.")

            processor = get_processor(role)
            if processor is None:
                await websocket.send_text("❌ Unknown role or invalid module.")
                continue

            # ---- Wrap the WS to track activity and start idle watcher ----
            aws = ActivityWebSocket(websocket)
            idle_task = asyncio.create_task(_idle_watcher(aws))

            try:
                # --- HAND OVER SESSION ---
                should_logout = await processor(aws, username)
            finally:
                # Ensure watcher is stopped regardless of how the session ends
                if not idle_task.done():
                    idle_task.cancel()
                    try:
                        await idle_task
                    except asyncio.CancelledError:
                        pass

            if not should_logout:
                await websocket.send_text("Session ended.")
                break  # Close socket
            else:
                await websocket.send_text("🔄 Logged out. Returning to login.\n")

    except WebSocketDisconnect:
        print(f"🔌 User '{username if 'username' in locals() else 'unknown'}' disconnected.")
