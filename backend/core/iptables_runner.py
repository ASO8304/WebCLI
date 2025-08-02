import asyncio
import ipaddress

VALID_TABLES = {"filter", "nat", "mangle", "raw", "security"}
VALID_CHAINS = {"INPUT", "OUTPUT", "FORWARD", "PREROUTING", "POSTROUTING"}
VALID_ACTIONS = ["list", "flush", "block", "unblock"]

def is_valid_ip(ip):
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False

async def run_command(websocket, args):
    try:
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )

        async for line in process.stdout:
            await websocket.send_text(line.decode().strip())

        await process.wait()
    except Exception as e:
        await websocket.send_text(f"❌ Error: {e}")

async def handle_iptables(websocket, cmd: str):
    tokens = cmd.strip().split()
    if len(tokens) < 2:
        await websocket.send_text("❌ Usage: iptables <list|flush|block|unblock> [...]")
        return

    action = tokens[1]

    if action == "list":
        # iptables list [<table>] [<chain>]
        table = tokens[2] if len(tokens) >= 3 else "filter"
        chain = tokens[3] if len(tokens) >= 4 else None

        if table not in VALID_TABLES:
            await websocket.send_text(f"❌ Invalid table: {table}")
            return

        args = ["sudo", "iptables", "-t", table, "-L", "-n", "-v"]
        if chain:
            args.append(chain)

        await websocket.send_text(f"📄 Listing rules in table '{table}'" + (f", chain '{chain}'" if chain else "") + "...")
        await run_command(websocket, args)

    elif action == "flush":
        # iptables flush [<table>] [<chain>]
        table = tokens[2] if len(tokens) >= 3 else "filter"
        chain = tokens[3] if len(tokens) >= 4 else None

        if table not in VALID_TABLES:
            await websocket.send_text(f"❌ Invalid table: {table}")
            return

        args = ["sudo", "iptables", "-t", table, "-F"]
        if chain:
            args.append(chain)

        await websocket.send_text(f"🧼 Flushing table '{table}'" + (f", chain '{chain}'" if chain else "") + "...")
        await run_command(websocket, args)

    elif action == "block":
        # iptables block <table> <chain> <ip>
        if len(tokens) != 5:
            await websocket.send_text("❌ Usage: iptables block <table> <chain> <ip>")
            return

        table, chain, ip = tokens[2], tokens[3], tokens[4]

        if table not in VALID_TABLES or chain not in VALID_CHAINS or not is_valid_ip(ip):
            await websocket.send_text("❌ Invalid syntax or values. Check table, chain, and IP.")
            return

        args = ["sudo", "iptables", "-t", table, "-A", chain, "-s", ip, "-j", "DROP"]
        await websocket.send_text(f"🚫 Blocking IP {ip} in {table}/{chain}...")
        await run_command(websocket, args)

    elif action == "unblock":
        # iptables unblock <table> <chain> <ip>
        if len(tokens) != 5:
            await websocket.send_text("❌ Usage: iptables unblock <table> <chain> <ip>")
            return

        table, chain, ip = tokens[2], tokens[3], tokens[4]

        if table not in VALID_TABLES or chain not in VALID_CHAINS or not is_valid_ip(ip):
            await websocket.send_text("❌ Invalid syntax or values. Check table, chain, and IP.")
            return

        args = ["sudo", "iptables", "-t", table, "-D", chain, "-s", ip, "-j", "DROP"]
        await websocket.send_text(f"🔓 Unblocking IP {ip} in {table}/{chain}...")
        await run_command(websocket, args)

    else:
        await websocket.send_text(f"❌ Unsupported iptables command: '{action}'")



async def autocomplete(tokens):
    """Autocomplete for iptables command."""
    if not tokens:
        return VALID_ACTIONS

    # Case 1: complete the action
    if len(tokens) == 1:
        partial = tokens[0].lower()
        return [action for action in VALID_ACTIONS if action.startswith(partial)]

    action = tokens[0].lower()

    # Case 2: complete the table name
    if len(tokens) == 2 and action in {"list", "flush", "block", "unblock"}:
        partial = tokens[1].lower()
        return [f"{action} {tbl}" for tbl in VALID_TABLES if tbl.startswith(partial)]

    # Case 3: complete the chain name
    if len(tokens) == 3 and action in {"list", "flush", "block", "unblock"}:
        table = tokens[1].lower()
        partial = tokens[2].upper()
        if table in VALID_TABLES:
            return [f"{action} {table} {chain}" for chain in VALID_CHAINS if chain.startswith(partial)]

    # Case 4: no autocomplete for IPs (4th arg for block/unblock)
    return []