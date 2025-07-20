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
    └── uninstall.sh</pre>

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

<h3>🔹 Option 1: Open the HTML File Directly</h3>
<ol>
  <li>
    Copy the HTML (with its CSS & JS) client UI from the config directory to your home folder:
    <pre>
cp -ra /etc/webcli/config/ ~/webcli_ui
chown -R &lt;your_username&gt;: ~/webcli_ui
chmod -R 640 ~/webcli_ui
chmod 755 ~/webcli_ui</pre>
    <p>Replace <code>&lt;your_username&gt;</code> with your actual Linux username.</p>
  </li>

  <li>
    Open the HTML file using your browser:
    <pre>
xdg-open ~/webcli_ui/index.html</pre>
    <p>Or manually open it via your file manager.</p>
  </li>

  <li>
    You’ll see a browser-based Linux terminal UI. Log in and try:
    <pre>
(root)$ help
(root)$ tcpdump
(root)$ tcpdump http</pre>
  </li>
</ol>

<h3>🔹 Option 2: Serve the Web UI via Nginx (Recommended)</h3>
<ol>
  <li>Install Nginx:
    <pre>sudo apt update && sudo apt install nginx -y</pre>
  </li>

  <li>Copy the client files into the Nginx web root:
    <pre>
sudo mkdir -p /var/www/webcli
sudo cp -r /etc/webcli/config/* /var/www/webcli/
sudo chown -R www-data:www-data /var/www/webcli
sudo chmod -R 755 /var/www/webcli</pre>
  </li>

  <li>Edit the Nginx configuration:
    <pre>sudo nano /etc/nginx/sites-available/default</pre>
    Add this inside the <code>server {}</code> block:<pre>
location /cli/ {
    alias /var/www/webcli/;
    index index.html;
    try_files $uri $uri/ /index.html;
}</pre>
  </li>

  <li>Check and reload Nginx:
    <pre>
sudo nginx -t
sudo systemctl reload nginx</pre>
  </li>

  <li>
    Now visit <code>http://&lt;your-server-ip&gt;/cli/</code> in your browser.
    <br />
    You’ll see the Web CLI without needing to open the HTML manually.
  </li>
</ol>

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
    <li>Add new tcpdump profiles in <code>core/tcpdump.py</code></li>
    <li>Modify CSS in <code>client/style.css</code> for different terminal themes</li>
  </ul>

  <p>Enjoy your new browser-based CLI! 🚀</p>
</body>
</html>