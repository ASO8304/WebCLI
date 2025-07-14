<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>🖥️ Web CLI Service</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      line-height: 1.6;
      background-color: #f4f4f4;
      color: #333;
      padding: 40px;
    }
    h1, h2, h3 {
      color: #2c3e50;
    }
    code, pre {
      background-color: #e8e8e8;
      padding: 4px 6px;
      border-radius: 4px;
      font-family: "Courier New", monospace;
    }
    pre {
      padding: 10px;
      overflow-x: auto;
    }
    .section {
      margin-bottom: 40px;
    }
    ul {
      list-style-type: "🚀 ";
      padding-left: 20px;
    }
    .file-structure, .systemd {
      background-color: #fdfdfd;
      border-left: 5px solid #007acc;
      padding: 15px;
      font-family: monospace;
      white-space: pre;
    }
    .footer {
      margin-top: 50px;
      font-size: 0.9em;
      color: #777;
    }
  </style>
</head>
<body>

  <h1>🖥️ Web CLI Service</h1>
  <p>This project implements a <strong>web-based command-line interface (CLI)</strong> using <strong>FastAPI</strong> and <strong>WebSockets</strong>. It allows users to connect via a browser and run predefined or shell commands interactively—similar to a Linux terminal—with authentication, limitations, and session-based command history.</p>

  <div class="section">
    <h2>📦 Features</h2>
    <ul>
      <li>🔐 <strong>User Authentication</strong> via <code>users.json</code> and <code>pass.json</code></li>
      <li>🧠 <strong>Command History</strong> using arrow keys (Up/Down)</li>
      <li>💻 <strong>Linux-style CLI</strong> in the browser</li>
      <li>🧱 <strong>Modular Command System</strong> (easy to add new commands)</li>
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
├── command_processor.py    # All command logic
├── users.json              # Stores valid usernames
├── pass.json               # Stores usernames' hash
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
    <h2>🔐 Authentication</h2>
    <p>Users authenticate via the web terminal. Stored in <code>users.json</code>:</p>
    <pre>{
  "alice": "password1",
  "bob": "password2"
}</pre>
    <p><strong>⚠️ Warning:</strong> Passwords are stored as plaintext by default. Secure handling is advised.</p>
  </div>

  <div class="section">
    <h2>🧩 Command System</h2>
    <p>Define new commands in <code>command_processor.py</code> like:</p>
    <pre>def cmd_hello(user: str) -> str:
    return "Hello, " + user + "!"</pre>
  </div>

  <div class="section">
    <h2>🌐 Accessing the Web Terminal</h2>
    <p>Restart service if needed:</p>
    <pre>sudo systemctl restart webcli.service</pre>
    <p>Open your browser and go to:</p>
    <pre>http://&lt;your-server-ip&gt;:8000</pre>
  </div>

  <div class="section">
    <h2>🧠 Built-in Commands</h2>
    <ul>
      <li><code>help</code> — list available commands</li>
      <li><code>exit</code> — end session</li>
      <li><code>uptime</code> — system uptime</li>
      <li><code>whoami</code> — current user</li>
      <li><code>hello_10</code> — prints "hello" 10 times</li>
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
      <li>Reload your browser to view changes</li>
      <li>Restart the backend service after editing Python files</li>
    </ul>
  </div>

  <div class="footer">
    <p>🙌 Created by Abolfazl Sheikhoveisi — happy CLI hacking!</p>
  </div>

</body>
</html>
