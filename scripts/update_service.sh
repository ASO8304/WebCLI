#!/bin/bash

set -e

# --- Constants ---
SERVICE_NAME="webcli.service"
SYSTEMD_SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME"
LOCAL_BACKEND_DIR="./backend"

# --- Check service file existence ---
if [[ ! -f "$SYSTEMD_SERVICE_PATH" ]]; then
  echo "❌ Systemd service file not found at $SYSTEMD_SERVICE_PATH"
  exit 1
fi

# --- Extract WorkingDirectory ---
WORKING_DIR=$(grep -Po '^WorkingDirectory=\K.*' "$SYSTEMD_SERVICE_PATH" || true)
if [[ -z "$WORKING_DIR" ]]; then
  echo "❌ 'WorkingDirectory=' not found in $SYSTEMD_SERVICE_PATH"
  exit 1
fi

# --- Extract User (service owner) ---
SERVICE_USER=$(grep -Po '^User=\K.*' "$SYSTEMD_SERVICE_PATH" || true)
if [[ -z "$SERVICE_USER" ]]; then
  echo "❌ 'User=' not found in $SYSTEMD_SERVICE_PATH"
  exit 1
fi

echo "📁 Detected install path: $WORKING_DIR"
echo "👤 Service user: $SERVICE_USER"

# --- Ensure working directory exists ---
if [[ ! -d "$WORKING_DIR" ]]; then
  echo "❌ WorkingDirectory path does not exist: $WORKING_DIR"
  exit 1
fi

# --- Backup current backend ---
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${WORKING_DIR}_backup_$TIMESTAMP"
echo "📦 Backing up existing backend to: $BACKUP_DIR"
cp -r "$WORKING_DIR" "$BACKUP_DIR"

# --- Replace backend files ---
echo "♻️ Replacing backend with latest files..."
rm -rf "$WORKING_DIR"/*
cp -r "$LOCAL_BACKEND_DIR"/* "$WORKING_DIR"

# --- Set ownership ---
echo "🔑 Setting ownership to user: $SERVICE_USER"
chown -R "$SERVICE_USER:$SERVICE_USER" "$WORKING_DIR"

# --- Set permissions ---
echo "🔐 Applying file (644) and directory (755) permissions..."
find "$WORKING_DIR" -type f -exec chmod 644 {} \;
find "$WORKING_DIR" -type d -exec chmod 755 {} \;

# --- Restart service ---
echo "🔁 Restarting $SERVICE_NAME..."
systemctl daemon-reload
systemctl restart "$SERVICE_NAME"

# --- Check status ---
if systemctl is-active --quiet "$SERVICE_NAME"; then
  echo "✅ Service restarted and running successfully!"
else
  echo "❌ Failed to restart $SERVICE_NAME. Check logs:"
  echo "   journalctl -xe -u $SERVICE_NAME"
  exit 1
fi
