#!/bin/bash

set -e  # Exit on error

# --- Configuration ---
APP_NAME="webcli_server"
USERNAME="webcli"
APP_DIR="/opt/webcli"
LOG_DIR="/var/log/webcli"
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
Description=Web CLI Server                 # Description of the service
After=network.target                       # Ensure the service starts after the network is up

[Service]
User=$USERNAME                             # User that will run the service
Group=$USERNAME                            # Group under which the service runs
WorkingDirectory=$APP_DIR                  # Working directory where the app resides
ExecStart=$VENV_DIR/bin/uvicorn $APP_NAME:app --host 0.0.0.0 --port 8000
                                           # Command to start the FastAPI app using Uvicorn

# --- Capabilities section ---

AmbientCapabilities=CAP_NET_RAW CAP_NET_ADMIN CAP_NET_BIND_SERVICE
                                           # Grants required capabilities to the service:
                                           # - CAP_NET_RAW: Required by tcpdump for raw packet capture
                                           # - CAP_NET_ADMIN: For more advanced network access (e.g., interface config, capture filtering)
                                           # - CAP_NET_BIND_SERVICE: Allows binding to ports <1024 (e.g., port 80/443 if needed)

CapabilityBoundingSet=CAP_NET_RAW CAP_NET_ADMIN CAP_NET_BIND_SERVICE
                                           # Restricts the service to only the listed capabilities (dropping all others)

# --- Security hardening section ---

ProtectSystem=full                         # Mounts /usr, /boot, and /etc as read-only to protect system integrity
ReadWritePaths=/etc/webcli                 # Allows write access to this path (used for app logs/config if needed)
ProtectHome=yes                            # Prevents access to users' home directories
NoNewPrivileges=true                       # Ensures the process and children can't gain new privileges (recommended for security)

PrivateTmp=false                           # Disable private /tmp to allow packet tools like tcpdump to work properly
PrivateDevices=false                       # Required to access real network devices (e.g., eth0, wlo1) for packet capture

RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6 AF_NETLINK AF_PACKET
                                           # Restricts socket creation to only required families:
                                           # - AF_UNIX: Local IPC
                                           # - AF_INET/AF_INET6: IPv4/IPv6 communication
                                           # - AF_NETLINK: For kernel networking messages
                                           # - AF_PACKET: Required for raw socket access used by tcpdump

[Install]
WantedBy=multi-user.target                 # Makes the service start at boot under standard multi-user mode
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

