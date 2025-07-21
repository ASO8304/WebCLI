import json
import hashlib
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from roles.root_handler import root_handler
from roles.admin_handler import admin_handler
from roles.operator_handler import operator_handler
from roles.viewer_handler import viewer_handler


app = FastAPI()
prefix = ">>>PROMPT:"

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
        "admin": admin_handler,
        "operator": operator_handler,
        "viewer": viewer_handler,
        "root": root_handler
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
            password= await websocket.receive_text()
    
            # Load user info
            with open("/etc/webcli/users.json", "r") as f:
                USERS = json.load(f)

            with open("/etc/webcli/pass.json", "r") as f:
                PASS_HASHES = json.load(f)

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
            if processor is None :
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
