import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import command_processor  # Make sure this module exists and works

app = FastAPI()

# Load user credentials from users.json
with open("users.json", "r") as f:
    USERS = json.load(f)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    try:
        # Step 1: Prompt for username
        await websocket.send_text("Enter your username:")
        username = await websocket.receive_text()

        # Step 2: Prompt for password
        await websocket.send_text("Enter your password:")
        password = await websocket.receive_text()

        # Step 3: Validate credentials
        if username not in USERS or USERS[username] != password:
            await websocket.send_text("❌ Authentication failed. Closing connection.")
            await websocket.close()
            return

        # Step 4: Success
        await websocket.send_text(f"✅ Welcome {username}! Type 'help' for available commands.")

        # CLI loop
        while True:
            command = await websocket.receive_text()
            result = command_processor.process_command(command, username)

            if result.strip().lower() == "exit":
                await websocket.send_text("👋 Goodbye!")
                await websocket.close()
                break

            await websocket.send_text(result)

    except WebSocketDisconnect:
        print(f"🔌 User '{username if 'username' in locals() else 'unknown'}' disconnected.")

