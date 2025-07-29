#!/bin/bash

set -e  # Exit on error

# --- Configuration ---
APP_NAME="webcli_server"
USERNAME="webcli"
APP_DIR="/opt/webcli"
CONF_DIR="/etc/webcli"
LOG_DIR="/var/log/webcli"
SERVICE_FILE_NAME="webcli.service"
SERVICE_PATH="/etc/systemd/system/$SERVICE_FILE_NAME"
SUDOERS_FILE="/etc/sudoers.d/webcli"

echo "🔧 Starting WebCLI uninstallation..."

# --- Stop and disable the systemd service ---
if systemctl list-units --full -all | grep -q "$SERVICE_FILE_NAME"; then
  echo "Stopping and disabling systemd service..."
  systemctl stop "$SERVICE_FILE_NAME" || true
  systemctl disable "$SERVICE_FILE_NAME" || true
  systemctl daemon-reload
fi

# --- Remove systemd service file ---
if [ -f "$SERVICE_PATH" ]; then
  echo "Removing systemd service file..."
  rm -f "$SERVICE_PATH"
  systemctl daemon-reload
fi

# --- Remove application files ---
if [ -d "$APP_DIR" ]; then
  echo "Removing application directory at $APP_DIR..."
  rm -rf "$APP_DIR"
fi

# --- Remove configuration and log directories ---
if [ -d "$CONF_DIR" ]; then
  echo "Removing configuration directory at $CONF_DIR..."
  rm -rf "$CONF_DIR"
fi

if [ -d "$LOG_DIR" ]; then
  echo "Removing log directory at $LOG_DIR..."
  rm -rf "$LOG_DIR"
fi

# --- Delete the system user ---
if id "$USERNAME" &>/dev/null; then
  echo "Deleting system user '$USERNAME'..."
  userdel -r "$USERNAME" || true
fi

# --- Delete the sudoers file ---
if [ -f "$SUDOERS_FILE" ]; then
    echo "🧽 Removing sudoers entry..."
    sudo rm -f "$SUDOERS_FILE"
    echo "✅ Removed $SUDOERS_FILE"
else
    echo "ℹ️ No sudoers file found at $SUDOERS_FILE"
fi


echo "✅ Uninstallation complete. WebCLI has been removed."
