from shared_commands import command_control

COMMANDS = ["help", "signout", "do_something", "config", "consent"]

async def handle_session(websocket, username):
    role = "admin"
    prompt = f">>>PROMPT:({role})$ "

    await websocket.send_text(f"🛠 Logged in as '{role}'. Type 'help' for commands.")

    while True:
        await websocket.send_text(f"{prompt}")
        cmd = await websocket.receive_text()

        
        if cmd.startswith("__TAB__:"):
            partial = cmd.split(":", 1)[1]
            matches = [c for c in COMMANDS if c.startswith(partial)]
            if len(matches) == 1:
                await websocket.send_text(f"__AUTOCOMPLETE__:[REPLACE]{matches[0]}")
            elif len(matches) > 1:
                await websocket.send_text(f"__AUTOCOMPLETE__:[MATCHES]{'  '.join(sorted(matches))}")
            else:
                await websocket.send_text("__AUTOCOMPLETE__:[MATCHES]")
            continue  # Prevent prompt from being sent again here

        if cmd == "signout":
            await websocket.send_text("🚪 Signing out...")
            return True

        elif cmd == "help":
            await websocket.send_text("🛠 Available commands: " + ", ".join(COMMANDS))
            
        elif cmd == "config":
            await websocket.send_text("🔧 Entering config mode...")
            should_return = await command_control.cmd_config(websocket, prompt)
            if not should_return:
                return False
            await websocket.send_text("🔙 Returned from config mode.")

        else:
            await websocket.send_text("❓ Unknown command.")
