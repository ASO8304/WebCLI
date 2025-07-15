from commands import command_control 

def process_command(command: str, username: str) -> str:
    command = command.strip().lower()
    
    if command == "help":
        return "Available commands: reboot, shutdown, configure, status, help, exit"
    elif command == "reboot":
        return "🔄 System rebooting..."
    elif command == "shutdown":
        return "⚠️ System shutting down..."
    elif command == "configure":
        return "⚙️ Entering configuration mode..."
    elif command == "status":
        return "📊 System status: All systems operational."
    else:
        return f"❓ Unknown command: {command}"
