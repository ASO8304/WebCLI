import asyncio
from typing import List
from core.process_manager import (
    set_current_process,
    clear_current_process,
    get_current_process,
)

# ---------------------------
# Whitelists
# ---------------------------
# Only these sub‑commands may be executed.  Feel free to expand if you audit
# additional systemctl actions that are safe for your environment.
ALLOWED_SUBCOMMANDS = {
    "status",
    "restart",
    "start",
    "stop",
    "reload",
    "enable",
    "disable",
}

# Hard whitelist of services administrators are allowed to manage via WebCLI.
# Use bare names (no ".service" suffix).  Add or remove entries to suit your
# operational policy.
ALLOWED_SERVICES = {
    "nginx",
    "ssh",        # OpenSSH server (sometimes called sshd)
    "sshd",
    "cron",
    "webcli",     # your own backend service
}

# ---------------------------
# Helper functions
# ---------------------------

def _strip_suffix(service: str) -> str:
    """Return the service name without a trailing .service."""
    return service[:-8] if service.endswith(".service") else service


def _is_allowed_service(service: str) -> bool:
    return _strip_suffix(service) in ALLOWED_SERVICES


def _build_cmd(subcommand: str, service: str) -> List[str]:
    """Assemble the final sudo/systemctl command list."""
    return [
        "sudo",
        "systemctl",
        subcommand,
        f"{_strip_suffix(service)}.service",  # Ensures the suffix
    ]

# ---------------------------
# Main handler
# ---------------------------

async def handle_systemctl(websocket, full_command: str):
    """Validate, build, and run a whitelisted systemctl command."""

    tokens = full_command.strip().split()

    if len(tokens) < 3:
        await websocket.send_text("❌ Usage: systemctl <subcommand> <service>")
        return

    # tokens[0] == "systemctl"
    subcommand = tokens[1].lower()
    service_arg = tokens[2]

    # --- Validate sub‑command ---
    if subcommand not in ALLOWED_SUBCOMMANDS:
        await websocket.send_text(f"❌ Subcommand '{subcommand}' is not allowed.")
        return

    # --- Validate service name ---
    if not _is_allowed_service(service_arg):
        allowed = ", ".join(sorted(ALLOWED_SERVICES))
        await websocket.send_text(
            f"❌ Service '{service_arg}' is not in the whitelist. Allowed: {allowed}"
        )
        return

    cmd = _build_cmd(subcommand, service_arg)
    await websocket.send_text(f"🛠 Running: {' '.join(cmd)}")

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        set_current_process(websocket, process)

        async for line in process.stdout:
            await websocket.send_text(line.decode(errors="ignore").rstrip())

        await process.wait()

    except asyncio.CancelledError:
        proc = get_current_process(websocket)
        if proc and proc.returncode is None:
            proc.terminate()
            await proc.wait()
        clear_current_process(websocket)
        raise
    except Exception as e:
        await websocket.send_text(f"⚠️ Error running systemctl: {e}")
    finally:
        clear_current_process(websocket)
        await websocket.send_text("✅ systemctl finished.")

# ---------------------------
# Autocomplete
# ---------------------------

async def autocomplete(tokens):
    """Provide tab‑completion suggestions.

    tokens → list of arguments after the top‑level 'systemctl'.
    """

    # Case 0: no tokens yet → suggest sub‑commands
    if not tokens:
        return sorted(ALLOWED_SUBCOMMANDS)

    # Case 1: completing the sub‑command itself
    if len(tokens) == 1:
        partial = tokens[0].lower()
        return [cmd for cmd in ALLOWED_SUBCOMMANDS if cmd.startswith(partial)]

    # Case 2: completing the service name
    if len(tokens) == 2:
        subcommand = tokens[0].lower()
        if subcommand not in ALLOWED_SUBCOMMANDS:
            return []
        partial_service = _strip_suffix(tokens[1].lower())
        suggestions = [
            f"{subcommand} {svc}.service" for svc in sorted(ALLOWED_SERVICES)
            if svc.startswith(partial_service)
        ]
        return suggestions

    # No suggestions for additional tokens
    return []
