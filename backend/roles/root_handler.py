import asyncio
from core.command_control import cmd_config
from core.tcpdump_runner import handle_tcpdump
from core.userctl_runner import handle_userctl
from core.autocomplete_handler import autocomplete_handler
from core.process_manager import interrupt_current_process

async def root_handler(websocket, username):
    role = "root"
    prompt = f">>>PROMPT:({role})$ "
    await websocket.send_text(f"🛠 Logged in as '{role}'. Type 'help' for commands.")

    running_task = None

    new_prompt_flag = False
    while True:
        if not running_task and not new_prompt_flag:
            await websocket.send_text(prompt)

        new_prompt_flag = False
        cmd = await websocket.receive_text()

        # Handle Ctrl+C interrupt
        if cmd == "__INTERRUPT__":
            if running_task and not running_task.done():
                await interrupt_current_process(websocket)
                running_task.cancel()
                try:
                    await running_task
                except asyncio.CancelledError:
                    pass
                running_task = None
                continue
            else:
                await websocket.send_text("⚠️ No running command to interrupt.")
                continue

        # If a command is running, block new commands except interrupt
        if running_task and not running_task.done():
            await websocket.send_text("⚠️ A command is already running. Interrupt it with Ctrl+C.")
            continue

        # Autocomplete handler
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

        if cmd == "signout":
            await websocket.send_text("🚪 Signing out...")
            return True

        elif cmd == "help":
            await websocket.send_text("🛠 Available commands: help, signout, config, userctl <subcommand>, tcpdump")

        elif cmd == "config":
            should_return = await cmd_config(websocket, prompt)
            if not should_return:
                return False
            await websocket.send_text("🔙 Returned from config mode.")

        elif cmd.startswith("userctl ") or cmd == "userctl":
            await handle_userctl(websocket, cmd)

        elif cmd.startswith("tcpdump ") or cmd == "tcpdump":
            # Run tcpdump in background task to keep loop responsive
            running_task = asyncio.create_task(handle_tcpdump(websocket, cmd))

        else:
            await websocket.send_text(f"❓ Unknown command: '{cmd}'")
