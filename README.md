<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>

  <h1>🖥️ Web CLI Service</h1>
  <p>This project implements a <strong>web-based command-line interface (CLI)</strong> using <strong>FastAPI</strong> and <strong>WebSockets</strong>. It allows users to connect via a browser and interact with a terminal-like CLI that supports user authentication, role-based command restrictions, and session-based history.</p>

  <h2>📦 Features</h2>
  <ul>
    <li>🔐 <strong>Role-Based Access Control</strong> (root, admin, operator, viewer)</li>
    <li>🧠 <strong>Command History</strong> using arrow keys (Up/Down)</li>
    <li>💻 <strong>Linux-style CLI</strong> in the browser</li>
    <li>🧱 <strong>Modular Command System</strong> with pluggable command sets per role</li>
    <li>🌐 <strong>WebSocket Communication</strong> for real-time interaction</li>
    <li>🔁 <strong>Persistent service</strong> via <code>systemd</code></li>
    <li>🖋️ <strong>Customizable frontend</strong> (HTML/CSS/JS)</li>
  </ul>

  <h2>🗂️ Project Structure</h2>
  <pre>/opt/webcli/
├── web_cli_server.py       # Main FastAPI server entry point
├── command_processor.py    # Shared command logic
├── admin_commands.py       # Admin-level commands
├── operator_commands.py    # Operator-level commands
├── viewer_commands.py      # Viewer-level commands
└── venv/                   # Python virtual environment

/etc/webcli/
├── users.json              # User metadata (userID, username, role)
└── pass.json               # SHA-256 password hashes (userID as keys)
  </pre>

  <h2>⚙️ Systemd Service</h2>
  <p>A <code>systemd</code> service to start the CLI automatically at boot:</p>
  <pre>[Unit]
Description=Web CLI FastAPI WebSocket Service
After=network.target

[Service]
User=webcli
WorkingDirectory=/opt/webcli
ExecStart=/opt/webcli/venv/bin/uvicorn web_cli_server:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
  </pre>

  <h2>🚀 Setup Instructions</h2>
  <ol>
    <li>Run the setup script:</li>
    <pre>chmod +x setup_webcli.sh
./setup_webcli.sh</pre>
    <li>This will:
      <ul>
        <li>Create a system user <code>webcli</code></li>
        <li>Copy files to <code>/opt/webcli</code></li>
        <li>Set up Python venv and install dependencies</li>
        <li>Deploy and start the <code>systemd</code> service</li>
      </ul>
    </li>
  </ol>

  <h2>🔐 Authentication & Role Management</h2>
  <p>Authentication is now handled using <strong>two files</strong> for better security and flexibility:</p>

  <ul>
    <li><code>users.json</code> — stores user metadata:</li>
  </ul>
  <pre>{
  "ali":   { "userid": 1, "username": "ali",   "role": "admin" },
  "reza":  { "userid": 2, "username": "reza",  "role": "operator" },
  "mina":  { "userid": 3, "username": "mina",  "role": "viewer" },
  "root":  { "userid": 0, "username": "root",  "role": "root" }
}
  </pre>

  <ul>
    <li><code>pass.json</code> — stores SHA-256 password hashes by userID:</li>
  </ul>
  <pre>{
  "0": "hash_of_root",
  "1": "hash_of_ali123",
  "2": "hash_of_reza123",
  "3": "hash_of_mina123"
}
  </pre>

  <p>✅ Each user is authenticated by matching the SHA-256 hash of their password against <code>pass.json</code>.</p>
  <p>✅ Once authenticated, users are routed to role-specific command handlers.</p>

</body>
</html>
