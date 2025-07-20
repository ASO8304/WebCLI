#!/bin/bash

set -e  # Exit on error

# --- Configuration ---
APP_NAME="webcli_service"
USERNAME="webcli"
APP_DIR="/opt/webcli"
CONF_DIR="/etc/webcli"
LOG_DIR="/var/log/webcli"
VENV_DIR="$APP_DIR/venv"
SERVICE_FILE_NAME="webcli.service"
PYTHON_BIN="/usr/bin/python3.10"  # Adjust if needed

# --- Validate Python binary exists ---
if [ ! -x "$PYTHON_BIN" ]; then
  echo "❌ Python binary not found at $PYTHON_BIN"
  exit 1
fi

# --- Create a new system user ---
echo "Creating user '$USERNAME' (if not exists)..."
id -u "$USERNAME" &>/dev/null || useradd --system -m -s /bin/nologin "$USERNAME"

# --- Create application directories ---
echo "Creating application, config, and log directories..."
mkdir -pv "$APP_DIR" "$CONF_DIR" "$LOG_DIR"

# --- Set ownership and permissions BEFORE venv creation ---
echo "Setting ownership and permissions on app, config, and log directories..."
chown -R "$USERNAME:$USERNAME" "$APP_DIR" "$CONF_DIR" "$LOG_DIR"
chmod 750 "$APP_DIR" "$CONF_DIR" "$LOG_DIR"

# Ensure full write and execute for user recursively on APP_DIR before venv
chmod -R u+rwX "$APP_DIR"

# --- Remove any existing virtual environment to avoid permission issues ---
if [ -d "$VENV_DIR" ]; then
  echo "Removing existing virtual environment at $VENV_DIR"
  rm -rf "$VENV_DIR"
fi

# --- Set up Python virtual environment ---
echo "Creating virtual environment..."
sudo -u "$USERNAME" "$PYTHON_BIN" -m venv "$VENV_DIR"

# --- Activate venv and install dependencies ---
echo "Installing Python packages..."
sudo -u "$USERNAME" "$VENV_DIR/bin/pip" install --upgrade pip
sudo -u "$USERNAME" "$VENV_DIR/bin/pip" install fastapi "uvicorn[standard]"

# --- Copy project files ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Copying webcli service files to $APP_DIR..."
cp -rv "$SCRIPT_DIR/../backend" "$APP_DIR/"
chown -R "$USERNAME:$USERNAME" "$APP_DIR"

# --- Set ownership for config and log directories again (just in case) ---
echo "Ensuring ownership of configuration and log directories..."
chown -R "$USERNAME:$USERNAME" "$CONF_DIR" "$LOG_DIR"

# --- Create systemd service file ---
echo "Creating systemd service file..."
cat <<EOF > /etc/systemd/system/$SERVICE_FILE_NAME
[Unit]
Description=Web CLI Server
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

# --- Set ownership and permissions for service file ---
echo "Setting permissions for systemd service file..."
chown root:root /etc/systemd/system/$SERVICE_FILE_NAME
chmod 644 /etc/systemd/system/$SERVICE_FILE_NAME

# --- Reload systemd and start service ---
echo "Reloading systemd and enabling service..."
systemctl daemon-reload
systemctl enable --now "$SERVICE_FILE_NAME"

# --- Check service status ---
if ! systemctl is-active --quiet "$SERVICE_FILE_NAME"; then
  echo "❌ Failed to start $SERVICE_FILE_NAME. Check logs:"
  journalctl -xe -u "$SERVICE_FILE_NAME"
  exit 1
fi

echo "✅ Setup complete. WebCLI service is now running!"
