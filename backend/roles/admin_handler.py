from core import autocomplete_handler
from core.command_control import cmd_config

#
# 🚀 admin command handler
async def admin_handler(websocket, username):
    # await websocket.send_text(f"🔐 Backend is running as user: {getpass.getuser()}")

    role = "admin"
    prompt = f">>>PROMPT:({role})$ "

    await websocket.send_text(f"🛠 Logged in as '{role}'. Type 'help' for commands.")

    new_prompt_flag = False
    while True:
        if not new_prompt_flag:
            await websocket.send_text(prompt)
        cmd = await websocket.receive_text()
        new_prompt_flag = False

        # 🧠 Handle TAB-based autocompletion
        if cmd.startswith("__TAB__:"):
            partial = cmd[len("__TAB__:"):].strip()
            suggestions = await autocomplete_handler(partial, role)

            if not suggestions:
                await websocket.send_text("__AUTOCOMPLETE__:[NOMATCHES]")
                new_prompt_flag = True  # Set flag to replace next prompt
            elif len(suggestions) == 1:
                await websocket.send_text(f"__AUTOCOMPLETE__:[REPLACE]{suggestions[0]}")
                new_prompt_flag = True  # Set flag to replace next prompt
            else:
                await websocket.send_text(f"__AUTOCOMPLETE__:[MATCHES] {', '.join(suggestions)}")
            continue

        # 🚪 Built-in command: signout
        if cmd == "signout":
            await websocket.send_text("🚪 Signing out...")
            return True

        # 📖 Help
        elif cmd == "help":
            await websocket.send_text("🛠 Available commands: help, signout, config, userctl <subcommand>, tcpdump")

        # 🛠 Config mode
        elif cmd == "config":
            await websocket.send_text("🔧 Entering config mode...")
            should_return = await cmd_config(websocket, prompt)
            if not should_return:
                return False
            await websocket.send_text("🔙 Returned from config mode.")

        # ❓ Unknown
        else:
            await websocket.send_text(f"❓ Unknown command: {cmd}")
