#!/bin/bash

set -e  # Exit on error

# --- Configuration ---
APP_NAME="webcli_service"
USERNAME="webcli"
APP_DIR="/opt/webcli"
CONF_DIR="/etc/webcli"
LOG_DIR="/var/log/webcli"
SERVICE_FILE_NAME="webcli.service"

# --- Function to find the highest available Python 3.X version ---
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

# --- Detect Python binary ---
PYTHON_BIN=$(find_python) || {
  echo "❌ No compatible Python 3.x interpreter found (>=3.8 required)."
  exit 1
}

PYTHON_VERSION=$($PYTHON_BIN -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✅ Using Python: $PYTHON_BIN (version $PYTHON_VERSION)"

# --- Ensure pythonX.Y-venv is installed ---
if ! "$PYTHON_BIN" -m venv --help &>/dev/null; then
  echo "⚠️ 'venv' module is missing for Python $PYTHON_VERSION. Attempting to install..."
  apt update
  apt install -y "python${PYTHON_VERSION}-venv" || {
    echo "❌ Failed to install python${PYTHON_VERSION}-venv. Please check your package sources."
    exit 1
  }
fi

# --- Define virtualenv path after Python detection ---
VENV_DIR="$APP_DIR/venv"

# --- Create a new system user if needed ---
echo "Creating user '$USERNAME' (if not exists)..."
id -u "$USERNAME" &>/dev/null || useradd --system -m -s /bin/nologin "$USERNAME"

# --- Create necessary directories ---
echo "Creating application, config, and log directories..."
mkdir -pv "$APP_DIR" "$CONF_DIR" "$LOG_DIR"
chown -R "$USERNAME:$USERNAME" "$APP_DIR" "$CONF_DIR" "$LOG_DIR"
chmod 750 "$APP_DIR" "$CONF_DIR" "$LOG_DIR"
chmod -R u+rwX "$APP_DIR"

# --- Remove existing virtual environment (if any) ---
if [ -d "$VENV_DIR" ]; then
  echo "Removing old virtual environment..."
  rm -rf "$VENV_DIR"
fi

# --- Create virtual environment ---
echo "Creating virtual environment with $PYTHON_BIN..."
sudo -u "$USERNAME" "$PYTHON_BIN" -m venv "$VENV_DIR"

# --- Install Python dependencies ---
echo "Installing Python packages into virtualenv..."
sudo -u "$USERNAME" "$VENV_DIR/bin/pip" install --upgrade pip
sudo -u "$USERNAME" "$VENV_DIR/bin/pip" install fastapi "uvicorn[standard]"

# --- Copy backend application code ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Copying backend files to $APP_DIR..."
cp -rv "$SCRIPT_DIR/../backend" "$APP_DIR/"
chown -R "$USERNAME:$USERNAME" "$APP_DIR"

# --- Create systemd service file ---
echo "Creating systemd service file at /etc/systemd/system/$SERVICE_FILE_NAME"
cat <<EOF > /etc/systemd/system/$SERVICE_FILE_NAME
[Unit]
Description=Web CLI Service
After=network.target

[Service]
User=$USERNAME
Group=$USERNAME
WorkingDirectory=$APP_DIR/backend
ExecStart=$VENV_DIR/bin/uvicorn $APP_NAME:app --host 0.0.0.0 --port 8000

AmbientCapabilities=CAP_NET_RAW CAP_NET_ADMIN CAP_NET_BIND_SERVICE
CapabilityBoundingSet=CAP_NET_RAW CAP_NET_ADMIN CAP_NET_BIND_SERVICE

ProtectSystem=full
ReadWritePaths=/etc/webcli /var/log/webcli
ProtectHome=yes
NoNewPrivileges=true
PrivateTmp=false
PrivateDevices=false
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6 AF_NETLINK AF_PACKET

[Install]
WantedBy=multi-user.target
EOF

# --- Set correct permissions for systemd file ---
chown root:root /etc/systemd/system/$SERVICE_FILE_NAME
chmod 644 /etc/systemd/system/$SERVICE_FILE_NAME

# --- Reload systemd and enable/start the service ---
echo "Reloading systemd and starting the service..."
systemctl daemon-reload
systemctl enable --now "$SERVICE_FILE_NAME"

# --- Confirm service status ---
if systemctl is-active --quiet "$SERVICE_FILE_NAME"; then
  echo "✅ WebCLI service is running!"
else
  echo "❌ Failed to start service. Check logs with: journalctl -xe -u $SERVICE_FILE_NAME"
  exit 1
fi
