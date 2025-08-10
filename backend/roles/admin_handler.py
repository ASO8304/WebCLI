import asyncio
from core import config_manager
from core.iptables_runner import handle_iptables
from core.tcpdump_runner import handle_tcpdump
from core.userctl_runner import handle_userctl
from core.autocomplete_handler import autocomplete_handler
from core.process_manager import interrupt_current_process
from core.systemctl_runner import handle_systemctl


async def admin_handler(websocket, username):
    role = "admin"
    prompt = f">>>PROMPT:[{role}]--({username})$ "
    await websocket.send_text("🛠 Logged in as 'admin'. Type 'help' for commands.")

    running_task = None
    need_prompt = True  # We owe a prompt at start

    def is_userctl_allowed() -> bool:
        # Only the admin account named 'king' is allowed to use userctl
        return username == "king"

    async def send_prompt():
        await websocket.send_text(prompt)

    while True:
        # Show a prompt whenever nothing is running and we owe one
        if not running_task and need_prompt:
            await send_prompt()
            need_prompt = False

        cmd = await websocket.receive_text()

        # Handle Ctrl+C interrupt
        if cmd == "__INTERRUPT__":
            if running_task and not running_task.done():
                await interrupt_current_process(websocket)
                # Cancel current task; its done-callback will send the prompt
                running_task.cancel()
                try:
                    await running_task
                except asyncio.CancelledError:
                    pass
                running_task = None
                # Do NOT request a prompt here; the callback already does it
                need_prompt = False
                continue
            else:
                await websocket.send_text("⚠️ No running command to interrupt.")
                need_prompt = True
                continue

        # Prevent new command while one is running (unless it's an interrupt above)
        if running_task and not running_task.done():
            await websocket.send_text("⚠️ A command is already running. Interrupt it with Ctrl+C.")
            continue

        # Autocomplete logic
        if cmd.startswith("__TAB__:"):
            partial = cmd[len("__TAB__:"):].strip()
            # Pass username so only admin 'king' sees 'userctl'
            suggestions = await autocomplete_handler(partial, role, username)
            if not suggestions:
                await websocket.send_text("__AUTOCOMPLETE__:[NOMATCHES]")
            elif len(suggestions) == 1:
                await websocket.send_text(f"__AUTOCOMPLETE__:[REPLACE]{suggestions[0]}")
            else:
                await websocket.send_text(f"__AUTOCOMPLETE__:[MATCHES] {', '.join(suggestions)}")
            continue

        # Signout
        if cmd.startswith("signout ") or cmd == "signout":
            await websocket.send_text("🚪 Signing out...")
            return True

        # Help
        elif cmd.startswith("help ") or cmd == "help":
            cmds = ["help", "signout", "config", "tcpdump", "systemctl"]
            if is_userctl_allowed():
                # Show to king only
                cmds.insert(3, "userctl <subcommand>")
            await websocket.send_text("🛠 Available commands: " + ", ".join(cmds))
            need_prompt = True
            continue

        # Config
        elif cmd.startswith("config ") or cmd == "config":
            await config_manager.show(websocket, prompt)
            await websocket.send_text("🔙 Returned from config mode.")
            need_prompt = True
            continue

        # User management (only admin 'king')
        elif cmd.startswith("userctl ") or cmd == "userctl":
            if not is_userctl_allowed():
                await websocket.send_text("⛔ 'userctl' is restricted. Permission Denied!")
                need_prompt = True
                continue
            await handle_userctl(websocket, cmd)
            need_prompt = True
            continue

        # Tcpdump (long-running)
        elif cmd.startswith("tcpdump ") or cmd == "tcpdump":
            running_task = asyncio.create_task(handle_tcpdump(websocket, cmd))

            def done_callback(task):
                nonlocal running_task, need_prompt
                running_task = None
                # Send exactly one prompt when the task ends (success or cancel)
                need_prompt = False
                asyncio.create_task(send_prompt())

            running_task.add_done_callback(done_callback)
            continue

        # Systemctl (treat as task)
        elif cmd.startswith("systemctl ") or cmd == "systemctl":
            running_task = asyncio.create_task(handle_systemctl(websocket, cmd))

            def done_callback(task):
                nonlocal running_task, need_prompt
                running_task = None
                need_prompt = False
                asyncio.create_task(send_prompt())

            running_task.add_done_callback(done_callback)
            continue

        # Iptables (treat as task)
        elif cmd.startswith("iptables ") or cmd == "iptables":
            running_task = asyncio.create_task(handle_iptables(websocket, cmd))

            def done_callback(task):
                nonlocal running_task, need_prompt
                running_task = None
                need_prompt = False
                asyncio.create_task(send_prompt())

            running_task.add_done_callback(done_callback)
            continue

        # Unknown command
        else:
            await websocket.send_text(f"❓ Unknown command: '{cmd}'")
            need_prompt = True
            continue
