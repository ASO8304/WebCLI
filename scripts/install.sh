#!/bin/bash
#
# Install WebCLI and register the systemd service
# ------------------------------------------------

set -e  # Exit immediately on any error

# ── Configurable constants ────────────────────────────────────────────────
APP_NAME="webcli_server"          # Python entry-point module (without .py)
USERNAME="webcli"                 # Dedicated system user
APP_DIR="/opt/webcli"             # Code + virtual-env location
CONF_DIR="/etc/webcli"            # Runtime config
LOG_DIR="/var/log/webcli"         # Log directory (optional)
SERVICE_FILE_NAME="webcli.service"
SERVICE_PATH="/etc/systemd/system/${SERVICE_FILE_NAME}"
PORT="12000"

# ── Helper: find the newest available python3.x ──────────────────────────
find_python() {
  for ver in 3.{13..8}; do
    command -v python$ver &>/dev/null && { echo python$ver; return; }
  done
  command -v python3 && { echo python3; return; }
  return 1
}
PYTHON_BIN=$(find_python) || { echo "❌ No Python 3.x found."; exit 1; }
PYTHON_VERSION=$($PYTHON_BIN - <<'PY' ; import sys,platform ; print(f"{sys.version_info.major}.{sys.version_info.minor}") ; PY)
echo "✅ Using $PYTHON_BIN  (v$PYTHON_VERSION)"

# Ensure python-venv package exists
if ! "$PYTHON_BIN" -m venv --help &>/dev/null; then
  echo "🔧 Installing python${PYTHON_VERSION}-venv ..."
  apt update && apt install -y "python${PYTHON_VERSION}-venv"
fi

# Ensure tcpdump is present (for packet capture)
command -v tcpdump &>/dev/null || { echo "🔧 Installing tcpdump ..."; apt update && apt install -y tcpdump; }

VENV_DIR="${APP_DIR}/venv"

# ── Create system user ────────────────────────────────────────────────────
echo "👤 Ensuring system user '$USERNAME' …"
id -u "$USERNAME" &>/dev/null || useradd --system -m -s /usr/sbin/nologin "$USERNAME"

# ── Create directories and set ownership ─────────────────────────────────
echo "📁 Creating application directories …"
mkdir -pv "$APP_DIR" "$CONF_DIR" "$LOG_DIR"
chown -R "$USERNAME:$USERNAME" "$APP_DIR" "$CONF_DIR" "$LOG_DIR"
chmod 750 "$APP_DIR" "$CONF_DIR" "$LOG_DIR"

# ── Virtual-env and dependencies ─────────────────────────────────────────
echo "🐍 Building virtual environment …"
sudo -u "$USERNAME" "$PYTHON_BIN" -m venv "$VENV_DIR"

echo "📦 Installing Python dependencies …"
sudo -u "$USERNAME" "$VENV_DIR/bin/pip" install --upgrade pip
sudo -u "$USERNAME" "$VENV_DIR/bin/pip" install fastapi "uvicorn[standard]"

# ── Copy backend code / config ───────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "📁 Deploying backend files …"
cp -rv "$SCRIPT_DIR/../backend/"* "$APP_DIR/"
chown -R "$USERNAME:$USERNAME" "$APP_DIR"

if [ -d "$SCRIPT_DIR/../config" ]; then
  echo "⚙️  Deploying config files …"
  cp -rv "$SCRIPT_DIR/../config/"* "$CONF_DIR/"
  chown -R "$USERNAME:$USERNAME" "$CONF_DIR"
else
  echo "⚠️  No project-level 'config/' directory found."
fi

# ── Create / update systemd unit ─────────────────────────────────────────
echo "🛠️  Writing systemd unit …"
cat > "$SERVICE_PATH" <<EOF
[Unit]
Description=WebCLI Backend (FastAPI / Uvicorn)
After=network.target

[Service]
User=$USERNAME
Group=$USERNAME
WorkingDirectory=$APP_DIR
Environment=PYTHONPATH=$APP_DIR
ExecStart=$VENV_DIR/bin/uvicorn $APP_NAME:app --host 0.0.0.0 --port $PORT

# ── Capabilities:
#   • tcpdump   → CAP_NET_RAW CAP_NET_ADMIN CAP_NET_BIND_SERVICE
#   • sudo      → CAP_SETUID  CAP_SETGID  CAP_AUDIT_WRITE
CapabilityBoundingSet=CAP_NET_RAW CAP_NET_ADMIN CAP_NET_BIND_SERVICE \\
                      CAP_SETUID CAP_SETGID CAP_AUDIT_WRITE
AmbientCapabilities=CAP_NET_RAW CAP_NET_ADMIN CAP_NET_BIND_SERVICE

# ── Sandboxing that *still* allows sudo
NoNewPrivileges=false
ProtectSystem=off
ProtectHome=yes
PrivateTmp=true
PrivateDevices=true
ReadWritePaths=$CONF_DIR $LOG_DIR
InaccessiblePaths=/root
LockPersonality=true

# Resilience
Restart=on-failure
RestartSec=5
LimitNOFILE=16384

[Install]
WantedBy=multi-user.target
EOF

chmod 644 "$SERVICE_PATH"
chown root:root "$SERVICE_PATH"

# ── sudoers whitelist for controlled privilege ───────────────────────────
SUDOERS_FILE="/etc/sudoers.d/webcli"
echo "🛡️  Installing sudo whitelist …"
cat > "$SUDOERS_FILE" <<'EOF'
# /etc/sudoers.d/webcli
# Allow the 'webcli' user to run *only* these commands without password.
webcli ALL=(ALL) NOPASSWD: /bin/systemctl restart *, /bin/systemctl status *, /usr/sbin/tcpdump
EOF
chmod 440 "$SUDOERS_FILE"

# ── Enable + start service ───────────────────────────────────────────────
echo "🚀 Enabling and starting webcli.service …"
systemctl daemon-reload
systemctl enable --now "$SERVICE_FILE_NAME"

if systemctl is-active --quiet "$SERVICE_FILE_NAME"; then
  echo "✅ WebCLI service is running."
else
  echo "❌ Service failed. Inspect with: journalctl -xe -u $SERVICE_FILE_NAME"
  exit 1
fi
