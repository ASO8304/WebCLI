import asyncio
from core.command_control import cmd_config
from core.tcpdump_runner import handle_tcpdump
from core.userctl_runner import handle_userctl
from core.autocomplete_handler import autocomplete_handler
from core.process_manager import interrupt_current_process
from core.systemctl_runner import handle_systemctl
from core.iptables_runner import handle_iptables  # ✅ NEW


async def admin_handler(websocket, username):
    role = "admin"
    prompt = f">>>PROMPT:({role})$ "
    await websocket.send_text(f"🛠 Logged in as '{role}'. Type 'help' for commands.")

    running_task = None
    new_prompt_flag = False

    async def send_prompt():
        if not running_task or (running_task and running_task.done()):
            await websocket.send_text(prompt)

    while True:
        if not running_task and not new_prompt_flag:
            await websocket.send_text(prompt)

        new_prompt_flag = False
        cmd = await websocket.receive_text()

        # Ctrl+C interrupt
        if cmd == "__INTERRUPT__":
            if running_task and not running_task.done():
                await interrupt_current_process(websocket)
                running_task.cancel()
                try:
                    await running_task
                except asyncio.CancelledError:
                    pass
                running_task = None
                await send_prompt()
                continue
            else:
                await websocket.send_text("⚠️ No running command to interrupt.")
                continue

        if running_task and not running_task.done():
            await websocket.send_text("⚠️ A command is already running. Interrupt it with Ctrl+C.")
            continue

        # Autocomplete
        if cmd.startswith("__TAB__:"):
            partial = cmd[len("__TAB__:"):].strip()
            suggestions = await autocomplete_handler(partial, role)
            if not suggestions:
                await websocket.send_text("__AUTOCOMPLETE__:[NOMATCHES]")
                new_prompt_flag = True
            elif len(suggestions) == 1:
                await websocket.send_text(f"__AUTOCOMPLETE__:[REPLACE]{suggestions[0]}")
                new_prompt_flag = True
            else:
                await websocket.send_text(f"__AUTOCOMPLETE__:[MATCHES] {', '.join(suggestions)}")
            continue

        # Sign out
        if cmd == "signout":
            await websocket.send_text("🚪 Signing out...")
            return True

        # Help
        elif cmd == "help":
            await websocket.send_text(
                "🛠 Available commands: help, signout, config, userctl <subcommand>, tcpdump, systemctl, iptables"
            )

        # Config
        elif cmd == "config":
            should_return = await cmd_config(websocket, prompt)
            if not should_return:
                return False
            await websocket.send_text("🔙 Returned from config mode.")

        # Tcpdump
        elif cmd.startswith("tcpdump ") or cmd == "tcpdump":
            running_task = asyncio.create_task(handle_tcpdump(websocket, cmd))

            def done_callback(task):
                nonlocal running_task
                running_task = None
                asyncio.create_task(send_prompt())

            running_task.add_done_callback(done_callback)

        # Systemctl
        elif cmd.startswith("systemctl ") or cmd == "systemctl":
            running_task = asyncio.create_task(handle_systemctl(websocket, cmd))

            def done_callback(task):
                nonlocal running_task
                running_task = None
                asyncio.create_task(send_prompt())

            running_task.add_done_callback(done_callback)

        # Iptables
        elif cmd.startswith("iptables ") or cmd == "iptables":
            running_task = asyncio.create_task(handle_iptables(websocket, cmd))

            def done_callback(task):
                nonlocal running_task
                running_task = None
                asyncio.create_task(send_prompt())

            running_task.add_done_callback(done_callback)

        # Unknown command
        else:
            await websocket.send_text(f"❓ Unknown command: '{cmd}'")

        if not running_task and not new_prompt_flag:
            await websocket.send_text(prompt)
