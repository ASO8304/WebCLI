import asyncio
import shutil
from core.process_manager import set_current_process, clear_current_process, get_current_process

TCPDUMP_PATH = shutil.which("tcpdump")

# Whitelisted options and filters
ALLOWED_FLAGS = {
    "-i", "-n", "-nn", "-v", "-vv", "-vvv", "-c", "-s", "-X", "-XX",
      "-A", "-e", "-tt", "-ttt", "-q", "-Q", "-U", "-E", "-p"
}
ALLOWED_KEYWORDS = {
    "port", "host", "src", "dst", "and", "or", "not", "ip", "ip6", "tcp", "udp", "icmp"
}

def build_tcpdump_command(tokens: list[str]) -> list[str] | None:
    cmd = [TCPDUMP_PATH, "-l"]
    skip_next = False

    for i, token in enumerate(tokens):
        if skip_next:
            skip_next = False
            continue

        if token in ALLOWED_FLAGS:
            cmd.append(token)
            if token in {"-i", "-c", "-s", "-w", "-r", "-E", "-Q"} and i + 1 < len(tokens):
                next_token = tokens[i + 1]
                if next_token.startswith("-"):
                    return None
                cmd.append(next_token)
                skip_next = True
        elif token in ALLOWED_KEYWORDS or token.replace('.', '').isnumeric():
            cmd.append(token)
        else:
            return None  # invalid or unsafe argument

    return cmd


async def handle_tcpdump(websocket, cmd: str):
    if not TCPDUMP_PATH:
        await websocket.send_text("❌ tcpdump not found on this system.")
        return

    tokens = cmd.strip().split()[1:]  # strip 'tcpdump' prefix
    tcpdump_cmd = build_tcpdump_command(tokens)

    if not tcpdump_cmd:
        await websocket.send_text("❌ Invalid or unsupported tcpdump options.")
        return

    await websocket.send_text(f"🐾 Running: {' '.join(tcpdump_cmd)}\n(Collecting packets...)\n")

    try:
        process = await asyncio.create_subprocess_exec(
            *tcpdump_cmd,
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
        await websocket.send_text(f"⚠️ Error running tcpdump: {e}")
    finally:
        clear_current_process(websocket)
        await websocket.send_text("✅ tcpdump finished.")
