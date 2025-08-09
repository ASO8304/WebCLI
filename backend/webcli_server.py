import json
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from roles.root_handler import root_handler
from roles.admin_handler import admin_handler
from roles.operator_handler import operator_handler
from roles.viewer_handler import viewer_handler

# Strong password hashing: Argon2id
from argon2 import PasswordHasher, exceptions as argon2_exceptions

app = FastAPI()
prefix = ">>>PROMPT:"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Lock this down in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Argon2id parameters (tune for your server)
PH = PasswordHasher(
    time_cost=3,             # iterations
    memory_cost=64 * 1024,   # KiB (64 MiB)
    parallelism=2,
    hash_len=32,
    salt_len=16,
)

USERS_PATH = Path("/etc/webcli/users.json")
PASS_PATH = Path("/etc/webcli/pass.json")


def get_processor(role: str):
    return {
        "admin": admin_handler,
        "operator": operator_handler,
        "viewer": viewer_handler,
        "root": root_handler
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


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # --- LOGIN ---
            await websocket.send_text(f"{prefix}Enter your username: ")
            username = await websocket.receive_text()

            await websocket.send_text(f"{prefix}Enter your password: ")
            password = await websocket.receive_text()

            # Load user info
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

            await websocket.send_text(f"✅ Welcome {username}! Your role is '{role}'.")

            processor = get_processor(role)
            if processor is None:
                await websocket.send_text("❌ Unknown role or invalid module.")
                continue

            # --- HAND OVER SESSION ---
            should_logout = await processor(websocket, username)

            if not should_logout:
                await websocket.send_text("Session ended.")
                break  # Close socket
            else:
                await websocket.send_text("🔄 Logged out. Returning to login.\n")

    except WebSocketDisconnect:
        print(f"🔌 User '{username if 'username' in locals() else 'unknown'}' disconnected.")
