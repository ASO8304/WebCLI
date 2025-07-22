#!/bin/bash

set -e

# --- Constants ---
SERVICE_NAME="webcli.service"
SYSTEMD_SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME"
LOCAL_BACKEND_DIR="./backend"

# --- Check if systemd service file exists ---
if [[ ! -f "$SYSTEMD_SERVICE_PATH" ]]; then
  echo "❌ Systemd service file not found at $SYSTEMD_SERVICE_PATH. Aborting."
  exit 1
fi

# --- Extract WorkingDirectory path from service file ---
WORKING_DIR=$(grep -Po '^WorkingDirectory=\K.*' "$SYSTEMD_SERVICE_PATH" || true)

if [[ -z "$WORKING_DIR" ]]; then
  echo "❌ Could not find 'WorkingDirectory=' in $SYSTEMD_SERVICE_PATH"
  exit 1
fi

echo "📁 Detected backend install path: $WORKING_DIR"

# --- Confirm backend exists at expected path ---
if [[ ! -d "$WORKING_DIR" ]]; then
  echo "❌ WorkingDirectory path does not exist: $WORKING_DIR"
  exit 1
fi

# --- Backup old backend files ---
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${WORKING_DIR}_backup_$TIMESTAMP"
echo "📦 Backing up existing backend to: $BACKUP_DIR"
cp -r "$WORKING_DIR" "$BACKUP_DIR"

# --- Replace backend with updated files ---
echo "♻️ Updating backend files from Git repo..."
rm -rf "$WORKING_DIR"/*
cp -r "$LOCAL_BACKEND_DIR"/* "$WORKING_DIR"

# --- Optional: Reset ownership to webcli user (optional, adjust if needed) ---
# chown -R webcli:webcli "$WORKING_DIR"

# --- Restart service ---
echo "🔁 Reloading systemd and restarting $SERVICE_NAME..."
systemctl daemon-reload
systemctl restart "$SERVICE_NAME"

# --- Check service status ---
if systemctl is-active --quiet "$SERVICE_NAME"; then
  echo "✅ Service restarted and running successfully!"
else
  echo "❌ Failed to restart $SERVICE_NAME. Check logs with:"
  echo "   journalctl -xe -u $SERVICE_NAME"
  exit 1
fi
