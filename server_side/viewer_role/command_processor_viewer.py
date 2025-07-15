from commands import command_control

async def handle_session(websocket, username):
    role = "viewer"
    prompt = f"({role})$ "  # Example: (viewer) $ 
    await websocket.send_text(f"🛠 Logged in as '{role}'. Type 'help' for commands.")

    while True:
        await websocket.send_text(prompt)  # Send role-specific prompt
        cmd = await websocket.receive_text()

        if cmd == "signout":
            await websocket.send_text("🚪 Signing out...")
            return True

        elif cmd == "help":
            await websocket.send_text("🛠 Available commands: help, signout, do_something, config")

        elif cmd == "do_something":
            await websocket.send_text(f"✅ Hello {username}, doing admin task...")

        elif cmd == "config":
            await websocket.send_text("🔧 Entering config mode...")
            should_return = await command_control.cmd_config(websocket, username)
            if not should_return:
                return False  # Exit the entire session
            await websocket.send_text("🔙 Returned from config mode.")

        else:
            await websocket.send_text("❓ Unknown command.")
