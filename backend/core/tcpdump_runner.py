import asyncio
from core.process_manager import set_current_process, clear_current_process, get_current_process

PREDEFINED_COMMANDS = {
    "default": ["/usr/bin/tcpdump", "-i", "any", "-l"],
    "http": ["/usr/bin/tcpdump", "-i", "any", "-n", "port", "80", "-l"],
    "https": ["/usr/bin/tcpdump", "-i", "any", "-n", "port", "443", "-l"],
    "dns": ["/usr/bin/tcpdump", "-i", "any", "-n", "port", "53", "-l"],
}

async def handle_tcpdump(websocket, cmd: str):
    tokens = cmd.strip().split()
    keyword = tokens[1] if len(tokens) > 1 else "default"

    tcpdump_cmd = PREDEFINED_COMMANDS.get(keyword)

    if not tcpdump_cmd:
        await websocket.send_text(
            f"❌ Unknown tcpdump profile '{keyword}'. Available: {', '.join(PREDEFINED_COMMANDS)}"
        )
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
            await websocket.send_text(line.decode().rstrip())

        await process.wait()

    except asyncio.CancelledError:
        # Task cancelled (e.g. via interrupt), terminate subprocess if still running
        proc = get_current_process(websocket)
        if proc and proc.returncode is None:
            proc.terminate()
            await proc.wait()
        clear_current_process(websocket)
        raise

    except FileNotFoundError:
        await websocket.send_text("❌ tcpdump not found on this system.")
    except Exception as e:
        await websocket.send_text(f"⚠️ Error running tcpdump: {e}")
    finally:
        clear_current_process(websocket)
        await websocket.send_text("✅ tcpdump finished.")
