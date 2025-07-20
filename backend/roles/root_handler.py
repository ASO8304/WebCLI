import getpass
from core.command_control import cmd_config           
from core.tcpdump_runner import handle_tcpdump 
from core.userctl_runner import handle_userctl 

import getpass
from core.command_control import cmd_config
from core.tcpdump_runner import handle_tcpdump
from core.userctl_runner import handle_userctl
from core.autocomplete_handler import autocomplete_handler  # ✅ use role-based autocomplete

# 🚀 Root command handler
async def root_handler(websocket, username):
    await websocket.send_text(f"🔐 Backend is running as user: {getpass.getuser()}")

    role = "root"
    prompt = f">>>PROMPT:({role})$ "

    await websocket.send_text(f"🛠 Logged in as '{role}'. Type 'help' for commands.")

    while True:
        await websocket.send_text(prompt)
        cmd = await websocket.receive_text()

        # 🧠 Handle TAB-based autocompletion
        if cmd.startswith("__TAB__:"):
            partial = cmd[len("__TAB__:"):].strip()
            suggestions = await autocomplete_handler(partial, role)

            if not suggestions:
                await websocket.send_text("__AUTOCOMPLETE__:[NOMATCHES]")
            elif len(suggestions) == 1:
                await websocket.send_text(f"__AUTOCOMPLETE__:[REPLACE]{suggestions[0]}")
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

        # 👤 User control
        elif cmd.startswith("userctl "):
            await handle_userctl(websocket, cmd)

        # 🐾 Tcpdump
        elif cmd.startswith("tcpdump "):
            await handle_tcpdump(websocket, cmd)

        # ❓ Unknown
        else:
            await websocket.send_text("❓ Unknown command.")
