from shared_commands import command_control

# 👇 Replaces flat COMMANDS list
COMMAND_TREE = {
    "help": {},
    "signout": {},
    "do_something": {},
    "config": {
        "set": {},
        "get": {},
        "reset": {}
    },
    "consent": {
        "grant": {},
        "revoke": {},
        "status": {}
    }
}

# 🧠 Recursive logic to resolve suggestions
def get_command_completions(tokens, tree):
    if not tokens:
        return list(tree.keys())
    head, *rest = tokens
    if head in tree:
        return get_command_completions(rest, tree[head])
    else:
        return [cmd for cmd in tree if cmd.startswith(head)]

# 🌟 Wraps into async handler
async def autocomplete_handler(partial_command: str):
    tokens = partial_command.strip().split()
    if partial_command.endswith(" "):
        tokens.append("")
    suggestions = get_command_completions(tokens, COMMAND_TREE)
    if len(tokens) > 1:
        prefix = ' '.join(tokens[:-1])
        suggestions = [f"{prefix} {s}".strip() for s in suggestions]
    return suggestions

# 🚀 Main session loop
async def handle_session(websocket, username):
    role = "admin"
    prompt = f">>>PROMPT:{username}--({role})$ "

    await websocket.send_text(f"🛠 Logged in as '{role}'. Type 'help' for commands.")

    while True:
        await websocket.send_text(f"{prompt}")
        cmd = await websocket.receive_text()

        # ✅ Autocomplete support
        if cmd.startswith("__TAB__:"):
            partial = cmd.split(":", 1)[1]
            matches = await autocomplete_handler(partial)

            if len(matches) == 1:
                await websocket.send_text(f"__AUTOCOMPLETE__:[REPLACE]{matches[0]}")
            elif len(matches) > 1:
                await websocket.send_text(f"__AUTOCOMPLETE__:[MATCHES]{'  '.join(sorted(matches))}")
            else:
                await websocket.send_text("__AUTOCOMPLETE__:[MATCHES]")
            continue  # Skip re-displaying prompt

        # 📤 Command execution
        if cmd == "signout":
            await websocket.send_text("🚪 Signing out...")
            return True

        elif cmd == "help":
            # 🧾 Flatten all top-level commands for display
            def flatten_cmds(tree, prefix=""):
                cmds = []
                for key, sub in tree.items():
                    full = f"{prefix} {key}".strip()
                    cmds.append(full)
                    if sub:
                        cmds.extend(flatten_cmds(sub, full))
                return cmds

            available = flatten_cmds(COMMAND_TREE)
            await websocket.send_text("🛠 Available commands:\n" + "\n".join(sorted(available)))

        elif cmd.startswith("config"):
            await websocket.send_text("🔧 Entering config mode...")
            should_return = await command_control.cmd_config(websocket, prompt)
            if not should_return:
                return False
            await websocket.send_text("🔙 Returned from config mode.")

        else:
            await websocket.send_text("❓ Unknown command.")
