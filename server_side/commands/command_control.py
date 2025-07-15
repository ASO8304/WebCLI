import subprocess
from commands import config

async def cmd_config(websocket, prompt):

    prompt = f"{prompt}config-mode> " 

    while True:
        await websocket.send_text(f"{prompt}")
        
        command = await websocket.receive_text()
        cmd = command.strip().lower()

        if cmd == "back":
            await websocket.send_text("↩️ Returning to previous menu.")
            return True  # Go back to role handler

        elif cmd == "show":
            await config.show(websocket, prompt) 

        elif cmd.startswith("set "):
            await websocket.send_text(f"✅ Config updated: {cmd[4:]}")

        elif cmd == "exit":
            await websocket.send_text("👋 Exiting session.")
            return False  # Ends entire session

        else:
            await websocket.send_text("❓ Unknown config command. Use 'show', 'set <key=value>', 'back', or 'exit'.")
