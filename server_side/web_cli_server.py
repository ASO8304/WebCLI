import json
import hashlib
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

import command_processor_admin
import command_processor_operator
import command_processor_viewer
import command_processor_root

app = FastAPI()

# Load users and password hashes
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
    if role == "admin":
        return command_processor_admin
    elif role == "operator":
        return command_processor_operator
    elif role == "viewer":
        return command_processor_viewer
    elif role == "root":
        return command_processor_root
    return None

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    try:
        await websocket.send_text("Enter your username:")
        username = await websocket.receive_text()

        await websocket.send_text("Enter your password:")
        password = await websocket.receive_text()

        if username not in USERS:
            await websocket.send_text("❌ User not found. Closing connection.")
            await websocket.close()
            return

        user = USERS[username]
        userid = user["userid"]
        role = user["role"]

        hashed_input = hash_password(password)
        stored_hash = PASS_HASHES.get(str(userid))

        if stored_hash != hashed_input:
            await websocket.send_text("❌ Authentication failed. Closing connection.")
            await websocket.close()
            return

        await websocket.send_text(f"✅ Welcome {username}! Your role is '{role}'. Type 'help' for available commands.")

        processor = get_processor(role)
        if processor is None:
            await websocket.send_text("❌ Unknown role. Closing connection.")
            await websocket.close()
            return

        while True:
            command = await websocket.receive_text()

            if command.strip().lower() == "exit":
                await websocket.send_text("👋 Goodbye!")
                await websocket.close()
                break

            result = processor.process_command(command, username)
            await websocket.send_text(result)

    except WebSocketDisconnect:
        print(f"🔌 User '{username if 'username' in locals() else 'unknown'}' disconnected.")
