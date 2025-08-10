<!DOCTYPE html>
<html lang="en">
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
    <li>🐾 <strong>Secure tcpdump:</strong> Direct `/usr/sbin|/usr/bin/tcpdump` with Linux capabilities</li>
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
│   ├── autocomplete_handler.py  # Role-based command suggestions for autocomplete
│   ├── command_control.py       # Dispatches and manages config-related CLI commands
│   ├── config_manager.py        # Lists and edits INI/JSON config files interactively
│   ├── process_manager.py       # Tracks and controls long-running subprocesses (interrupt, etc.)
│   ├── systemctl_runner.py      # Safely handles systemctl commands
│   ├── tcpdump_runner.py        # Validates and runs secure tcpdump subprocesses (whitelisted flags)
│   ├── userctl_runner.py        # Add, edit, delete, list users and roles
│   ├── validators.py            # Central router for per-file validators (+ helpers)
│   └── validators_files/        # One module per config file (your custom validators live here)
│       └── __init__.py
├── roles/
│   ├── admin_role.py
│   ├── operator_role.py
│   └── viewer_role.py
├── webcli_server.py        # FastAPI + WebSocket entrypoint
├── config/
│   ├── pass.json
│   └── users.json
└── scripts/
    ├── install.sh
    ├── uninstall.sh
    ├── update.sh
    └── setup_nginx_webcli
  </pre>

  <h2>⚙️ Setup & Installation</h2>
  <ol>
    <li>Clone the repo and enter it:
      <pre>git clone https://github.com/ASO8304/WebCli.git && cd WebCli</pre>
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
      Ensure you are in the <code>scripts/</code> directory:
      <pre>
cd /path/to/WebCli/scripts</pre>
    </li>
    <li>
      Run the provided setup script to configure Nginx and deploy the UI:
      <pre>
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
(root)$ userctl add 
(root)$ systemctl restart</pre>
    </li>
  </ol>

  <h3>🔹 Option 2: Run the Web UI Manually (Direct File Access)</h3>
  <ol>
    <li>
      Open <code>client/script.js</code> and locate the WebSocket section:
      <pre><code>// let socket = new WebSocket("ws://192.168.56.105:12000/ws");
let loc = window.location;
let wsProtocol = loc.protocol === "https:" ? "wss" : "ws";
let socket = new WebSocket(`${wsProtocol}://${loc.host}/webcli/ws`);</code></pre>
      <p>To point at a fixed server during development, you may swap to:</p>
      <pre><code>let socket = new WebSocket("ws://192.168.56.105:12000/ws");</code></pre>
    </li>
    <li>
      Open the HTML file directly in your browser:
      <pre>xdg-open client/index.html</pre>
    </li>
    <li>
      Interact with the Web CLI:
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

  <h3>✅ How validation works (per file → per section → per key)</h3>
  <p>
    Each config file has its own Python module under 
    <code>backend/core/validators_files/</code>. For every parameter you want to control,
    define exactly two functions:
  </p>
  <ul>
    <li><code>help_&lt;Section&gt;_&lt;Key&gt;() -&gt; str</code>: short guide shown to the user when they type <code>edit &lt;n&gt;</code></li>
    <li><code>validate_&lt;Section&gt;_&lt;Key&gt;(value) -&gt; bool | (bool, str)</code>: returns True/False; optional custom error string</li>
  </ul>
  <p>
    Function names can be written using your original INI casing (e.g. <code>CatSleep</code>, <code>Sleep</code>) 
    or all lowercase—both are accepted. Non-alphanumerics become underscores. Example keys like 
    <code>cat_height</code> remain <code>cat_height</code> in function names.
  </p>

  <h4>1) Create a per-file validator module</h4>
  <p>
    Example for a file named <code>settings.test</code>:
  </p>
  <pre><code>
  
# backend/core/validators_files/settings_test.py

## [CatSleep] Sleep in {yes, trying, no}
def help_CatSleep_Sleep():
    return "Cat sleep state. Allowed values: yes, trying, no."

def validate_CatSleep_Sleep(value: str):
    allowed = {"yes", "trying", "no"}
    v = str(value).strip().lower()
    return v in allowed

## [ClockSleep] Sleep in {0, 2, 4}
def help_ClockSleep_Sleep():
    return "Clock sleep mode. Allowed numeric codes: 0, 2, 4."

def validate_ClockSleep_Sleep(value: str):
    allowed = {"0", "2", "4"}
    v = str(value).strip()
    return v in allowed


</code></pre>

  <h4>2) Register the file in the central router</h4>
  <p>
    Map your file name to the module path in <code>backend/core/validators.py</code>:
  </p>
  <pre><code># backend/core/validators.py
FILE_MODULES = {
    "settings.ini": "core.validators_files.settings_ini",
    # Add more files here:
    # "example.ini": "core.validators_files.example_ini",
}</code></pre>

  <h4>3) Ensure the editor knows about your file</h4>
  <p>
    Add the file to the config menu in <code>backend/core/config_manager.py</code>:
  </p>
  <pre><code># backend/core/config_manager.py
CONFIG_MAP = {
    "settings.ini": "edit_ini_format",
    "example.ini": "edit_ini_format",   # if another INI
    # "custom_config.json": "edit_custom_json",
}</code></pre>
  <p>
    The INI editor (<code>edit_ini_format</code>) will:
  </p>
  <ul>
    <li>Show section list and keys</li>
    <li>When you type <code>edit &lt;n&gt;</code>, it calls <code>help_&lt;Section&gt;_&lt;Key&gt;()</code> and displays your help string</li>
    <li>On submit, it calls <code>validate_&lt;Section&gt;_&lt;Key&gt;(value)</code> to accept or reject</li>
  </ul>

  <h4>4) Naming rules & flexibility</h4>
  <ul>
    <li>Case preserved or lowercase both work:
      <code>validate_CatSleep_Sleep</code> and <code>validate_catsleep_sleep</code> are both valid.
    </li>
    <li>Characters other than letters/digits become underscores: 
      key <code>cat_height</code> → function suffix <code>cat_height</code>.
    </li>
    <li>If a function returns <code>(False, "custom error")</code>, that message is shown to the user;
      otherwise the router falls back to your <code>help_...</code> text.</li>
  </ul>

  <h3>➕ Adding a brand-new config file</h3>
  <ol>
    <li>Place the file under <code>/etc/webcli</code> (default <em>CONFIG_DIR</em>).</li>
    <li>Create <code>backend/core/validators_files/&lt;yourfile&gt;.py</code> with your <code>help_...</code> and <code>validate_...</code> functions (see examples above).</li>
    <li>Register it in <code>backend/core/validators.py</code> → <code>FILE_MODULES</code>.</li>
    <li>Add it to <code>backend/core/config_manager.py</code> → <code>CONFIG_MAP</code> with the appropriate handler (usually <code>edit_ini_format</code> for INI files).</li>
    <li>Use the CLI:
      <pre>
(admin)$ config
📄 Available config files:
1. settings.ini
2. yourfile.ini
...
      </pre>
    </li>
  </ol>

  <h3>🧰 Useful helpers (optional)</h3>
  <p>You can import basic validators from <code>core.validators</code> if you prefer:</p>
  <pre><code>from core.validators import validate_boolean, validate_integer, validate_ip, EnumValidator

def help_Network_EnableIPv6(): return "Enable IPv6: true or false."
def validate_Network_EnableIPv6(v): return validate_boolean(v)

def help_Network_Mode(): return "Mode: auto, manual."
def validate_Network_Mode(v): return EnumValidator({"auto","manual"})(v)
</code></pre>

  <h3>🐞 Troubleshooting</h3>
  <ul>
    <li><strong>“No validator for [Section].Key”</strong> → Check your function name matches the section/key (underscores for non-alphanumerics) and that the file is registered in <code>FILE_MODULES</code>.</li>
    <li><strong>Help not shown</strong> → Make sure you implemented <code>help_&lt;Section&gt;_&lt;Key&gt;</code> and it returns a string.</li>
    <li><strong>Module not loaded</strong> → Ensure <code>backend/core/validators_files/__init__.py</code> exists and Python path matches <code>core.validators_files.&lt;module&gt;</code>.</li>
  </ul>

  <p>Enjoy your new browser-based CLI! 🚀</p>
</body>
</html>
