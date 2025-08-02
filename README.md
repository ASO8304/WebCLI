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
/client/ 
├── index.html           # Browser terminal UI (HTML)
├── style.css            # Terminal styling 
└── script.js            # WebSocket + input handling

/backend/
├── core/
│   ├── command_control.py
│   ├── config_manager.py
│   ├── tcpdump_runner.py
│   ├── userctl_runner.py
│   └── validators.py
├── roles/
│   ├── admin_role.py
│   ├── operator_role.py
│   ├── root_role.py
│   └── viewer_role.py
├── webcli_server.py        # FastAPI + WebSocket entrypoint
├── config/
│   ├── pass.json
│   ├── setting.INI
│   └── users.json
└── scripts/
    ├── install.sh
    ├── uninstall.sh
    ├── update.sh
    └── setup_nginx_webcli</pre>

  <h2>⚙️ Setup & Installation</h2>
  <ol>
    <li>Clone the repo and enter it:
      <pre>git clone https://github.com/ASO8304/web-cli.git && cd webcli</pre>
    </li>
    <li>
      Navigate to the <code>scripts/</code> directory, make <code>install.sh</code> executable, and run it:
      <pre>
cd scripts
chmod +x install.sh
./install.sh</pre>
    </li>
    <li>
      After installation, check that the <code>webcli</code> service is running.
      Look for <code>active (running)</code> in green:
      <pre>
systemctl status webcli</pre>
    </li>
  </ol>

<h2>🚀 Usage</h2>

<p>You can use the Web CLI in two different ways:</p>

<h3>🔹 Option 1: Serve the Web UI via Nginx (Recommended)</h3>
<ol>
  <li>
    Ensure you are in the <code>client/</code> directory:
    <pre>
cd /path/to/WebCLI-main/client</pre>
  </li>

  <li>
    Run the provided setup script to configure Nginx and deploy the UI:<pre>
chmod +x setup_nginx_webcli.sh
sudo ./setup_nginx_webcli.sh</pre>
  </li>

  <li>
    Once complete, open your browser and navigate to:
    <pre>http://&lt;your-server-ip&gt;/webcli/</pre>
    <p>You’ll see the browser-based terminal. Log in and try commands:</p>
    <pre>
(root)$ help
(root)$ tcpdump
(root)$ userctl add</pre>
  </li>
</ol>

<h3>🔹 Option 2: Run the Web UI Manually (Direct File Access)</h3>
<ol>
  <li>
    Open <code>script.js</code> in your code editor and locate this section:
    <pre><code>
// let socket = new WebSocket("ws://192.168.56.105:12000/ws");
let loc = window.location;
let wsProtocol = loc.protocol === "https:" ? "wss" : "ws";
let socket = new WebSocket(`${wsProtocol}://${loc.host}/webcli/ws`);</code></pre>
    <p>Comment out the dynamic WebSocket line and uncomment the manual IP-based one:</p><pre><code>
let socket = new WebSocket("ws://192.168.56.105:12000/ws");
// let loc = window.location;
// let wsProtocol = loc.protocol === "https:" ? "wss" : "ws";
// let socket = new WebSocket(`${wsProtocol}://${loc.host}/webcli/ws`);</code></pre>
    <p>Replace the IP address with your server's actual IP if needed.</p>
  </li>

  <li>
    Open the HTML file directly in your browser:
    <pre>
xdg-open index.html</pre>
    <p>Or double-click <code>index.html</code> to open it manually.</p>
  </li>

  <li>
    You can now interact with the Web CLI directly over WebSocket:
    <pre>
(root)$ config
(root)$ tcpdump -i eth0
(root)$ userctl list</pre>
  </li>
</ol>


  <h2>🛡️ Security Notes</h2>
  <ul>
    <li>Only safe capabilities are granted via <code>CapabilityBoundingSet</code>.</li>
    <li>systemd enforces sandboxing with <code>PrivateTmp</code>, <code>ProtectSystem</code>, etc.</li>
    <li>TCP commands are validated and filtered server-side.</li>
    <li><code>/var/log/webcli</code> is isolated from users.</li>
  </ul>

  <h2>🔄 Customization</h2>
  <ul>
    <li>Add new tcpdump profiles in <code>core/tcpdump_runner.py</code></li>
    <li>Modify CSS in <code>client/style.css</code> for different terminal themes</li>
  </ul>

  <p>Enjoy your new browser-based CLI! 🚀</p>
</body>
</html>