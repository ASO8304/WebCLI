<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
</head>
<body>

  <h1>🖥️ Web CLI Service</h1>
  <p>
    A <strong>web-based command-line interface</strong> built with 
    <strong>FastAPI</strong> and <strong>WebSockets</strong>, 
    letting users run a restricted Linux-style shell in their browser.
  </p>

  <h2>📦 Features</h2>
  <ul>
    <li>🔐 <strong>Role-Based Access Control:</strong> root, admin, operator, viewer</li>
    <li>🧠 <strong>Command History:</strong> Up/Down arrow navigation</li>
    <li>💻 <strong>Terminal UI:</strong> HTML/CSS/JS “green on black” terminal</li>
    <li>⚙️ <strong>Modular Commands:</strong> Separate processors per role</li>
    <li>🌐 <strong>Real-Time WebSocket:</strong> Low-latency I/O between client & server</li>
    <li>🐾 <strong>Secure tcpdump:</strong> Direct `/usr/bin/tcpdump` with Linux capabilities</li>
    <li>🛡️ <strong>Sandboxing & Hardening:</strong> systemd with capabilities + ACLs</li>
    <li>🔁 <strong>Always-On Service:</strong> systemd unit for automatic startup</li>
  </ul>

  <h2>🗂️ Project Structure</h2>
  <pre>
/client_side/
├── frontend.html        # Browser terminal UI (HTML)
├── style.css            # Terminal styling (wider, monospace)
└── script.js            # WebSocket + input handling

/server_side/
├── admin_role/
│   └── command_processor_admin.py
├── operator_role/
│   └── command_processor_operator.py
├── root_role/
│   ├── command_processor_root.py
│   └── userctl.py
├── shared_commands/
│   ├── command_control.py
│   ├── config.py
│   ├── tcpdump.py           # Direct tcpdump integration
│   └── validators.py
├── viewer_role/
│   └── command_processor_viewer.py
├── web_cli_server.py       # FastAPI + WebSocket entrypoint
├── users.json              # User → {id, role} mappings
├── pass.json               # SHA-256 password hashes by userID
└── test.py                 # Unit & integration tests
  </pre>

  <h2>⚙️ Setup & Installation</h2>
  <ol>
    <li>Clone the repo and enter it:
      <pre>git clone https://… && cd webcli</pre>
    </li>
    <li>Run the installer (creates <code>webcli</code> user, venv, systemd service):
      <pre>chmod +x install.sh
./install.sh</pre>
    </li>
    <li>Verify systemd status:
      <pre>systemctl status webcli</pre>
    </li>
  </ol>

  <h2>🚀 Usage</h2>
  <p>Open your browser at <code>http://&lt;host&gt;:8000</code>, log in, and you’ll see a Linux-style prompt:</p>
  <pre>
(root)$ help
… available commands …
(root)$ tcpdump       # runs predefined tcpdump on interface wlo1, line-buffered
(root)$ tcpdump http  # captures 10 HTTP packets on port 80
  </pre>

  <h2>🛡️ Security & Hardening</h2>
  <ul>
    <li><strong>/usr/bin/tcpdump</strong> has <code>cap_net_raw,cap_net_admin+eip</code> via <code>setcap</code>.</li>
    <li><code>chmod 750</code> + <code>setfacl -m u:webcli:x</code> ensure only <code>webcli</code> can execute it.</li>
    <li><strong>systemd</strong> unit grants only:
      <code>CAP_NET_RAW</code>, <code>CAP_NET_ADMIN</code>, <code>CAP_NET_BIND_SERVICE</code>.<br>
      <code>RestrictAddressFamilies</code> includes <code>AF_PACKET</code> for packet capture.</li>
    <li><code>NoNewPrivileges=true</code>, <code>ProtectSystem=full</code>, <code>ProtectHome=yes</code>, etc.</li>
  </ul>

  <h2>🔄 Customization</h2>
  <ul>
    <li>Add new tcpdump profiles in <code>shared_commands/tcpdump.py</code></li>
    <li>Modify CSS in <code>client_side/style.css</code> for different terminal themes</li>
    <li>Extend command sets per role under <code>server_side/<em>&lt;role&gt;_role/</em></code></li>
  </ul>

  <p>Enjoy your new browser-based CLI! 🚀</p>
</body>
</html>