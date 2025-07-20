#!/bin/bash

set -e  # Exit on first error

# --- Configuration ---
APP_NAME="webcli_server"  # the actual Python file name without .py
USERNAME="webcli"
APP_DIR="/opt/webcli"
CONF_DIR="/etc/webcli"
LOG_DIR="/var/log/webcli"
SERVICE_FILE_NAME="webcli.service"
SERVICE_PATH="/etc/systemd/system/$SERVICE_FILE_NAME"
PORT="12000"

# --- Find the highest available Python 3.X version ---
find_python() {
  for version in 3.{13..8}; do
    if command -v python$version &>/dev/null; then
      echo "python$version"
      return 0
    fi
  done
  if command -v python3 &>/dev/null; then
    echo "python3"
    return 0
  fi
  return 1
}

PYTHON_BIN=$(find_python) || {
  echo "❌ No suitable Python 3.X interpreter found."
  exit 1
}
PYTHON_VERSION=$($PYTHON_BIN -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')

echo "✅ Found Python: $PYTHON_BIN (v$PYTHON_VERSION)"

# --- Ensure venv module is available ---
if ! "$PYTHON_BIN" -m venv --help &>/dev/null; then
  echo "🔧 Installing python${PYTHON_VERSION}-venv..."
  apt update
  apt install -y "python${PYTHON_VERSION}-venv"
fi

# --- Ensure tcpdump is installed ---
if ! command -v tcpdump &>/dev/null; then
  echo "🔧 Installing tcpdump..."
  apt update
  apt install -y tcpdump
fi

VENV_DIR="$APP_DIR/venv"

# --- Create a system user if not exists ---
echo "👤 Creating system user '$USERNAME'..."
id -u "$USERNAME" &>/dev/null || useradd --system -m -s /bin/nologin "$USERNAME"

# --- Create directories ---
echo "📁 Creating directories..."
mkdir -pv "$APP_DIR" "$CONF_DIR" "$LOG_DIR"
chown -R "$USERNAME:$USERNAME" "$APP_DIR" "$CONF_DIR" "$LOG_DIR"
chmod 750 "$APP_DIR" "$CONF_DIR" "$LOG_DIR"

# --- Create Python virtualenv ---
echo "🐍 Creating virtual environment..."
sudo -u "$USERNAME" "$PYTHON_BIN" -m venv "$VENV_DIR"

# --- Install required Python packages ---
echo "📦 Installing Python dependencies..."
sudo -u "$USERNAME" "$VENV_DIR/bin/pip" install --upgrade pip
sudo -u "$USERNAME" "$VENV_DIR/bin/pip" install fastapi "uvicorn[standard]"

# --- Copy backend code ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "📁 Copying backend project files..."
cp -rv "$SCRIPT_DIR/../backend/*" "$APP_DIR/"
chown -R "$USERNAME:$USERNAME" "$APP_DIR"

# --- Copy config files ---
if [ -d "$SCRIPT_DIR/../config" ]; then
  echo "⚙️ Copying configuration files to $CONF_DIR..."
  cp -rv "$SCRIPT_DIR/../config/"* "$CONF_DIR/"
  chown -R "$USERNAME:$USERNAME" "$CONF_DIR"
else
  echo "⚠️ Warning: No 'config/' directory found in project root."
fi

# --- Create systemd service file ---
echo "🛠️ Writing systemd service file..."
cat <<EOF > "$SERVICE_PATH"
[Unit]
Description=Web CLI Server (FastAPI)
After=network.target

[Service]
User=$USERNAME
Group=$USERNAME
WorkingDirectory=$APP_DIR/backend
ExecStart=$VENV_DIR/bin/uvicorn $APP_NAME:app --host 0.0.0.0 --port $PORT

AmbientCapabilities=CAP_NET_RAW CAP_NET_ADMIN CAP_NET_BIND_SERVICE
CapabilityBoundingSet=CAP_NET_RAW CAP_NET_ADMIN CAP_NET_BIND_SERVICE

ProtectSystem=full
ReadWritePaths=$CONF_DIR $LOG_DIR
ProtectHome=yes
NoNewPrivileges=true
PrivateTmp=false
PrivateDevices=false
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6 AF_NETLINK AF_PACKET

[Install]
WantedBy=multi-user.target
EOF

# --- Set permissions on the service file ---
chmod 644 "$SERVICE_PATH"
chown root:root "$SERVICE_PATH"

# --- Enable and start the service ---
echo "🚀 Enabling and starting service..."
systemctl daemon-reload
systemctl enable --now "$SERVICE_FILE_NAME"

# --- Check service status ---
if systemctl is-active --quiet "$SERVICE_FILE_NAME"; then
  echo "✅ WebCLI service is up and running!"
else
  echo "❌ Service failed to start. Check logs with: journalctl -xe -u $SERVICE_FILE_NAME"
  exit 1
fi
