import json
import hashlib
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from admin_role import command_processor_admin
from viewer_role import command_processor_viewer
from root_role import command_processor_root
from operator_role import command_processor_operator

app = FastAPI()
prefix = ">>>PROMPT:"

# Load user info
with open("/etc/webcli/users.json", "r") as f:
    USERS = json.load(f)

with open("/etc/webcli/pass.json", "r") as f:
    PASS_HASHES = json.load(f)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Lock this down in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def get_processor(role: str):
    return {
        "admin": command_processor_admin,
        "operator": command_processor_operator,
        "viewer": command_processor_viewer,
        "root": command_processor_root
    }.get(role)

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

            if username not in USERS:
                await websocket.send_text("❌ User not found.")
                continue

            user = USERS[username]
            userid = user["userid"]
            role = user["role"]
            hashed_input = hash_password(password)
            stored_hash = PASS_HASHES.get(str(userid))

            if stored_hash != hashed_input:
                await websocket.send_text("❌ Authentication failed.")
                continue

            await websocket.send_text(f"✅ Welcome {username}! Your role is '{role}'.")

            processor = get_processor(role)
            if processor is None or not hasattr(processor, "handle_session"):
                await websocket.send_text("❌ Unknown role or invalid module.")
                continue

            # --- HAND OVER SESSION ---
            should_logout = await processor.handle_session(websocket, username)

            if not should_logout:
                await websocket.send_text("Session ended.")
                break  # Close socket
            else:
                await websocket.send_text("🔄 Logged out. Returning to login.\n")

    except WebSocketDisconnect:
        print(f"🔌 User '{username if 'username' in locals() else 'unknown'}' disconnected.")
