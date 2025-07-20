import getpass
from core.command_control import cmd_config           
from core.tcpdump_runner import handle_tcpdump 
from core.userctl_runner import handle_userctl 

# 🔧 Define the full command tree structure
COMMAND_TREE = {
    "help": {},
    "signout": {},
    "config": {},
    "userctl": {
        "add": {},
        "remove": {},
        "list": {},
        "modify": {
            "password": {},
            "role": {},
        }
    },
    "tcpdump": {}
}



# 🚀 Recursively traverse the command tree to suggest completions
def get_command_completions(tokens, tree):
    if not tokens:
        return list(tree.keys())

    head, *rest = tokens
    if head in tree:
        return get_command_completions(rest, tree[head])
    else:
        return [cmd for cmd in tree if cmd.startswith(head)]


# 🌟 Autocomplete handler using the command tree
async def autocomplete_handler(partial_command: str):
    tokens = partial_command.strip().split()

    # Determine if we're completing a new token or current one
    if partial_command.endswith(" "):
        tokens.append("")  # User is starting a new token

    suggestions = get_command_completions(tokens, COMMAND_TREE)

    # Reconstruct suggestions with prefix
    if len(tokens) > 1:
        prefix = ' '.join(tokens[:-1])
        suggestions = [f"{prefix} {s}".strip() for s in suggestions]

    return suggestions


async def root_handler(websocket, username):
    await websocket.send_text(f"🔐 Backend is running as user: {getpass.getuser()}")

    role = "root"
    prompt = f">>>PROMPT:({role})$ "

    await websocket.send_text(f"🛠 Logged in as '{role}'. Type 'help' for commands.")

    while True:
        await websocket.send_text(f"{prompt}")
        cmd = await websocket.receive_text()

        # 🧩 Autocomplete handling
        if cmd.startswith("__TAB__:"):
            partial = cmd[len("__TAB__:"):].strip()
            suggestions = await autocomplete_handler(partial)

            if suggestions:
                await websocket.send_text(f"✨ Suggestions: {', '.join(suggestions)}")
            else:
                await websocket.send_text("🤷 No suggestions found.")
            continue


        # 📤 Command handling logic
        if cmd == "signout":
            await websocket.send_text("🚪 Signing out...")
            return True

        elif cmd == "help":
            await websocket.send_text("🛠 Available commands: help, signout, config, userctl <subcommand>")

        elif cmd == "config":
            await websocket.send_text("🔧 Entering config mode...")
            should_return = await cmd_config(websocket, prompt)
            if not should_return:
                return False
            await websocket.send_text("🔙 Returned from config mode.")

        elif cmd.startswith("userctl "):
            await handle_userctl(websocket, cmd)

        elif cmd.startswith("tcpdump"):
            await handle_tcpdump(websocket, cmd)

        else:
            await websocket.send_text("❓ Unknown command.")
