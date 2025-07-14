#!/bin/bash

set -e  # Exit on error

# --- Configuration ---
APP_NAME="web_cli_server"
USERNAME="webcli"
APP_DIR="/opt/webcli"
VENV_DIR="$APP_DIR/venv"
SERVICE_FILE_NAME="webcli.service"
SOURCE_FILES="web_cli_server.py command_processor.py"
PYTHON_BIN="/usr/bin/python3.10"  # Adjust if needed

# --- Create a new system user ---
echo "Creating user '$USERNAME' (if not exists)..."
id -u $USERNAME &>/dev/null || useradd -m -s /bin/nologin $USERNAME

# --- Create application directories ---
echo "Creating application directory at '$APP_DIR'..."
mkdir -p "$APP_DIR"
chown -R $USERNAME:$USERNAME "$APP_DIR"

# --- Set ownership for created directories ---
echo "🔐 Setting ownership of $APP_DIR to '$USERNAME:$USERNAME'..."
chown -R $USERNAME:$USERNAME "$APP_DIR"

# --- Set up Python virtual environment ---
echo "Creating virtual environment..."
sudo -u $USERNAME $PYTHON_BIN -m venv "$VENV_DIR"

# --- Activate venv and install dependencies ---
echo "Installing Python packages..."
sudo -u $USERNAME "$VENV_DIR/bin/pip" install --upgrade pip
sudo -u $USERNAME "$VENV_DIR/bin/pip" install fastapi "uvicorn[standard]"

# --- Copy project files ---
echo "📂 Copying FastAPI server files to $APP_DIR..."
cp $SOURCE_FILES "$APP_DIR/"
chown -R $USERNAME:$USERNAME "$APP_DIR"

# --- Create systemd service file ---
echo "Creating systemd service..."
cat <<EOF > /etc/systemd/system/$SERVICE_FILE_NAME
[Unit]
Description=Web CLI FastAPI WebSocket Service
After=network.target

[Service]
User=$USERNAME
WorkingDirectory=$APP_DIR
ExecStart=$VENV_DIR/bin/uvicorn $APP_NAME:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF

# --- Set ownership and permissions for service file ---
echo "Setting correct permissions for service file..."
chown $USERNAME:$USERNAME /etc/systemd/system/$SERVICE_FILE_NAME
chmod 644 /etc/systemd/system/$SERVICE_FILE_NAME

# --- Reload systemd and start service ---
echo "Starting service..."
systemctl daemon-reexec
systemctl daemon-reload
systemctl enable $SERVICE_FILE_NAME
systemctl start $SERVICE_FILE_NAME

echo "Setup complete. WebCLI is now running!"

