from shared_commands import command_control
from root_role.userctl import handle_userctl

async def handle_session(websocket, username):
    role = "root"
    prompt = f">>>PROMPT:({role})$ "

    await websocket.send_text(f"🛠 Logged in as '{role}'. Type 'help' for commands.")

    while True:
        await websocket.send_text(f"{prompt}")
        cmd = await websocket.receive_text()

        if cmd == "signout":
            await websocket.send_text("🚪 Signing out...")
            return True

        elif cmd == "help":
            await websocket.send_text("🛠 Available commands: help, signout, config, userctl <subcommand>")

        elif cmd == "config":
            await websocket.send_text("🔧 Entering config mode...")
            should_return = await command_control.cmd_config(websocket)
            if not should_return:
                return False
            await websocket.send_text("🔙 Returned from config mode.")

        elif cmd.startswith("userctl "):
            await handle_userctl(websocket, cmd, prompt)

        else:
            await websocket.send_text("❓ Unknown command.")
