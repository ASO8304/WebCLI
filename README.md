<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Web CLI Service</title>
</head>
<body>

  <h1>🖥️ Web CLI Service</h1>
  <p>This project implements a <strong>web-based command-line interface (CLI)</strong> using <strong>FastAPI</strong> and <strong>WebSockets</strong>. It allows users to connect via a browser and interact with a terminal-like CLI that supports user authentication, role-based command restrictions, and session-based history.</p>

  <div class="section">
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
  </div>

  <div class="section">
    <h2>🗂️ Project Structure</h2>
    <div class="file-structure">
/opt/webcli/
├── web_cli_server.py       # Main FastAPI server entry point
├── command_processor.py    # Shared command logic
├── admin_commands.py       # Admin-level commands
├── operator_commands.py    # Operator-level commands
├── viewer_commands.py      # Viewer-level commands
├── users.json              # User metadata (userID, username, role)
├── pass.json               # SHA-256 password hashes (userID as keys)
└── venv/                   # Python virtual environment

/etc/webcli/
├── users.json              # (Linked or copied config)
└── pass.json               # (Linked or copied config)
    </div>
  </div>

  <div class="section">
    <h2>⚙️ Systemd Service</h2>
    <p>A <code>systemd</code> service to start the CLI automatically at boot:</p>
    <div class="systemd">
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
    </div>
  </div>

  <div class="section">
    <h2>🚀 Setup Instructions</h2>
    <ol>
      <li>Run the setup script:<br>
        <pre>chmod +x setup_webcli.sh
./setup_webcli.sh</pre>
      </li>
      <li>This will:
        <ul>
          <li>Create a system user <code>webcli</code></li>
          <li>Copy files to <code>/opt/webcli</code></li>
          <li>Set up Python venv and install dependencies</li>
          <li>Deploy and start the <code>systemd</code> service</li>
        </ul>
      </li>
    </ol>
  </div>

  <div class="section">
    <h2>🔐 Authentication & Role Management</h2>
    <p>Authentication is now handled using <strong>two files</strong> for better security and flexibility:</p>

    <ul>
      <li><code>users.json</code> — stores user metadata:</li>
    </ul>
    <pre>{
  "ali": {
    "userid": 1,
    "username": "ali",
    "role": "admin"
  },
  "reza": {
    "userid": 2,
    "username": "reza",
    "role": "operator"
  },
  "mina": {
    "userid": 3,
    "username": "mina",
    "role": "viewer"
  },
  "root": {
    "userid": 0,
    "username": "root",
    "role": "root"
  }
}</pre>

    <ul>
      <li><code>pass.json</code> — stores SHA-256 password hashes by userID:</li>
    </ul>
    <pre>{
  "0": "hash_of_root",
  "1": "hash_of_ali123",
  "2": "hash_of_reza123",
  "3": "hash_of_mina123"
}</pre>

    <p>✅ Each user is authenticated by matching the SHA-256 hash of their password against <code>pass.json</code>.</p>
    <p>✅ Once authenticated, users are routed to role-specific command handlers.</p>
  </div>

  <div class="section">
    <h2>🧩 Command System</h2>
    <p>Commands are separated by role for secure access control:</p>
    <ul>
      <li><code>admin_commands.py</code> — full access to control, configuration, monitoring, and action commands</li>
      <li><code>operator_commands.py</code> — access to monitoring and limited action/configuration commands</li>
      <li><code>viewer_commands.py</code> — read-only access to system state and monitoring info</li>
    </ul>
    <p>Define commands using this pattern:</p>
    <pre>def cmd_status(username: str) -> str:
    return "System running normally."</pre>
  </div>

  <div class="section">
    <h2>🌐 Accessing the Web Terminal</h2>
    <p>Restart service if needed:</p>
    <pre>sudo systemctl restart webcli.service</pre>
    <p>Open your browser and go to:</p>
    <pre>http://&lt;your-server-ip&gt;:8000</pre>
  </div>

  <div class="section">
    <h2>🧠 Built-in Commands (Example)</h2>
    <ul>
      <li><code>help</code> — list available commands for your role</li>
      <li><code>exit</code> — end session</li>
      <li><code>uptime</code> — system uptime</li>
      <li><code>whoami</code> — current user</li>
      <li><code>reboot</code> — (admin only) restart the server</li>
      <li><code>status</code> — view system status</li>
    </ul>
  </div>

  <div class="section">
    <h2>🛠️ Service Management</h2>
    <ul>
      <li><strong>Check status:</strong><br><code>sudo systemctl status webcli.service</code></li>
      <li><strong>Restart:</strong><br><code>sudo systemctl restart webcli.service</code></li>
      <li><strong>Enable on boot:</strong><br><code>sudo systemctl enable webcli.service</code></li>
      <li><strong>View logs:</strong><br><code>journalctl -u webcli.service -b --no-pager -n 50</code></li>
    </ul>
  </div>

  <div class="section">
    <h2>🧪 Development Tips</h2>
    <ul>
      <li>Edit <code>static/index.html</code>, <code>style.css</code>, and <code>script.js</code> for frontend</li>
      <li>Restart the backend service after editing Python files</li>
      <li>Add new roles or commands in their respective modules</li>
    </ul>
  </div>

  <div class="footer">
    <p>🙌 Created by Abolfazl Sheikhoveisi — happy CLI hacking!</p>
  </div>

</body>
</html>
