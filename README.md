# 🖥️ Web CLI Service 

This project implements a **web-based command-line interface (CLI)** using **FastAPI** and **WebSockets**. It allows users to connect via a browser and run predefined or shell commands interactively—similar to a Linux terminal—with authentication, limitation and session-based command history.

---

## 📦 Features

- 🔐 **User Authentication** via `users.json` and 'pass.json' file
- 🧠 **Command History** using arrow keys (Up/Down)
- 💻 **Linux-style CLI** in the browser
- 🧱 **Modular Command System** (easy to add new commands and also manage previos commands)
- 🌐 **WebSocket Communication** for real-time interaction
- 🔁 **Persistent background service** using `systemd`
- 🖋️ Fully customizable HTML/JS frontend (`script.js`, `style.css`)

---

## 🗂️ Project Structure

/opt/webcli/
├── web_cli_server.py # Main FastAPI server entry point
├── command_processor.py
├── users.json # Stores valid usernames
├── pass.json # Stores usernames hashcode
└── venv/ # Python virtual environment

/etc/webcli/
├── users.json # Stores valid usernames
└── pass.json # Stores usernames hashcode
---

## ⚙️ Systemd Service

A `systemd` service is created to manage and start the CLI automatically on boot.

### 🔧 Service file: `/etc/systemd/system/webcli.service`

[Unit]
Description=Web CLI FastAPI WebSocket Service
After=network.target

[Service]
User=webcli
WorkingDirectory=/opt/webcli
ExecStart=/opt/webcli/venv/bin/uvicorn web_cli_server:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target

🚀 Setup Instructions
⚠️ Run the following as root (or using sudo) unless otherwise noted.

1. Run Bootstrap Script
Use the provided bash installer to set everything up:

chmod +x setup_webcli.sh
./setup_webcli.sh

This script will:

Create a new system user webcli

Create /opt/webcli and copy all necessary files

Set up Python virtual environment & install dependencies

Deploy the systemd service

Start and enable the service

🔐 Authentication (users.json)
Users authenticate interactively through the terminal UI.

{
  "alice": "password1",
  "bob": "password2"
}
Passwords are stored in plaintext by default

🧩 Command System
All commands are placed in individual functions inside command_processor.py

def cmd_hello(user: str) -> str:
    return "Hello, " + user + "!"

🌐 Accessing the Terminal UI
Start the service (if not running):

sudo systemctl restart webcli.service
Open browser and go to:

http://<your-server-ip>:8000
Authenticate and start typing commands (e.g., help, hello_10, uptime)

🧠 Built-in Commands
help — show available commands

exit — end session

uptime — system uptime

whoami — current system user

hello_10 — prints "hello" 10 times (for demo)

You can add your own easily in command_processor/.

🛠️ Managing the Service

# Check status
sudo systemctl status webcli.service

# Restart service
sudo systemctl restart webcli.service

# Enable on boot
sudo systemctl enable webcli.service

# View logs
journalctl -u webcli.service -b --no-pager -n 50

🧪 Development Tips
Edit index.html, style.css, and script.js in static/ for UI changes.

Reload the browser to reflect changes.

Restart the service after any backend Python edits.


🙌 Author
Created by Abolfazl Sheikhoveisi — happy CLI hacking!


