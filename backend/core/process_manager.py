import asyncio
# core/process_manager.py

CURRENT_RUNNING_PROCESS = {}

def set_current_process(websocket, process):
    CURRENT_RUNNING_PROCESS[websocket] = process

def get_current_process(websocket):
    return CURRENT_RUNNING_PROCESS.get(websocket)

def clear_current_process(websocket):
    CURRENT_RUNNING_PROCESS.pop(websocket, None)

async def interrupt_current_process(websocket):
    process = get_current_process(websocket)
    if process and process.returncode is None:
        process.terminate()
        try:
            await process.wait()
        except Exception:
            pass
        clear_current_process(websocket)
        await websocket.send_text("✋ Command interrupted by user.")
        return True
    return False
