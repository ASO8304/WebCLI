### ls -hal $(which tcpdump)
####-rwxr-xr-x 1 root root 1.3M Feb  8  2024 /usr/bin/tcpdump

### chmod 750 /usr/bin/tcpdump
 
### setcap cap_net_raw,cap_net_admin=eip /usr/bin/tcpdump 
# e = Effective (enabled when the program runs)
# i = Inheritable (can pass this cap to child processes)
# p = Permitted (the cap is allowed at all)

### setfacl -m u:webcli:x /usr/bin/tcpdump
import asyncio

# Predefined safe tcpdump commands (you can add more filters later)
PREDEFINED_COMMANDS = {
    "default": ["/usr/bin/tcpdump", "-i", "wlo1", "-l"],
    "http": ["/opt/webcli/tcpdump_wrapper.sh", "-i", "any", "-n", "port", "80", "-c", "10"],
    "https": ["/opt/webcli/tcpdump_wrapper.sh", "-i", "any", "-n", "port", "443", "-c", "10"],
    "dns": ["/opt/webcli/tcpdump_wrapper.sh", "-i", "any", "-n", "port", "53", "-c", "10"],
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
            stderr=asyncio.subprocess.STDOUT
        )

        async for line in process.stdout:
            await websocket.send_text(line.decode().rstrip())

        await process.wait()

    except FileNotFoundError:
        await websocket.send_text("❌ tcpdump not found on this system.")
    except Exception as e:
        await websocket.send_text(f"⚠️ Error running tcpdump: {e}")
