import subprocess

def cmd_help(user: str) -> str:
    return (
        "Available commands:\n"
        "  help\n"
        "  uptime\n"
        "  whoami\n"
        "  hello_10\n"
        "  hello_5\n"
        "  exit"
    )

def cmd_uptime(user: str) -> str:
    return subprocess.getoutput("uptime")

def cmd_whoami(user: str) -> str:
    return subprocess.getoutput("whoami")

def cmd_hello_10(user: str) -> str:
    return subprocess.getoutput("bash -c 'for i in {1..10}; do echo hello; done'")

def cmd_hello_5(user: str) -> str:
    return subprocess.getoutput("bash -c 'for i in {1..5}; do echo hello; done'")

def cmd_exit(user: str) -> str:
    return "exit"

# Map command names to function names
COMMAND_MAP = {
    "help": cmd_help,
    "uptime": cmd_uptime,
    "whoami": cmd_whoami,
    "hello_10": cmd_hello_10,
    "hello_5": cmd_hello_5,
    "exit": cmd_exit,
}

def process_command(command: str, user: str = "guest") -> str:
    command = command.strip().lower()
    func = COMMAND_MAP.get(command)
    if func:
        return func(user)
    else:
        return f"Unknown command: {command}"

