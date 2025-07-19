import asyncio
import shlex

### ls -hal $(which tcpdump)
####-rwxr-xr-x 1 root root 1.3M Feb  8  2024 /usr/bin/tcpdump

### chmod 750 /usr/bin/tcpdump
 
### setcap cap_net_raw,cap_net_admin=eip /usr/bin/tcpdump 
# e = Effective (enabled when the program runs)
# i = Inheritable (can pass this cap to child processes)
# p = Permitted (the cap is allowed at all)

### setfacl -m u:webcli:x /usr/bin/tcpdump



async def handle_tcpdump(websocket, cmd):
    await websocket.send_text("📡 Attempting to run tcpdump...")
    
    try:
        # Test basic command execution first
        test_cmd = ["/usr/bin/id"]
        process = await asyncio.create_subprocess_exec(
            *test_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        await websocket.send_text(f"👤 User context: {stdout.decode().strip()}")
        
        # Now try tcpdump with minimal options
        command = ["/usr/bin/tcpdump", "-c", "3", "-i", "lo"]  # Use loopback first
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if stdout:
            await websocket.send_text(f"ℹ️ tcpdump version: {stdout.decode().strip()}")
        if stderr:
            await websocket.send_text(f"⚠️ stderr: {stderr.decode().strip()}")
        
        await websocket.send_text("✅ Basic tcpdump check completed.")
        
    except Exception as e:
        await websocket.send_text(f"❌ Debug error: {str(e)}")