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

    async def send_prompt_if_needed():
        if not running_task or (running_task and running_task.done()):
            await websocket.send_text(prompt)

    while True:
        # Show prompt if no task is running and no autocomplete override
        if not running_task and not new_prompt_flag:
            await websocket.send_text(prompt)

        new_prompt_flag = False  # Reset flag before receiving new input
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
                await send_prompt_if_needed()
                continue
            else:
                await websocket.send_text("⚠️ No running command to interrupt.")
                continue

        # Prevent running multiple commands at once
        if running_task and not running_task.done():
            await websocket.send_text("⚠️ A command is already running. Interrupt it with Ctrl+C.")
            continue

        # Handle autocomplete
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

        # Command: signout
        if cmd == "signout":
            await websocket.send_text("🚪 Signing out...")
            return True

        # Command: help
        elif cmd == "help":
            await websocket.send_text("🛠 Available commands: help, signout, config, userctl <subcommand>, tcpdump")

        # Command: config
        elif cmd == "config":
            should_return = await cmd_config(websocket, prompt)
            if not should_return:
                return False
            await websocket.send_text("🔙 Returned from config mode.")

        # Command: userctl
        elif cmd.startswith("userctl ") or cmd == "userctl":
            await handle_userctl(websocket, cmd)

        # Command: tcpdump
        elif cmd.startswith("tcpdump ") or cmd == "tcpdump":
            running_task = asyncio.create_task(handle_tcpdump(websocket, cmd))

            def done_callback(task):
                nonlocal running_task
                running_task = None
                asyncio.create_task(send_prompt_if_needed())

            running_task.add_done_callback(done_callback)

        # Unknown command
        else:
            await websocket.send_text(f"❓ Unknown command: '{cmd}'")

        # Final check to maybe show prompt after fast commands
        if not running_task and not new_prompt_flag:
            await websocket.send_text(prompt)
