# core/process_manager.py
import asyncio

CURRENT_RUNNING_PROCESS = {}
CURRENT_RUNNING_TASK = {}

def set_current_process(websocket, process, task=None):
    CURRENT_RUNNING_PROCESS[websocket] = process
    if task:
        CURRENT_RUNNING_TASK[websocket] = task

def get_current_process(websocket):
    return CURRENT_RUNNING_PROCESS.get(websocket)

def get_current_task(websocket):
    return CURRENT_RUNNING_TASK.get(websocket)

def clear_current_process(websocket):
    CURRENT_RUNNING_PROCESS.pop(websocket, None)
    CURRENT_RUNNING_TASK.pop(websocket, None)

async def interrupt_current_process(websocket):
    """Stop both the asyncio task and the subprocess immediately."""
    proc = get_current_process(websocket)
    task = get_current_task(websocket)

    if not proc and not task:
        return False

    # Terminate process immediately
    if proc and proc.returncode is None:
        try:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=2.0)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
        except Exception:
            try:
                proc.kill()
                await proc.wait()
            except Exception:
                pass

    # Cancel asyncio task as well
    if task and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    clear_current_process(websocket)
    await websocket.send_text("✋ Command interrupted by user.")
    
    return True

