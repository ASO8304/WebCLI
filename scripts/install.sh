#!/bin/bash
# Install WebCLI and register the systemd service

set -e

# Constants
APP_NAME="webcli_server"
USERNAME="webcli"
PCAP_USER="pcap"
APP_DIR="/opt/webcli"
CONF_DIR="/etc/webcli"
LOG_DIR="/var/log/webcli"
SERVICE_FILE_NAME="webcli.service"
SERVICE_PATH="/etc/systemd/system/${SERVICE_FILE_NAME}"
WRAPPER_PATH="/usr/local/sbin/webcli-tcpdump.sh"
PORT="12000"

# Find the newest available python3.x
find_python() {
  for ver in 3.{13..8}; do
    command -v python$ver &>/dev/null && { echo python$ver; return; }
  done
  command -v python3 && { echo python3; return; }
  return 1
}
PYTHON_BIN=$(find_python) || { echo "No Python 3.x found."; exit 1; }
PYTHON_VERSION=$($PYTHON_BIN -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Using $PYTHON_BIN (v$PYTHON_VERSION)"

# Ensure python-venv is available
if ! "$PYTHON_BIN" -m venv --help &>/dev/null; then
  echo "Installing python${PYTHON_VERSION}-venv ..."
  apt update && apt install -y "python${PYTHON_VERSION}-venv"
fi

# Ensure tcpdump exists
command -v tcpdump &>/dev/null || {
  echo "Installing tcpdump ..."
  apt update && apt install -y tcpdump
}

VENV_DIR="${APP_DIR}/venv"

# Create system users
echo "Creating system user '$USERNAME' ..."
id -u "$USERNAME" &>/dev/null || useradd --system -m -s /usr/sbin/nologin "$USERNAME"

echo "Creating system user '$PCAP_USER' ..."
id -u "$PCAP_USER" &>/dev/null || useradd --system -s /usr/sbin/nologin "$PCAP_USER"

# Create necessary directories
echo "Creating application directories ..."
mkdir -pv "$APP_DIR" "$CONF_DIR" "$LOG_DIR"
chown -R "$USERNAME:$USERNAME" "$APP_DIR" "$CONF_DIR"
chown root:$PCAP_USER "$LOG_DIR"
chmod 770 "$LOG_DIR"
usermod -a -G $PCAP_USER $USERNAME

# Create tcpdump wrapper script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Deploying tcpdump wrapper ..."
if [ -f "$SCRIPT_DIR/tcpdump_wrapper" ]; then
  cp "$SCRIPT_DIR/tcpdump_wrapper" "$WRAPPER_PATH"
  chown root:$PCAP_USER "$WRAPPER_PATH"
  chmod 750 "$WRAPPER_PATH"
else
  echo "Warning: tcpdump_wrapper file not found in $SCRIPT_DIR"
fi

if [ -f "$SCRIPT_DIR/tcpdump_wrapper" ]; then
  rm -f "$SCRIPT_DIR/tcpdump_wrapper"
fi 

# Create virtual environment and install dependencies
echo "Building virtual environment ..."
sudo -u "$USERNAME" "$PYTHON_BIN" -m venv "$VENV_DIR"

echo "Installing Python dependencies ..."
sudo -u "$USERNAME" "$VENV_DIR/bin/pip" install --upgrade pip
sudo -u "$USERNAME" "$VENV_DIR/bin/pip" install -r requirements.txt

# Deploy backend and config
echo "Deploying backend files ..."
cp -rv "$SCRIPT_DIR/../backend/"* "$APP_DIR/"
chown -R "$USERNAME:$USERNAME" "$APP_DIR"

if [ -d "$SCRIPT_DIR/../config" ]; then
  echo "Deploying config files ..."
  cp -rv "$SCRIPT_DIR/../config/"* "$CONF_DIR/"
  chown -R "$USERNAME:$USERNAME" "$CONF_DIR"
  chmod 600  "$CONF_DIR""/*.json"
else
  echo "Warning: No 'config/' directory found."
fi

# Create systemd unit (exact as requested)
echo "Writing systemd unit ..."
cat > "$SERVICE_PATH" <<EOF
[Unit]
Description=WebCLI backend (FastAPI + Uvicorn)
After=network.target
Documentation=https://github.com/ASO8304/WebCLI

[Service]
User=$USERNAME
Group=$USERNAME
WorkingDirectory=$APP_DIR
Environment=PYTHONPATH=$APP_DIR
ExecStart=$VENV_DIR/bin/uvicorn $APP_NAME:app --host 127.0.0.1 --port $PORT

# --- Capabilities ----------------------------------
# Needed by:
#   · tcpdump  →  CAP_NET_RAW  CAP_NET_ADMIN
#   · sudo     →  CAP_SETUID   CAP_SETGID     CAP_AUDIT_WRITE
CapabilityBoundingSet=CAP_NET_RAW CAP_NET_ADMIN CAP_SETUID  CAP_SETGID  CAP_AUDIT_WRITE
AmbientCapabilities=CAP_NET_RAW CAP_NET_ADMIN


# --- Sandboxing that still permits sudo ------------
NoNewPrivileges=false         # must remain false for sudo
ProtectSystem=off             # keep root FS writable (sudo/systemctl)
ProtectHome=yes               # hide /home and /root by default
PrivateTmp=true               # isolated /tmp and /var/tmp
PrivateDevices=true           # minimal /dev (network still works)
ReadWritePaths=$CONF_DIR $LOG_DIR

# Extra hygiene that does NOT force NoNewPrivs=true
InaccessiblePaths=/root       # prevent accidental access to /root
LockPersonality=true          # block personality(2) trickery

# Resource limits / resilience

# Cap CPU usage to 50% of one CPU
CPUQuota=50%

# Hard memory cap (process killed if exceeded)
MemoryMax=500M

# Soft memory cap (preferred target, may exceed temporarily)
MemoryHigh=300M

# Deny swap usage (optional, stricter isolation)
MemorySwapMax=0

# Max open files
LimitNOFILE=8192

# Max processes the service can spawn
TasksMax=200

# Kill service if startup hangs
TimeoutStartSec=30s

# Kill service if stop takes too long
TimeoutStopSec=20s

Restart=on-failure

RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

chmod 644 "$SERVICE_PATH"
chown root:root "$SERVICE_PATH"

# Create sudoers whitelist
SUDOERS_FILE="/etc/sudoers.d/webcli"
echo "Installing sudoers file ..."
cat > "$SUDOERS_FILE" <<'EOF'
# /etc/sudoers.d/webcli

# systemctl policies
webcli ALL=(root) NOPASSWD: /bin/systemctl restart *
webcli ALL=(root) NOPASSWD: /bin/systemctl status *

# tcpdump policies
webcli ALL=(root) NOPASSWD: /usr/local/sbin/webcli-tcpdump.sh *
EOF
chmod 440 "$SUDOERS_FILE"

# Enable and start service
echo "Enabling and starting service ..."
systemctl daemon-reexec
systemctl daemon-reload
systemctl enable --now "$SERVICE_FILE_NAME"

if systemctl is-active --quiet "$SERVICE_FILE_NAME"; then
  echo "WebCLI service is running."
else
  echo "Service failed. Use: journalctl -xe -u $SERVICE_FILE_NAME"
  exit 1
fi