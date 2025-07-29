# core/autocomplete_handler.py

from core import tcpdump_runner, userctl_runner, systemctl_runner 

# 🔐 Role-based access control for top-level commands
ROLE_COMMANDS = {
    "root":     ["tcpdump", "userctl", "config", "help", "signout", "systemctl"],
    "admin":    ["tcpdump", "config", "help", "signout", "systemctl"],
    "operator": ["tcpdump", "help", "signout"],
    "viewer":   ["help", "signout"],
}

# 🔧 Command-to-module mapping (for autocomplete delegation)
ALL_COMMANDS = {
    "help": None,
    "signout": None,
    "config": None,
    "userctl": userctl_runner,
    "tcpdump": tcpdump_runner,
    "systemctl": systemctl_runner,
}


async def autocomplete_handler(partial_command: str, role: str):
    """
    Handles autocomplete logic based on user input and role.

    :param partial_command: The current input string before TAB
    :param role: User's role ("root", "admin", etc.)
    :return: List of autocompletion suggestions
    """
    tokens = partial_command.strip().split()
    if partial_command.endswith(" "):
        tokens.append("")  # User is starting a new token

    allowed_cmds = ROLE_COMMANDS.get(role, [])

    # Case 1: Nothing typed yet → suggest allowed commands
    if not tokens or tokens == [""]:
        return allowed_cmds

    cmd = tokens[0]
    
    # Case 2: Autocompleting the top-level command
    if len(tokens) == 1 and not partial_command.endswith(" "):
        return [c for c in allowed_cmds if c.startswith(cmd)]

    # Case 3: Valid top-level command → delegate to its autocomplete
    if cmd in allowed_cmds:
        handler = ALL_COMMANDS.get(cmd)
        if handler and hasattr(handler, "autocomplete"):
            suggestions = await handler.autocomplete(tokens[1:])
            return [f"{cmd} {s}" if s else f"{cmd} " for s in suggestions]

    # Case 4: Unknown or disallowed command
    return []
